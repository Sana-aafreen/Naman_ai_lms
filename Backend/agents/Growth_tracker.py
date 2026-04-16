"""
Growth_tracker.py — Resilient Growth Tracker entry point
=========================================================
Dynamically selects between MongoDB and SQLite backends without blocking startup.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Any

# Add agents directory to path for imports
_agents_dir = Path(__file__).parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

# Global state
_INITIALIZED = False
_BACKEND = "sqlite" # Default
_impl = {}

def _ensure_init():
    """Lazy initialization of the actual backend implementation."""
    global _INITIALIZED, _BACKEND, _impl
    if _INITIALIZED:
        return
    
    try:
        from mongo_db import init_mongodb
        # We don't call init_mongodb here because it blocks. 
        # We just try to import the mongo implementation.
        from growth_tracker_mongo import (
            init_growth_tracker_db, publish_generated_course, list_published_courses,
            get_course_quiz_for_employee, submit_course_quiz, get_employee_progress_report,
            get_team_progress_overview
        )
        # Test connection quickly
        init_mongodb() 
        
        _impl = {
            "init_growth_tracker_db": init_growth_tracker_db,
            "publish_generated_course": publish_generated_course,
            "list_published_courses": list_published_courses,
            "get_course_quiz_for_employee": get_course_quiz_for_employee,
            "submit_course_quiz": submit_course_quiz,
            "get_employee_progress_report": get_employee_progress_report,
            "get_team_progress_overview": get_team_progress_overview,
        }
        _BACKEND = "mongo"
        print("[OK] Growth Tracker: Using MongoDB backend")
    except Exception as e:
        print(f"[GrowthTracker] MongoDB unavailable, falling back to SQLite. Error: {e}")
        from Growth_tracker_sqlite import (
            init_growth_tracker_db, publish_generated_course, list_published_courses,
            get_course_quiz_for_employee, submit_course_quiz, get_employee_progress_report,
            get_team_progress_overview
        )
        _impl = {
            "init_growth_tracker_db": init_growth_tracker_db,
            "publish_generated_course": publish_generated_course,
            "list_published_courses": list_published_courses,
            "get_course_quiz_for_employee": get_course_quiz_for_employee,
            "submit_course_quiz": submit_course_quiz,
            "get_employee_progress_report": get_employee_progress_report,
            "get_team_progress_overview": get_team_progress_overview,
        }
        _BACKEND = "sqlite"

    _INITIALIZED = True

# --- Exported Functions (Wrappers) ---

def init_growth_tracker_db(*args, **kwargs):
    _ensure_init()
    return _impl["init_growth_tracker_db"](*args, **kwargs)

def publish_generated_course(*args, **kwargs):
    _ensure_init()
    return _impl["publish_generated_course"](*args, **kwargs)

def list_published_courses(*args, **kwargs):
    _ensure_init()
    return _impl["list_published_courses"](*args, **kwargs)

def get_course_quiz_for_employee(*args, **kwargs):
    _ensure_init()
    return _impl["get_course_quiz_for_employee"](*args, **kwargs)

def submit_course_quiz(*args, **kwargs):
    _ensure_init()
    return _impl["submit_course_quiz"](*args, **kwargs)

def get_employee_progress_report(*args, **kwargs):
    _ensure_init()
    return _impl["get_employee_progress_report"](*args, **kwargs)

def get_team_progress_overview(*args, **kwargs):
    _ensure_init()
    return _impl["get_team_progress_overview"](*args, **kwargs)

def USING_MONGO():
    _ensure_init()
    return _BACKEND == "mongo"

__all__ = [
    "init_growth_tracker_db", "publish_generated_course", "list_published_courses",
    "get_course_quiz_for_employee", "submit_course_quiz", "get_employee_progress_report",
    "get_team_progress_overview", "USING_MONGO"
]
