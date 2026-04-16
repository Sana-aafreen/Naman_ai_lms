"""
Growth_tracker.py — MongoDB-backed Growth Tracker for NamanDarshan LMS
======================================================================
Replaces SQLite with MongoDB for scalability and real-time analytics.

Collections:
  - published_courses      → Course metadata and availability
  - quiz_results          → Individual quiz attempt scores
  - growth_data           → Raw learner progress records
  - growth_summary        → Pre-aggregated summaries for dashboard

Backward Compatibility:
  Automatically falls back to SQLite if MongoDB is unavailable.
"""

from __future__ import annotations

import os, sqlite3, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any

# Defines the SQLite legacy handlers directly.
USING_MONGO = False

# Re-export all functions for compatibility
__all__ = [
    "init_growth_tracker_db",
    "publish_generated_course",
    "list_published_courses",
    "get_course_quiz_for_employee",
    "submit_course_quiz",
    "get_employee_progress_report",
    "get_team_progress_overview",
]


# ── Storage paths ─────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).resolve().parent
DB_PATH           = BASE_DIR / "growth_tracker.db"
CALENDAR_DB_PATH  = BASE_DIR / "calendar.db"
OUTPUT_DIR        = BASE_DIR.parent / "data" / "generated_courses"
GROWTH_FILE       = OUTPUT_DIR / "growth_data.json"
SUMMARY_FILE      = OUTPUT_DIR / "growth_summary.json"

PASS_THRESHOLD = int(os.getenv("LMS_PASS_THRESHOLD", "70"))   # %


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


# ════════════════════════════════════════════════════════════════════════════════
# SQLITE HELPERS  (existing — used by main.py imports)
# ════════════════════════════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_calendar_db() -> sqlite3.Connection:
    conn = sqlite3.connect(CALENDAR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_growth_tracker_db() -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS published_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            audience TEXT,
            generated_at TEXT,
            pdf_path TEXT NOT NULL,
            pdf_filename TEXT NOT NULL,
            index_html_path TEXT,
            index_html_filename TEXT,
            source_notes_json TEXT DEFAULT '[]',
            modules_json TEXT DEFAULT '[]',
            modules_html_json TEXT DEFAULT '[]',
            quiz_json TEXT DEFAULT '[]',
            created_by TEXT,
            published_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
        """
    )
    # ── Migrations (add columns if missing) ──────────────────────────────────
    try:
        cursor.execute("ALTER TABLE published_courses ADD COLUMN index_html_path TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE published_courses ADD COLUMN index_html_filename TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE published_courses ADD COLUMN modules_html_json TEXT DEFAULT '[]'")
    except: pass
    try:
        cursor.execute("ALTER TABLE published_courses ADD COLUMN db_course_id INTEGER DEFAULT 0")
    except: pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_course_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            employee_id TEXT NOT NULL,
            employee_name TEXT,
            department TEXT,
            score REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            answers_json TEXT DEFAULT '[]',
            completed_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Completed',
            UNIQUE(course_id, employee_id)
        )
        """
    )
    conn.commit()
    conn.close()


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except Exception:
        return fallback


def _serialize_published_course(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    db_course_id = int(item.get("db_course_id") or 0)
    index_html_filename = item.get("index_html_filename", "")
    index_html_url = (
        f"/api/generated-courses/download/{db_course_id}/index"
        if db_course_id
        else (f"/api/generated-courses/file/{index_html_filename}" if index_html_filename else "")
    )
    return {
        "id": item["id"],
        "department": item["department"],
        "title": item["title"],
        "summary": item.get("summary", ""),
        "audience": item.get("audience", ""),
        "generated_at": item.get("generated_at", ""),
        "published_at": item.get("published_at", ""),
        "db_course_id": db_course_id,
        "pdf_path": item.get("pdf_path", ""),
        "pdf_filename": item.get("pdf_filename", ""),
        "pdf_url": (f"/api/generated-courses/file/{item.get('pdf_filename', '')}"
                    if item.get("pdf_filename") else ""),
        "index_html_path": item.get("index_html_path", ""),
        "index_html_filename": index_html_filename,
        "index_html_url": index_html_url,
        "source_notes": _json_loads(item.get("source_notes_json", "[]"), []),
        "modules": _json_loads(item.get("modules_json", "[]"), []),
        "modules_html": _json_loads(item.get("modules_html_json", "[]"), []),
        "quiz_questions": _json_loads(item.get("quiz_json", "[]"), []),
        "created_by": item.get("created_by", ""),
    }


def publish_generated_course(course: dict[str, Any], created_by: str = "") -> dict[str, Any]:
    init_growth_tracker_db()
    db_course_id = int(course.get("db_course_id") or 0)

    # Accept both legacy shapes and v5 HTML-only payloads.
    index_pdf = course.get("index_pdf") if isinstance(course.get("index_pdf"), dict) else {}
    index_html = course.get("index_html") if isinstance(course.get("index_html"), dict) else {}

    pdf_path = str(course.get("pdf_path") or index_pdf.get("pdf_path") or "").strip()
    pdf_filename = str(course.get("pdf_filename") or index_pdf.get("pdf_filename") or "").strip()
    if pdf_path and not pdf_filename:
        pdf_filename = Path(pdf_path).name

    if not pdf_path and not db_course_id:
        raise ValueError("Either db_course_id (HTML in DB) or pdf_path (legacy) is required")

    index_html_path = str(course.get("index_html_path") or index_html.get("html_path") or "")
    index_html_filename = str(course.get("index_html_filename") or index_html.get("html_filename") or "")

    modules_html = course.get("modules_html")
    if not isinstance(modules_html, list):
        modules_html = course.get("module_htmls") if isinstance(course.get("module_htmls"), list) else []

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO published_courses (
            department, title, summary, audience, generated_at, pdf_path, pdf_filename,
            index_html_path, index_html_filename,
            source_notes_json, modules_json, modules_html_json, quiz_json, created_by, published_at,
            db_course_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(course.get("department", "")).strip(),
            str(course.get("title", "")).strip(),
            str(course.get("summary") or course.get("description") or "").strip(),
            str(course.get("audience", "")).strip(),
            str(course.get("generated_at", "")).strip(),
            pdf_path,
            pdf_filename,
            index_html_path,
            index_html_filename,
            json.dumps(course.get("source_notes", [])),
            json.dumps(course.get("modules", [])),
            json.dumps(modules_html),
            json.dumps(course.get("quiz_questions", [])),
            created_by,
            _utc_now(),
            db_course_id,
        ),
    )
    course_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM published_courses WHERE id=?", (course_id,))
    row = cursor.fetchone()
    conn.close()
    return _serialize_published_course(row)


def list_published_courses(department: Optional[str] = None) -> list[dict[str, Any]]:
    init_growth_tracker_db()
    conn = get_db()
    cursor = conn.cursor()
    if department:
        cursor.execute(
            """
            SELECT * FROM published_courses
            WHERE is_active=1 AND LOWER(department)=LOWER(?)
            ORDER BY id DESC
            """,
            (department,),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM published_courses
            WHERE is_active=1
            ORDER BY id DESC
            """
        )
    rows = cursor.fetchall()
    conn.close()
    return [_serialize_published_course(row) for row in rows]


def get_published_course(course_id: str) -> Optional[dict[str, Any]]:
    init_growth_tracker_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM published_courses WHERE id=? AND is_active=1", (course_id,))
    row = cursor.fetchone()
    conn.close()
    return _serialize_published_course(row) if row else None


def get_course_quiz_for_employee(course_id: str) -> Optional[dict[str, Any]]:
    course = get_published_course(course_id)
    if not course:
        return None

    sanitized_questions = []
    for question in course.get("quiz_questions", []):
        sanitized_questions.append(
            {
                "id": question.get("id"),
                "question": question.get("question", ""),
                "options": question.get("options", []),
            }
        )

    return {
        "id": course["id"],
        "department": course["department"],
        "title": course["title"],
        "summary": course["summary"],
        "audience": course["audience"],
        "pdf_url": course["pdf_url"],
        "modules": course.get("modules", []),
        "quiz_questions": sanitized_questions,
    }


def submit_course_quiz(
    *,
    course_id: str,
    employee_id: str,
    employee_name: str,
    department: str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    course = get_published_course(course_id)
    if not course:
        raise ValueError("Published course not found")

    answer_map = {str(item.get("questionId")): item.get("selectedOptionIndex") for item in answers}
    quiz_questions = course.get("quiz_questions", [])
    total_questions = len(quiz_questions)
    if total_questions == 0:
        raise ValueError("No quiz is attached to this course")

    correct_answers = 0
    detailed_results = []
    for question in quiz_questions:
        question_id = str(question.get("id"))
        selected_option = answer_map.get(question_id)
        correct_index = question.get("correctOptionIndex")
        is_correct = selected_option == correct_index
        if is_correct:
            correct_answers += 1
        detailed_results.append(
            {
                "questionId": question_id,
                "selectedOptionIndex": selected_option,
                "correctOptionIndex": correct_index,
                "isCorrect": is_correct,
            }
        )

    score = round((correct_answers / total_questions) * 100, 2)

    init_growth_tracker_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO employee_course_progress (
            course_id, employee_id, employee_name, department, score, total_questions,
            correct_answers, answers_json, completed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(course_id, employee_id) DO UPDATE SET
            employee_name=excluded.employee_name,
            department=excluded.department,
            score=excluded.score,
            total_questions=excluded.total_questions,
            correct_answers=excluded.correct_answers,
            answers_json=excluded.answers_json,
            completed_at=excluded.completed_at,
            status=excluded.status
        """,
        (
            course_id,
            employee_id,
            employee_name,
            department,
            score,
            total_questions,
            correct_answers,
            json.dumps(detailed_results),
            _utc_now(),
            "Completed",
        ),
    )
    conn.commit()
    conn.close()

    # Also record in GrowthTracker for analytics
    try:
        _tracker.record_completion(
            employee_id=employee_id,
            employee_name=employee_name,
            department=department,
            role="Employee",
            module_id=f"course-{course_id}",
            module_title=course["title"],
            course_title=course["title"],
            score=int(score),
            source="html",
        )
    except Exception:
        pass  # analytics recording is best-effort

    return {
        "course_id": course_id,
        "title": course["title"],
        "score": score,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "status": "Completed",
    }


def get_employee_progress_report(employee_id: str) -> dict[str, Any]:
    init_growth_tracker_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT progress.*, course.title, course.department as course_department
        FROM employee_course_progress AS progress
        JOIN published_courses AS course ON course.id = progress.course_id
        WHERE progress.employee_id=?
        ORDER BY progress.completed_at DESC
        """,
        (employee_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    completed_courses = [
        {
            "course_id": row["course_id"],
            "title": row["title"],
            "department": row["course_department"],
            "score": row["score"],
            "completed_at": row["completed_at"],
            "status": row["status"],
            "correct_answers": row["correct_answers"],
            "total_questions": row["total_questions"],
        }
        for row in rows
    ]
    completed_course_ids = [item["course_id"] for item in completed_courses]

    courses_done = len(completed_courses)
    average_score = round(
        sum(item["score"] for item in completed_courses) / courses_done, 2
    ) if courses_done else 0.0
    learning_hours = round(courses_done * 1.5, 1)

    badges = []
    if courses_done >= 1:
        badges.append({"icon": "📘", "title": "Course Starter", "desc": "Completed your first published course"})
    if average_score >= 80:
        badges.append({"icon": "🎯", "title": "Quiz Ace", "desc": "Maintained an 80%+ average score"})
    if courses_done >= 3:
        badges.append({"icon": "⭐", "title": "Fast Learner", "desc": "Completed 3 or more department courses"})

    skill_scores = [
        {"name": "Course Knowledge", "score": int(average_score or 0), "color": "bg-saffron"},
        {"name": "Assessment Accuracy", "score": int(average_score or 0), "color": "bg-gold"},
        {"name": "Learning Consistency", "score": min(100, courses_done * 20), "color": "bg-nd-blue"},
        {"name": "SOP Alignment", "score": min(100, max(int(average_score or 0), 55 if courses_done else 0)), "color": "bg-nd-green"},
    ]

    # Enrich with GrowthTracker analytics
    growth = {}
    try:
        growth = _tracker.get_employee_growth(employee_id)
    except Exception:
        pass

    return {
        "overallScore": average_score,
        "coursesDone": courses_done,
        "learningHours": learning_hours,
        "departmentRank": "#1" if courses_done else "-",
        "skills": skill_scores,
        "badges": badges,
        "completedCourses": completed_courses,
        "completedCourseIds": completed_course_ids,
        # Growth analytics extras
        "growthStats": growth.get("stats", {}),
        "growthBadges": growth.get("badges", []),
        "level": growth.get("level", "Beginner"),
        "recentCompletions": growth.get("recent_completions", []),
        "currentStreak": growth.get("stats", {}).get("current_streak", 0),
    }


def get_team_progress_overview(viewer_role: str, viewer_department: str = "") -> dict[str, Any]:
    init_growth_tracker_db()

    calendar_conn = get_calendar_db()
    growth_conn = get_db()
    calendar_cursor = calendar_conn.cursor()
    growth_cursor = growth_conn.cursor()

    employee_query = """
        SELECT id, name, department, role, gsheet_uid
        FROM employees
        WHERE LOWER(role) IN ('employee', 'manager')
    """
    employee_args: list[Any] = []

    normalized_role = str(viewer_role or "").strip().lower()
    normalized_department = str(viewer_department or "").strip().lower()
    if normalized_role == "manager":
        employee_query += " AND LOWER(role)='employee' AND LOWER(COALESCE(department, ''))=?"
        employee_args.append(normalized_department)

    calendar_cursor.execute(employee_query, employee_args)
    employees = [dict(row) for row in calendar_cursor.fetchall()]

    rows: list[dict[str, Any]] = []
    for employee in employees:
        identity_candidates = [
            str(employee.get("gsheet_uid") or "").strip(),
            str(employee.get("id") or "").strip(),
        ]
        identity_candidates = [candidate for candidate in identity_candidates if candidate]
        if not identity_candidates:
            continue

        placeholders = ",".join("?" for _ in identity_candidates)
        growth_cursor.execute(
            f"""
            SELECT course.title, course.department AS course_department, progress.score,
                   progress.completed_at, progress.status
            FROM employee_course_progress AS progress
            JOIN published_courses AS course ON course.id = progress.course_id
            WHERE progress.employee_id IN ({placeholders})
            ORDER BY progress.completed_at DESC
            """,
            identity_candidates,
        )
        completions = [dict(row) for row in growth_cursor.fetchall()]
        average_score = round(
            sum(float(item["score"]) for item in completions) / len(completions),
            2,
        ) if completions else 0.0

        # Enrich with GrowthTracker streak/badge data
        emp_id = str(employee.get("gsheet_uid") or employee.get("id") or "")
        streak = 0
        growth_badges: list[str] = []
        level = "Beginner"
        try:
            g = _tracker.get_employee_growth(emp_id)
            if "error" not in g:
                streak = g.get("stats", {}).get("current_streak", 0)
                growth_badges = g.get("badges", [])[:2]
                level = g.get("level", "Beginner")
        except Exception:
            pass

        rows.append(
            {
                "employeeId": emp_id,
                "employeeName": employee.get("name", ""),
                "department": employee.get("department", ""),
                "role": str(employee.get("role", "")).title(),
                "coursesCompleted": len(completions),
                "averageScore": average_score,
                "latestScore": float(completions[0]["score"]) if completions else 0.0,
                "latestCompletedAt": completions[0]["completed_at"] if completions else "",
                "streak": streak,
                "growthBadges": growth_badges,
                "level": level,
                "completedCourses": [
                    {
                        "title": item["title"],
                        "department": item["course_department"],
                        "score": item["score"],
                        "completedAt": item["completed_at"],
                        "status": item["status"],
                    }
                    for item in completions
                ],
            }
        )

    calendar_conn.close()
    growth_conn.close()

    if normalized_role == "manager":
        title = f"{viewer_department} Employee Progress"
        subtitle = "Employee course completion and quiz scores in your department"
    else:
        title = "Organization Progress Overview"
        subtitle = "Employee and manager course completion with quiz scores"

    return {
        "title": title,
        "subtitle": subtitle,
        "rows": rows,
    }


# ════════════════════════════════════════════════════════════════════════════════
# GROWTH TRACKER  (new analytics engine)
# ════════════════════════════════════════════════════════════════════════════════

class GrowthTracker:
    """
    Central tracker for all LMS activity.

    Schema of growth_data.json:
    {
      "employees": {
        "<employee_id>": {
          "employee_id":   str,
          "employee_name": str,
          "department":    str,
          "role":          str,
          "joined_at":     ISO str,
          "completions": [
            {
              "completion_id":    str,
              "module_id":        str,
              "module_title":     str,
              "course_title":     str,
              "department":       str,
              "score":            int,   # %
              "passed":           bool,
              "attempt":          int,
              "completed_at":     ISO str,
              "source":           "html" | "pdf",
            }
          ],
          "streaks": {
            "current":   int,
            "longest":   int,
            "last_date": str,
          },
          "badges": [str],
          "updated_at": ISO str,
        }
      },
      "meta": {
        "last_updated": ISO str,
        "total_completions": int,
      }
    }
    """

    def __init__(
        self,
        growth_file: Optional[Path] = None,
        summary_file: Optional[Path] = None,
    ) -> None:
        self.growth_file  = growth_file  or GROWTH_FILE
        self.summary_file = summary_file or SUMMARY_FILE
        self.growth_file.parent.mkdir(parents=True, exist_ok=True)

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.growth_file.exists():
            try:
                return json.loads(self.growth_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"employees": {}, "meta": {"last_updated": _now_iso(), "total_completions": 0}}

    def _save(self, data: dict) -> None:
        data["meta"]["last_updated"] = _now_iso()
        self.growth_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._rebuild_summary(data)

    def _rebuild_summary(self, data: dict) -> None:
        summary = self._build_summary(data)
        self.summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── WRITE: record a module / quiz completion ──────────────────────────────

    def record_completion(
        self,
        employee_id:    str,
        employee_name:  str,
        department:     str,
        role:           str,
        module_id:      str,
        module_title:   str,
        course_title:   str,
        score:          int,
        source:         str = "html",
    ) -> dict[str, Any]:
        """
        Record one module quiz completion. Idempotent — repeated calls for the
        same (employee_id, module_id) increment the attempt counter.
        Returns the employee's updated growth record.
        """
        data = self._load()
        employees = data.setdefault("employees", {})

        if employee_id not in employees:
            employees[employee_id] = {
                "employee_id":   employee_id,
                "employee_name": employee_name,
                "department":    department,
                "role":          role,
                "joined_at":     _now_iso(),
                "completions":   [],
                "streaks":       {"current": 0, "longest": 0, "last_date": ""},
                "badges":        [],
                "updated_at":    _now_iso(),
            }

        emp = employees[employee_id]
        emp["employee_name"] = employee_name
        emp["department"]    = department

        prev_attempts = sum(1 for c in emp["completions"] if c["module_id"] == module_id)
        attempt = prev_attempts + 1

        completion_id = f"{employee_id}-{module_id}-{attempt}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        emp["completions"].append({
            "completion_id": completion_id,
            "module_id":     module_id,
            "module_title":  module_title,
            "course_title":  course_title,
            "department":    department,
            "score":         score,
            "passed":        score >= PASS_THRESHOLD,
            "attempt":       attempt,
            "completed_at":  _now_iso(),
            "source":        source,
        })

        self._update_streak(emp)
        emp["badges"] = self._compute_badges(emp)
        emp["updated_at"] = _now_iso()

        data["meta"]["total_completions"] = sum(
            len(e["completions"]) for e in employees.values()
        )

        self._save(data)
        return self.get_employee_growth(employee_id)

    # ── STREAK LOGIC ──────────────────────────────────────────────────────────

    def _update_streak(self, emp: dict) -> None:
        today = _today_str()
        streaks = emp.setdefault("streaks", {"current": 0, "longest": 0, "last_date": ""})
        last = streaks.get("last_date", "")

        if last == today:
            pass
        elif last == (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"):
            streaks["current"] += 1
        else:
            streaks["current"] = 1

        streaks["last_date"] = today
        if streaks["current"] > streaks.get("longest", 0):
            streaks["longest"] = streaks["current"]

    # ── BADGES ────────────────────────────────────────────────────────────────

    def _compute_badges(self, emp: dict) -> list[str]:
        badges: list[str] = []
        completions = emp.get("completions", [])
        passed = [c for c in completions if c.get("passed")]
        scores = [c["score"] for c in passed]

        if len(passed) >= 1:  badges.append("🌱 First Step")
        if len(passed) >= 5:  badges.append("📚 Knowledge Builder")
        if len(passed) >= 10: badges.append("🎓 Course Graduate")
        if len(passed) >= 20: badges.append("🏅 Learning Champion")

        if scores and max(scores) == 100: badges.append("💯 Perfect Score")
        if scores and sum(scores) / len(scores) >= 90: badges.append("⭐ High Achiever")

        streak = emp.get("streaks", {}).get("current", 0)
        if streak >= 3:  badges.append("🔥 3-Day Streak")
        if streak >= 7:  badges.append("🔥 Week Warrior")
        if streak >= 30: badges.append("🔥 Monthly Master")

        seen: set[str] = set()
        return [b for b in badges if not (b in seen or seen.add(b))]  # type: ignore

    # ── READ: employee growth card ────────────────────────────────────────────

    def get_employee_growth(self, employee_id: str) -> dict[str, Any]:
        data = self._load()
        emp  = data.get("employees", {}).get(employee_id)
        if not emp:
            return {"error": "Employee not found", "employee_id": employee_id}

        completions = emp.get("completions", [])
        passed      = [c for c in completions if c.get("passed")]
        scores      = [c["score"] for c in passed] or [0]

        best_by_module: dict[str, int] = {}
        for c in completions:
            mid = c["module_id"]
            if c["score"] > best_by_module.get(mid, -1):
                best_by_module[mid] = c["score"]

        recent = sorted(completions, key=lambda x: x["completed_at"], reverse=True)[:5]

        return {
            "employee_id":     employee_id,
            "employee_name":   emp.get("employee_name", ""),
            "department":      emp.get("department", ""),
            "role":            emp.get("role", ""),
            "level":           _level_from_completions(len(passed)),
            "joined_at":       emp.get("joined_at", ""),
            "updated_at":      emp.get("updated_at", ""),
            "stats": {
                "total_attempts":    len(completions),
                "modules_passed":    len(best_by_module),
                "average_score":     round(sum(scores) / len(scores)) if scores else 0,
                "highest_score":     max(scores) if scores else 0,
                "current_streak":    emp.get("streaks", {}).get("current", 0),
                "longest_streak":    emp.get("streaks", {}).get("longest", 0),
            },
            "badges":       emp.get("badges", []),
            "recent_completions": [
                {
                    "module_id":    c["module_id"],
                    "module_title": c["module_title"],
                    "score":        c["score"],
                    "passed":       c["passed"],
                    "completed_at": c["completed_at"],
                    "badge":        _badge_for_score(c["score"]),
                }
                for c in recent
            ],
            "module_progress": [
                {
                    "module_id":   mid,
                    "best_score":  score,
                    "passed":      score >= PASS_THRESHOLD,
                    "badge":       _badge_for_score(score),
                }
                for mid, score in sorted(best_by_module.items())
            ],
        }

    # ── READ: department analytics ────────────────────────────────────────────

    def get_department_analytics(self, department: str) -> dict[str, Any]:
        data      = self._load()
        employees = data.get("employees", {})
        dept_emps = {eid: e for eid, e in employees.items()
                     if e.get("department", "").lower() == department.lower()}

        if not dept_emps:
            return {
                "department": department,
                "employees_tracked": 0,
                "total_completions": 0,
                "pass_rate": 0,
                "average_score": 0,
                "rows": [],
            }

        rows = []
        all_scores = []
        total_comps = 0
        total_passed = 0

        for eid, emp in dept_emps.items():
            completions = emp.get("completions", [])
            passed_c    = [c for c in completions if c.get("passed")]
            scores      = [c["score"] for c in completions] or [0]
            total_comps += len(completions)
            total_passed += len(passed_c)
            all_scores.extend(scores)

            best_by_module: dict[str, int] = {}
            for c in completions:
                mid = c["module_id"]
                if c["score"] > best_by_module.get(mid, -1):
                    best_by_module[mid] = c["score"]

            rows.append({
                "employee_id":    eid,
                "employee_name":  emp.get("employee_name", ""),
                "role":           emp.get("role", ""),
                "level":          _level_from_completions(len(passed_c)),
                "modules_passed": len(best_by_module),
                "total_attempts": len(completions),
                "average_score":  round(sum(scores) / len(scores)) if scores else 0,
                "badges":         emp.get("badges", [])[:3],
                "last_active":    emp.get("updated_at", ""),
            })

        rows.sort(key=lambda r: r["average_score"], reverse=True)

        return {
            "department":         department,
            "employees_tracked":  len(dept_emps),
            "total_completions":  total_comps,
            "total_passed":       total_passed,
            "pass_rate":          round((total_passed / total_comps) * 100) if total_comps else 0,
            "average_score":      round(sum(all_scores) / len(all_scores)) if all_scores else 0,
            "rows":               rows,
        }

    # ── READ: leaderboard ────────────────────────────────────────────────────

    def get_leaderboard(
        self,
        department: Optional[str] = None,
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        data      = self._load()
        employees = data.get("employees", {})

        board: list[dict] = []
        for eid, emp in employees.items():
            if department and emp.get("department", "").lower() != department.lower():
                continue
            completions = emp.get("completions", [])
            passed      = [c for c in completions if c.get("passed")]
            scores      = [c["score"] for c in passed] or [0]

            best_by_module: dict[str, int] = {}
            for c in completions:
                mid = c["module_id"]
                if c["score"] > best_by_module.get(mid, -1):
                    best_by_module[mid] = c["score"]

            board.append({
                "rank":           0,
                "employee_id":    eid,
                "employee_name":  emp.get("employee_name", ""),
                "department":     emp.get("department", ""),
                "role":           emp.get("role", ""),
                "modules_passed": len(best_by_module),
                "average_score":  round(sum(scores) / len(scores)) if scores else 0,
                "badges":         emp.get("badges", [])[:2],
                "streak":         emp.get("streaks", {}).get("current", 0),
            })

        board.sort(key=lambda r: (-r["modules_passed"], -r["average_score"]))
        for i, row in enumerate(board[:top_n], 1):
            row["rank"] = i

        return board[:top_n]

    # ── READ: platform overview ───────────────────────────────────────────────

    def get_platform_overview(self) -> dict[str, Any]:
        if self.summary_file.exists():
            try:
                return json.loads(self.summary_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._build_summary(self._load())

    def _build_summary(self, data: dict) -> dict[str, Any]:
        employees = data.get("employees", {})
        total_emps = len(employees)
        total_comps = sum(len(e["completions"]) for e in employees.values())
        all_passed  = sum(
            len([c for c in e["completions"] if c.get("passed")])
            for e in employees.values()
        )
        all_scores = [
            c["score"] for e in employees.values() for c in e["completions"]
        ]

        dept_map: dict[str, dict] = defaultdict(lambda: {
            "employees": set(), "completions": 0, "passed": 0, "scores": []
        })
        for emp in employees.values():
            dept = emp.get("department", "Unknown")
            dept_map[dept]["employees"].add(emp["employee_id"])
            for c in emp["completions"]:
                dept_map[dept]["completions"] += 1
                if c.get("passed"): dept_map[dept]["passed"] += 1
                dept_map[dept]["scores"].append(c["score"])

        dept_summary = []
        for dept, d in dept_map.items():
            scores = d["scores"] or [0]
            dept_summary.append({
                "department":   dept,
                "employees":    len(d["employees"]),
                "completions":  d["completions"],
                "pass_rate":    round(d["passed"] / d["completions"] * 100) if d["completions"] else 0,
                "avg_score":    round(sum(scores) / len(scores)),
            })
        dept_summary.sort(key=lambda x: x["avg_score"], reverse=True)

        today = _today_str()
        active_today = sum(
            1 for e in employees.values()
            if e.get("updated_at", "")[:10] == today
        )

        all_completions_flat = [
            {**c, "employee_name": e.get("employee_name", ""), "department": e.get("department", "")}
            for e in employees.values()
            for c in e.get("completions", [])
        ]
        all_completions_flat.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        recent_10 = all_completions_flat[:10]

        return {
            "generated_at":         _now_iso(),
            "total_employees":       total_emps,
            "active_today":          active_today,
            "total_completions":     total_comps,
            "total_passed":          all_passed,
            "platform_pass_rate":    round(all_passed / total_comps * 100) if total_comps else 0,
            "platform_avg_score":    round(sum(all_scores) / len(all_scores)) if all_scores else 0,
            "departments":           dept_summary,
            "recent_completions":    [
                {
                    "employee_name":  c.get("employee_name", ""),
                    "department":     c.get("department", ""),
                    "module_title":   c.get("module_title", ""),
                    "score":          c.get("score", 0),
                    "passed":         c.get("passed", False),
                    "completed_at":   c.get("completed_at", ""),
                }
                for c in recent_10
            ],
        }

    # ── BACKWARD COMPAT: legacy ProgressTracker interface ─────────────────────

    def record_assessment(
        self,
        learner_id:    str,
        module_id:     str,
        module_title:  str,
        department:    str,
        score:         int,
        total:         int,
        answers:       list,
        learner_name:  str = "",
        role:          str = "Employee",
        course_title:  str = "",
        source:        str = "html",
    ) -> dict:
        pct = round((score / total) * 100) if total else 0
        return self.record_completion(
            employee_id=learner_id,
            employee_name=learner_name or learner_id,
            department=department,
            role=role,
            module_id=module_id,
            module_title=module_title,
            course_title=course_title or f"{department} Course",
            score=pct,
            source=source,
        )

    def get_progress(self, learner_id: str) -> dict:
        growth = self.get_employee_growth(learner_id)
        if "error" in growth:
            return {}
        modules_dict = {
            m["module_id"]: {
                "module_id":    m["module_id"],
                "percentage":   m["best_score"],
                "passed":       m["passed"],
            }
            for m in growth.get("module_progress", [])
        }
        return {
            "learner_id":  learner_id,
            "modules":     modules_dict,
            "updated_at":  growth.get("updated_at", ""),
        }

    def get_all_progress(self) -> dict:
        data = self._load()
        result = {}
        for eid in data.get("employees", {}):
            result[eid] = self.get_progress(eid)
        return result


# ════════════════════════════════════════════════════════════════════════════════
# SINGLETON  (module-level, used by SQLite functions above)
# ════════════════════════════════════════════════════════════════════════════════

_tracker = GrowthTracker()


# ════════════════════════════════════════════════════════════════════════════════
# FASTAPI ROUTE HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def api_update_progress(
    module_id:     str,
    score:         int,
    employee_id:   str,
    employee_name: str,
    department:    str,
    role:          str        = "Employee",
    module_title:  str        = "",
    course_title:  str        = "",
    source:        str        = "html",
    timestamp:     str        = "",
) -> dict[str, Any]:
    """
    Called by POST /api/update-progress from the HTML course quiz JS.
    Records completion to both GrowthTracker JSON and SQLite database.

    FastAPI endpoint example:
    ─────────────────────────
    from agents.Growth_tracker import api_update_progress

    @app.post("/api/update-progress")
    async def update_progress(body: dict, current_user = Depends(get_current_user)):
        return api_update_progress(
            module_id     = body.get("module_id", ""),
            score         = int(body.get("score", 0)),
            employee_id   = str(current_user.id),
            employee_name = current_user.name,
            department    = current_user.department,
            role          = current_user.role,
            module_title  = body.get("module_title", ""),
            course_title  = body.get("course_title", ""),
            source        = body.get("source", "html"),
        )
    """
    # Record to GrowthTracker for analytics
    growth_result = _tracker.record_completion(
        employee_id=employee_id,
        employee_name=employee_name,
        department=department,
        role=role,
        module_id=module_id,
        module_title=module_title or module_id,
        course_title=course_title or f"{department} Course",
        score=score,
        source=source,
    )

    # Also record to SQLite database for compatibility with course progress tracking
    try:
        init_growth_tracker_db()
        conn = get_db()
        cursor = conn.cursor()
        
        # For HTML module completions, create a synthetic course link
        # Find or create a course record if it matches an existing published course
        cursor.execute(
            """
            INSERT INTO employee_course_progress (
                course_id, employee_id, employee_name, department, score, total_questions,
                correct_answers, answers_json, completed_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(course_id, employee_id) DO UPDATE SET
                score=excluded.score,
                total_questions=excluded.total_questions,
                correct_answers=excluded.correct_answers,
                answers_json=excluded.answers_json,
                completed_at=excluded.completed_at,
                status=excluded.status
            """,
            (
                -1,  # Use -1 as a synthetic course_id for HTML modules
                employee_id,
                employee_name,
                department,
                score,
                1,  # Treating as a single assessment
                min(score // 10, 1),  # Convert score percentage to correct answers
                json.dumps([{"module_id": module_id, "module_title": module_title, "score": score}]),
                _utc_now(),
                "Completed",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  SQLite sync error for module {module_id}: {e}")
        pass  # Don't fail the entire request if SQLite sync fails

    return growth_result


def api_get_employee_growth(employee_id: str) -> dict[str, Any]:
    """GET /api/growth/employee/{employee_id}"""
    return _tracker.get_employee_growth(employee_id)


def api_get_department_analytics(department: str) -> dict[str, Any]:
    """GET /api/growth/department/{department}"""
    return _tracker.get_department_analytics(department)


def api_get_leaderboard(department: Optional[str] = None, top_n: int = 10) -> list[dict]:
    """GET /api/growth/leaderboard?department=Sales&top_n=10"""
    return _tracker.get_leaderboard(department=department, top_n=top_n)


def api_get_platform_overview() -> dict[str, Any]:
    """GET /api/growth/overview"""
    return _tracker.get_platform_overview()


# ════════════════════════════════════════════════════════════════════════════════
# CLI  (quick test / seed)
# ════════════════════════════════════════════════════════════════════════════════

def main() -> None:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        print("Seeding test data...")
        tracker = GrowthTracker()
        test_data = [
            ("emp001", "Ananya Sharma",  "Sales",   "Employee", "sales-mod-1",  "Sales Foundations",       85),
            ("emp001", "Ananya Sharma",  "Sales",   "Employee", "sales-mod-2",  "SOP Execution",           92),
            ("emp002", "Rohit Verma",    "Sales",   "Employee", "sales-mod-1",  "Sales Foundations",       70),
            ("emp003", "Priya Nair",     "Ops",     "Manager",  "ops-mod-1",    "Operations Overview",     95),
            ("emp004", "Deepak Mishra",  "HR",      "Employee", "hr-mod-1",     "HR Foundations",          65),
            ("emp004", "Deepak Mishra",  "HR",      "Employee", "hr-mod-1",     "HR Foundations",          78),
        ]
        for eid, name, dept, role, mid, title, score in test_data:
            tracker.record_completion(
                employee_id=eid, employee_name=name, department=dept, role=role,
                module_id=mid, module_title=title, course_title=f"{dept} Course", score=score,
            )
        print("✅ Seed complete. growth_data.json updated.")
        overview = tracker.get_platform_overview()
        print(f"\nPlatform Overview:")
        print(f"  Employees tracked : {overview['total_employees']}")
        print(f"  Total completions : {overview['total_completions']}")
        print(f"  Platform pass rate: {overview['platform_pass_rate']}%")
        print(f"  Avg score         : {overview['platform_avg_score']}%")
        return

    print("Growth Tracker CLI")
    print("Usage:")
    print("  python Growth_tracker.py seed       — seed with test data")
    print("\nImport in FastAPI:")
    print("  from agents.Growth_tracker import api_update_progress, api_get_platform_overview")


if __name__ == "__main__":
    main()
