#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   🗓️  CALENDAR MANAGER  —  GenAI Agent                       ║
║   Outlook-style | Leave Management | Meeting Scheduling      ║
║   Powered by Gemini AI  ×  Google Calendar                   ║
╚══════════════════════════════════════════════════════════════╝

Setup:
  pip install fastapi uvicorn google-generativeai python-dotenv \
              google-api-python-client google-auth

Environment Variables (.env):
  # AI
  GEMINI_API_KEY=your_gemini_api_key

  # Google Sheets  (employee roster)
  SPREADSHEET_ID=1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po

  # Google Calendar
  GCAL_CALENDAR_ID=primary           # or a specific calendar ID
  GCAL_TIMEZONE=Asia/Kolkata

  # Google Auth — choose ONE method:
  #  A) API key (read-only Sheets; Calendar needs service account)
  GOOGLE_API_KEY=your_google_api_key

  #  B) Service account (recommended — supports Calendar write)
  GOOGLE_SERVICE_ACCOUNT_EMAIL=sa@project.iam.gserviceaccount.com
  GOOGLE_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\\n..."
  #  OR point to a JSON key file:
  GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service_account.json

Run:
  python calendar_manager.py
  → Open http://localhost:8000
"""

import mongo_db
from bson import ObjectId
import csv
import os
from pathlib import Path
import base64
import json
import os
import hmac
import hashlib
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, List, Any


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import Depends, Header, HTTPException
from .auth import decode_token, normalize_role

# ── Gemini ─────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARN: google-genai not installed. Run: pip install google-genai")

# ── Google APIs ─────────────────────────────────────────────
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GAPIS_AVAILABLE = True
except ImportError:
    GAPIS_AVAILABLE = False
    print("WARN: google-api-python-client not installed. Run: pip install google-api-python-client google-auth")

import uvicorn
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════
GEMINI_API_KEY   = os.getenv("CALENDAR_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEY   = os.getenv("CALENDAR_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL     = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

SPREADSHEET_ID   = os.getenv("SPREADSHEET_ID", "1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po")
GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_SVC_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
GOOGLE_PRIV_KEY  = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
GOOGLE_SVC_JSON  = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")  # path to JSON file

GCAL_CALENDAR_ID = os.getenv("GCAL_CALENDAR_ID", "primary")
GCAL_TIMEZONE    = os.getenv("GCAL_TIMEZONE", "Asia/Kolkata")
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", os.getenv("JWT_SECRET", "change-me-in-production"))
AUTH_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "28800"))

AVATAR_COLORS = ["#6366f1","#f59e0b","#10b981","#ef4444","#8b5cf6",
                 "#14b8a6","#f97316","#06b6d4","#ec4899","#84cc16"]

HOLIDAY_TEMPLATES = [
    {"month": 1, "day": 14, "name": "Makar Sankranti", "type": "Festival"},
    {"month": 1, "day": 26, "name": "Republic Day", "type": "National"},
    {"month": 2, "day": 26, "name": "Mahashivratri", "type": "Festival"},
    {"month": 3, "day": 13, "name": "Holi", "type": "Festival"},
    {"month": 4, "day": 6, "name": "Ram Navami", "type": "Festival"},
    {"month": 4, "day": 14, "name": "Baisakhi / Ambedkar Jayanti", "type": "National"},
    {"month": 8, "day": 15, "name": "Independence Day", "type": "National"},
    {"month": 8, "day": 16, "name": "Janmashtami", "type": "Festival"},
    {"month": 10, "day": 2, "name": "Gandhi Jayanti", "type": "National"},
    {"month": 10, "day": 2, "name": "Navratri (early close)", "type": "Festival"},
    {"month": 10, "day": 23, "name": "Dussehra", "type": "Festival"},
    {"month": 11, "day": 1, "name": "Diwali", "type": "Festival"},
    {"month": 12, "day": 25, "name": "Christmas", "type": "Optional"},
]

# ════════════════════════════════════════════════════════════
#  GOOGLE SERVICE ACCOUNT CREDENTIALS  (shared by Sheets + Calendar)
# ════════════════════════════════════════════════════════════
_svc_credentials = None

def _get_svc_credentials(scopes: list):
    """Build service-account credentials for the given scopes."""
    if not GAPIS_AVAILABLE:
        return None
    try:
        if GOOGLE_SVC_JSON and os.path.isfile(GOOGLE_SVC_JSON):
            return service_account.Credentials.from_service_account_file(
                GOOGLE_SVC_JSON, scopes=scopes)
        elif GOOGLE_SVC_EMAIL and GOOGLE_PRIV_KEY:
            return service_account.Credentials.from_service_account_info(
                {
                    "client_email": GOOGLE_SVC_EMAIL,
                    "private_key":  GOOGLE_PRIV_KEY,
                    "token_uri":    "https://oauth2.googleapis.com/token",
                    "type":         "service_account",
                },
                scopes=scopes,
            )
    except Exception as e:
        print(f"WARN: Credentials error: {e}")
    return None

# ════════════════════════════════════════════════════════════
#  GOOGLE SHEETS  (employee roster)
# ════════════════════════════════════════════════════════════
_sheets_api = None

def get_sheets_api():
    global _sheets_api
    if _sheets_api:
        return _sheets_api
    if not GAPIS_AVAILABLE:
        return None
    try:
        if GOOGLE_API_KEY:
            _sheets_api = build("sheets", "v4", developerKey=GOOGLE_API_KEY)
        else:
            creds = _get_svc_credentials(
                ["https://www.googleapis.com/auth/spreadsheets.readonly"])
            if creds:
                _sheets_api = build("sheets", "v4", credentials=creds)
            else:
                print("WARN: No Google credentials - employees will use seed data.")
                return None
        return _sheets_api
    except Exception as e:
        print(f"WARN: Sheets API init error: {e}")
        return None

def gsheet_get_departments() -> list:
    api = get_sheets_api()
    if not api:
        return []
    try:
        meta = api.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        return [s["properties"]["title"]
                for s in meta["sheets"]
                if s["properties"]["title"].lower() != "master"]
    except Exception as e:
        print(f"WARN: Sheets departments error: {e}")
        return []

def gsheet_get_rows(sheet_name: str) -> list:
    api = get_sheets_api()
    if not api:
        try:
            from services.sheets import ensure_dummy_manager_row
            return ensure_dummy_manager_row([], sheet_name)
        except Exception:
            return []
    try:
        result = api.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{sheet_name}'!A:Z"
        ).execute()
        rows = result.get("values", [])
        if len(rows) < 2:
            try:
                from services.sheets import ensure_dummy_manager_row
                return ensure_dummy_manager_row([], sheet_name)
            except Exception:
                return []
        headers = [h.strip() for h in rows[0]]
        mapped_rows = [
            {headers[i]: (row[i] if i < len(row) else "")
             for i in range(len(headers))}
            for row in rows[1:]
        ]
        try:
            from services.sheets import ensure_dummy_manager_row
            return ensure_dummy_manager_row(mapped_rows, sheet_name)
        except Exception:
            return mapped_rows
    except Exception as e:
        print(f"WARN: Sheets rows error ({sheet_name}): {e}")
        try:
            from services.sheets import ensure_dummy_manager_row
            return ensure_dummy_manager_row([], sheet_name)
        except Exception:
            return []

# -- Helpers ---------------------------------------------------------------------

def find_value(r, keys, default=""):
    # Try exact, then case-insensitive, then loose
    target_keys = [k.lower().strip().replace(" ", "_").replace(".", "_") for k in keys]
    for k_raw, v in r.items():
        k_clean = str(k_raw).lower().strip().replace(" ", "_").replace(".", "_")
        if k_clean in target_keys:
            return str(v).strip()
    return default


def sync_employees_from_csv():
    """Sync employees from local CSV files in the assets folder."""
    print("  [Sync] Starting sync from local CSV files...")
    BASE_DIR = Path(__file__).resolve().parent.parent
    ASSETS_DIR = BASE_DIR / "assets"
    
    csv_files = [
        "NamanLMS - Employees.csv",
        "NamanLMS - Manager.csv",
        "NamanLMS - Admin.csv"
    ]
    
    synced = 0
    for filename in csv_files:
        path = ASSETS_DIR / filename
        if not path.exists():
            print(f"  [Sync] File not found: {path}")
            continue
            
        try:
            with open(path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid  = find_value(row, ["User_id", "id", "uid", "emp_id", "employee_id"])
                    name = find_value(row, ["User_name", "name", "employee_name", "full_name"])
                    pwd  = find_value(row, ["Password", "pass", "pwd"])
                    dept = find_value(row, ["Department", "dept", "dep"])
                    role = find_value(row, ["Role", "access", "type"], "employee").lower()
                    
                    if not uid or not name:
                        continue
                    
                    email = find_value(row, ["Email", "e-mail", "mail"])
                    if not email:
                        email = f"{uid.lower().replace(' ', '.')}@company.com"
                    
                    # Upsert into MongoDB
                    mongo_db.update_one(
                        "employees",
                        {"gsheet_uid": uid},
                        {"$set": {
                            "name": name,
                            "department": dept,
                            "role": role,
                            "gsheet_uid": uid,
                            "gsheet_password": pwd,
                            "email": email,
                            "updated_at": mongo_db.now_iso()
                        }},
                        upsert=True
                    )
                    synced += 1
        except Exception as e:
            print(f"  [Sync] Error processing {filename}: {e}")
            
    print(f"  [Sync] OK: Synced {synced} employees from local CSV files")

def sync_employees_from_gsheet():
    """Sync employee roster from Google Sheets to MongoDB as a background task."""
    print("  [Sync] Starting background sync from Google Sheets...")
    
    if not SPREADSHEET_ID:
        print("  [Sync] No SPREADSHEET_ID set - skipping Sheets sync.")
        return
    
    try:
        departments = gsheet_get_departments()
    except Exception as e:
        print(f"  [Sync] ERROR fetching departments: {e}")
        return

    if not departments:
        print("  [Sync] WARNING: No departments found - using seeded employees or existing data.")
        return
    
    synced = 0
    all_sheet_data = [] # For "save all sheets" requirement
    
    for idx, dept in enumerate(departments):
        color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        try:
            rows = gsheet_get_rows(dept)
        except Exception:
            continue
        
        # Track all raw data
        all_sheet_data.append({"sheet_name": dept, "rows": rows, "updated_at": mongo_db.now_iso()})

        for row in rows:
            uid  = find_value(row, ["User_id", "id", "uid", "emp_id", "employee_id"])
            name = find_value(row, ["User_name", "name", "employee_name", "full_name"])
            pwd  = find_value(row, ["Password", "pass", "pwd"])

            if not uid or not name:
                continue

            email = find_value(row, ["Email", "e-mail", "mail"])
            if not email:
                email = f"{uid.lower().replace(' ', '.')}@company.com"

            role  = find_value(row, ["Role", "access", "type"], "employee").lower()
            
            # Upsert into MongoDB
            mongo_db.update_one(
                "employees",
                {"gsheet_uid": uid}, # Query by UID now as it's the primary stable ID
                {"$set": {
                    "name": name,
                    "department": dept,
                    "role": role,
                    "avatar_color": color,
                    "gsheet_uid": uid,
                    "gsheet_password": pwd,
                    "email": email,
                    "updated_at": mongo_db.now_iso()
                }},
                upsert=True
            )
            synced += 1
            
    # Also save ALL sheets data into a dedicated collection for backup/reference as requested
    mongo_db.update_one(
        "sheets_backup",
        {"id": "latest_sync"},
        {"$set": {
            "sheets": all_sheet_data,
            "timestamp": mongo_db.now_iso(),
            "status": "success",
            "synced_count": synced
        }},
        upsert=True
    )

    print(f"  [Sync] OK: Synced {synced} employees and backed up all Sheets at {mongo_db.now_iso()}")

def sync_leaves_from_gsheet():
    """Sync the 'Leaves' sheet to MongoDB leaves collection."""
    api = get_sheets_api()
    if not api: return
    
    rows = gsheet_get_rows("Leaves")
    synced = 0
    for row in rows:
        leave_id = str(row.get("Leave_ID", "")).strip()
        if not leave_id: continue
        
        mongo_db.update_one(
            "leaves",
            {"leave_id": leave_id},
            {"$set": {
                "employee_id": str(row.get("User_ID", "")).strip(),
                "employee_name": str(row.get("User_Name", "")).strip(),
                "department": str(row.get("Department", "")).strip(),
                "start_date": str(row.get("Date_of_Leave_From", "")).strip(),
                "end_date": str(row.get("Date_of_Leave_Till", "")).strip(),
                "reason": str(row.get("Reason", "")).strip(),
                "type": str(row.get("Leave_Type", "General")).strip(),
                "days": str(row.get("Days", "")).strip(),
                "status": str(row.get("Status", "Pending")).strip(),
                "requested_date": str(row.get("Requested_Date", "")).strip(),
                "approved_by": str(row.get("Approved_by_Manager_Name", "")).strip(),
                "updated_at": mongo_db.now_iso()
            }},
            upsert=True
        )
        synced += 1
    print(f"  OK: Synced {synced} leave records from Sheets to MongoDB")

def sync_all_raw_sheets_to_mongo():
    """Backup EVERY sheet in the spreadsheet to raw_sheets_data collection."""
    api = get_sheets_api()
    if not api: return
    
    depts = gsheet_get_departments()
    all_data = {}
    for d in depts + ["Leaves", "Master"]:
        try:
            rows = gsheet_get_rows(d)
            if rows: all_data[d] = rows
        except: continue
        
    mongo_db.update_one(
        "sheets_backup",
        {"backup_id": "comprehensive_backup"},
        {"$set": {
            "data": all_data,
            "timestamp": mongo_db.now_iso(),
            "status": "complete"
        }},
        upsert=True
    )
    print(f"  OK: Backed up {len(all_data)} sheets to MongoDB Atlas raw storage")
_gcal_api = None

def get_gcal_api():
    """Return an authenticated Google Calendar API client or None."""
    global _gcal_api
    if _gcal_api:
        return _gcal_api
    if not GAPIS_AVAILABLE:
        return None
    try:
        creds = _get_svc_credentials([
            "https://www.googleapis.com/auth/calendar"
        ])
        if creds:
            _gcal_api = build("calendar", "v3", credentials=creds)
            print("  OK: Google Calendar API connected")
        else:
            print("  WARN: No service-account credentials for Calendar - meetings stored locally only.")
    except Exception as e:
        print(f"  WARN: Calendar API error: {e}")
    return _gcal_api

def gcal_create_event(title: str, date: str, start_time: str, end_time: str,
                      description: str, location: str, meeting_link: str,
                      attendee_emails: list) -> Optional[str]:
    """Push event to Google Calendar; returns gcal_event_id or None."""
    api = get_gcal_api()
    if not api:
        return None
    body = {
        "summary":     title,
        "description": description,
        "location":    location,
        "start": {"dateTime": f"{date}T{start_time}:00", "timeZone": GCAL_TIMEZONE},
        "end":   {"dateTime": f"{date}T{end_time}:00",   "timeZone": GCAL_TIMEZONE},
        "attendees": [{"email": e} for e in attendee_emails if e],
    }
    if meeting_link:
        body["description"] = f"{description}\n\nJoin: {meeting_link}".strip()
    try:
        event = api.events().insert(
            calendarId=GCAL_CALENDAR_ID, body=body,
            sendUpdates="none"          # no external emails
        ).execute()
        print(f"  [GCal] Event created: {event.get('id')} -> '{title}'")
        return event.get("id")
    except Exception as e:
        print(f"  WARN: GCal create error: {e}")
        return None

def gcal_delete_event(gcal_event_id: str) -> bool:
    api = get_gcal_api()
    if not api or not gcal_event_id:
        return False
    try:
        api.events().delete(
            calendarId=GCAL_CALENDAR_ID, eventId=gcal_event_id).execute()
        print(f"  [GCal] Event deleted: {gcal_event_id}")
        return True
    except Exception as e:
        print(f"  WARN: GCal delete error: {e}")
        return False

def gcal_list_events(year: int, month: int) -> list:
    """Fetch all events for the given month from Google Calendar."""
    api = get_gcal_api()
    if not api:
        return []
    import calendar as cal_mod
    last_day = cal_mod.monthrange(year, month)[1]
    time_min = f"{year}-{month:02d}-01T00:00:00Z"
    time_max = f"{year}-{month:02d}-{last_day}T23:59:59Z"
    try:
        result = api.events().list(
            calendarId=GCAL_CALENDAR_ID,
            timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy="startTime"
        ).execute()
        return result.get("items", [])
    except Exception as e:
        print(f"  WARN: GCal list error: {e}")
        return []

# ════════════════════════════════════════════════════════════
#  DATABASE
# ════════════════════════════════════════════════════════════
import mongo_db
from bson.objectid import ObjectId

def init_db():
    return mongo_db.init_mongodb()

# ════════════════════════════════════════════════════════════
#  PYDANTIC MODELS
# ════════════════════════════════════════════════════════════
class MeetingRequest(BaseModel):
    title:        str
    description:  Optional[str] = None
    date:         str
    start_time:   str
    end_time:     str
    organizer_id: int | str
    attendee_ids: List[int | str] = []
    location:     str = "Online"
    meeting_link: Optional[str] = None

class LeaveRequest(BaseModel):
    employee_id: int | str
    start_date:  str
    end_date:    str
    leave_type:  str = "casual"
    reason:      Optional[str] = None

class LeaveStatusUpdate(BaseModel):
    status: str  # approved | rejected

class AgentMessage(BaseModel):
    message:     str
    employee_id: Optional[int | str] = 1

# ════════════════════════════════════════════════════════════
#  NOTIFICATION STUB  (console-only, no SMTP)
# ════════════════════════════════════════════════════════════
def notify_meeting_invite(to_email: str, meeting: dict, organizer_name: str):
    print(f"  [NOTIFY] Invite -> {to_email} | '{meeting.get('title')}' "
          f"on {meeting.get('date')} {meeting.get('start_time')}-{meeting.get('end_time')} "
          f"| Organizer: {organizer_name}")

def notify_leave_applied(to_email: str, emp_name: str, leave: dict):
    print(f"  [NOTIFY] Leave applied -> {to_email} | {emp_name} | "
          f"{leave.get('start_date')} to {leave.get('end_date')} ({leave.get('leave_type')})")

def notify_leave_status(to_email: str, emp_name: str, leave: dict, status: str):
    icon = "OK" if status == "approved" else "X"
    print(f"  {icon} [NOTIFY] Leave {status} -> {to_email} | {emp_name} | "
          f"{leave.get('start_date')} to {leave.get('end_date')}")

# ════════════════════════════════════════════════════════════
#  CORE FUNCTIONS  (also called by the AI agent as tools)
# ════════════════════════════════════════════════════════════
def _get_employees() -> list:
    """Fetch all employees from MongoDB."""
    return mongo_db.find_many("employees")


# Adapt the older sheet helpers to the current workbook layout:
# Employees tab contains the Dep column, while Manager and Admin are separate tabs.
def gsheet_get_departments() -> list:
    try:
        from services.sheets import get_departments as get_sheet_departments

        return get_sheet_departments()
    except Exception as e:
        print(f"  Sheets departments error: {e}")
        return []


def gsheet_get_rows(sheet_name: str) -> list:
    try:
        from services.sheets import get_sheet_data as get_service_sheet_data

        return get_service_sheet_data(sheet_name)
    except Exception as e:
        print(f"  Sheets rows error ({sheet_name}): {e}")
        return []


# -- Auth Helpers (Delegated to auth.py) ----------------------------------------

def _get_current_user(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(401, "Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid authorization header")
    return decode_token(token)

def _normalize_role(role: Any) -> str:
    return normalize_role(role)

# -- End of Auth Helpers --

def _serialize_employee(emp: dict) -> dict:
    clean_emp = dict(emp)
    clean_emp.pop("gsheet_password", None)
    clean_emp["role"] = _normalize_role(clean_emp.get("role"))
    return clean_emp


def _merge_sheet_identity(emp: dict, sheet_user: dict) -> dict:
    merged = dict(emp)
    merged["role"] = sheet_user.get("role", merged.get("role", "Employee"))
    merged["department"] = sheet_user.get("department", merged.get("department", ""))
    merged["email"] = sheet_user.get("email", merged.get("email", ""))
    merged["name"] = sheet_user.get("userName", merged.get("name", ""))
    return _serialize_employee(merged)


def _decode_auth_token(token: str) -> dict:
    try:
        header_segment, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(401, "Invalid authentication token") from exc

    try:
        header = json.loads(_b64url_decode(header_segment).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise HTTPException(401, "Unsupported authentication token")

    signing_input = f"{header_segment}.{payload_segment}"
    expected = hmac.new(
        AUTH_TOKEN_SECRET.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided_signature = _b64url_decode(signature_segment)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    if not hmac.compare_digest(provided_signature, expected):
        raise HTTPException(401, "Invalid authentication token")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(401, "Authentication token expired")

    payload["role"] = _normalize_role(payload.get("role"))
    return payload


def _get_current_user(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(401, "Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid authorization header")
    return _decode_auth_token(token)


def _update_leave_status_record(lid: str, status: str, approved_by: str = "", comments: str = ""):
    leave = mongo_db.find_one("leaves", {"_id": ObjectId(lid)})
    if not leave:
        raise HTTPException(404, "Leave not found")

    mongo_db.update_one("leaves", {"_id": ObjectId(lid)}, {"$set": {"status": status}})
    
    emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": leave.get("employee_id")}, {"id": leave.get("employee_id")}]})
    if not emp:
        try: emp = mongo_db.find_one("employees", {"_id": ObjectId(leave.get("employee_id"))})
        except: pass

    if emp:
        notify_leave_status(emp["email"], emp["name"], leave, status)
        
    return {
        "success": True,
        "message": f"Leave {status}",
        "approved_by": approved_by,
        "comments": comments,
    }


def _resolve_employee_db_id(employee_ref: int | str) -> str:
    ref = str(employee_ref).strip()
    
    # In MongoDB, we use gsheet_uid or the string _id
    query = {"$or": [{"gsheet_uid": ref}, {"id": ref}]}
    user = mongo_db.find_one("employees", query)
    
    if not user:
        # Fallback to checking by ID if it's already a Mongo ID
        try:
            user = mongo_db.find_one("employees", {"_id": ObjectId(ref)})
        except:
            user = None
            
    if not user:
        raise HTTPException(404, "Employee not found")
        
    return str(user.get("gsheet_uid") or user.get("_id"))


def _get_holidays_for_month(year: int, month: int) -> list:
    holidays = []
    for holiday in HOLIDAY_TEMPLATES:
        if holiday["month"] != month:
            continue
        holidays.append({
            "date": f"{year}-{month:02d}-{holiday['day']:02d}",
            "name": holiday["name"],
            "type": holiday["type"],
        })
    return holidays

def _get_calendar_events(year: int, month: int, current_user: Optional[dict] = None) -> dict:
    prefix = f"{year}-{month:02d}"
    resolved_role = _normalize_role((current_user or {}).get("role"))
    resolved_employee_id = None
    if current_user and current_user.get("sub"):
        try:
            resolved_employee_id = _resolve_employee_db_id(current_user["sub"])
        except HTTPException:
            resolved_employee_id = None

    # ── Meetings from MongoDB ───────────
    meetings_data = mongo_db.find_many("meetings", {"date": {"$regex": f"^{prefix}"}})
    meetings = []
    for m in meetings_data:
        m["id"] = str(m.get("_id"))
        # Get organizer details
        org = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": m.get("organizer_id")}, {"id": m.get("organizer_id")}]})
        if not org:
            try: org = mongo_db.find_one("employees", {"_id": ObjectId(m.get("organizer_id"))})
            except: pass
            
        m["organizer_name"] = org.get("name") if org else "Unknown"
        m["avatar_color"] = org.get("avatar_color") if org else "#6366f1"
        
        # Get attendees
        attendees_data = mongo_db.find_many("meeting_attendees", {"meeting_id": m["id"]})
        m["attendees"] = []
        for att in attendees_data:
            emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": att.get("employee_id")}, {"id": att.get("employee_id")}]})
            if not emp:
                try: emp = mongo_db.find_one("employees", {"_id": ObjectId(att.get("employee_id"))})
                except: pass
            if emp:
                m["attendees"].append({
                    "id": str(emp.get("gsheet_uid") or emp.get("_id")),
                    "name": emp.get("name"),
                    "email": emp.get("email"),
                    "rsvp": att.get("rsvp", "pending")
                })
        
        # Filter for Employee role
        if resolved_role == "Employee" and resolved_employee_id:
            if m.get("organizer_id") == resolved_employee_id or any(a["id"] == resolved_employee_id for a in m["attendees"]):
                meetings.append(m)
        else:
            meetings.append(m)

    # ── Merge live GCal events not yet in SQLite ────────────
    gcal_events = gcal_list_events(year, month)
    local_gcal_ids = {m["gcal_event_id"] for m in meetings if m.get("gcal_event_id")}
    for ev in gcal_events:
        if ev.get("id") in local_gcal_ids:
            continue  # already mirrored
        start_dt = ev.get("start", {}).get("dateTime", "")
        end_dt   = ev.get("end",   {}).get("dateTime", "")
        if start_dt:
            ev_date  = start_dt[:10]
            ev_start = start_dt[11:16]
            ev_end   = end_dt[11:16] if end_dt else ev_start
            meetings.append({
                "id": None,
                "title":          ev.get("summary", "(No title)"),
                "description":    ev.get("description", ""),
                "date":           ev_date,
                "start_time":     ev_start,
                "end_time":       ev_end,
                "location":       ev.get("location", ""),
                "organizer_name": "Google Calendar",
                "avatar_color":   "#14b8a6",
                "attendees":      [],
                "gcal_event_id":  ev.get("id"),
                "source":         "gcal",
            })

    # ── Leaves from MongoDB ───────────────────────────────────
    leave_filters = {
        "status": {"$ne": "rejected"},
        "$or": [
            {"start_date": {"$regex": f"^{prefix}"}},
            {"end_date": {"$regex": f"^{prefix}"}},
            {"$and": [{"start_date": {"$lte": f"{prefix}-31"}}, {"end_date": {"$gte": f"{prefix}-01"}}]}
        ]
    }
    if resolved_role == "Employee" and resolved_employee_id:
        leave_filters["employee_id"] = resolved_employee_id
        
    leaves_data = mongo_db.find_many("leaves", leave_filters, sort=[("start_date", 1)])
    leaves = []
    for l in leaves_data:
        l["id"] = str(l.get("_id"))
        emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": l.get("employee_id")}, {"id": l.get("employee_id")}]})
        if not emp:
            try: emp = mongo_db.find_one("employees", {"_id": ObjectId(l.get("employee_id"))})
            except: pass
            
        if emp:
            l["employee_name"] = emp.get("name")
            l["avatar_color"] = emp.get("avatar_color")
            l["department"] = emp.get("department")
            leaves.append(l)
    return {
        "holidays": _get_holidays_for_month(year, month),
        "meetings": meetings,
        "leaves": leaves,
    }

def _schedule_meeting(title: str, date: str, start_time: str, end_time: str,
                      organizer_id: str, attendee_ids: list = [],
                      description: str = "", location: str = "Online",
                      meeting_link: str = "") -> dict:
    all_ids = list(set(attendee_ids))
    if organizer_id not in all_ids:
        all_ids.append(organizer_id)

    # Gather attendee emails for Google Calendar
    org = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": organizer_id}, {"id": organizer_id}]})
    if not org:
        # Try finding by ObjectId in case it's a mongo ID
        try:
            org = mongo_db.find_one("employees", {"_id": ObjectId(organizer_id)})
        except:
            org = None
            
    if not org:
        return {"success": False, "message": "Organizer not found."}

    attendee_emails = []
    for eid in all_ids:
        emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": eid}, {"id": eid}]})
        if not emp:
            try:
                emp = mongo_db.find_one("employees", {"_id": ObjectId(eid)})
            except:
                continue
        if emp:
            attendee_emails.append(emp["email"])

    # ── Push to Google Calendar ──────────────────────────────
    gcal_event_id = gcal_create_event(
        title=title, date=date,
        start_time=start_time, end_time=end_time,
        description=description, location=location,
        meeting_link=meeting_link or "",
        attendee_emails=attendee_emails,
    )

    # ── Mirror in MongoDB ─────────────────────────────────────
    meeting_doc = {
        "title": title,
        "description": description,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "organizer_id": organizer_id,
        "location": location,
        "meeting_link": meeting_link or "",
        "gcal_event_id": gcal_event_id or "",
        "created_at": mongo_db.now_iso()
    }
    mid = mongo_db.insert_one("meetings", meeting_doc)

    # Attendees
    for eid in all_ids:
        if eid != organizer_id:
            mongo_db.update_one(
                "meeting_attendees",
                {"meeting_id": mid, "employee_id": eid},
                {"$set": {"rsvp": "pending"}},
                upsert=True
            )

    # ── Console notifications ─────────────────────
    meeting_info = {"title": title, "date": date,
                    "start_time": start_time, "end_time": end_time}
    for eid in all_ids:
        emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": eid}, {"id": eid}]})
        if emp:
            notify_meeting_invite(emp["email"], meeting_info, org["name"])

    gcal_note = f" | GCal ID: {gcal_event_id}" if gcal_event_id else " (GCal unavailable — stored locally)"
    return {
        "success":        True,
        "meeting_id":     mid,
        "gcal_event_id":  gcal_event_id,
        "message":        f"✅ Meeting '{title}' scheduled on {date} {start_time}–{end_time}{gcal_note}",
    }

def _apply_leave(employee_id: str, start_date: str, end_date: str,
                 leave_type: str = "casual", reason: str = "") -> dict:
    """Apply for leave and save to MongoDB."""
    # Check for overlaps in MongoDB
    conflict = mongo_db.find_one("leaves", {
        "employee_id": employee_id,
        "status": {"$ne": "rejected"},
        "$nor": [
            {"end_date": {"$lt": start_date}},
            {"start_date": {"$gt": end_date}}
        ]
    })
    
    if conflict:
        return {"success": False, "message": "Conflict: overlapping leave already exists."}

    leave_doc = {
        "employee_id": employee_id,
        "start_date": start_date,
        "end_date": end_date,
        "leave_type": leave_type,
        "reason": reason,
        "status": "pending",
        "applied_at": mongo_db.now_iso()
    }
    lid = mongo_db.insert_one("leaves", leave_doc)

    emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": employee_id}, {"id": employee_id}]})
    if not emp:
        try: emp = mongo_db.find_one("employees", {"_id": ObjectId(employee_id)})
        except: pass
        
    if emp:
        managers = mongo_db.find_many("employees", {"role": "Manager", "$or": [{"gsheet_uid": {"$ne": employee_id}}, {"id": {"$ne": employee_id}}]})
        leave_data = {"start_date": start_date, "end_date": end_date,
                      "leave_type": leave_type, "reason": reason}
        notify_leave_applied(emp["email"], emp["name"], leave_data)
        for mgr in managers:
            notify_leave_applied(mgr["email"], emp["name"], leave_data)

    return {
        "success":  True,
        "leave_id": lid,
        "message":  f"🏖️ Leave applied {start_date} → {end_date} ({leave_type}). Manager notified (console).",
    }

def _check_availability(date: str, employee_ids: list) -> dict:
    """Check availability of employees in MongoDB."""
    result = {}
    for eid in employee_ids:
        emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": eid}, {"id": eid}]})
        if not emp:
            try: emp = mongo_db.find_one("employees", {"_id": ObjectId(eid)})
            except: pass
            
        if not emp:
            continue
            
        # Check leave in MongoDB
        on_leave = mongo_db.find_one("leaves", {
            "employee_id": eid,
            "status": "approved",
            "start_date": {"$lte": date},
            "end_date": {"$gte": date}
        }) is not None
        
        # Check meetings in MongoDB
        meetings_that_day = mongo_db.find_many("meetings", {"date": date, "organizer_id": eid})
        # Plus where they are an attendee
        attended_meetings = mongo_db.find_many("meeting_attendees", {"employee_id": eid})
        for am in attended_meetings:
            m = mongo_db.find_one("meetings", {"_id": am.get("meeting_id"), "date": date})
            if m:
                meetings_that_day.append(m)
                
        result[str(eid)] = {
            "name":     emp["name"],
            "on_leave": on_leave,
            "meetings": meetings_that_day,
        }
    return result

# ════════════════════════════════════════════════════════════
#  TOOL MAP  (name → function)
# ════════════════════════════════════════════════════════════
TOOL_MAP = {
    "schedule_meeting":    _schedule_meeting,
    "apply_leave":         _apply_leave,
    "get_employees":       _get_employees,
    "check_availability":  _check_availability,
    "get_calendar_events": _get_calendar_events,
}

# ════════════════════════════════════════════════════════════
#  GEMINI AI AGENT
# ════════════════════════════════════════════════════════════
def _build_gemini_tools() -> list:
    """Build tool list using the new google.genai SDK (google-genai package)."""
    return [
        genai_types.Tool(function_declarations=[
            genai_types.FunctionDeclaration(
                name="schedule_meeting",
                description="Schedule a meeting and push it to Google Calendar.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "title":        genai_types.Schema(type=genai_types.Type.STRING,  description="Meeting title"),
                        "date":         genai_types.Schema(type=genai_types.Type.STRING,  description="Date YYYY-MM-DD"),
                        "start_time":   genai_types.Schema(type=genai_types.Type.STRING,  description="Start time HH:MM (24 h)"),
                        "end_time":     genai_types.Schema(type=genai_types.Type.STRING,  description="End time HH:MM (24 h)"),
                        "organizer_id": genai_types.Schema(type=genai_types.Type.INTEGER, description="Organizer employee ID"),
                        "attendee_ids": genai_types.Schema(type=genai_types.Type.ARRAY,
                                            items=genai_types.Schema(type=genai_types.Type.INTEGER),
                                            description="Attendee employee IDs"),
                        "description":  genai_types.Schema(type=genai_types.Type.STRING,  description="Agenda / description"),
                        "location":     genai_types.Schema(type=genai_types.Type.STRING,  description="Room or 'Online'"),
                        "meeting_link": genai_types.Schema(type=genai_types.Type.STRING,  description="Video call URL"),
                    },
                    required=["title", "date", "start_time", "end_time", "organizer_id"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="apply_leave",
                description="Apply for employee leave and notify managers.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "employee_id": genai_types.Schema(type=genai_types.Type.INTEGER, description="Employee ID"),
                        "start_date":  genai_types.Schema(type=genai_types.Type.STRING,  description="Start date YYYY-MM-DD"),
                        "end_date":    genai_types.Schema(type=genai_types.Type.STRING,  description="End date YYYY-MM-DD"),
                        "leave_type":  genai_types.Schema(type=genai_types.Type.STRING,  description="casual | sick | earned"),
                        "reason":      genai_types.Schema(type=genai_types.Type.STRING,  description="Reason for leave"),
                    },
                    required=["employee_id", "start_date", "end_date"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="get_employees",
                description="Get all employees with IDs, departments, and roles.",
                parameters=genai_types.Schema(type=genai_types.Type.OBJECT, properties={}),
            ),
            genai_types.FunctionDeclaration(
                name="check_availability",
                description="Check whether specific employees are free on a given date.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "date":         genai_types.Schema(type=genai_types.Type.STRING, description="Date YYYY-MM-DD"),
                        "employee_ids": genai_types.Schema(type=genai_types.Type.ARRAY,
                                            items=genai_types.Schema(type=genai_types.Type.INTEGER),
                                            description="Employee IDs to check"),
                    },
                    required=["date", "employee_ids"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="get_calendar_events",
                description="Get all meetings and leaves for a given month.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "year":  genai_types.Schema(type=genai_types.Type.INTEGER, description="4-digit year"),
                        "month": genai_types.Schema(type=genai_types.Type.INTEGER, description="Month 1–12"),
                    },
                    required=["year", "month"],
                ),
            ),
        ])
    ]


def run_agent(message: str, employee_id: int = 1) -> str:
    if not GEMINI_AVAILABLE:
        return "⚠️ google-genai not installed. Run: pip install google-genai"
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not set. Add it to .env to enable AI assistant."

    today = date.today().isoformat()
    system_prompt = f"""You are CalendarBot 🗓️ — an intelligent assistant for a company calendar system powered by Google Calendar.
Today: {today}. Current user's employee_id: {employee_id}.

You help with:
• Scheduling meetings (pushed to Google Calendar automatically)
• Applying for leaves (casual / sick / earned)
• Checking employee availability before scheduling
• Summarising calendar events for the month

Guidelines:
- ALWAYS use tools to perform real actions — never pretend to schedule or apply.
- If the user says "schedule with Rahul", first call get_employees to find Rahul's ID.
- Before scheduling, call check_availability when dates are ambiguous.
- Be warm, concise, and professional. Use emojis sparingly.
- After a successful action, confirm clearly what was done.
"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    tools  = _build_gemini_tools()

    # Build initial message history
    contents = [genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message)]
    )]

    model_candidates = [GEMINI_MODEL, "gemini-2.0-flash", "gemini-1.5-flash-latest"]

    for _ in range(8):  # max agentic loops
        last_error = None
        response = None
        for model_name in model_candidates:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=tools,
                    ),
                )
                break
            except Exception as exc:
                last_error = exc
                if "not found" not in str(exc).lower() and "not supported" not in str(exc).lower():
                    raise

        if response is None:
            if last_error is not None:
                raise last_error
            return "I ran into an issue completing the request. Please try again."

        candidate = response.candidates[0]
        contents.append(genai_types.Content(
            role="model",
            parts=candidate.content.parts,
        ))

        # Collect function calls
        fn_calls = [p.function_call for p in candidate.content.parts
                    if p.function_call]

        if not fn_calls:
            # No tool calls — return the text reply
            text_parts = [p.text for p in candidate.content.parts
                          if hasattr(p, "text") and p.text]
            return "\n".join(text_parts) if text_parts else "Done ✓"

        # Execute tools and feed results back
        fn_response_parts = []
        for fc in fn_calls:
            fn = TOOL_MAP.get(fc.name)
            try:
                args   = dict(fc.args)
                result = fn(**args) if fn else {"error": f"Unknown tool: {fc.name}"}
            except Exception as e:
                result = {"error": str(e)}

            fn_response_parts.append(
                genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=fc.name,
                        response={"result": json.dumps(result, default=str)},
                    )
                )
            )

        contents.append(genai_types.Content(role="user", parts=fn_response_parts))

    return "I ran into an issue completing the request. Please try again."

# ════════════════════════════════════════════════════════════
#  FASTAPI
# ════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════
from fastapi import APIRouter
router = APIRouter()

# ── Sync ────────────────────────────────────────────────────
@router.post("/api/sync-employees")
async def sync_employees_endpoint():
    try:
        sync_employees_from_gsheet()
        count = mongo_db.count("employees")
        return {"success": True, "count": count,
                "message": f"Synced {count} employees ✅"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/api/sync-all")
async def sync_all_endpoint():
    """Unified endpoint to sync everything from Sheets to MongoDB."""
    try:
        sync_employees_from_gsheet()
        sync_leaves_from_gsheet()
        sync_all_raw_sheets_to_mongo()
        return {
            "success": True,
            "message": "Full synchronization from Google Sheets to MongoDB Atlas complete! 🚀",
            "timestamp": mongo_db.now_iso()
        }
    except Exception as e:
        raise HTTPException(500, str(e))

# -- Auth Helpers (Delegated to auth.py) ----------------------------------------

def _get_current_user(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(401, "Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid authorization header")
    return decode_token(token)

def _normalize_role(role: Any) -> str:
    return normalize_role(role)

# -- End of Auth Helpers --


@router.get("/api/departments")
async def list_departments():
    try:
        import sys
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)
        from services.sheets import get_departments as get_gsheet_departments

        departments = get_gsheet_departments()
        if departments:
            return departments
    except Exception:
        pass

    result = mongo_db.distinct("employees", "department")
    return [d for d in result if d and str(d).strip()]

@router.get("/api/employees")
async def list_employees():
    employees = []
    # Fetch from Mongo
    for employee in mongo_db.find_many("employees", {}):
        employees.append({
            "id":       employee.get("gsheet_uid", str(employee.get("_id"))),
            "userId":   employee.get("gsheet_uid", str(employee.get("_id"))),
            "userName": employee.get("name", ""),
            "name":     employee.get("name", ""),
            "department": employee.get("department", "General"),
            "role":     employee.get("role", "Employee"),
            "status":   "Active",
        })
    return employees

# ── Calendar ─────────────────────────────────────────────────
@router.get("/api/calendar/{year}/{month}")
async def calendar(year: int, month: int, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization) if authorization else None
    return _get_calendar_events(year, month, current_user)


@router.get("/api/calendar")
async def calendar_by_query(year: int, month: int, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization) if authorization else None
    return _get_calendar_events(year, month, current_user)

# ── Meetings ─────────────────────────────────────────────────
@router.post("/api/meetings")
async def create_meeting(req: MeetingRequest, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    organizer_id = _resolve_employee_db_id(req.organizer_id)
    attendee_ids = [_resolve_employee_db_id(attendee_id) for attendee_id in req.attendee_ids]
    current_user_employee_id = _resolve_employee_db_id(current_user["sub"])
    if current_user.get("role") == "Employee" and organizer_id != current_user_employee_id:
        raise HTTPException(403, "Employees can only schedule meetings for themselves")
    r = _schedule_meeting(
        title=req.title, date=req.date,
        start_time=req.start_time, end_time=req.end_time,
        organizer_id=organizer_id, attendee_ids=attendee_ids,
        description=req.description or "", location=req.location,
        meeting_link=req.meeting_link or "",
    )
    if not r["success"]:
        raise HTTPException(400, r["message"])
    return r

@router.delete("/api/meetings/{mid}")
async def delete_meeting(mid: str):
    meeting = mongo_db.find_one("meetings", {"_id": ObjectId(mid)})
    if meeting and meeting.get("gcal_event_id"):
        gcal_delete_event(meeting["gcal_event_id"])
    
    mongo_db.delete_many("meeting_attendees", {"meeting_id": mid})
    mongo_db.delete_one("meetings", {"_id": ObjectId(mid)})
    return {"success": True}

# ── Leaves ───────────────────────────────────────────────────
@router.get("/api/leaves")
async def get_leaves(
    employee_id: Optional[str] = None,
    userId: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(authorization)
    resolved_employee_id = employee_id or userId
    requested_role = _normalize_role(role)
    resolved_role = current_user.get("role", requested_role)

    filters = {}
    if resolved_role == "Employee":
        resolved_employee_id = _resolve_employee_db_id(current_user["sub"])
        filters["employee_id"] = resolved_employee_id
    elif resolved_role == "Manager":
        resolved_department = current_user.get("department") or department or ""
        # Filter handled after lookup
    elif resolved_employee_id:
        try:
            resolved_employee_id = _resolve_employee_db_id(resolved_employee_id)
            filters["employee_id"] = resolved_employee_id
        except:
            pass

    leaves_data = mongo_db.find_many("leaves", filters, sort=[("applied_at", -1)])
    result = []
    
    for l in leaves_data:
        l["id"] = str(l.get("_id"))
        emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": l.get("employee_id")}, {"id": l.get("employee_id")}]})
        if not emp:
            try: emp = mongo_db.find_one("employees", {"_id": ObjectId(l.get("employee_id"))})
            except: pass
            
        if emp:
            # Manager department filter
            if resolved_role == "Manager" and emp.get("department") != (current_user.get("department") or department):
                continue
            
            l["employee_name"] = emp.get("name")
            l["department"] = emp.get("department")
            l["avatar_color"] = emp.get("avatar_color")
            result.append(l)
            
    return result

@router.post("/api/leaves")
async def apply_leave(req: LeaveRequest, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    resolved_employee_id = _resolve_employee_db_id(req.employee_id)
    current_user_employee_id = _resolve_employee_db_id(current_user["sub"])
    if current_user.get("role") == "Employee" and resolved_employee_id != current_user_employee_id:
        raise HTTPException(403, "Employees can only apply for their own leave")
    r = _apply_leave(resolved_employee_id, req.start_date, req.end_date,
                     req.leave_type, req.reason or "")
    if not r["success"]:
        raise HTTPException(400, r["message"])
    return r


@router.patch("/api/leaves/{lid}")
async def patch_leave(lid: str, body: dict, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Manager", "Admin"}:
        raise HTTPException(403, "Only managers and admins can update leave status")
    action = str(body.get("action", "")).strip().lower()
    status = "approved" if action == "approve" else "rejected" if action == "reject" else ""
    if not status:
        raise HTTPException(400, "Action must be 'approve' or 'reject'")
        
    leave = mongo_db.find_one("leaves", {"_id": ObjectId(lid)})
    if not leave:
        raise HTTPException(404, "Leave not found")
        
    emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": leave.get("employee_id")}, {"id": leave.get("employee_id")}]})
    if not emp:
        try: emp = mongo_db.find_one("employees", {"_id": ObjectId(leave.get("employee_id"))})
        except: pass
        
    if not emp:
         raise HTTPException(404, "Employee for leave not found")

    if current_user.get("role") == "Manager" and emp.get("department") != current_user.get("department"):
        raise HTTPException(403, "Managers can only approve leaves in their department")
        
    return _update_leave_status_record(
        lid,
        status,
        str(body.get("approvedBy", "")).strip() or current_user.get("name", ""),
        str(body.get("comments", "")).strip(),
    )


@router.put("/api/leaves/{lid}/status")
async def update_leave(lid: int, req: LeaveStatusUpdate):
    return _update_leave_status_record(lid, req.status)

@router.delete("/api/leaves/{lid}")
async def delete_leave(lid: str):
    mongo_db.delete_one("leaves", {"_id": ObjectId(lid)})
    return {"success": True}

# ── Gemini Agent ─────────────────────────────────────────────
@router.post("/api/agent")
async def agent_endpoint(req: AgentMessage):
    try:
        resolved_employee_id = _resolve_employee_db_id(req.employee_id or 1)
        reply = run_agent(req.message, resolved_employee_id)
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error: {e}"}

# ════════════════════════════════════════════════════════════
#  EMBEDDED HTML  UI  (dark, Gemini-branded CalendarBot)
# ════════════════════════════════════════════════════════════
HTML_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CalMgr — Gemini × Google Calendar</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#07111f;--surface:#0d1a2e;--card:#111e33;--border:#182845;--border2:#1e3560;
  --text:#dde5f4;--muted:#5a7299;
  --accent:#4285f4;--accent2:#669df6;  /* Gemini/Google blue */
  --gem1:#4285f4;--gem2:#ea4335;--gem3:#fbbc04;--gem4:#34a853;
  --green:#34a853;--amber:#fbbc04;--red:#ea4335;--purple:#9c27b0;
  --radius:12px;--shadow:0 8px 32px rgba(0,0,0,.55);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);
     height:100vh;display:flex;flex-direction:column;overflow:hidden}
button{cursor:pointer;font-family:inherit}
input,select,textarea{font-family:inherit}

/* ── HEADER ─────────────────────────────────────────────── */
.header{display:flex;align-items:center;gap:14px;padding:12px 20px;
  background:var(--surface);border-bottom:1px solid var(--border);flex-shrink:0}
.logo{display:flex;align-items:center;gap:9px;font-size:17px;font-weight:800;
  letter-spacing:-.4px;color:#fff;white-space:nowrap}
.logo-icon{width:30px;height:30px;border-radius:8px;
  background:linear-gradient(135deg,var(--gem1),var(--gem4));
  display:flex;align-items:center;justify-content:center;font-size:16px}
.logo-badge{font-size:9px;padding:2px 7px;border-radius:20px;font-weight:700;
  background:linear-gradient(90deg,var(--gem1),var(--gem4));color:#fff;margin-left:4px;
  letter-spacing:.5px;text-transform:uppercase}
.nav-center{display:flex;align-items:center;gap:10px;flex:1;justify-content:center}
.month-title{font-size:17px;font-weight:700;min-width:190px;text-align:center}
.btn{padding:7px 15px;border-radius:8px;border:1px solid var(--border2);
  background:var(--card);color:var(--text);font-size:12px;font-weight:600;transition:all .15s}
.btn:hover{background:var(--border2);border-color:var(--accent)}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover{background:var(--accent2);border-color:var(--accent2)}
.btn-sm{padding:5px 12px;font-size:11px}
.btn-icon{padding:7px 10px;font-size:14px}
.tab-group{display:flex;background:var(--card);border-radius:8px;overflow:hidden;border:1px solid var(--border)}
.tab{padding:6px 14px;font-size:11px;font-weight:600;border:none;
  background:transparent;color:var(--muted);transition:all .15s;letter-spacing:.3px}
.tab.active{background:var(--accent);color:#fff}

/* ── LAYOUT ─────────────────────────────────────────────── */
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:232px;flex-shrink:0;background:var(--surface);
  border-right:1px solid var(--border);display:flex;flex-direction:column;overflow-y:auto}
.main{flex:1;overflow:hidden;display:flex;flex-direction:column}
.ai-panel{width:310px;flex-shrink:0;background:var(--surface);
  border-left:1px solid var(--border);display:flex;flex-direction:column}

/* ── SIDEBAR ─────────────────────────────────────────────── */
.sidebar-section{padding:14px}
.sidebar-label{font-size:9px;font-weight:700;letter-spacing:1.8px;
  text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.employee-item{display:flex;align-items:center;gap:9px;padding:7px 9px;
  border-radius:8px;cursor:pointer;transition:background .12s}
.employee-item:hover{background:var(--card)}
.employee-item.active{background:var(--card);outline:1px solid var(--border2)}
.avatar{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:11px;font-weight:800;color:#fff;flex-shrink:0}
.emp-name{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.emp-dept{font-size:10px;color:var(--muted)}
.role-badge{font-size:8px;padding:1px 6px;border-radius:10px;
  background:#0d2957;color:#669df6;font-weight:700}
.legend-item{display:flex;align-items:center;gap:8px;font-size:11px;
  color:var(--muted);margin-bottom:6px}
.legend-dot{width:8px;height:8px;border-radius:2px}

/* ── CALENDAR ────────────────────────────────────────────── */
.calendar-wrap{flex:1;overflow:auto;padding:14px}
.cal-header-row{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:4px}
.day-label{text-align:center;font-size:10px;font-weight:700;letter-spacing:1px;
  color:var(--muted);padding:5px 0;text-transform:uppercase}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.cal-cell{background:var(--card);border-radius:8px;min-height:96px;padding:7px;
  border:1px solid var(--border);transition:border-color .15s;cursor:pointer;position:relative}
.cal-cell:hover{border-color:var(--border2)}
.cal-cell.today{border-color:var(--accent);background:#0a1d3d}
.cal-cell.other-month{opacity:.28}
.date-num{font-size:11px;font-weight:700;margin-bottom:4px;
  display:flex;align-items:center;justify-content:space-between}
.today-dot{width:19px;height:19px;background:var(--accent);border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:10px;color:#fff;font-weight:800}
.event-pill{font-size:9.5px;font-weight:600;padding:2px 6px;border-radius:4px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}
.meeting-pill{background:rgba(66,133,244,.18);color:#90b8f8;border-left:2px solid var(--gem1)}
.gcal-pill{background:rgba(52,168,83,.15);color:#6ed88a;border-left:2px solid var(--gem4)}
.leave-pill{background:rgba(251,188,4,.12);color:#fdd663;border-left:2px solid var(--amber)}
.approved-pill{border-left-color:var(--green);background:rgba(52,168,83,.12);color:#6ed88a}
.pending-pill{border-left-color:var(--amber);background:rgba(251,188,4,.1);color:#fdd663}
.rejected-pill{border-left-color:var(--red);background:rgba(234,67,53,.1);color:#f29295}
.more-badge{font-size:9px;color:var(--muted);margin-top:2px}

/* ── LEAVE TABLE ─────────────────────────────────────────── */
.table-view{padding:14px;overflow:auto;flex:1}
.data-table{width:100%;border-collapse:collapse;font-size:12px}
.data-table th{text-align:left;padding:9px 13px;background:var(--card);
  border-bottom:1px solid var(--border2);font-size:9px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
.data-table td{padding:9px 13px;border-bottom:1px solid var(--border)}
.data-table tr:hover td{background:rgba(255,255,255,.015)}
.status-badge{padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700}
.s-pending{background:rgba(251,188,4,.12);color:#fdd663}
.s-approved{background:rgba(52,168,83,.12);color:#6ed88a}
.s-rejected{background:rgba(234,67,53,.1);color:#f29295}
.action-row{display:flex;gap:5px}

/* ── AI PANEL ────────────────────────────────────────────── */
.ai-header{padding:12px 15px;border-bottom:1px solid var(--border);
  font-weight:700;font-size:13px;display:flex;align-items:center;gap:8px}
.ai-header-badge{font-size:9px;padding:2px 8px;border-radius:20px;font-weight:700;
  background:linear-gradient(90deg,var(--gem1) 0%,var(--gem4) 100%);color:#fff;
  letter-spacing:.6px;text-transform:uppercase;margin-left:2px}
.ai-messages{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:9px}
.msg{max-width:92%;padding:9px 12px;border-radius:10px;font-size:12px;
  line-height:1.6;word-break:break-word}
.msg-user{background:var(--accent);color:#fff;align-self:flex-end;
  border-radius:10px 10px 3px 10px}
.msg-bot{background:var(--card);color:var(--text);align-self:flex-start;
  border-radius:10px 10px 10px 3px;border:1px solid var(--border)}
.msg-bot.typing{opacity:.55;font-style:italic}
.ai-input-row{padding:10px;border-top:1px solid var(--border);display:flex;gap:7px}
.ai-input{flex:1;background:var(--card);border:1px solid var(--border2);
  border-radius:8px;padding:8px 11px;color:var(--text);font-size:12px;
  resize:none;outline:none;transition:border-color .15s}
.ai-input:focus{border-color:var(--accent)}
.ai-send{background:linear-gradient(135deg,var(--gem1),var(--gem4));
  border:none;color:#fff;padding:8px 13px;border-radius:8px;font-size:14px;
  transition:opacity .15s}
.ai-send:hover{opacity:.85}
.quick-chip{display:inline-block;padding:3px 9px;border-radius:20px;
  background:var(--card);border:1px solid var(--border2);font-size:10px;
  color:var(--muted);cursor:pointer;margin:2px;transition:all .12s;font-weight:500}
.quick-chip:hover{border-color:var(--accent);color:var(--accent)}
.quick-chips{padding:0 10px 7px;display:flex;flex-wrap:wrap}

/* ── MODAL ───────────────────────────────────────────────── */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.72);backdrop-filter:blur(5px);
  z-index:100;display:flex;align-items:center;justify-content:center;
  opacity:0;pointer-events:none;transition:opacity .2s}
.overlay.open{opacity:1;pointer-events:all}
.modal{background:var(--surface);border-radius:14px;border:1px solid var(--border2);
  width:510px;max-width:95vw;max-height:90vh;overflow-y:auto;
  box-shadow:var(--shadow);transform:scale(.96);transition:transform .2s}
.overlay.open .modal{transform:scale(1)}
.modal-header{padding:18px 22px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between}
.modal-header h3{font-size:15px;font-weight:700}
.modal-close{background:transparent;border:none;color:var(--muted);font-size:18px;padding:3px}
.modal-close:hover{color:var(--text)}
.modal-body{padding:18px 22px}
.form-group{margin-bottom:14px}
.form-group label{display:block;font-size:10px;font-weight:700;color:var(--muted);
  margin-bottom:5px;text-transform:uppercase;letter-spacing:.8px}
.form-control{width:100%;background:var(--card);border:1px solid var(--border2);
  border-radius:8px;padding:8px 11px;color:var(--text);font-size:12px;
  outline:none;transition:border-color .15s}
.form-control:focus{border-color:var(--accent)}
select.form-control option{background:#1a2d4f}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.checkbox-grid{display:flex;flex-wrap:wrap;gap:6px}
.emp-check{display:flex;align-items:center;gap:6px;padding:5px 9px;border-radius:7px;
  background:var(--card);border:1px solid var(--border);cursor:pointer;
  font-size:11px;transition:all .12s}
.emp-check input{accent-color:var(--accent)}
.emp-check:hover{border-color:var(--border2)}
.modal-footer{padding:14px 22px;border-top:1px solid var(--border);
  display:flex;justify-content:flex-end;gap:9px}

/* ── TOAST ───────────────────────────────────────────────── */
.toast-container{position:fixed;bottom:18px;right:18px;
  display:flex;flex-direction:column;gap:7px;z-index:200}
.toast{padding:10px 16px;border-radius:9px;font-size:12px;font-weight:600;
  display:flex;align-items:center;gap:9px;animation:slideIn .25s ease;box-shadow:var(--shadow)}
.toast-success{background:#052e10;color:#6ed88a;border:1px solid #0d4f1f}
.toast-error{background:#2e0505;color:#f29295;border:1px solid #7f1d1d}
.toast-info{background:#051633;color:#90b8f8;border:1px solid #0d2957}
@keyframes slideIn{from{transform:translateX(110%);opacity:0}to{transform:translateX(0);opacity:1}}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="logo">
    <div class="logo-icon">📅</div>
    CalMgr
    <span class="logo-badge">Gemini</span>
  </div>
  <div class="nav-center">
    <button class="btn btn-icon" onclick="changeMonth(-1)">◀</button>
    <div class="month-title" id="monthTitle">—</div>
    <button class="btn btn-icon" onclick="changeMonth(1)">▶</button>
    <button class="btn btn-sm" onclick="goToday()">Today</button>
  </div>
  <div style="display:flex;align-items:center;gap:7px;margin-left:auto">
    <div class="tab-group">
      <button class="tab active" id="tab-cal"    onclick="switchView('calendar')">Calendar</button>
      <button class="tab"        id="tab-leaves" onclick="switchView('leaves')">Leaves</button>
    </div>
    <button class="btn btn-primary btn-sm" onclick="openModal('meeting')">+ Meeting</button>
    <button class="btn btn-sm" onclick="openModal('leave')">🏖️ Leave</button>
    <button class="btn btn-sm" id="syncBtn" onclick="syncEmployees()" title="Re-sync from Google Sheet">🔄 Sync</button>
  </div>
</div>

<!-- LAYOUT -->
<div class="layout">

  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-label">Team Members</div>
      <div id="employeeList"></div>
    </div>
    <div class="sidebar-section" style="border-top:1px solid var(--border)">
      <div class="sidebar-label">Legend</div>
      <div class="legend-item"><div class="legend-dot" style="background:#4285f4"></div>Local Meeting</div>
      <div class="legend-item"><div class="legend-dot" style="background:#34a853"></div>Google Calendar</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fbbc04"></div>Leave Pending</div>
      <div class="legend-item"><div class="legend-dot" style="background:#34a853;opacity:.6"></div>Leave Approved</div>
      <div class="legend-item"><div class="legend-dot" style="background:#ea4335"></div>Leave Rejected</div>
    </div>
  </div>

  <!-- MAIN -->
  <div class="main">
    <div id="view-calendar" class="calendar-wrap">
      <div class="cal-header-row">
        <div class="day-label">Sun</div><div class="day-label">Mon</div>
        <div class="day-label">Tue</div><div class="day-label">Wed</div>
        <div class="day-label">Thu</div><div class="day-label">Fri</div>
        <div class="day-label">Sat</div>
      </div>
      <div class="cal-grid" id="calGrid"></div>
    </div>

    <div id="view-leaves" class="table-view" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div style="font-size:13px;font-weight:700">All Leave Requests</div>
        <select class="form-control" style="width:auto;font-size:11px"
          onchange="filterLeaves(this.value)" id="leaveFilter">
          <option value="">All Employees</option>
        </select>
      </div>
      <table class="data-table">
        <thead><tr>
          <th>Employee</th><th>Type</th><th>From</th><th>To</th>
          <th>Reason</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody id="leaveTableBody"></tbody>
      </table>
    </div>
  </div>

  <!-- AI PANEL -->
  <div class="ai-panel">
    <div class="ai-header">
      🤖 CalendarBot
      <span class="ai-header-badge">Gemini</span>
    </div>
    <div class="ai-messages" id="aiMessages">
      <div class="msg msg-bot">Hi! 👋 I'm CalendarBot, powered by Gemini. I can schedule meetings on Google Calendar, apply for leaves, and check team availability. Just ask!</div>
    </div>
    <div class="quick-chips">
      <div class="quick-chip" onclick="sendQuick('Show this month events')">📅 This month</div>
      <div class="quick-chip" onclick="sendQuick('Who is on leave today?')">🏖️ On leave</div>
      <div class="quick-chip" onclick="sendQuick('List all employees')">👥 Team</div>
      <div class="quick-chip" onclick="sendQuick('Check my availability today')">✅ My availability</div>
    </div>
    <div class="ai-input-row">
      <textarea class="ai-input" id="aiInput" rows="1"
        placeholder="Ask Gemini anything…"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage();}"></textarea>
      <button class="ai-send" onclick="sendMessage()">➤</button>
    </div>
  </div>
</div>

<!-- MEETING MODAL -->
<div class="overlay" id="meetingModal">
  <div class="modal">
    <div class="modal-header">
      <h3>📅 Schedule Meeting → Google Calendar</h3>
      <button class="modal-close" onclick="closeModal('meeting')">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label>Title *</label>
        <input type="text" class="form-control" id="m-title" placeholder="e.g. Sprint Planning">
      </div>
      <div class="form-group">
        <label>Description / Agenda</label>
        <textarea class="form-control" id="m-desc" rows="2" placeholder="What's this meeting about?"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Date *</label>
          <input type="date" class="form-control" id="m-date">
        </div>
        <div class="form-group">
          <label>Location</label>
          <input type="text" class="form-control" id="m-loc" value="Online">
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Start *</label>
          <input type="time" class="form-control" id="m-start">
        </div>
        <div class="form-group">
          <label>End *</label>
          <input type="time" class="form-control" id="m-end">
        </div>
      </div>
      <div class="form-group">
        <label>Meeting Link (Google Meet / Zoom)</label>
        <input type="url" class="form-control" id="m-link" placeholder="https://meet.google.com/...">
      </div>
      <div class="form-group">
        <label>Organizer *</label>
        <select class="form-control" id="m-organizer"></select>
      </div>
      <div class="form-group">
        <label>Invite Attendees</label>
        <div class="checkbox-grid" id="m-attendees"></div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('meeting')">Cancel</button>
      <button class="btn btn-primary" onclick="submitMeeting()">Schedule on GCal 📅</button>
    </div>
  </div>
</div>

<!-- LEAVE MODAL -->
<div class="overlay" id="leaveModal">
  <div class="modal">
    <div class="modal-header">
      <h3>🏖️ Apply for Leave</h3>
      <button class="modal-close" onclick="closeModal('leave')">✕</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label>Employee *</label>
        <select class="form-control" id="l-employee"></select>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>From *</label>
          <input type="date" class="form-control" id="l-start">
        </div>
        <div class="form-group">
          <label>To *</label>
          <input type="date" class="form-control" id="l-end">
        </div>
      </div>
      <div class="form-group">
        <label>Leave Type</label>
        <select class="form-control" id="l-type">
          <option value="casual">Casual Leave</option>
          <option value="sick">Sick Leave</option>
          <option value="earned">Earned Leave</option>
        </select>
      </div>
      <div class="form-group">
        <label>Reason</label>
        <textarea class="form-control" id="l-reason" rows="2" placeholder="Brief reason…"></textarea>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('leave')">Cancel</button>
      <button class="btn btn-primary" onclick="submitLeave()">Apply Leave 🏖️</button>
    </div>
  </div>
</div>

<div class="toast-container" id="toastContainer"></div>

<script>
let now = new Date();
let viewYear = now.getFullYear(), viewMonth = now.getMonth() + 1;
let employees = [], calData = {meetings:[], leaves:[]};
let allLeaves = [], leaveFilter = '', currentView = 'calendar', currentUser = 1;
const MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December'];

async function init() { await loadEmployees(); await refresh(); }

async function loadEmployees() {
  const r = await fetch('/api/employees'); employees = await r.json();
  renderSidebar(); populateSelects();
}
async function refresh() {
  currentView === 'calendar' ? await loadCalendar() : await loadLeaves();
}
async function loadCalendar() {
  const r = await fetch(`/api/calendar/${viewYear}/${viewMonth}`);
  calData = await r.json(); renderCalendar();
}
async function loadLeaves() {
  const url = leaveFilter ? `/api/leaves?employee_id=${leaveFilter}` : '/api/leaves';
  const r = await fetch(url); allLeaves = await r.json(); renderLeaveTable();
}

function changeMonth(d) {
  viewMonth += d;
  if (viewMonth > 12) { viewMonth = 1; viewYear++; }
  if (viewMonth < 1)  { viewMonth = 12; viewYear--; }
  refresh();
}
function goToday() { viewYear = now.getFullYear(); viewMonth = now.getMonth()+1; refresh(); }
function switchView(v) {
  currentView = v;
  document.getElementById('view-calendar').style.display = v==='calendar' ? 'block' : 'none';
  document.getElementById('view-leaves').style.display   = v==='leaves'   ? 'block' : 'none';
  document.getElementById('tab-cal').classList.toggle('active', v==='calendar');
  document.getElementById('tab-leaves').classList.toggle('active', v==='leaves');
  refresh();
}
function filterLeaves(val) { leaveFilter = val; loadLeaves(); }

function renderSidebar() {
  document.getElementById('employeeList').innerHTML = employees.map(e => `
    <div class="employee-item ${e.id===currentUser?'active':''}" onclick="setUser(${e.id})">
      <div class="avatar" style="background:${e.avatar_color}">${e.name.split(' ').map(n=>n[0]).join('')}</div>
      <div style="flex:1;overflow:hidden">
        <div class="emp-name">${e.name}</div>
        <div class="emp-dept">${e.department||''} ${e.role==='manager'?'<span class="role-badge">MGR</span>':''}</div>
      </div>
    </div>`).join('');
  const f = document.getElementById('leaveFilter');
  if (f) f.innerHTML = '<option value="">All Employees</option>' +
    employees.map(e=>`<option value="${e.id}">${e.name}</option>`).join('');
}
function setUser(id) {
  currentUser = id;
  document.querySelectorAll('.employee-item').forEach((el,i) =>
    el.classList.toggle('active', employees[i]?.id === id));
}
function populateSelects() {
  const opts = employees.map(e=>`<option value="${e.id}">${e.name} (${e.department||''})</option>`).join('');
  document.getElementById('m-organizer').innerHTML = opts;
  document.getElementById('l-employee').innerHTML  = opts;
  document.getElementById('m-attendees').innerHTML = employees.map(e=>`
    <label class="emp-check">
      <input type="checkbox" value="${e.id}" class="att-check">
      <div class="avatar" style="background:${e.avatar_color};width:18px;height:18px;font-size:8px">
        ${e.name.split(' ').map(n=>n[0]).join('')}</div>
      ${e.name.split(' ')[0]}
    </label>`).join('');
}

function renderCalendar() {
  document.getElementById('monthTitle').textContent = `${MONTHS[viewMonth-1]} ${viewYear}`;
  const grid = document.getElementById('calGrid');
  const first = new Date(viewYear, viewMonth-1, 1).getDay();
  const days  = new Date(viewYear, viewMonth, 0).getDate();
  const prev  = new Date(viewYear, viewMonth-1, 0).getDate();
  const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;

  let cells = [];
  for (let i=first-1;i>=0;i--) cells.push({day:prev-i,thisMonth:false});
  for (let d=1;d<=days;d++)     cells.push({day:d,thisMonth:true});
  while (cells.length%7!==0)    cells.push({day:cells.length-first-days+1,thisMonth:false});

  grid.innerHTML = cells.map(cell => {
    if (!cell.thisMonth) return `<div class="cal-cell other-month"><div class="date-num">${cell.day}</div></div>`;
    const ds = `${viewYear}-${String(viewMonth).padStart(2,'0')}-${String(cell.day).padStart(2,'0')}`;
    const isToday = ds === todayStr;
    const dm = calData.meetings.filter(m=>m.date===ds);
    const dl = calData.leaves.filter(l=>l.start_date<=ds&&l.end_date>=ds);
    const all = [...dm.map(m=>({type:'meeting',m})), ...dl.map(l=>({type:'leave',l}))];
    const shown = all.slice(0,3), extra = all.length-3;
    const pills = shown.map(ev => {
      if (ev.type==='meeting') {
        const cls = ev.m.source==='gcal' ? 'gcal-pill' : 'meeting-pill';
        return `<div class="event-pill ${cls}" title="${ev.m.title}">${ev.m.start_time} ${ev.m.title}</div>`;
      }
      const cls = ev.l.status==='approved'?'approved-pill':ev.l.status==='rejected'?'rejected-pill':'pending-pill';
      return `<div class="event-pill leave-pill ${cls}">${ev.l.employee_name.split(' ')[0]} 🏖️</div>`;
    }).join('');
    return `<div class="cal-cell ${isToday?'today':''}" onclick="clickDay('${ds}')">
      <div class="date-num">${isToday?`<div class="today-dot">${cell.day}</div>`:cell.day}</div>
      ${pills}${extra>0?`<div class="more-badge">+${extra} more</div>`:''}
    </div>`;
  }).join('');
}

function clickDay(ds) { document.getElementById('m-date').value=ds; openModal('meeting'); }

function renderLeaveTable() {
  const body = document.getElementById('leaveTableBody');
  if (!allLeaves.length) {
    body.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:36px;color:var(--muted)">No leave requests</td></tr>`;
    return;
  }
  body.innerHTML = allLeaves.map(l => {
    const cls = l.status==='approved'?'s-approved':l.status==='rejected'?'s-rejected':'s-pending';
    const emp = employees.find(e=>e.id===l.employee_id);
    const init = (l.employee_name||'?').split(' ').map(n=>n[0]).join('');
    return `<tr>
      <td style="display:flex;align-items:center;gap:7px">
        <div class="avatar" style="background:${emp?.avatar_color||'#4285f4'};width:26px;height:26px;font-size:10px">${init}</div>
        <div>
          <div style="font-weight:600">${l.employee_name}</div>
          <div style="font-size:10px;color:var(--muted)">${l.department||''}</div>
        </div>
      </td>
      <td><span class="status-badge" style="background:rgba(66,133,244,.12);color:#90b8f8">${l.leave_type}</span></td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${l.start_date}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px">${l.end_date}</td>
      <td style="color:var(--muted);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.reason||'—'}</td>
      <td><span class="status-badge ${cls}">${l.status}</span></td>
      <td><div class="action-row">
        ${l.status==='pending'?`
        <button class="btn btn-sm" style="background:rgba(52,168,83,.12);color:#6ed88a;border-color:#1a5c30" onclick="setLeaveStatus(${l.id},'approved')">✓</button>
        <button class="btn btn-sm" style="background:rgba(234,67,53,.1);color:#f29295;border-color:#7f1d1d"  onclick="setLeaveStatus(${l.id},'rejected')">✕</button>`:''}
        <button class="btn btn-sm" onclick="deleteLeave(${l.id})">🗑</button>
      </div></td>
    </tr>`;
  }).join('');
}

function openModal(type) {
  document.getElementById(type==='meeting'?'meetingModal':'leaveModal').classList.add('open');
  if (type==='meeting' && !document.getElementById('m-date').value)
    document.getElementById('m-date').value = new Date().toISOString().split('T')[0];
  if (type==='leave') {
    const t = new Date().toISOString().split('T')[0];
    document.getElementById('l-start').value = t;
    document.getElementById('l-end').value   = t;
    document.getElementById('l-employee').value = currentUser;
  }
}
function closeModal(type) {
  document.getElementById(type==='meeting'?'meetingModal':'leaveModal').classList.remove('open');
}
document.querySelectorAll('.overlay').forEach(el =>
  el.addEventListener('click', e => { if(e.target===el) el.classList.remove('open'); }));

async function submitMeeting() {
  const title = document.getElementById('m-title').value.trim();
  const date  = document.getElementById('m-date').value;
  const start = document.getElementById('m-start').value;
  const end   = document.getElementById('m-end').value;
  const org   = parseInt(document.getElementById('m-organizer').value);
  if (!title||!date||!start||!end) { toast('Fill all required fields','error'); return; }
  const attendees = [...document.querySelectorAll('.att-check:checked')]
    .map(el=>parseInt(el.value)).filter(id=>id!==org);
  const r = await fetch('/api/meetings',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({title,date,start_time:start,end_time:end,
      organizer_id:org,attendee_ids:attendees,
      description:document.getElementById('m-desc').value,
      location:document.getElementById('m-loc').value,
      meeting_link:document.getElementById('m-link').value})});
  const d = await r.json();
  if (r.ok) { toast(d.gcal_event_id?'Scheduled on Google Calendar! 📅':'Scheduled (GCal unavailable)','success');
    closeModal('meeting'); document.getElementById('m-title').value=''; await refresh();
  } else { toast(d.detail||'Error','error'); }
}

async function submitLeave() {
  const emp=parseInt(document.getElementById('l-employee').value);
  const start=document.getElementById('l-start').value;
  const end=document.getElementById('l-end').value;
  if (!start||!end) { toast('Select dates','error'); return; }
  const r = await fetch('/api/leaves',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({employee_id:emp,start_date:start,end_date:end,
      leave_type:document.getElementById('l-type').value,
      reason:document.getElementById('l-reason').value})});
  const d = await r.json();
  if (r.ok) { toast('Leave applied! 🏖️','success');
    closeModal('leave'); document.getElementById('l-reason').value=''; await refresh();
  } else { toast(d.detail||'Error','error'); }
}

async function setLeaveStatus(id,status) {
  const r = await fetch(`/api/leaves/${id}/status`,{method:'PUT',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
  if (r.ok) { toast(`Leave ${status} ✓`,'success'); await refresh(); }
}
async function deleteLeave(id) {
  if (!confirm('Delete this leave request?')) return;
  await fetch(`/api/leaves/${id}`,{method:'DELETE'}); await refresh();
}

function sendQuick(msg) { document.getElementById('aiInput').value=msg; sendMessage(); }
async function sendMessage() {
  const input = document.getElementById('aiInput');
  const text  = input.value.trim();
  if (!text) return;
  input.value = '';
  appendMsg(text,'user');
  const typing = appendMsg('Thinking…','bot typing');
  try {
    const r = await fetch('/api/agent',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text,employee_id:currentUser})});
    const d = await r.json();
    typing.remove();
    appendMsg(d.reply||'Done ✓','bot');
    await refresh();
  } catch(e) { typing.remove(); appendMsg('Connection error.','bot'); }
}
function appendMsg(text,type) {
  const msgs = document.getElementById('aiMessages');
  const div  = document.createElement('div');
  div.className = `msg msg-${type.includes('user')?'user':'bot'}${type.includes('typing')?' typing':''}`;
  div.textContent = text;
  msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function toast(msg,type='info') {
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `${type==='success'?'✅':type==='error'?'❌':'ℹ️'} ${msg}`;
  c.appendChild(t);
  setTimeout(()=>{t.style.opacity='0';t.style.transform='translateX(110%)';
    t.style.transition='all .3s';setTimeout(()=>t.remove(),300);},3500);
}

async function syncEmployees() {
  const btn = document.getElementById('syncBtn');
  btn.textContent='⏳…'; btn.disabled=true;
  try {
    const r = await fetch('/api/sync-employees',{method:'POST'});
    const d = await r.json();
    toast(r.ok ? d.message : (d.detail||'Sync failed'), r.ok?'success':'error');
    if (r.ok) { await loadEmployees(); await refresh(); }
  } catch(e) { toast('Sync error: '+e.message,'error'); }
  finally { btn.textContent='🔄 Sync'; btn.disabled=false; }
}

init();
</script>
</body>
</html>"""

@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTML_UI

# ════════════════════════════════════════════════════════════
#  LMS ROUTES & HELPERS  (moved from main.py)
# ════════════════════════════════════════════════════════════

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from fastapi import Query
from fastapi.responses import FileResponse, HTMLResponse, Response

# ── LMS Imports ───────────────────────────────────────────────────────────────
try:
    from agents.AIChat import AIChatAgent, ORIGINAL_SOPS_DIR, load_sops
    from agents import Career
    from agents.Course_generator import CourseGeneratorAgent
    from agents.Growth_tracker import (
        get_course_quiz_for_employee,
        get_employee_progress_report,
        get_team_progress_overview,
        init_growth_tracker_db,
        list_published_courses,
        publish_generated_course,
        submit_course_quiz,
    )
    from services.sheets import (
        authenticate_user,
        get_departments,
        get_sheets_api,
    )
    from whats_new_routes import router as whats_new_router
    _LMS_AVAILABLE = True
except ImportError as e:
    print(f"WARN: LMS modules not fully available: {e}")
    _LMS_AVAILABLE = False

# ── Gemini setup ──────────────────────────────────────────────────────────────
try:
    from google import genai  # type: ignore

    _GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
    _gemini_client = None
    _gemini_model_name = "gemini-1.5-flash"
    
    if _GEMINI_KEY:
        _gemini_client = genai.Client(api_key=_GEMINI_KEY)
        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
            try:
                _gemini_client.models.generate_content(model=model_name, contents="test")
                _gemini_model_name = model_name
                print(f"[Gemini] Using model: {_gemini_model_name}")
                break
            except Exception:
                continue
except ImportError:
    _gemini_client = None
except Exception as e:
    print(f"⚠️  Gemini initialization error: {e}")
    _gemini_client = None


def _gemini(prompt: str, system: str = "") -> str:
    if _gemini_client is None:
        return _gemini_fallback(prompt, system)
    try:
        full = f"{system}\n\n{prompt}" if system else prompt
        return _gemini_client.models.generate_content(model=_gemini_model_name, contents=full).text.strip()
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini error: {exc}")
        return _gemini_fallback(prompt, system)


def _gemini_fallback(prompt: str, system: str = "") -> str:
    """Fallback response generator when Gemini is unavailable."""
    if "progress" in prompt.lower() or "analysis" in prompt.lower():
        return "📊 Your learning journey is progressing well! Here's what I see: You're building consistent habits and exploring new topics. Keep up the momentum by setting specific weekly goals for yourself. Remember, quality learning matters more than quantity. Pick one area to focus on this week and dive deep!"
    elif "recommend" in prompt.lower() or "course" in prompt.lower():
        return "📚 Great question! Based on your profile, I'd suggest exploring advanced courses in your field. Start with foundational courses if you're new, then move to specialized topics. What specific skills are you trying to develop?"
    elif "quiz" in prompt.lower() or "score" in prompt.lower():
        return "🎯 Quiz performance is key to mastery! Try these strategies: Review each wrong answer deeply, practice daily for 30 mins, and take practice tests in your weak areas. Consistency beats intensity every time!"
    elif "goal" in prompt.lower() or "plan" in prompt.lower():
        return "🎯 Let's build a smart learning plan! First, tell me your main career goal this quarter. Then share 2-3 skills you want to develop. I'll create a personalized roadmap with specific courses and timelines."
    else:
        return "I'm here to help you grow! Ask me about your learning progress, course recommendations, quiz strategies, or goal planning. What would you like to know?"


# ── Profile DB helpers ────────────────────────────────────────────────────────

# Profile helpers now use mongo_db directly...


def _get_progress_summary(user_id: str) -> dict:
    try:
        # Aggregation for count and average score
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$user_id",
                "cnt": {"$sum": 1},
                "avg": {"$avg": "$score"}
            }}
        ]
        results = mongo_db.aggregate("quiz_results", pipeline)
        if results:
            row = results[0]
            return {
                "courses_done": row.get("cnt", 0),
                "avg_score": round(row.get("avg", 0) or 0, 1),
            }
        return {"courses_done": 0, "avg_score": 0.0}
    except Exception:
        return {"courses_done": 0, "avg_score": 0.0}


# ── Pydantic models ───────────────────────────────────────────────────────────

class AIChatRequest(BaseModel):
    query: str
    department: Optional[str] = None
    employeeName: Optional[str] = None


class LoginRequest(BaseModel):
    userId: str
    userName: str
    password: str
    department: str


class CourseGenerationRequest(BaseModel):
    department: str
    relatedQueries: Optional[list[str]] = None


class PublishCourseRequest(BaseModel):
    """
    Accepts both legacy PDF-based payloads and newer DB-backed HTML payloads.
    """
    model_config = {"extra": "allow"}
    department: str = ""
    title: str = ""
    summary: str = ""
    audience: str = ""
    generated_at: str = ""
    db_course_id: str = "0"
    pdf_path: str = ""
    pdf_filename: Optional[str] = None
    index_html_path: str = ""
    index_html_filename: str = ""
    index_html: Optional[dict[str, Any]] = None
    source_notes: list[str] = []
    modules: list[dict] = []
    modules_html: list[dict] = []
    module_htmls: list[dict] = []
    quiz_questions: list[dict] = []


class QuizSubmissionRequest(BaseModel):
    answers: list[dict]


class ProfileUpdateRequest(BaseModel):
    bio:        str       = ""
    phone:      str       = ""
    linkedin:   str       = ""
    goals:      str       = ""
    skills:     list[str] = []
    avatar_url: str       = ""


class MonitoringChatRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str
    message:    str
    history:    list[dict] = []


class MonitoringInsightsRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str


# ── Cached agents ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_ai_chat_agent() -> AIChatAgent:
    return AIChatAgent()


@lru_cache(maxsize=1)
def get_course_generator_agent() -> CourseGeneratorAgent:
    return CourseGeneratorAgent()


# ── Course DB singleton ───────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_course_db():
    from agents.Course_database import CourseDatabase
    db = CourseDatabase()
    db.init_schema()
    return db


# ── Startup ──
# (No longer using @router.on_event("startup") to avoid lifespan conflict in main.py)


# ── LMS Routes ────────────────────────────────────────────────────────────────

@router.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing required field: query")
    agent = get_ai_chat_agent()
    return agent.answer(
        query=query,
        department=req.department,
        employee_name=req.employeeName or "",
    )


@router.post("/api/login")
async def login_alias(req: LoginRequest):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    user = authenticate_user(req.userId, req.userName, req.password, req.department)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    normalized_user = {
        "id":         str(user.get("userId", "")),
        "name":       user.get("userName", ""),
        "department": user.get("department", ""),
        "role":       user.get("role", "Employee"),
        "email":      user.get("email", ""),
    }
    token = _create_auth_token(normalized_user)

    return {
        "success": True,
        "user": {
            "userId":     normalized_user["id"],
            "userName":   normalized_user["name"],
            "department": normalized_user["department"],
            "role":       normalized_user["role"],
            "token":      token,
        },
        "token": token,
    }


@router.get("/api/employees")
async def get_employees(authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    """Get all employees from Google Sheets."""
    try:
        _get_current_user(authorization)  # Require auth
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        sheets_api = get_sheets_api()
        if not sheets_api:
            return {
                "success": False,
                "error": "Google Sheets API not configured",
                "employees": [],
            }

        result = sheets_api.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="EmployeeDB!A:F"
        ).execute()

        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            return {"success": True, "employees": []}

        employees = []
        for row in rows[1:]:
            if len(row) < 4:
                continue
            try:
                employee = {
                    "id":         row[0] if len(row) > 0 else "",
                    "userId":     row[0] if len(row) > 0 else "",
                    "userName":   row[1] if len(row) > 1 else "",
                    "name":       row[1] if len(row) > 1 else "",
                    "department": row[2] if len(row) > 2 else "General",
                    "role":       row[3] if len(row) > 3 else "Employee",
                    "status":     row[4] if len(row) > 4 else "Active",
                }
                employees.append(employee)
            except (IndexError, KeyError):
                continue

        return {
            "success": True,
            "employees": employees,
            "total": len(employees),
        }

    except Exception as e:
        print(f"Error fetching employees: {e}")
        return {
            "success": False,
            "error": str(e),
            "employees": [],
        }


@router.get("/api/courses")
async def courses_by_department(department: str = Query(...)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    published_courses = list_published_courses(department)
    return [
        {
            "id":               f"generated-{c['id']}",
            "title":            c["title"],
            "dept":             c["department"],
            "dur":              "1.5 hrs",
            "level":            "Generated",
            "progress":         0,
            "status":           "Assigned",
            "icon":             "📄",
            "bg":               "linear-gradient(135deg, hsl(22 85% 42%), hsl(34 83% 52%))",
            "source":           "generated",
            "publishedCourseId": c["id"],
            "pdf_url":          c["pdf_url"],
            "index_html_url":   c.get("index_html_url", ""),
            "modules_html":     c.get("modules_html", []),
            "summary":          c["summary"],
            "hasQuiz":          bool(c.get("quiz_questions")),
        }
        for c in published_courses
    ]


@router.post("/api/course-generator")
async def generate_course(req: CourseGenerationRequest, authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    department = (req.department or "").strip()
    if not department:
        raise HTTPException(status_code=400, detail="Department is required")
    
    agent = get_course_generator_agent()
    try:
        print(f"[CourseGen] Generating course for department: {department}")
        print(f"[CourseGen] Queries: {req.relatedQueries or []}")
        result = agent.generate_course_package(
            department=department,
            related_queries=req.relatedQueries or [],
        )
        print(f"[CourseGen] Course generated successfully")
        return result
    except Exception as exc:
        print(f"[CourseGen] Course generation error: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Course generation failed: {str(exc)}") from exc


@router.get("/api/generated-courses")
async def list_generated_courses(authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Admin", "Manager"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can view generated course publishing data")
    return list_published_courses()


@router.get("/api/generated-courses/file/{filename}")
async def get_generated_course_file(filename: str):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    BASE_DIR = Path(__file__).resolve().parent.parent
    file_path = (BASE_DIR / "data" / "generated_courses" / Path(filename).name).resolve()
    allowed_dir = (BASE_DIR / "data" / "generated_courses").resolve()
    if allowed_dir not in file_path.parents or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    ext = file_path.suffix.lower()
    mtype = "application/pdf"
    if ext == ".html": mtype = "text/html"
    elif ext == ".css": mtype = "text/css"
    elif ext == ".js": mtype = "application/javascript"
    
    if ext in {".html", ".css", ".js"}:
        return FileResponse(file_path, media_type=mtype)
    return FileResponse(file_path, media_type=mtype, filename=file_path.name)


@router.get("/api/generated-courses/download/{course_id}/index")
async def download_course_index_html(course_id: str, as_file: bool = False):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    try:
        db = _get_course_db()
        html, filename = db.get_html_for_download(course_id, "index")
        if not html:
            raise ValueError("No index HTML found for this course")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Course not found: {exc}") from exc

    if as_file:
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=html, media_type="text/html", headers=headers)
    return HTMLResponse(content=html)


@router.get("/api/generated-courses/download/{course_id}/exam")
async def download_course_exam_html(course_id: str, as_file: bool = False):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    try:
        db = _get_course_db()
        html, filename = db.get_html_for_download(course_id, "exam")
        if not html:
            raise ValueError("No exam HTML found for this course")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Course not found: {exc}") from exc

    if as_file:
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=html, media_type="text/html", headers=headers)
    return HTMLResponse(content=html)


@router.get("/api/generated-courses/download/{course_id}/module/{module_index}")
async def download_course_module_html(course_id: str, module_index: int, as_file: bool = False):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    try:
        db = _get_course_db()
        html, filename = db.get_html_for_download(course_id, f"module:{module_index}")
        if not html:
            raise ValueError(f"No HTML found for module {module_index}")
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Module not found: {exc}") from exc

    if as_file:
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=html, media_type="text/html", headers=headers)
    return HTMLResponse(content=html)


@router.post("/api/update-progress")
async def api_update_progress_route(body: dict, authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    try:
        current_user = _get_current_user(authorization)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    
    if not body.get("module_id"):
        raise HTTPException(status_code=400, detail="module_id is required")
    
    if body.get("score") is None:
        raise HTTPException(status_code=400, detail="score is required")
    
    try:
        score = int(body.get("score", 0))
        if not (0 <= score <= 100):
            raise ValueError("score must be between 0 and 100")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="score must be a number between 0 and 100") from exc
    
    try:
        from agents.Growth_tracker import api_update_progress
        result = api_update_progress(
            module_id=str(body.get("module_id", "")).strip(),
            score=score,
            employee_id=str(current_user.get("sub", current_user.get("id", ""))),
            employee_name=current_user.get("name", ""),
            department=current_user.get("department", ""),
            role=current_user.get("role", "Employee"),
            module_title=str(body.get("module_title", "")).strip(),
            course_title=str(body.get("course_title", "")).strip(),
            source=str(body.get("source", "html")).strip(),
        )
        return result
    except Exception as exc:
        print(f"Error updating progress: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to record progress: {str(exc)}") from exc


@router.post("/api/generated-courses/publish")
async def publish_course(req: PublishCourseRequest, authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Admin", "Manager"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can publish generated courses")
    try:
        return publish_generated_course(req.model_dump(), created_by=current_user.get("name", ""))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to publish course: {exc}") from exc




@router.get("/api/progress-report")
async def get_progress_report(authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    current_user = _get_current_user(authorization)
    return get_employee_progress_report(str(current_user.get("sub", current_user.get("id", ""))))


@router.get("/api/progress-overview")
async def get_progress_overview(authorization: Optional[str] = Header(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Manager", "Admin"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can view team progress reports")
    return get_team_progress_overview(
        viewer_role=current_user.get("role", ""),
        viewer_department=current_user.get("department", ""),
    )


@router.get("/api/sops")
async def list_sops(department: Optional[str] = Query(default=None)):
    if not _LMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="LMS not available")
    normalized_department = (department or "").strip().lower()
    sops = load_sops()
    sop_entries = [
        {
            "department": sop.department,
            "title":      sop.title,
            "steps":      sop.steps,
            "keywords":   sop.keywords,
            "escalation": sop.escalation,
        }
        for sop in sops
        if not normalized_department or sop.department.strip().lower() == normalized_department
    ]

    pdf_entries = []
    if ORIGINAL_SOPS_DIR.exists():
        for pdf_path in sorted(ORIGINAL_SOPS_DIR.glob("*.pdf")):
            guessed_department = pdf_path.stem.split("_")[0].replace("-", " ").strip().title()
            if normalized_department and guessed_department.lower() != normalized_department:
                continue
            pdf_entries.append(
                {
                    "department": guessed_department or "General",
                    "title":      pdf_path.stem.replace("_", " ").replace("-", " ").strip().title(),
                    "href":       f"/sops/{pdf_path.name}",
                    "filename":   pdf_path.name,
                }
            )

    return {"entries": sop_entries, "pdfs": pdf_entries}


@router.get("/api/profile/{user_id}")
async def get_profile(user_id: str, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = _get_profile_conn()
    try:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()

        emp_row = conn.execute(
            "SELECT created_at FROM employees WHERE id = ?", (user_id,)
        ).fetchone()
        joined = emp_row["created_at"] if emp_row and emp_row["created_at"] else ""
    finally:
        conn.close()

    progress = _get_progress_summary(user_id)

    if row is None:
        return {
            "user_id":     user_id,
            "bio":         "",
            "avatar_url":  "",
            "skills":      [],
            "goals":       "",
            "phone":       "",
            "linkedin":    "",
            "joined_date": joined,
            **progress,
        }

    return {
        "user_id":     row["user_id"],
        "bio":         row["bio"],
        "avatar_url":  row["avatar_url"],
        "skills":      json.loads(row["skills"] or "[]"),
        "goals":       row["goals"],
        "phone":       row["phone"],
        "linkedin":    row["linkedin"],
        "joined_date": joined,
        **progress,
    }


@router.post("/api/profile/{user_id}")
async def save_profile(
    user_id: str,
    req: ProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(authorization)
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    if len(req.avatar_url) > 2_600_000:
        raise HTTPException(status_code=413, detail="Avatar image exceeds 2 MB limit")

    conn = _get_profile_conn()
    try:
        conn.execute(
            """
            INSERT INTO user_profiles
                (user_id, bio, phone, linkedin, goals, skills, avatar_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                bio        = excluded.bio,
                phone      = excluded.phone,
                linkedin   = excluded.linkedin,
                goals      = excluded.goals,
                skills     = excluded.skills,
                avatar_url = excluded.avatar_url,
                updated_at = datetime('now')
            """,
            (
                user_id,
                req.bio,
                req.phone,
                req.linkedin,
                req.goals,
                json.dumps(req.skills),
                req.avatar_url,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok"}


def _build_monitoring_system_prompt(
    name: str,
    role: str,
    department: str,
    profile: dict | None,
    progress: dict,
    calendar_data: dict | None = None,
) -> str:
    goals  = (profile or {}).get("goals",  "") or "No goals set yet."
    bio    = (profile or {}).get("bio",    "") or "Not provided yet."
    skills = (profile or {}).get("skills", [])
    
    # Format schedule if available
    schedule_text = "No scheduled events found for this month."
    if calendar_data:
        meetings = calendar_data.get("meetings", [])
        leaves = calendar_data.get("leaves", [])
        holidays = calendar_data.get("holidays", [])
        
        schedule_parts = []
        if meetings:
            schedule_parts.append("Meetings: " + ", ".join([f"{m['title']} ({m['date']})" for m in meetings[:5]]))
        if leaves:
            schedule_parts.append("Leaves: " + ", ".join([f"{l['employee_name']} on leave ({l['start_date']} to {l['end_date']})" for l in leaves[:3]]))
        if holidays:
            schedule_parts.append("Holidays: " + ", ".join([f"{h['name']} ({h['date']})" for h in holidays[:3]]))
        
        if schedule_parts:
            schedule_text = "\n".join(schedule_parts)

    return f"""You are Monitoring AI — a warm, deeply personalized learning coach for {name} at NamanDarshan LMS.

## Employee Profile
- Name: {name}
- Role: {role}
- Department: {department}
- Bio: {bio}
- Skills: {", ".join(skills) if skills else "None listed yet"}

## Learning Goals
{goals}

## Current Progress
- Courses completed: {progress.get("courses_done", 0)}
- Average quiz score: {progress.get("avg_score", 0)}%

## Schedule & Availability (Current Context)
{schedule_text}

## Your Coaching Style
- Warm, encouraging, direct — like a brilliant senior mentor who genuinely cares
- Occasionally use Hindi/Sanskrit phrases (Namaste, Shubh, Jai Shri Ram) naturally
- Give SPECIFIC actionable advice; never vague platitudes
- Reference their actual goals, scores, and department in every response
- Keep replies concise (2–4 paragraphs) unless asked for a detailed plan
- End every response with one clear action they can take TODAY
- Help with: learning progress, career growth, skill development, goal tracking, study planning, **schedule management, and professional analytics**.
- If asked about "Analytics", define it in the context of their specific learning data and growth trajectory.
- If asked off-topic, gently redirect them back to their professional development journey.
"""


@router.post("/api/monitoring/chat")
async def monitoring_chat(req: MonitoringChatRequest, authorization: Optional[str] = Header(default=None)):
    _get_current_user(authorization)

    # MongoDB Profile lookup
    profile = mongo_db.find_one("user_profiles", {"user_id": req.user_id})
    if profile:
        profile["skills"] = profile.get("skills") if isinstance(profile.get("skills"), list) else json.loads(profile.get("skills") or "[]")

    from datetime import datetime
    now = datetime.now()
    current_user = _get_current_user(authorization)
    calendar_data = _get_calendar_events(now.year, now.month, current_user)

    progress = _get_progress_summary(req.user_id)
    system   = _build_monitoring_system_prompt(req.name, req.role, req.department, profile, progress, calendar_data)

    history_text = "".join(
        f"{'Employee' if m.get('role') == 'user' else 'Monitoring AI'}: {m.get('text', '')}\n"
        for m in req.history[-8:]
    )
    prompt = f"{history_text}Employee: {req.message}\nMonitoring AI:"

    return {"reply": _gemini(prompt, system=system)}


@router.post("/api/monitoring/insights")
async def monitoring_insights(req: MonitoringInsightsRequest, authorization: Optional[str] = Header(default=None)):
    _get_current_user(authorization)

    # MongoDB Profile lookup
    profile = mongo_db.find_one("user_profiles", {"user_id": req.user_id})
    if profile:
        profile["skills"] = profile.get("skills") if isinstance(profile.get("skills"), list) else json.loads(profile.get("skills") or "[]")

    progress = _get_progress_summary(req.user_id)
    goals    = (profile or {}).get("goals", "None set")
    courses  = progress.get("courses_done", 0)
    score    = progress.get("avg_score", 0)

    prompt = f"""
Generate a personalized daily insights summary for {req.name} ({req.role}, {req.department}).

Facts:
- Courses completed: {courses}
- Average quiz score: {score}%
- Goals: {goals}

Return ONLY valid JSON — no markdown, no backticks:
{{
  "greeting": "A warm 1–2 sentence personalized greeting mentioning their name",
  "insights": [
    {{"type": "tip",         "text": "A specific actionable learning tip for today (under 20 words)"}},
    {{"type": "celebration", "text": "Celebrate something specific about their progress (under 20 words)"}},
    {{"type": "warning",     "text": "One gentle nudge or area to improve (under 20 words)"}}
  ]
}}
"""

    raw = _gemini(prompt)

    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data  = json.loads(clean)
        return {
            "greeting": data.get("greeting", f"Namaste {req.name}! Ready to grow today?"),
            "insights": data.get("insights", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "greeting": f"Namaste {req.name} 🙏 Let's make today count!",
            "insights": [
                {"type": "tip",         "text": f"Focus on one new course in {req.department} today."},
                {"type": "celebration", "text": f"You've completed {courses} course{'s' if courses != 1 else ''} — keep going!"},
                {"type": "warning",     "text": "Set your learning goals in your profile for better AI guidance."},
            ],
        }



#  ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║   🗓️  CALENDAR MANAGER  v2  —  Gemini × Google Calendar  ║
╚══════════════════════════════════════════════════════════╝

  Install:
    pip install fastapi uvicorn google-generativeai python-dotenv \\
                google-api-python-client google-auth

  .env variables:
    GEMINI_API_KEY=your_gemini_key

    # Google Sheets (employee roster)
    SPREADSHEET_ID=your_sheet_id
    GOOGLE_API_KEY=your_google_api_key        # read-only Sheets
    # OR service account (required for Calendar write):
    GOOGLE_SERVICE_ACCOUNT_JSON=/path/key.json
    GOOGLE_SERVICE_ACCOUNT_EMAIL=sa@project.iam.gserviceaccount.com
    GOOGLE_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\\n..."

    # Google Calendar
    GCAL_CALENDAR_ID=primary                  # or specific calendar ID
    GCAL_TIMEZONE=Asia/Kolkata

  Notes:
    • Meetings are pushed to Google Calendar in real-time.
    • AI agent (CalendarBot) is powered by Gemini 1.5 Flash.
    • No SMTP — notifications are logged to this console.
    • Without GCal service account, meetings are stored locally only.
""")
    if __name__ == "__main__":
        uvicorn.run("calendar_manager:app", host="0.0.0.0", port=8000, reload=True)
