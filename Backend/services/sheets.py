from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass

try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    _GOOGLE_OK = True
except Exception:
    _GOOGLE_OK = False

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "").strip()
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()

EMPLOYEES_SHEET = "Employees"
MANAGERS_SHEET = "Manager"
ADMINS_SHEET = "Admin"

DEFAULT_DEPARTMENTS = [
    "Sales",
    "Ops",
    "Sewa",
    "Puja & Pandit",
    "Logistics",
    "Content & SEO",
    "Tech & Stream",
    "Finance",
]

DUMMY_MANAGER_DETAILS = {
    "Sales": {"userId": "MGR001", "userName": "Aarav Sales", "password": "salesmgr123", "email": "sales.manager@namandarshan.com"},
    "Ops": {"userId": "MGR002", "userName": "Diya Ops", "password": "opsmgr123", "email": "ops.manager@namandarshan.com"},
    "Sewa": {"userId": "MGR003", "userName": "Ishaan Sewa", "password": "sewamgr123", "email": "sewa.manager@namandarshan.com"},
    "Puja & Pandit": {"userId": "MGR004", "userName": "Meera Puja", "password": "pujamgr123", "email": "puja.manager@namandarshan.com"},
    "Logistics": {"userId": "MGR005", "userName": "Kabir Logistics", "password": "logmgr123", "email": "logistics.manager@namandarshan.com"},
    "Content & SEO": {"userId": "MGR006", "userName": "Riya Content", "password": "contentmgr123", "email": "content.manager@namandarshan.com"},
    "Tech & Stream": {"userId": "MGR007", "userName": "Vihaan Tech", "password": "techmgr123", "email": "tech.manager@namandarshan.com"},
    "Finance": {"userId": "MGR008", "userName": "Anaya Finance", "password": "finmgr123", "email": "finance.manager@namandarshan.com"},
}

DUMMY_ADMIN = {
    "userId": "ADM001",
    "userName": "Naman Admin",
    "password": "admin123",
    "email": "admin@namandarshan.com",
    "department": "Admin",
    "role": "Admin",
}

DEFAULT_COURSES = [
    {
        "id": 1,
        "title": "Sample Course 1",
        "dur": "2 hrs",
        "level": "Beginner",
        "progress": 0,
        "status": "Not Started",
        "icon": "Book",
        "bg": "linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))",
    },
    {
        "id": 2,
        "title": "Sample Course 2",
        "dur": "4 hrs",
        "level": "Intermediate",
        "progress": 50,
        "status": "In Progress",
        "icon": "Laptop",
        "bg": "linear-gradient(135deg, hsl(220 72% 41%), hsl(213 73% 22%))",
    },
]

_sheets_api = None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _normalized_map(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        normalized["".join(ch for ch in str(key).lower() if ch.isalnum())] = value
    return normalized


def _get_value(row: dict[str, Any], *candidates: str, default: str = "") -> str:
    normalized = _normalized_map(row)
    for candidate in candidates:
        value = normalized.get("".join(ch for ch in candidate.lower() if ch.isalnum()))
        if _clean(value):
            return _clean(value)
    return default


def get_dummy_manager_row(department: str) -> dict[str, Any]:
    safe_department = _clean(department) or "General"
    manager = DUMMY_MANAGER_DETAILS.get(safe_department)
    if not manager:
        slug = "".join(ch for ch in safe_department.lower() if ch.isalnum())[:6] or "general"
        manager = {
            "userId": f"MGR-{slug.upper()}",
            "userName": f"{safe_department} Manager",
            "password": f"{slug}mgr123",
            "email": f"{slug}.manager@namandarshan.com",
        }
    return {
        "User_id": manager["userId"],
        "User_name": manager["userName"],
        "Password": manager["password"],
        "Role": "Manager",
        "Email": manager["email"],
        "Department": safe_department,
    }


def ensure_dummy_manager_row(rows: list[dict[str, Any]], department: str) -> list[dict[str, Any]]:
    normalized_department = _clean(department)
    if not normalized_department:
        return rows
    has_manager = any(_get_value(row, "Role").lower() == "manager" for row in rows)
    if has_manager:
        return rows
    return [get_dummy_manager_row(normalized_department), *rows]


def _make_person(
    *,
    user_id: str,
    user_name: str,
    password: str,
    role: str,
    department: str,
    email: str = "",
) -> dict[str, Any]:
    return {
        "userId": _clean(user_id),
        "userName": _clean(user_name),
        "password": _clean(password),
        "department": _clean(department),
        "role": _clean(role) or "Employee",
        "email": _clean(email),
    }


def _normalize_person_row(
    row: dict[str, Any],
    *,
    fallback_role: str,
    fallback_department: str = "",
) -> dict[str, Any]:
    user_id = _get_value(row, "User_id", "UserId", "Employee ID", "Employee_ID", "ID")
    user_name = _get_value(row, "User_name", "UserName", "Name", "Employee Name", "Employee_Name")
    password = _get_value(row, "Password", "Passcode", "Pwd")
    role = _get_value(row, "Role", default=fallback_role) or fallback_role
    department = _get_value(row, "Dep", "Department", "Dept", default=fallback_department) or fallback_department
    email = _get_value(row, "Email", "Mail", "Email ID", "Email_ID")
    return _make_person(
        user_id=user_id,
        user_name=user_name,
        password=password,
        role=role.title(),
        department=department,
        email=email,
    )


def _make_dummy_manager_people() -> list[dict[str, Any]]:
    return [
        _make_person(
            user_id=details["userId"],
            user_name=details["userName"],
            password=details["password"],
            role="Manager",
            department=department,
            email=details["email"],
        )
        for department, details in DUMMY_MANAGER_DETAILS.items()
    ]


def _make_dummy_employee_people() -> list[dict[str, Any]]:
    return [
        _make_person(
            user_id=f"EMP{index + 1:03d}",
            user_name=f"{department} Employee",
            password="emp123",
            role="Employee",
            department=department,
            email=f"{department.lower().replace(' ', '').replace('&', 'and')}.employee@namandarshan.com",
        )
        for index, department in enumerate(DEFAULT_DEPARTMENTS)
    ]


def _make_dummy_admin_people() -> list[dict[str, Any]]:
    return [
        _make_person(
            user_id=DUMMY_ADMIN["userId"],
            user_name=DUMMY_ADMIN["userName"],
            password=DUMMY_ADMIN["password"],
            role=DUMMY_ADMIN["role"],
            department=DUMMY_ADMIN["department"],
            email=DUMMY_ADMIN["email"],
        )
    ]


def get_sheets_api():
    global _sheets_api
    if _sheets_api is not None:
        return _sheets_api

    if not _GOOGLE_OK:
        return None

    try:
        if GOOGLE_API_KEY:
            _sheets_api = build("sheets", "v4", developerKey=GOOGLE_API_KEY)
            return _sheets_api

        if GOOGLE_SERVICE_ACCOUNT_JSON and Path(GOOGLE_SERVICE_ACCOUNT_JSON).is_file():
            creds = service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_JSON,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            _sheets_api = build("sheets", "v4", credentials=creds)
            return _sheets_api

        if GOOGLE_SERVICE_ACCOUNT_EMAIL and GOOGLE_PRIVATE_KEY:
            creds = service_account.Credentials.from_service_account_info(
                {
                    "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
                    "private_key": GOOGLE_PRIVATE_KEY,
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "type": "service_account",
                },
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            _sheets_api = build("sheets", "v4", credentials=creds)
            return _sheets_api
    except Exception:
        return None

    return None


def _read_sheet_rows(sheet_name: str) -> list[dict[str, Any]]:
    api = get_sheets_api()
    if not api:
        return []

    try:
        response = api.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{sheet_name}'!A:Z",
        ).execute()
        rows = response.get("values", [])
        if not rows:
            return []

        headers = [_clean(header) for header in rows[0]]
        mapped_rows: list[dict[str, Any]] = []
        for row in rows[1:]:
            item = {}
            for index, header in enumerate(headers):
                item[header] = row[index] if index < len(row) else ""
            mapped_rows.append(item)
        return mapped_rows
    except Exception:
        return []


def get_employees_sheet_data() -> list[dict[str, Any]]:
    return _read_sheet_rows(EMPLOYEES_SHEET)


def get_manager_sheet_data() -> list[dict[str, Any]]:
    rows = _read_sheet_rows(MANAGERS_SHEET)
    if rows:
        return rows
    return [get_dummy_manager_row(department) for department in DEFAULT_DEPARTMENTS]


def get_admin_sheet_data() -> list[dict[str, Any]]:
    rows = _read_sheet_rows(ADMINS_SHEET)
    if rows:
        return rows
    return [
        {
            "User_id": DUMMY_ADMIN["userId"],
            "User_name": DUMMY_ADMIN["userName"],
            "Password": DUMMY_ADMIN["password"],
            "Role": DUMMY_ADMIN["role"],
            "Email": DUMMY_ADMIN["email"],
            "Department": DUMMY_ADMIN["department"],
        }
    ]


def get_departments() -> list[str]:
    rows = get_employees_sheet_data()
    if not rows:
        return DEFAULT_DEPARTMENTS

    departments = sorted(
        {
            _get_value(row, "Dep", "Department", "Dept")
            for row in rows
            if _get_value(row, "Dep", "Department", "Dept")
        }
    )
    return departments or DEFAULT_DEPARTMENTS


def get_sheet_data(sheet_name: str) -> list[dict[str, Any]]:
    normalized_name = _clean(sheet_name).lower()
    if normalized_name == EMPLOYEES_SHEET.lower():
        return get_employees_sheet_data()
    if normalized_name == MANAGERS_SHEET.lower():
        return get_manager_sheet_data()
    if normalized_name == ADMINS_SHEET.lower():
        return get_admin_sheet_data()

    employees = get_employees_sheet_data()
    if employees:
        return [
            row
            for row in employees
            if _get_value(row, "Dep", "Department", "Dept").lower() == normalized_name
        ]

    return _read_sheet_rows(sheet_name)


def get_directory_people() -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []

    employee_rows = get_employees_sheet_data()
    if employee_rows:
        for row in employee_rows:
            person = _normalize_person_row(row, fallback_role="Employee")
            if person["userId"] and person["userName"]:
                people.append(person)
    else:
        people.extend(_make_dummy_employee_people())

    manager_rows = get_manager_sheet_data()
    if manager_rows:
        for row in manager_rows:
            person = _normalize_person_row(row, fallback_role="Manager")
            if person["userId"] and person["userName"]:
                people.append(person)
    else:
        people.extend(_make_dummy_manager_people())

    admin_rows = get_admin_sheet_data()
    if admin_rows:
        for row in admin_rows:
            person = _normalize_person_row(row, fallback_role="Admin", fallback_department="Admin")
            if person["userId"] and person["userName"]:
                people.append(person)
    else:
        people.extend(_make_dummy_admin_people())

    return people


def authenticate_user(user_id: str, user_name: str, password: str, department: str) -> dict[str, Any] | None:
    expected_user_id = _clean(user_id)
    expected_user_name = _clean(user_name).lower()
    expected_password = _clean(password)
    expected_department = _clean(department)
    login_scope = expected_department.lower()

    if login_scope == "manager":
        candidates = [
            person
            for person in get_directory_people()
            if person["role"].lower() == "manager"
        ]
    elif login_scope == "admin":
        candidates = [
            person
            for person in get_directory_people()
            if person["role"].lower() == "admin"
        ]
    else:
        candidates = [
            person
            for person in get_directory_people()
            if person["role"].lower() == "employee"
        ]
        if expected_department:
            candidates = [
                person
                for person in candidates
                if person["department"].strip().lower() == login_scope
            ]

    for person in candidates:
        if (
            person["userId"].strip() == expected_user_id
            and person["userName"].strip().lower() == expected_user_name
            and person["password"].strip() == expected_password
        ):
            return {
                "userId": person["userId"],
                "userName": person["userName"],
                "department": person["department"],
                "role": person["role"],
                "email": person["email"],
            }
    return None


def get_courses_by_department(department: str) -> list[dict[str, Any]]:
    api = get_sheets_api()
    if not api:
        return [{**course, "dept": department} for course in DEFAULT_COURSES]

    data = _read_sheet_rows(department)
    courses = []
    for index, row in enumerate(data, start=1):
        title = _get_value(row, "Course Name", "Course_Name", "Title")
        if not title:
            continue
        try:
            progress = int(_get_value(row, "Progress", default="0") or 0)
        except (TypeError, ValueError):
            progress = 0
        courses.append(
            {
                "id": _get_value(row, "ID", "Course_ID", default=str(index)) or index,
                "title": title,
                "dept": department,
                "dur": _get_value(row, "Duration", "Course Duration", default="2 hrs") or "2 hrs",
                "level": _get_value(row, "Level", default="Beginner") or "Beginner",
                "progress": progress,
                "status": _get_value(row, "Status", default="Not Started") or "Not Started",
                "icon": _get_value(row, "Icon", default="Book") or "Book",
                "bg": _get_value(
                    row,
                    "Bg_Gradient",
                    default="linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))",
                )
                or "linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))",
            }
        )
    return courses
