"""
Growth_tracker.py — MongoDB Growth Tracker entry point
=========================================================
Exclusively using MongoDB for growth tracking and analytics.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add agents directory to path for imports
_agents_dir = Path(__file__).parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

# Exclusively import MongoDB implementation
from growth_tracker_mongo import (
    init_growth_tracker_db,
    publish_generated_course,
    list_published_courses,
    get_course_quiz_for_employee,
    submit_course_quiz,
    get_employee_progress_report,
    get_team_progress_overview
)

__all__ = [
    "init_growth_tracker_db",
    "publish_generated_course",
    "list_published_courses",
    "get_course_quiz_for_employee",
    "submit_course_quiz",
    "get_employee_progress_report",
    "get_team_progress_overview"
]
