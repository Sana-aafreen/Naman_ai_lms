"""
kpi_manager.py  Department-Aware KPI Manager for NamanDarshan LMS
===================================================================

Computes per-employee KPI scores across 4 pillars:
  1. Learning      (30%)   Quiz scores & course completions
  2. Attendance    (25%)   Leave records from calendar.db
  3. Work Output   (30%)   Manager-entered targets vs actuals (kpi_ratings table)
  4. Growth        (15%)   Streaks, badges, level from GrowthTracker

Role-aware:
  - Employee  -> own KPI only
  - Manager   -> full department view, can set work targets
  - Admin     -> org-wide leaderboard

Work targets carry forward month-to-month if not updated.
"""

from datetime import datetime, timezone
import json
import mongo_db
from typing import Any, Optional, List
from bson import ObjectId
from pathlib import Path
import sys

_AGENTS_DIR = Path(__file__).parent
from mongo_db import safe_print

# -- Scoring constants ----------------------------------------------------------
WORKING_DAYS_PER_MONTH = 22     # approximation
DEFAULT_WORK_SCORE     = 70     # used when manager hasn't set a rating yet

RATING_THRESHOLDS = [
    (90, " Exceptional"),
    (80, " Excellent"),
    (70, "[OK] Good"),
    (60, " Developing"),
    (0,  "[WARN] Needs Attention"),
]

LEVEL_SCORES = {
    "Senior":       80,
    "Intermediate": 60,
    "Associate":    40,
    "Beginner":     20,
}


# ==============================================================================
#  DB HELPERS
# ==============================================================================

# DB Helpers now use mongo_db directly...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ==============================================================================
#  INIT  create kpi_ratings table inside calendar.db
# ==============================================================================

def init_kpi_db() -> None:
    # Managed via mongo_db.init_mongodb()
    pass


# ==============================================================================
#  WORK RATING  (Manager writes)
# ==============================================================================

def set_work_rating(
    *,
    employee_id: str,
    department: str,
    month: str,          # "YYYY-MM"
    work_target: float,
    work_actual: float,
    notes: str = "",
    rated_by: str = "",
) -> dict[str, Any]:
    mongo_db.update_one(
        "kpi_ratings",
        {"employee_id": employee_id, "month": month},
        {"$set": {
            "department": department,
            "month": month,
            "rated_by": rated_by,
            "work_target": work_target,
            "work_actual": work_actual,
            "notes": notes,
            "updated_at": mongo_db.now_iso()
        }},
        upsert=True
    )
    return {"success": True, "employee_id": employee_id, "month": month}


def _get_work_rating(employee_ids: list[str], month: str) -> Optional[dict[str, Any]]:
    # Try exact month first
    res = mongo_db.find_one("kpi_ratings", {"employee_id": {"$in": employee_ids}, "month": month})
    if res:
        return res

    # Carry-forward: get the most recent rating before this month
    res = mongo_db.find_many(
        "kpi_ratings",
        {"employee_id": {"$in": employee_ids}, "month": {"$lt": month}},
        sort=[("month", -1)],
        limit=1
    )
    return res[0] if res else None


# ==============================================================================
#  PILLAR CALCULATORS
# ==============================================================================

def _calc_learning_score(employee_ids: list[str]) -> tuple[float, int, float]:
    """Returns (learning_score, courses_done, avg_quiz_score)."""
    try:
        # Pull from quiz_results (was employee_course_progress in SQLite)
        results = mongo_db.find_many("quiz_results", {"user_id": {"$in": employee_ids}})
        if not results:
            return 0.0, 0, 0.0

        scores = [float(r.get("score", 0)) for r in results]
        courses_done = len(scores)
        avg_quiz = round(sum(scores) / courses_done, 1)

        # Scale: full credit needs 3 courses; partial if fewer
        completion_factor = min(courses_done / 3, 1.0)
        learning_score = round(avg_quiz * completion_factor, 1)
        return learning_score, courses_done, avg_quiz
    except Exception:
        return 0.0, 0, 0.0


def _calc_attendance_score(employee_ids: list[str], month: str) -> tuple[float, int]:
    """Returns (attendance_score, leave_days_taken)."""
    year_str, month_str = month.split("-")
    prefix = f"{year_str}-{month_str}"
    try:
        # In MongoDB, we use gsheet_uid for employee_id
        # and leaves are stored in 'leaves' collection
        query = {
            "employee_id": {"$in": employee_ids},
            "status": {"$regex": "(?i)^approved$"},
            "$or": [
                {"start_date": {"$regex": f"^{prefix}"}},
                {"end_date": {"$regex": f"^{prefix}"}},
                {"$and": [{"start_date": {"$lte": f"{prefix}-28"}}, {"end_date": {"$gte": f"{prefix}-01"}}]}
            ]
        }
        rows = mongo_db.find_many("leaves", query)
    except Exception:
        return 100.0, 0

    leave_days = 0
    for r in rows:
        try:
            start = datetime.strptime(r["start_date"], "%Y-%m-%d")
            end   = datetime.strptime(r["end_date"],   "%Y-%m-%d")
            # Count only days within the target month
            month_start = datetime(int(year_str), int(month_str), 1)
            import calendar as _cal
            last_day = _cal.monthrange(int(year_str), int(month_str))[1]
            month_end = datetime(int(year_str), int(month_str), last_day)
            overlap_start = max(start, month_start)
            overlap_end   = min(end,   month_end)
            days = (overlap_end - overlap_start).days + 1
            if days > 0:
                leave_days += days
        except Exception:
            pass

    score = max(0.0, round(100 - (leave_days / WORKING_DAYS_PER_MONTH * 100), 1))
    return score, leave_days


def _calc_work_score(employee_ids: list[str], month: str) -> tuple[float, Optional[dict]]:
    """Returns (work_score, rating_row_or_None)."""
    rating = _get_work_rating(employee_ids, month)
    if not rating or rating.get("work_target", 0) == 0:
        return float(DEFAULT_WORK_SCORE), rating

    target = float(rating["work_target"])
    actual = float(rating["work_actual"])
    score  = min(100.0, round((actual / target) * 100, 1))
    return score, rating


def _calc_growth_score(employee_id: str) -> tuple[float, int, list[str], str]:
    """Returns (growth_score, streak, badges, level)."""
    try:
        from .Growth_tracker import get_employee_progress_report
        report = get_employee_progress_report(employee_id)
        
        streak  = report.get("current_streak", 0)
        badges  = report.get("badges", [])
        
        # completions count
        n = report.get("courses_completed", 0)
        if n >= 20:    level = "Senior"
        elif n >= 10:  level = "Intermediate"
        elif n >= 4:   level = "Associate"
        else:          level = "Beginner"
        
        level_score   = LEVEL_SCORES.get(level, 20)
        badge_score   = min(len(badges) * 10, 40)
        streak_score  = min(streak * 5, 20)
        growth_score  = min(100.0, float(level_score + badge_score + streak_score))
        
        return growth_score, streak, badges, level
    except Exception as e:
        print(f"  [KPI] Error calculating growth score via GrowthTracker: {e}")
        return 20.0, 0, [], "Beginner"


# ==============================================================================
#  OVERALL KPI COMPOSER
# ==============================================================================

def _rating_label(overall: float) -> str:
    for threshold, label in RATING_THRESHOLDS:
        if overall >= threshold:
            return label
    return "[WARN] Needs Attention"


def compute_employee_kpi(
    employee_id: str,
    department: str,
    month: Optional[str] = None,
) -> dict[str, Any]:
    """
    Compute the full KPI for one employee for the given month (default: current month).
    """
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Resolve employee aliases (historical records sometimes used Mongo _id as user_id)
    emp_name = employee_id
    resolved_ids = {str(employee_id).strip()} if str(employee_id).strip() else set()
    try:
        or_terms: list[dict[str, Any]] = [
            {"gsheet_uid": employee_id},
            {"id": employee_id},
            {"userId": employee_id},
        ]
        if ObjectId.is_valid(str(employee_id)):
            or_terms.append({"_id": ObjectId(str(employee_id))})
        emp = mongo_db.find_one("employees", {"$or": or_terms})
        if emp:
            emp_name = emp.get("name", employee_id)
            for key in ("gsheet_uid", "id", "userId", "_id"):
                val = str(emp.get(key) or "").strip()
                if val:
                    resolved_ids.add(val)
    except Exception:
        emp = None

    # Canonical id used in API responses
    canonical_employee_id = str(employee_id).strip()
    employee_ids = [eid for eid in sorted(resolved_ids) if eid]
    if not employee_ids:
        employee_ids = [canonical_employee_id]

    # Pillar scores
    safe_print(f"  [KPI Debug] Computing pillar scores for {canonical_employee_id} ({month})")
     
    try:
        learning_score, courses_done, avg_quiz = _calc_learning_score(employee_ids)
        safe_print(f"  [KPI Debug] Learning: {learning_score}")
         
        attendance_score, leave_days           = _calc_attendance_score(employee_ids, month)
        safe_print(f"  [KPI Debug] Attendance: {attendance_score}")
         
        work_score, rating_row                 = _calc_work_score(employee_ids, month)
        safe_print(f"  [KPI Debug] Work: {work_score}")
         
        growth_score, streak, badges, level    = _calc_growth_score(canonical_employee_id)
        safe_print(f"  [KPI Debug] Growth: {growth_score}")
    except Exception as e:
        safe_print(f"  [KPI Debug] PILLAR CRASH for {employee_id}: {e}")
        import traceback
        safe_print(traceback.format_exc())
        raise

    # Weighted overall
    overall = round(
        learning_score    * 0.30
        + attendance_score * 0.25
        + work_score       * 0.30
        + growth_score     * 0.15,
        1,
    )

    work_target = float((rating_row or {}).get("work_target", 100))
    work_actual = float((rating_row or {}).get("work_actual", 0))
    is_carried  = bool(rating_row and rating_row.get("month") != month)

    return {
        "employee_id":       canonical_employee_id,
        "employee_name":     emp_name,
        "department":        department,
        "month":             month,
        "scores": {
            "learning":     learning_score,
            "attendance":   attendance_score,
            "work_output":  work_score,
            "growth":       growth_score,
        },
        "overall":           overall,
        "rating":            _rating_label(overall),
        "badges":            badges,
        "streak":            streak,
        "level":             level,
        "leave_days":        leave_days,
        "courses_done":      courses_done,
        "avg_quiz_score":    avg_quiz,
        "work_target":       work_target,
        "work_actual":       work_actual,
        "work_rating_notes": (rating_row or {}).get("notes", ""),
        "work_rating_carried_forward": is_carried,
    }


# ==============================================================================
#  DEPARTMENT VIEW  (Manager)
# ==============================================================================

def get_department_kpi(department: str, month: Optional[str] = None) -> dict[str, Any]:
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    rows = mongo_db.find_many("employees", {
        "department": {"$regex": f"(?i)^{department}$"},
        "role": {"$regex": "(?i)^employee$"}
    })

    employees_kpi = []
    for emp in rows:
        uid = str(emp.get("gsheet_uid") or emp.get("id") or emp.get("userId") or emp.get("_id") or "").strip()
        if not uid:
            continue
        kpi = compute_employee_kpi(uid, department, month)
        employees_kpi.append(kpi)

    # Sort by overall score desc
    employees_kpi.sort(key=lambda x: x["overall"], reverse=True)

    dept_avg = 0.0
    if employees_kpi:
        dept_avg = round(sum(k["overall"] for k in employees_kpi) / len(employees_kpi), 1)

    return {
        "department":  department,
        "month":       month,
        "dept_avg":    dept_avg,
        "dept_rating": _rating_label(dept_avg),
        "employees":   employees_kpi,
    }


# ==============================================================================
#  ORG VIEW  (Admin)
# ==============================================================================

def get_org_kpi(month: Optional[str] = None) -> dict[str, Any]:
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Get distinct departments using aggregation
    pipeline = [
        {"$match": {"role": {"$regex": "(?i)^employee$"}}},
        {"$group": {"_id": "$department"}}
    ]
    dept_rows = mongo_db.aggregate("employees", pipeline)
    departments = [r["_id"] for r in dept_rows if r.get("_id")]

    dept_summaries = []
    for dept in departments:
        dept_data = get_department_kpi(dept, month)
        dept_summaries.append({
            "department":    dept,
            "dept_avg":      dept_data["dept_avg"],
            "dept_rating":   dept_data["dept_rating"],
            "employee_count": len(dept_data["employees"]),
            "month":         month,
        })

    dept_summaries.sort(key=lambda x: x["dept_avg"], reverse=True)

    org_avg = 0.0
    if dept_summaries:
        org_avg = round(sum(d["dept_avg"] for d in dept_summaries) / len(dept_summaries), 1)

    return {
        "month":        month,
        "org_avg":      org_avg,
        "org_rating":   _rating_label(org_avg),
        "departments":  dept_summaries,
    }
