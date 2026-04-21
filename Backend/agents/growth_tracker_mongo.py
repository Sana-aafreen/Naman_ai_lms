# -*- coding: utf-8 -*-
"""
growth_tracker_mongo.py — MongoDB Version of Growth Tracker
============================================================
Replaces SQLite-based growth tracking with MongoDB collections.

Collections:
  - published_courses      → Course metadata and availability
  - quiz_results          → Individual quiz attempt scores
  - growth_data           → Raw learner progress records
  - growth_summary        → Pre-aggregated summaries for dashboard
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# MongoDB imports
from pymongo import ASCENDING, DESCENDING
from bson.objectid import ObjectId

# Add parent directory to path for mongo_db import
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mongo_db import (
    get_db,
    insert_one,
    find_one,
    find_many,
    update_one,
    count_documents,
    aggregate,
    MongoCollection,
)

# ── Configuration ─────────────────────────────────────────────────────────────

PASS_THRESHOLD = int(os.getenv("LMS_PASS_THRESHOLD", "70"))  # %

# Collections
published_courses_col = MongoCollection("published_courses")
quiz_results_col = MongoCollection("quiz_results")
growth_data_col = MongoCollection("growth_data")


# ════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _badge_for_score(pct: int) -> str:
    if pct >= 95: return "🏆 Expert"
    if pct >= 85: return "⭐ Proficient"
    if pct >= 70: return "✅ Competent"
    return "📘 Learning"

def _level_from_completions(n: int) -> str:
    if n >= 20: return "Senior"
    if n >= 10: return "Intermediate"
    if n >= 4:  return "Associate"
    return "Beginner"


def _resolve_employee_aliases(employee_id: str) -> list[str]:
    """
    Some historical records used MongoDB _id (as string) for user_id, while newer
    records use the canonical gsheet/id. This returns a list of ids to query with.
    """
    base = str(employee_id or "").strip()
    aliases: set[str] = {base} if base else set()
    if not base:
        return []

    or_terms: list[dict[str, Any]] = [
        {"gsheet_uid": base},
        {"id": base},
        {"userId": base},
    ]
    if ObjectId.is_valid(base):
        or_terms.append({"_id": ObjectId(base)})

    try:
        emp = find_one("employees", {"$or": or_terms})
    except Exception:
        emp = None

    if emp:
        for key in ("gsheet_uid", "id", "userId", "_id"):
            val = str(emp.get(key) or "").strip()
            if val:
                aliases.add(val)

    return [a for a in sorted(aliases) if a]


# ════════════════════════════════════════════════════════════════════════════════
# Database Initialization
# ════════════════════════════════════════════════════════════════════════════════

def init_growth_tracker_db() -> None:
    """Initialize MongoDB collections with schema (MongoDB auto-creates on first insert)."""
    try:
        db = get_db()
        
        # Ensure collections exist by creating them
        if "published_courses" not in db.list_collection_names():
            db.create_collection("published_courses")
        if "quiz_results" not in db.list_collection_names():
            db.create_collection("quiz_results")
        if "growth_data" not in db.list_collection_names():
            db.create_collection("growth_data")
        
        print("✅ Growth tracker MongoDB collections initialized")
    
    except Exception as e:
        print(f"⚠️  Warning initializing growth tracker: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# Published Courses (replaces published_courses table)
# ════════════════════════════════════════════════════════════════════════════════

def publish_generated_course(course_data: dict, created_by: str = "") -> dict:
    """
    Publish a generated course to MongoDB.
    
    Args:
        course_data: Course metadata from PDF generation
        created_by: User who published the course
    
    Returns:
        dict with published course info
    """
    try:
        course_doc = {
            "department": course_data.get("department", ""),
            "title": course_data.get("title", ""),
            "summary": course_data.get("summary", ""),
            "audience": course_data.get("audience", ""),
            "pdf_url": course_data.get("pdf_url") or f"/api/generated-courses/file/{course_data.get('pdf_filename', '')}",
            "pdf_filename": course_data.get("pdf_filename", ""),
            "index_html_url": course_data.get("index_html", {}).get("html_url", ""),
            "index_html_filename": course_data.get("index_html", {}).get("html_filename", ""),
            "source_notes": course_data.get("source_notes", []),
            "modules": course_data.get("modules", []),
            "quiz_questions": course_data.get("quiz_questions", []),
            "created_by": created_by,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        
        id_ = insert_one("published_courses", course_doc)
        course_doc["_id"] = id_
        course_doc["id"] = id_
        
        print(f"✅ Course published to MongoDB: {id_}")
        return course_doc
    
    except Exception as e:
        print(f"❌ Error publishing course: {e}")
        raise


def list_published_courses(department: str = "") -> list[dict]:
    """
    List published courses (optionally filtered by department).
    
    Args:
        department: Optional department filter
    
    Returns:
        List of published course dicts
    """
    query = {}
    if department:
        dept = str(department).strip()
        query["department"] = {"$regex": f"(?i)^{dept}$"}
    
    courses = find_many("published_courses", query, sort=[("created_at", DESCENDING)])
    
    for course in courses:
        course["id"] = str(course.get("_id", ""))
    
    return courses


# ════════════════════════════════════════════════════════════════════════════════
# Course Quizzes & Progress (replaces quiz_results table)
# ════════════════════════════════════════════════════════════════════════════════

def get_course_quiz_for_employee(course_id: str) -> Optional[dict]:
    """Get course metadata with quiz questions for an employee."""
    try:
        from bson.objectid import ObjectId
        course = find_one("published_courses", {"_id": ObjectId(course_id)})
        
        if not course:
            return None
        
        return {
            "id": str(course.get("_id", "")),
            "title": course.get("title", ""),
            "summary": course.get("summary", ""),
            "modules": course.get("modules", []),
            "quiz_questions": course.get("quiz_questions", []),
        }
    
    except Exception as e:
        print(f"❌ Error fetching course quiz: {e}")
        return None


def submit_course_quiz(
    course_id: str,
    employee_id: str,
    employee_name: str,
    department: str,
    answers: list[dict],
) -> dict:
    """
    Record a course quiz submission.
    
    Args:
        course_id: Published course ID
        employee_id: Employee user ID
        employee_name: Employee display name
        department: Employee department
        answers: List of answer dicts
    
    Returns:
        dict with score and result info
    """
    try:
        # Calculate score
        correct_count = sum(1 for ans in answers if ans.get("correct", False))
        total_count = len(answers)
        score_pct = int((correct_count / total_count * 100) if total_count > 0 else 0)
        passed = score_pct >= PASS_THRESHOLD
        
        # Fetch course title for historical record
        course_title = "Unnamed Course"
        try:
            from bson.objectid import ObjectId
            c_doc = find_one("published_courses", {"_id": ObjectId(course_id)})
            if c_doc:
                course_title = c_doc.get("title", "Unnamed Course")
        except: pass

        # Record submission
        submission = {
            "user_id": employee_id,
            "employee_name": employee_name,
            "department": department,
            "course_id": course_id,
            "course_title": course_title,
            "score": score_pct,
            "correct": correct_count,
            "total": total_count,
            "passed": passed,
            "answers": answers,
            "submitted_at": _now_iso(),
        }
        
        insert_one("quiz_results", submission)
        
        # Also record in growth data
        growth_record = {
            "user_id": employee_id,
            "employee_name": employee_name,
            "department": department,
            "event": "quiz_submission",
            "course_id": course_id,
            "score": score_pct,
            "passed": passed,
            "timestamp": _now_iso(),
        }
        insert_one("growth_data", growth_record)
        
        print(f"✅ Quiz submitted for {employee_name}: {score_pct}%")
        
        return {
            "success": True,
            "score": score_pct,
            "passed": passed,
            "correct": correct_count,
            "total": total_count,
            "badge": _badge_for_score(score_pct),
        }
    
    except Exception as e:
        print(f"❌ Error submitting quiz: {e}")
        raise


# ════════════════════════════════════════════════════════════════════════════════
# Progress Reports (aggregated from quiz_results)
# ════════════════════════════════════════════════════════════════════════════════

def get_employee_progress_report(employee_id: str) -> dict:
    """
    Get personalized progress report for an employee, synced with Frontend Performance Portfolio.
    
    Returns:
        ProgressReport compatible dictionary.
    """
    try:
        aliases = _resolve_employee_aliases(employee_id)
        if not aliases:
            aliases = [str(employee_id or "").strip()]

        # Find all quiz submissions for this employee
        submissions = find_many(
            "quiz_results",
            {"user_id": {"$in": aliases}},
            sort=[("submitted_at", DESCENDING)]
        )
        
        if not submissions:
            return {
                "overallScore": 0,
                "coursesDone": 0,
                "learningHours": 0,
                "departmentRank": "-",
                "skills": [],
                "badges": [],
                "completedCourses": [],
            }
        
        courses_done = len(submissions)
        avg_score = sum(s["score"] for s in submissions) / courses_done if submissions else 0
        
        # Calculate skill categories from department distributions
        dept_scores = defaultdict(list)
        for s in submissions:
            dept = s.get("department") or "General"
            dept_scores[dept].append(s["score"])
        
        skills = []
        colors = ["#FF7033", "#10b981", "#6366f1", "#f59e0b", "#ec4899", "#8b5cf6"]
        for i, (dept, scores) in enumerate(dept_scores.items()):
            skills.append({
                "name": dept,
                "score": int(sum(scores) / len(scores)),
                "color": colors[i % len(colors)]
            })

        # Enrich badges
        badge_types = {
            "🏆 Expert": {"icon": "🏆", "title": "Expert Practitioner", "desc": "Achieved 95%+ in professional modules."},
            "⭐ Proficient": {"icon": "⭐", "title": "Proficient Scholar", "desc": "Consistent high performance across disciplines."},
            "✅ Competent": {"icon": "✅", "title": "Certified Associate", "desc": "Verified competency in core institutional protocols."},
            "📘 Learning": {"icon": "📘", "title": "Active Learner", "desc": "Commenced professional development journey."},
        }
        
        raw_badges = list(set(_badge_for_score(s["score"]) for s in submissions))
        enriched_badges = [
            badge_types.get(b, {"icon": "🎖️", "title": b, "desc": "Achievement unlocked."})
            for b in raw_badges[:5]
        ]

        # Calculate Rank (simple logic: compare against average)
        dept_rank = "Top 10%" if avg_score > 85 else ("Top 25%" if avg_score > 75 else "Ranked")

        return {
            "overallScore": int(avg_score),
            "coursesDone": courses_done,
            "learningHours": round(courses_done * 1.2, 1), # Roughly 1.2h per course
            "departmentRank": dept_rank,
            "skills": skills,
            "badges": enriched_badges,
            "completedCourses": [
                {
                    "course_id": str(s.get("course_id", "")),
                    "title": s.get("course_title") or s.get("title") or "Unnamed Course",
                    "department": s.get("department") or "General",
                    "score": s["score"],
                    "completed_at": s.get("submitted_at", ""),
                    "status": "Completed"
                }
                for s in submissions[:15]
            ],
        }
    
    except Exception as e:
        print(f"❌ Error generating progress report: {e}")
        return {
            "overallScore": 0, "coursesDone": 0, "learningHours": 0,
            "departmentRank": "-", "skills": [], "badges": [], "completedCourses": []
        }


def get_team_progress_overview(viewer_role: str = "", viewer_department: str = "") -> dict:
    """
    Get team/department progress overview for managers/admins.
    
    Args:
        viewer_role: Role of person requesting (Manager, Admin)
        viewer_department: Department filter (for Managers)
    
    Returns:
        dict with team stats, leaderboard, department metrics
    """
    try:
        # Base query
        query = {}
        if viewer_role == "Manager" and viewer_department:
            query["department"] = viewer_department
        
        submissions = find_many("quiz_results", query)
        
        if not submissions:
            return {
                "total_employees": 0,
                "total_quizzes": 0,
                "avg_score": 0,
                "completion_rate": 0,
                "leaderboard": [],
                "department_stats": {},
            }
        
        # Aggregate stats
        total_quizzes = len(submissions)
        avg_score = sum(s["score"] for s in submissions) / total_quizzes if submissions else 0
        passed_quizzes = sum(1 for s in submissions if s["passed"])
        completion_rate = int((passed_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0)
        
        # Employee aggregation for leaderboard
        employee_stats = defaultdict(lambda: {"quizzes": 0, "scores": [], "passed": 0})
        department_stats = defaultdict(lambda: {"quizzes": 0, "employees": set(), "avg_score": 0})
        
        for sub in submissions:
            emp_id = sub["user_id"]
            emp_name = sub.get("employee_name", emp_id)
            dept = sub.get("department", "Unknown")
            
            employee_stats[emp_id]["name"] = emp_name
            employee_stats[emp_id]["quizzes"] += 1
            employee_stats[emp_id]["scores"].append(sub["score"])
            if sub["passed"]:
                employee_stats[emp_id]["passed"] += 1
            
            department_stats[dept]["quizzes"] += 1
            department_stats[dept]["employees"].add(emp_id)
        
        # Build leaderboard
        leaderboard = []
        for emp_id, stats in sorted(
            employee_stats.items(),
            key=lambda x: (sum(x[1]["scores"]) / len(x[1]["scores"]), x[1]["quizzes"]),
            reverse=True
        )[:20]:
            avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
            leaderboard.append({
                "employee_id": emp_id,
                "employee_name": stats.get("name", emp_id),
                "quizzes_completed": stats["quizzes"],
                "avg_score": round(avg, 1),
                "passed": stats["passed"],
                "badge": _badge_for_score(int(avg)),
            })
        
        # Build department stats
        dept_stats = {}
        for dept, stats in department_stats.items():
            avg = sum(s["score"] for s in filter(lambda x: x.get("department") == dept, submissions)) / stats["quizzes"] if stats["quizzes"] > 0 else 0
            dept_stats[dept] = {
                "employees": len(stats["employees"]),
                "quizzes_completed": stats["quizzes"],
                "avg_score": round(avg, 1),
            }
        
        return {
            "total_employees": len(employee_stats),
            "total_quizzes": total_quizzes,
            "avg_score": round(avg_score, 1),
            "completion_rate": completion_rate,
            "leaderboard": leaderboard,
            "department_stats": dept_stats,
        }
    
    except Exception as e:
        print(f"❌ Error generating team overview: {e}")
        return {}
