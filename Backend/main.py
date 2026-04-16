from __future__ import annotations

"""
NamanDarshan LMS - Main FastAPI Application
===============================================

Integrated Agents & Services:
---------------------------------------------

1.  AIChatAgent (AIChat.py)
   - Intelligent chatbot for answering user queries
   - Context: department, employee name, SOP knowledge
   - Route: POST /api/ai/chat

2.  CourseGeneratorAgent (Course_generator.py)
   - Generates department-specific training courses
   - Creates PDFs with modules and quiz questions
   - Routes: 
     - POST /api/course-generator
     - POST /api/generated-courses/publish
     - GET /api/generated-courses/file/{filename}

3.  Growth Tracker (Growth_tracker.py)
   - Tracks course completion, quiz scores, progress
   - Provides employee & team progress reports
   - Routes:
     - GET /api/courses (list by department)
     - GET /api/course-assignments/{course_id}
     - POST /api/course-assignments/{course_id}/submit
     - GET /api/progress-report
     - GET /api/progress-overview

4.  Calendar Manager (calendar_manager.py)
   - Manages user authentication & calendars
   - Provides token-based authorization
   - Base app imported and extended with other routers

5.  Career Portal (Career.py)
   - Job search and job board
   - Career interview preparation & ATS optimization
   - CV building & document generation
   - Routes: 
     - GET /api/career/jobs
     - POST /api/career/apply
     - POST /api/career/interview
     - And more...

6.  Monitoring Agent (Monitoring_agent.py)
   - Tracks learning progress & performance metrics
   - Generates insights and recommendations
   - Identif strengths, gaps, and personalized guidance
   - Factory: get_monitoring_agent(user_id, user_data)

7.  Profile Management (integrated in main.py)
   - User profile CRUD operations
   - Skills, goals, avatar, contact info
   - Routes:
     - GET /api/profile/{user_id}
     - POST /api/profile/{user_id}

8.  Monitoring AI Chat (integrated in main.py)
   - Powered by Gemini API
   - Personalized coaching & insights generation
   - Routes:
     - POST /api/monitoring/chat
     - POST /api/monitoring/insights

9.  SOP Management (integrated in main.py)
   - Standard Operating Procedures repository
   - Department-specific guidance
   - Routes:
     - GET /api/sops

10.  Employee Management (integrated in main.py)
    - Authentication & employee roster
    - Routes:
      - POST /api/login
      - GET /api/employees

============================================
"""

import json
import os
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, AliasChoices
import traceback

BASE_DIR = Path(__file__).resolve().parent
AGENTS_DIR = BASE_DIR / "agents"

from agents.auth import authenticate_and_issue_token

load_dotenv(BASE_DIR / ".env")

# Initialize MongoDB
from mongo_db import init_mongodb, get_db as get_mongo_db  # noqa: E402

from agents.AIChat import AIChatAgent, ORIGINAL_SOPS_DIR, load_sops  # noqa: E402
from agents.Career import router as career_router  # noqa: E402
from agents.Profile_routes import router as profile_router  # noqa: E402
from agents.Course_generator import CourseGeneratorAgent  # noqa: E402
from agents.Growth_tracker import (  # noqa: E402
    get_course_quiz_for_employee,
    get_employee_progress_report,
    get_team_progress_overview,
    init_growth_tracker_db,
    list_published_courses,
    publish_generated_course,
    submit_course_quiz,
)
from agents.Monitoring_agent import MonitoringAgent  # noqa: E402
from agents.calendar_manager import router as calendar_router, _get_calendar_events  # noqa: E402
from whats_new_routes import router as whats_new_router  # noqa: E402

from agents.kpi_manager import (  # noqa: E402
    init_kpi_db,
    compute_employee_kpi,
    get_department_kpi,
    get_org_kpi,
    set_work_rating,
)
from agents.profile_manager import (
    CourseGenerationRequest,
    PublishCourseRequest,
    QuizSubmissionRequest,
    ProfileUpdateRequest,
    MonitoringChatRequest,
    MonitoringInsightsRequest,
)

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # -- startup ------------------------------------------
    print("\n  NamanDarshan LMS | General Startup")
    print("  " + ("-" * 52))

    # Initialize MongoDB Connection
    try:
        init_mongodb()
        print("  [Main] MongoDB initialized")
    except Exception as e:
        safe_err = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"  [Main] MongoDB initialization warning: {safe_err}")

    import asyncio
    from agents.calendar_manager import init_db, sync_employees_from_gsheet, get_gcal_api
    from agents.Growth_tracker import init_growth_tracker_db
    from agents.kpi_manager import init_kpi_db
    
    # Initialize DB Schemas
    try:
        init_db()
        init_growth_tracker_db()
        init_kpi_db()
    except Exception as e:
        print(f"  [Main] DB Schema init warning: {e}")
    
    # Run heavy sync in background to avoid blocking port binding
    def run_sync_blocking():
        from agents.calendar_manager import sync_employees_from_gsheet, sync_employees_from_csv, get_gcal_api
        
        # 1. Sync from local CSVs first (high reliability)
        try:
            sync_employees_from_csv()
        except Exception as e:
            print(f"  [Background] Local CSV sync failed: {e}")

        # 2. Sync from Google Sheets (optional real-time source)
        print("  [Background] Syncing employees from Google Sheet...")
        try:
            sync_employees_from_gsheet()
            
            # Diagnostic: how many employees do we have now?
            try:
                emp_count = mongo_db.count_documents("employees")
                print(f"  [Background] Sync complete. Total employees in database: {emp_count}")
            except Exception:
                pass

            print("  [Background] Initializing Google APIs...")
            get_gcal_api()
        except Exception as e:
            print(f"  [Background] Sheets sync failed: {e}")

    # Use to_thread for safe non-blocking execution of sync tasks
    asyncio.create_task(asyncio.to_thread(run_sync_blocking))
    
    port = int(os.environ.get("PORT", 8000))
    print(f"  Server available on port {port} (Binding complete)\n")
    yield

app = FastAPI(title="NamanDarshan LMS", version="2.0", lifespan=lifespan)

# -- PERMANENT CORS FIX (MUST BE FIRST) ----------------------------------------
# We use allow_origins=["*"] for production flexibility between Vercel and Render.
# This ensures that preflight (OPTIONS) requests are never rejected with 405.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://naman-ai-lms.vercel.app",
        "*"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"\n[ERROR] Unhandled Exception at {request.url}")
    print(traceback.format_exc())
    
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check server logs for details."},
    )
    
    # Manually add CORS headers to the error response to avoid "CORS block" in browser
    # instead of the actual error detail.
    response.headers["Access-Control-Allow-Origin"] = "https://naman-ai-lms.vercel.app"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

app.include_router(calendar_router)
app.include_router(whats_new_router)
app.include_router(career_router)
app.include_router(profile_router)
from agents.Course_generator import router as course_gen_router
app.include_router(course_gen_router)


# -- Gemini setup --------------------------------------------------------------

try:
    from google import genai  # type: ignore

    _GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
    _gemini_client = None
    _GEMINI_MODEL_NAME = "gemini-1.5-flash"

    if _GEMINI_KEY:
        _gemini_client = genai.Client(api_key=_GEMINI_KEY)
        print(f"[OK] Gemini client initialised (model: {_GEMINI_MODEL_NAME})")
    else:
        print("[WARN]  GEMINI_API_KEY not set. Falling back to mock responses.")
except ImportError:
    _gemini_client = None
except Exception as e:
    print(f"[WARN]  Gemini initialisation error: {e}")
    _gemini_client = None


def _gemini(prompt: str, system: str = "") -> str:
    if _gemini_client is None:
        return _gemini_fallback(prompt, system)
    try:
        full = f"{system}\n\n{prompt}" if system else prompt
        return _gemini_client.models.generate_content(model=_GEMINI_MODEL_NAME, contents=full).text.strip()
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini error: {exc}")
        return _gemini_fallback(prompt, system)


def _gemini_fallback(prompt: str, system: str = "") -> str:
    """Fallback response generator when Gemini is unavailable."""
    if "progress" in prompt.lower() or "analysis" in prompt.lower():
        return " Your learning journey is progressing well! Here's what I see: You're building consistent habits and exploring new topics. Keep up the momentum by setting specific weekly goals for yourself. Remember, quality learning matters more than quantity. Pick one area to focus on this week and dive deep!"
    elif "recommend" in prompt.lower() or "course" in prompt.lower():
        return " Great question! Based on your profile, I'd suggest exploring advanced courses in your field. Start with foundational courses if you're new, then move to specialized topics. What specific skills are you trying to develop?"
    elif "quiz" in prompt.lower() or "score" in prompt.lower():
        return " Quiz performance is key to mastery! Try these strategies: Review each wrong answer deeply, practice daily for 30 mins, and take practice tests in your weak areas. Consistency beats intensity every time!"
    elif "goal" in prompt.lower() or "plan" in prompt.lower():
        return " Let's build a smart learning plan! First, tell me your main career goal this quarter. Then share 2-3 skills you want to develop. I'll create a personalized roadmap with specific courses and timelines."
    else:
        return "I'm here to help you grow! Ask me about your learning progress, course recommendations, quiz strategies, or goal planning. What would you like to know?"


# -- Profile DB helpers --------------------------------------------------------

def _get_progress_summary(user_id: str) -> dict:
    """Pull courses_done and avg_score from MongoDB analytics."""
    try:
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
                "avg_score":    round(row.get("avg", 0) or 0, 1),
            }
    except Exception:
        pass
    return {"courses_done": 0, "avg_score": 0.0}


# -- Pydantic models -----------------------------------------------------------

class AIChatRequest(BaseModel):
    query: str
    department: Optional[str] = None
    employeeName: Optional[str] = None


class LoginRequest(BaseModel):
    # Support both snake_case (Vercel) and camelCase (Original)
    userId: str = Field(validation_alias=AliasChoices("userId", "user_id"))
    userName: str = Field(validation_alias=AliasChoices("userName", "user_name"))
    password: str
    department: Optional[str] = None # Now optional to match Frontend AuthContext


class MonitoringInsightsRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str


# -- Cached agents -------------------------------------------------------------

@lru_cache(maxsize=1)
def get_ai_chat_agent() -> AIChatAgent:
    return AIChatAgent()


@lru_cache(maxsize=1)
def get_course_generator_agent() -> CourseGeneratorAgent:
    return CourseGeneratorAgent()


def get_monitoring_agent(user_id: str, user_data: dict) -> MonitoringAgent:
    """Factory to create MonitoringAgent instances (not cached since user-specific)."""
    return MonitoringAgent(user_id=user_id, user_data=user_data)



# -- Cached agents -------------------------------------------------------------



# -- Existing routes (unchanged) -----------------------------------------------

@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Missing required field: query")
    agent = get_ai_chat_agent()
    return agent.answer(
        query=query,
        department=req.department,
        employee_name=req.employeeName or "",
    )


@app.get("/api/authenticate")
async def verify_auth_status(authorization: Optional[str] = Header(default=None)):
    """
    Check if the auth endpoint is reachable. 
    If a valid token is provided, returns current user info.
    """
    if not authorization:
        return {
            "success": True,
            "status": "ready",
            "message": "NamanDarshan Auth API is active. Use POST to login."
        }
    
    try:
        # Attempt to verify token if provided
        from agents.calendar_manager import _get_current_user
        user = _get_current_user(authorization)
        return {"success": True, "authenticated": True, "user": user}
    except Exception:
        return {"success": False, "authenticated": False, "message": "Invalid token"}


@app.post("/api/login")
@app.post("/api/authenticate")
async def login_alias(req: LoginRequest):
    try:
        result = authenticate_and_issue_token(req.userId, req.userName, req.password, req.department)
        
        # Format for frontend compatibility
        employee = result["user"]
        return {
            "success": True,
            "user": {
                # Legacy keys
                "userId":     employee.get("gsheet_uid", employee.get("id", "")),
                "userName":   employee.get("name", ""),
                # Frontend expected keys
                "id":         employee.get("gsheet_uid", employee.get("id", "")),
                "name":       employee.get("name", ""),
                "department": employee.get("department", ""),
                "role":       employee.get("role", "Employee"),
                "email":      employee.get("email", ""),
                "avatar_color": employee.get("avatar_color", ""),
                "token":      result["token"],
            },
            "token": result["token"],
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"[Login] Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/api/employees")
async def get_employees(authorization: Optional[str] = Header(default=None)):
    """
    Get all employees from Google Sheets.
    Returns a list of employee records with their department, role, and status.
    """
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

        # Fetch employees from Google Sheets
        result = sheets_api.spreadsheets().values().get(
            spreadsheetId="1ObVuVLXelgrKjKTJC3AXpv1YPxbWXO03wt5lXY8I-Po",
            range="EmployeeDB!A:F"
        ).execute()

        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            return {"success": True, "employees": []}

        # Parse employee records
        headers = [h.strip().lower() for h in rows[0]]
        employees = []

        for row in rows[1:]:
            if len(row) < 4:
                continue

            try:
                employee = {
                    "id": row[0] if len(row) > 0 else "",
                    "userId": row[0] if len(row) > 0 else "",
                    "userName": row[1] if len(row) > 1 else "",
                    "name": row[1] if len(row) > 1 else "",
                    "department": row[2] if len(row) > 2 else "General",
                    "role": row[3] if len(row) > 3 else "Employee",
                    "status": row[4] if len(row) > 4 else "Active",
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


@app.get("/api/courses")
async def courses_by_department(department: str = Query(...)):
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
            "icon":             "",
            "bg":               "linear-gradient(135deg, hsl(22 85% 42%), hsl(34 83% 52%))",
            "source":           "generated",
            "publishedCourseId": c["id"],
            "pdf_url":          c["pdf_url"],
            "summary":          c["summary"],
            "hasQuiz":          bool(c.get("quiz_questions")),
        }
        for c in published_courses
    ]


@app.get("/api/growth-tracker/progress")
async def get_user_progress(authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    from agents.growth_tracker_mongo import get_employee_progress_report
    # Use 'id' which is the standard key returned by _get_current_user
    user_id = str(current_user.get("id", current_user.get("sub", "")))
    report = get_employee_progress_report(user_id)
    
    # Extract unique IDs of passed courses
    completed_ids = list(set(
        c["course_id"] for c in report.get("recent_courses", [])
        if c.get("passed", False)
    ))
    
    return {"completedCourseIds": completed_ids}


@app.post("/api/course-generator")
async def generate_course(req: CourseGenerationRequest, authorization: Optional[str] = Header(default=None)):
    # Require authentication
    try:
        _get_current_user(authorization)
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not req.department.strip():
        raise HTTPException(status_code=400, detail="Department is required")
    
    agent = get_course_generator_agent()
    try:
        print(f" Generating course for department: {req.department}")
        print(f" Queries: {req.relatedQueries or []}")
        result = agent.generate_course_pdf(
            department=req.department,
            related_queries=req.relatedQueries or [],
        )
        print(f"[OK] Course generated successfully: {result.get('pdf_filename', 'unknown')}")
        return result
    except Exception as exc:
        print(f"[ERROR] Course generation error: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Course generation failed: {str(exc)}") from exc


@app.get("/api/generated-courses")
async def list_generated_courses(authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Admin", "Manager"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can view generated course publishing data")
    return list_published_courses()


@app.get("/api/generated-courses/file/{filename}")
async def get_generated_course_file(filename: str):
    file_path = (AGENTS_DIR.parent / "generated_courses" / Path(filename).name).resolve()
    allowed_dir = (AGENTS_DIR.parent / "generated_courses").resolve()
    if allowed_dir not in file_path.parents or not file_path.exists():
        raise HTTPException(status_code=404, detail="Generated PDF not found")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


from fastapi.responses import HTMLResponse

try:
    from agents.Course_database import CourseDatabase
    _course_db = CourseDatabase()
except Exception:
    _course_db = None

@app.get("/api/generated-courses/download/{course_id}/{key:path}")
async def download_generated_course_html(course_id: str, key: str):
    if not _course_db:
        raise HTTPException(status_code=500, detail="Course database not initialized")
    html, filename = _course_db.get_html_for_download(course_id, key)
    if not html:
        raise HTTPException(status_code=404, detail="HTML content not found")
    return HTMLResponse(content=html)



@app.get("/api/generated-courses/file/{filename}")
async def get_generated_file(filename: str):
    """Serve generated course files (HTML/PDF) from disk."""
    file_path = BASE_DIR / "data" / "generated_courses" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileResponse(file_path)


@app.post("/api/generated-courses/publish")
async def publish_course(req: PublishCourseRequest, authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Admin", "Manager"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can publish generated courses")
    try:
        return publish_generated_course(req.model_dump(), created_by=current_user.get("name", ""))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to publish course: {exc}") from exc


@app.get("/api/course-assignments/{course_id}")
async def get_course_assignment(course_id: str, authorization: Optional[str] = Header(default=None)):
    _get_current_user(authorization)
    course = get_course_quiz_for_employee(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Published course not found")
    return course


@app.post("/api/course-assignments/{course_id}/submit")
async def submit_course_assignment(
    course_id: str,
    req: QuizSubmissionRequest,
    authorization: Optional[str] = Header(default=None),
):
    current_user = _get_current_user(authorization)
    try:
        return submit_course_quiz(
            course_id=course_id,
            employee_id=str(current_user.get("sub", current_user.get("id", ""))),
            employee_name=current_user.get("name", ""),
            department=current_user.get("department", ""),
            answers=req.answers,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Quiz submission failed: {exc}") from exc


@app.get("/api/progress-report")
async def get_progress_report(authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    return get_employee_progress_report(str(current_user.get("sub", current_user.get("id", ""))))


@app.get("/api/progress-overview")
async def get_progress_overview(authorization: Optional[str] = Header(default=None)):
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Manager", "Admin"}:
        raise HTTPException(status_code=403, detail="Only managers and admins can view team progress reports")
    return get_team_progress_overview(
        viewer_role=current_user.get("role", ""),
        viewer_department=current_user.get("department", ""),
    )


@app.get("/api/sops")
async def list_sops(department: Optional[str] = Query(default=None)):
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


# -- Profile routes ------------------------------------------------------------

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str, authorization: Optional[str] = Header(default=None)):
    from agents.profile_manager import get_user_profile
    current_user = _get_current_user(authorization)
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_user_profile(user_id)


@app.post("/api/profile/{user_id}")
async def save_profile(
    user_id: str,
    req: ProfileUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    from agents.profile_manager import update_user_profile
    current_user = _get_current_user(authorization)
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return update_user_profile(user_id, req.model_dump())


# -- Monitoring AI routes ------------------------------------------------------

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


@app.post("/api/monitoring/chat")
async def monitoring_chat(req: MonitoringChatRequest, authorization: Optional[str] = Header(default=None)):
    from agents.profile_manager import get_user_profile
    current_user = _get_current_user(authorization)
    profile = get_user_profile(req.user_id)

    from datetime import datetime
    now = datetime.now()
    calendar_data = _get_calendar_events(now.year, now.month, current_user)

    progress = _get_progress_summary(req.user_id)
    system   = _build_monitoring_system_prompt(req.name, req.role, req.department, profile, progress, calendar_data)

    history_text = "".join(
        f"{'Employee' if m.get('role') == 'user' else 'Monitoring AI'}: {m.get('text', '')}\n"
        for m in req.history[-8:]
    )
    prompt = f"{history_text}Employee: {req.message}\nMonitoring AI:"

    return {"reply": _gemini(prompt, system=system)}


@app.post("/api/monitoring/insights")
async def monitoring_insights(req: MonitoringInsightsRequest, authorization: Optional[str] = Header(default=None)):
    from agents.profile_manager import get_user_profile
    _get_current_user(authorization)
    profile = get_user_profile(req.user_id)

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

Return ONLY valid JSON  no markdown, no backticks:
{{
  "greeting": "A warm 12 sentence personalized greeting mentioning their name",
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
            "greeting": f"Namaste {req.name}  Let's make today count!",
            "insights": [
                {"type": "tip",         "text": f"Focus on one new course in {req.department} today."},
                {"type": "celebration", "text": f"You've completed {courses} course{'s' if courses != 1 else ''}  keep going!"},
                {"type": "warning",     "text": "Set your learning goals in your profile for better AI guidance."},
            ],
        }


# -- KPI routes ----------------------------------------------------------------

@app.get("/api/kpi/me")
async def kpi_me(authorization: Optional[str] = Header(default=None)):
    """Employee: view own KPI for current (or specified) month."""
    current_user = _get_current_user(authorization)
    employee_id  = str(current_user.get("sub", current_user.get("id", "")))
    department   = current_user.get("department", "")
    return compute_employee_kpi(employee_id, department)


@app.get("/api/kpi/employee/{employee_id}")
async def kpi_employee(
    employee_id: str,
    month: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """Manager/Admin: view KPI for a specific employee."""
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Manager", "Admin"}:
        raise HTTPException(status_code=403, detail="Managers and Admins only")
    # Determine department from calendar.db
    from agents.calendar_manager import get_db as _cal_get_db
    conn = _cal_get_db()
    row = conn.execute(
        "SELECT department FROM employees WHERE gsheet_uid=? OR CAST(id AS TEXT)=?",
        (employee_id, employee_id),
    ).fetchone()
    conn.close()
    department = row["department"] if row else current_user.get("department", "")
    return compute_employee_kpi(employee_id, department, month)


@app.get("/api/kpi/department")
async def kpi_department(
    month: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """Manager: view full department KPI. Admin can pass any department."""
    current_user = _get_current_user(authorization)
    role = current_user.get("role", "")
    if role not in {"Manager", "Admin"}:
        raise HTTPException(status_code=403, detail="Managers and Admins only")
    # Manager is restricted to their own department
    if role == "Manager":
        department = str(current_user.get("department") or "")
    elif not department:
        department = str(current_user.get("department") or "")
    return get_department_kpi(department, month)


@app.get("/api/kpi/org")
async def kpi_org(
    month: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """Admin only: org-wide KPI leaderboard."""
    current_user = _get_current_user(authorization)
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return get_org_kpi(month)


@app.post("/api/kpi/rate")
async def kpi_rate(
    req: KPIWorkRatingRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Manager/Admin: set work target and actual for an employee for a given month."""
    current_user = _get_current_user(authorization)
    if current_user.get("role") not in {"Manager", "Admin"}:
        raise HTTPException(status_code=403, detail="Managers and Admins only")
    if not req.employee_id or not req.month:
        raise HTTPException(status_code=400, detail="employee_id and month are required")
    rated_by = str(current_user.get("sub", ""))
    try:
        return set_work_rating(
            employee_id=req.employee_id,
            department=req.department,
            month=req.month,
            work_target=req.work_target,
            work_actual=req.work_actual,
            notes=req.notes,
            rated_by=rated_by,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# -- Entry point ---------------------------------------------------------------

# Register Profile router
app.include_router(profile_router)

if __name__ == "__main__":
    # Use the current app instance directly to avoid importing the module again.
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting uvicorn on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)