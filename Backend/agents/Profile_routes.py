"""
profile_routes.py
FastAPI routes for:
  - User profile CRUD  (GET/POST /api/profile/{user_id})
  - Monitoring AI chat  (POST /api/monitoring/chat)
  - Monitoring AI insights (POST /api/monitoring/insights)

Setup:
  pip install google-generativeai fastapi sqlalchemy

Environment variables needed:
  GEMINI_API_KEY=your-key-here
  CALENDAR_DB_PATH=path/to/calendar.db   (reuse existing DB)
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import google.generativeai as genai
from google.generativeai import GenerativeModel, configure  # type: ignore
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.auth import get_current_user, get_db  # reuse your existing helpers

load_dotenv()

router = APIRouter()

# -- Gemini setup --------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    configure(api_key=GEMINI_API_KEY)
    _gemini_model = GenerativeModel("gemini-1.5-flash")
else:
    _gemini_model = None


def _gemini(prompt: str, system: str = "") -> str:
    """Call Gemini and return the text response."""
    if _gemini_model is None:
        return "Gemini API key not configured. Please set GEMINI_API_KEY."
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = _gemini_model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as exc:
        return f"I ran into an issue: {exc}"


# -- DB helpers ----------------------------------------------------------------

def _ensure_profile_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id      TEXT PRIMARY KEY,
            display_name TEXT DEFAULT '',
            bio          TEXT DEFAULT '',
            avatar_url   TEXT DEFAULT '',
            skills       TEXT DEFAULT '[]',
            goals        TEXT DEFAULT '',
            phone        TEXT DEFAULT '',
            linkedin     TEXT DEFAULT '',
            joined_date  TEXT DEFAULT '',
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _get_progress_summary(user_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    """Pull courses_done and avg_score from quiz_results if the table exists."""
    try:
        cur = conn.execute(
            """
            SELECT COUNT(*) as cnt, AVG(score) as avg_score
            FROM quiz_results
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            return {
                "courses_done": row[0] or 0,
                "avg_score":    round(row[1] or 0, 1),
            }
    except sqlite3.OperationalError:
        pass
    return {"courses_done": 0, "avg_score": 0.0}


# -- Pydantic models -----------------------------------------------------------

class ProfileUpdate(BaseModel):
    bio:        str = ""
    phone:      str = ""
    linkedin:   str = ""
    goals:      str = ""
    skills:     list[str] = []
    avatar_url: str = ""   # base64 data-uri  2 MB


class ChatRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str
    message:    str
    history:    list[dict[str, str]] = []  # [{role, text}, ...]


class InsightsRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str


# -- Profile routes ------------------------------------------------------------

@router.get("/api/profile/{user_id}")
def get_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    # Users can only fetch their own profile; admins can fetch any
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    conn = get_db()
    try:
        _ensure_profile_table(conn)
        cur = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        )
        row = cur.fetchone()
        progress = _get_progress_summary(user_id, conn)

        # Also grab joined_date from employees table
        emp_cur = conn.execute(
            "SELECT created_at FROM employees WHERE id = ?", (user_id,)
        )
        emp_row = emp_cur.fetchone()
        joined  = emp_row["created_at"] if emp_row and emp_row["created_at"] else ""

        if row is None:
            return {
                "user_id":      user_id,
                "display_name": "",
                "bio":          "",
                "avatar_url":   "",
                "skills":       [],
                "goals":        "",
                "phone":        "",
                "linkedin":     "",
                "joined_date":  joined,
                **progress,
            }

        return {
            "user_id":      row["user_id"],
            "display_name": row["display_name"],
            "bio":          row["bio"],
            "avatar_url":   row["avatar_url"],
            "skills":       json.loads(row["skills"] or "[]"),
            "goals":        row["goals"],
            "phone":        row["phone"],
            "linkedin":     row["linkedin"],
            "joined_date":  row["joined_date"] or joined,
            **progress,
        }
    finally:
        conn.close()


@router.post("/api/profile/{user_id}")
def save_profile(
    user_id: str,
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Guard: don't store giant blobs accidentally
    if len(body.avatar_url) > 2_500_000:
        raise HTTPException(status_code=413, detail="Avatar image too large (max 2 MB)")

    conn = get_db()
    try:
        _ensure_profile_table(conn)
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
                body.bio,
                body.phone,
                body.linkedin,
                body.goals,
                json.dumps(body.skills),
                body.avatar_url,
            ),
        )
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


# -- Monitoring AI routes ------------------------------------------------------

def _build_system_prompt(
    name: str,
    role: str,
    department: str,
    profile: dict[str, Any] | None,
    progress: dict[str, Any],
) -> str:
    goals   = profile.get("goals",  "") if profile else ""
    bio     = profile.get("bio",    "") if profile else ""
    skills  = profile.get("skills", []) if profile else []

    return f"""You are Monitoring AI  a warm, encouraging, deeply personalized learning coach
built specifically for {name} at NamanDarshan LMS. You know them personally.

## About This Employee
- Name: {name}
- Role: {role}
- Department: {department}
- Bio: {bio or "Not provided yet"}
- Skills: {", ".join(skills) if skills else "Not listed yet"}

## Their Learning Goals
{goals or "No goals set yet. Encourage them to set goals in their profile."}

## Current Progress
- Courses completed: {progress.get("courses_done", 0)}
- Average quiz score: {progress.get("avg_score", 0)}%

## Your Personality & Approach
- Warm, direct, encouraging  like a brilliant mentor who truly cares
- You speak in simple, clear English with occasional Hindi/Sanskrit phrases (Namaste, Shubh, etc.)
- You give SPECIFIC, actionable advice  never vague platitudes
- You celebrate wins enthusiastically and address weaknesses with compassion
- You reference their actual goals, scores, and department in every response
- Keep responses concise (2-4 paragraphs max) unless they ask for a detailed plan
- Always end with one clear next action they can take TODAY

You are NOT a general chatbot. You ONLY help with:
- Learning progress and course guidance
- Career growth and skill development
- Goal setting and tracking
- Time management for learning
- Department-specific knowledge growth

If asked about unrelated topics, gently redirect to their growth journey.
"""


@router.post("/api/monitoring/chat")
def monitoring_chat(body: ChatRequest) -> dict[str, str]:
    conn = get_db()
    try:
        _ensure_profile_table(conn)
        profile_cur = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (body.user_id,)
        )
        profile_row = profile_cur.fetchone()
        profile = dict(profile_row) if profile_row else None
        if profile and profile.get("skills"):
            profile["skills"] = json.loads(profile["skills"] or "[]")

        progress = _get_progress_summary(body.user_id, conn)
    finally:
        conn.close()

    system = _build_system_prompt(body.name, body.role, body.department, profile, progress)

    # Build conversation context
    history_text = ""
    for msg in body.history[-8:]:  # last 8 messages for context
        speaker = "Employee" if msg.get("role") == "user" else "Monitoring AI"
        history_text += f"{speaker}: {msg.get('text', '')}\n"

    prompt = f"{history_text}Employee: {body.message}\nMonitoring AI:"

    reply = _gemini(prompt, system=system)
    return {"reply": reply}


@router.post("/api/monitoring/insights")
def monitoring_insights(body: InsightsRequest) -> dict[str, Any]:
    conn = get_db()
    try:
        _ensure_profile_table(conn)
        profile_cur = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (body.user_id,)
        )
        profile_row = profile_cur.fetchone()
        profile = dict(profile_row) if profile_row else None
        if profile and profile.get("skills"):
            profile["skills"] = json.loads(profile["skills"] or "[]")

        progress = _get_progress_summary(body.user_id, conn)
    finally:
        conn.close()

    goals   = profile.get("goals",  "None set") if profile else "None set"
    courses = progress.get("courses_done", 0)
    score   = progress.get("avg_score", 0)

    prompt = f"""
Generate a personalized daily insights summary for {body.name} ({body.role}, {body.department}).

Facts:
- Courses completed: {courses}
- Average quiz score: {score}%
- Goals: {goals}

Return ONLY valid JSON in this exact shape  no markdown, no backticks:
{{
  "greeting": "A warm 1-2 sentence personalized greeting mentioning their name",
  "insights": [
    {{"type": "tip", "text": "A specific actionable learning tip for today"}},
    {{"type": "celebration", "text": "Celebrate something specific about their progress"}},
    {{"type": "warning", "text": "One gentle nudge or area to improve"}}
  ]
}}

Keep each insight under 20 words. Be warm, specific, and motivating.
"""

    raw = _gemini(prompt)

    try:
        # Strip any accidental markdown fences
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data  = json.loads(clean)
        return {
            "greeting": data.get("greeting", f"Namaste {body.name}! Ready to grow today?"),
            "insights": data.get("insights", []),
        }
    except (json.JSONDecodeError, KeyError):
        # Fallback gracefully
        return {
            "greeting": f"Namaste {body.name}  Let's make today count!",
            "insights": [
                {"type": "tip",         "text": f"Focus on one new course in {body.department} today."},
                {"type": "celebration", "text": f"You've completed {courses} courses  keep going!"},
                {"type": "warning",     "text": "Set your learning goals in your profile for better guidance."},
            ],
        }


# -- Register in your main FastAPI app -----------------------------------------
#
# In your main.py:
#   from profile_routes import router as profile_router
#   app.include_router(profile_router)