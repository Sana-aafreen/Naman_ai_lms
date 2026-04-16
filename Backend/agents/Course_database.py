"""
Course_database.py — MongoDB-backed Course Database Wrapper
============================================================
Exclusively using MongoDB as the primary database.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add agents directory to path for imports
_agents_dir = Path(__file__).parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

# Exclusively import MongoDB implementation
try:
    from course_database_mongo import CourseDatabase
    USING_MONGO = True
except ImportError:
    # This should not happen in the new consolidated architecture
    raise ImportError("course_database_mongo not found. MongoDB consolidation is required.")

__all__ = ["CourseDatabase", "USING_MONGO"]
