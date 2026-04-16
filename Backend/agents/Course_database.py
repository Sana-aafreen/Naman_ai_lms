"""
course_database.py — MongoDB-backed Course Database Wrapper
============================================================
Replaces SQLite with MongoDB while maintaining backward compatibility.

Automatically tries MongoDB first, falls back to SQLite if unavailable.

Classes:
  CourseDatabase → Main database interface with full CRUD operations
"""

from __future__ import annotations

import os
from pathlib import Path

# Add agents directory to path for imports
import sys
_agents_dir = Path(__file__).parent
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))
    
# Also add parent (Backend) to path for mongo_db
_backend_dir = _agents_dir.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Try MongoDB first, fall back to SQLite
try:
    # Check if MongoDB is available before importing
    from mongo_db import init_mongodb
    init_mongodb()
    
    from course_database_mongo import CourseDatabase
    
    print("✅ Course Database: Using MongoDB backend")
    USING_MONGO = True

except Exception as e:
    print(f"⚠️  Course Database: MongoDB unavailable ({e}), falling back to SQLite")
    
    from course_database_sqlite import CourseDatabase
    
    USING_MONGO = False


__all__ = ["CourseDatabase", "USING_MONGO"]
