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

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# -- Paths ----------------------------------------------------------------------
_AGENTS_DIR      = Path(__file__).resolve().parent
CALENDAR_DB_PATH = _AGENTS_DIR / "calendar.db"
GROWTH_DB_PATH   = _AGENTS_DIR / "growth_tracker.db"

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

def _cal_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(CALENDAR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _growth_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(GROWTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ==============================================================================
#  INIT  create kpi_ratings table inside calendar.db
# ==============================================================================

def init_kpi_db() -> None:
    conn = _cal_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kpi_ratings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT    NOT NULL,
            department  TEXT    NOT NULL,
            month       TEXT    NOT NULL,       -- "YYYY-MM"
            rated_by    TEXT    DEFAULT '',
            work_target REAL    DEFAULT 100,
            work_actual REAL    DEFAULT 0,
            notes       TEXT    DEFAULT '',
            updated_at  TEXT    DEFAULT (datetime('now'))
        )
    """)
    # Unique constraint so upsert works cleanly
    try:
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_kpi_unique
            ON kpi_ratings (employee_id, month)
        """)
    except Exception:
        pass
    conn.commit()
    conn.close()


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
    init_kpi_db()
    conn = _cal_conn()
    conn.execute("""
        INSERT INTO kpi_ratings
            (employee_id, department, month, rated_by, work_target, work_actual, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(employee_id, month) DO UPDATE SET
            department  = excluded.department,
            rated_by    = excluded.rated_by,
            work_target = excluded.work_target,
            work_actual = excluded.work_actual,
            notes       = excluded.notes,
            updated_at  = excluded.updated_at
    """, (employee_id, department, month, rated_by, work_target, work_actual, notes, _utc_now()))
    conn.commit()
    conn.close()
    return {"success": True, "employee_id": employee_id, "month": month}


def _get_work_rating(employee_id: str, month: str) -> Optional[dict[str, Any]]:
    """
    Returns the latest work rating for the given month.
    If not found for this month, look for the most recent previous month (carry-forward).
    """
    init_kpi_db()
    conn = _cal_conn()
    # Try exact month first
    row = conn.execute(
        "SELECT * FROM kpi_ratings WHERE employee_id=? AND month=?",
        (employee_id, month),
    ).fetchone()
    if row:
        conn.close()
        return dict(row)

    # Carry-forward: get the most recent rating before this month
    row = conn.execute(
        "SELECT * FROM kpi_ratings WHERE employee_id=? AND month < ? ORDER BY month DESC LIMIT 1",
        (employee_id, month),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ==============================================================================
#  PILLAR CALCULATORS
# ==============================================================================

def _calc_learning_score(employee_id: str) -> tuple[float, int, float]:
    """Returns (learning_score, courses_done, avg_quiz_score)."""
    try:
        conn = _growth_conn()
        rows = conn.execute(
            "SELECT score FROM employee_course_progress WHERE employee_id=? AND status='Completed'",
            (employee_id,),
        ).fetchall()
        conn.close()
    except Exception:
        return 0.0, 0, 0.0

    if not rows:
        return 0.0, 0, 0.0

    scores = [float(r["score"]) for r in rows]
    courses_done = len(scores)
    avg_quiz = round(sum(scores) / courses_done, 1)

    # Scale: full credit needs 3 courses; partial if fewer
    completion_factor = min(courses_done / 3, 1.0)
    learning_score = round(avg_quiz * completion_factor, 1)
    return learning_score, courses_done, avg_quiz


def _calc_attendance_score(employee_id: str, month: str) -> tuple[float, int]:
    """Returns (attendance_score, leave_days_taken)."""
    year_str, month_str = month.split("-")
    prefix = f"{year_str}-{month_str}"
    try:
        conn = _cal_conn()
        # Resolve SQLite numeric employee_id from gsheet_uid
        emp_row = conn.execute(
            "SELECT id FROM employees WHERE gsheet_uid=?", (employee_id,)
        ).fetchone()
        if not emp_row:
            # Try direct numeric match
            emp_row = conn.execute(
                "SELECT id FROM employees WHERE CAST(id AS TEXT)=?", (employee_id,)
            ).fetchone()
        if not emp_row:
            conn.close()
            return 100.0, 0

        db_id = emp_row["id"]
        rows = conn.execute(
            """
            SELECT start_date, end_date FROM leaves
            WHERE employee_id=? AND status='approved'
              AND (start_date LIKE ? OR end_date LIKE ?
                   OR (start_date <= ? AND end_date >= ?))
            """,
            (db_id, f"{prefix}%", f"{prefix}%", f"{prefix}-28", f"{prefix}-01"),
        ).fetchall()
        conn.close()
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


def _calc_work_score(employee_id: str, month: str) -> tuple[float, Optional[dict]]:
    """Returns (work_score, rating_row_or_None)."""
    rating = _get_work_rating(employee_id, month)
    if not rating or rating.get("work_target", 0) == 0:
        return float(DEFAULT_WORK_SCORE), rating

    target = float(rating["work_target"])
    actual = float(rating["work_actual"])
    score  = min(100.0, round((actual / target) * 100, 1))
    return score, rating


def _calc_growth_score(employee_id: str) -> tuple[float, int, list[str], str]:
    """Returns (growth_score, streak, badges, level)."""
    try:
        _tracker_data_path = _AGENTS_DIR.parent / "data" / "generated_courses" / "growth_data.json"
        if _tracker_data_path.exists():
            data = json.loads(_tracker_data_path.read_text(encoding="utf-8"))
            emp = data.get("employees", {}).get(employee_id, {})
        else:
            emp = {}
    except Exception:
        emp = {}

    streak  = emp.get("streaks", {}).get("current", 0)
    badges  = emp.get("badges", [])
    level   = emp.get("level", "Beginner")   # may not be stored in JSON; derive below

    # Derive level from completions count
    completions = emp.get("completions", [])
    n = len(completions)
    if n >= 20:    level = "Senior"
    elif n >= 10:  level = "Intermediate"
    elif n >= 4:   level = "Associate"
    else:          level = "Beginner"

    level_score   = LEVEL_SCORES.get(level, 20)
    badge_score   = min(len(badges) * 10, 40)
    streak_score  = min(streak * 5, 20)
    growth_score  = min(100.0, float(level_score + badge_score + streak_score))

    return growth_score, streak, badges, level


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

    # Fetch employee name from DB
    emp_name = employee_id
    try:
        conn = _cal_conn()
        row = conn.execute(
            "SELECT name FROM employees WHERE gsheet_uid=?", (employee_id,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT name FROM employees WHERE CAST(id AS TEXT)=?", (employee_id,)
            ).fetchone()
        if row:
            emp_name = row["name"]
        conn.close()
    except Exception:
        pass

    # Pillar scores
    learning_score, courses_done, avg_quiz = _calc_learning_score(employee_id)
    attendance_score, leave_days           = _calc_attendance_score(employee_id, month)
    work_score, rating_row                 = _calc_work_score(employee_id, month)
    growth_score, streak, badges, level    = _calc_growth_score(employee_id)

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
        "employee_id":       employee_id,
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

    init_kpi_db()
    conn = _cal_conn()
    rows = conn.execute(
        """
        SELECT id, name, gsheet_uid, role FROM employees
        WHERE LOWER(COALESCE(department,'')) = LOWER(?)
          AND LOWER(COALESCE(role,'')) = 'employee'
        """,
        (department,),
    ).fetchall()
    conn.close()

    employees_kpi = []
    for emp in rows:
        uid = str(emp["gsheet_uid"] or emp["id"])
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

    init_kpi_db()
    conn = _cal_conn()
    dept_rows = conn.execute(
        "SELECT DISTINCT COALESCE(department,'General') AS department FROM employees WHERE LOWER(role)='employee'"
    ).fetchall()
    conn.close()

    departments = [r["department"] for r in dept_rows if r["department"]]
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
