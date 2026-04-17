# -*- coding: utf-8 -*-
"""
profile_manager.py — MongoDB Profile Management for NamanDarshan LMS
====================================================================

Consolidates user profile and progress analytics into MongoDB.
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import mongo_db
from datetime import datetime, timezone

# -- Pydantic models -----------------------------------------------------------

class CourseGenerationRequest(BaseModel):
    department: str
    topic: Optional[str] = None
    relatedQueries: Optional[List[str]] = None

class PublishCourseRequest(BaseModel):
    department: str
    title: str
    summary: str = ""
    audience: str = ""
    pdf_path: str
    pdf_filename: Optional[str] = None
    generated_at: str = ""
    source_notes: List[str] = []
    modules: List[Dict] = []
    quiz_questions: List[Dict] = []

class QuizSubmissionRequest(BaseModel):
    answers: List[Dict]

class ProfileUpdateRequest(BaseModel):
    bio:        str       = ""
    phone:      str       = ""
    linkedin:   str       = ""
    goals:      str       = ""
    skills:     List[str] = []
    avatar_url: str       = ""   # base64 data-uri, max ~2 MB

class MonitoringChatRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str
    message:    str
    history:    List[Dict] = []   # [{role, text}, ...]

class MonitoringInsightsRequest(BaseModel):
    user_id:    str
    name:       str
    role:       str
    department: str

# -- Logic -------------------------------------------------------------------

def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Fetch user profile from MongoDB, joined with progress and employee data."""
    profile = mongo_db.find_one("user_profiles", {"user_id": user_id}) or {}
    
    # Get employee details (joined_date, name, etc.)
    emp = mongo_db.find_one("employees", {"$or": [{"gsheet_uid": user_id}, {"id": user_id}]}) or {}
    
    # Get progress summary
    progress = get_progress_summary(user_id)
    
    # Merge and return
    return {
        "user_id":      user_id,
        "display_name": profile.get("display_name", emp.get("name", "")),
        "bio":          profile.get("bio", ""),
        "avatar_url":   profile.get("avatar_url", emp.get("avatar_url", "")),
        "skills":       profile.get("skills") if isinstance(profile.get("skills"), list) else json.loads(profile.get("skills") or "[]"),
        "goals":        profile.get("goals", ""),
        "phone":        profile.get("phone", ""),
        "linkedin":     profile.get("linkedin", ""),
        "joined_date":  profile.get("joined_date") or emp.get("created_at") or "",
        "department":   emp.get("department", ""),
        "role":         emp.get("role", "Employee"),
        **progress,
    }

def update_user_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Update or create user profile in MongoDB."""
    # Ensure fields exist
    update_data = {
        "bio":          data.get("bio", ""),
        "phone":        data.get("phone", ""),
        "linkedin":     data.get("linkedin", ""),
        "goals":        data.get("goals", ""),
        "skills":       data.get("skills", []),
        "avatar_url":   data.get("avatar_url", ""),
        "updated_at":   mongo_db.now_iso()
    }
    
    mongo_db.update_one(
        "user_profiles",
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True
    )
    return {"status": "ok"}

def get_progress_summary(user_id: str) -> Dict[str, Any]:
    """Pull courses_done and avg_score from MongoDB quiz_results."""
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
