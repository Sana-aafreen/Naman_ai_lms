"""
Growth_tracker.py  MongoDB-backed Growth Tracker for NamanDarshan LMS
======================================================================
Replaces SQLite with MongoDB for scalability and real-time analytics.

Collections:
  - published_courses      -> Course metadata and availability
  - quiz_results          -> Individual quiz attempt scores
  - growth_data           -> Raw learner progress records
  - growth_summary        -> Pre-aggregated summaries for dashboard

Backward Compatibility:
  Automatically falls back to SQLite if MongoDB is unavailable via growth_tracker_sqlite.py

Fast API Integration:
  All functions return plain dicts (no SQLAlchemy models)
  Used by main.py routes for courses, progress, leaderboards, etc.
"""

from __future__ import annotations

import os
from typing import Optional
from pathlib import Path

# Add agents directory to path for imports
import sys
_agents_dir = Path(__file__).parent
sys.path.insert(0, str(_agents_dir))

# Try MongoDB first, fall back to SQLite
try:
    # Check if MongoDB is available before importing
    from mongo_db import init_mongodb
    init_mongodb()
    
    from growth_tracker_mongo import (
        init_growth_tracker_db,
        publish_generated_course,
        list_published_courses,
        get_course_quiz_for_employee,
        submit_course_quiz,
        get_employee_progress_report,
        get_team_progress_overview,
    )
    
    print("[OK] Growth Tracker: Using MongoDB backend")
    USING_MONGO = True

except Exception as e:
    print(f"\n  [GrowthTracker] MongoDB connection failed (Timeout or URL error)")
    print(f"   Details: {e}")
    print("   FALLING BACK to local SQLite database. MongoDB analytics will be offline.\n")
    
    from Growth_tracker_sqlite import (
        init_growth_tracker_db,
        publish_generated_course,
        list_published_courses,
        get_course_quiz_for_employee,
        submit_course_quiz,
        get_employee_progress_report,
        get_team_progress_overview,
    )
    
    USING_MONGO = False


# Re-export all functions for compatibility with main.py
__all__ = [
    "init_growth_tracker_db",
    "publish_generated_course",
    "list_published_courses",
    "get_course_quiz_for_employee",
    "submit_course_quiz",
    "get_employee_progress_report",
    "get_team_progress_overview",
    "USING_MONGO",
]
