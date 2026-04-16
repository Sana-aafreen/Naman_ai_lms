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
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from google import genai
from dotenv import load_dotenv

from agents.auth import get_current_user
from agents.profile_manager import (
    get_user_profile,
    update_user_profile,
    ProfileUpdateRequest as ProfileUpdate,
    MonitoringChatRequest as ChatRequest,
    MonitoringInsightsRequest as InsightsRequest,
)
import mongo_db
from bson import ObjectId

load_dotenv()

router = APIRouter()

# -- Gemini setup --------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
_GEMINI_MODEL = "gemini-1.5-flash"


def _gemini(prompt: str, system: str = "") -> str:
    """Call Gemini and return the text response."""
    if _gemini_client is None:
        return "Gemini API key not configured. Please set GEMINI_API_KEY."
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = _gemini_client.models.generate_content(model=_GEMINI_MODEL, contents=full_prompt)
        return response.text.strip()
    except Exception as exc:
        return f"I ran into an issue: {exc}"


# -- DB helpers ----------------------------------------------------------------

# Models imported from profile_manager


# -- Profile routes ------------------------------------------------------------

@router.get("/api/profile/{user_id}")
def get_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    # Users can only fetch their own profile; admins can fetch any
    if current_user.get("sub") != user_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_user_profile(user_id)


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

    return update_user_profile(user_id, body.model_dump())


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
    # MongoDB Profile lookup
    profile = mongo_db.find_one("user_profiles", {"user_id": body.user_id})
    if profile and profile.get("skills"):
        profile["skills"] = profile["skills"] if isinstance(profile["skills"], list) else json.loads(profile["skills"] or "[]")
    
    progress = _get_progress_summary(body.user_id)
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
    # MongoDB Profile lookup
    profile = mongo_db.find_one("user_profiles", {"user_id": body.user_id})
    if profile and profile.get("skills"):
        profile["skills"] = profile["skills"] if isinstance(profile["skills"], list) else json.loads(profile["skills"] or "[]")
    
    progress = _get_progress_summary(body.user_id)

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