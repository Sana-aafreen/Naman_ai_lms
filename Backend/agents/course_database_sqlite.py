# -*- coding: utf-8 -*-
"""
course_database.py — NamanDarshan LMS Course Database v5.1
===========================================================
Single source of truth for all course persistence.

Architecture
────────────
• All generated HTML (index, per-module, final exam) is stored as TEXT
  in the DB.  NO files are written to disk during course generation.
• Files are only written when write_to_disk() is called explicitly
  (triggered by the /download/{id}/all-files endpoint).
• Supports SQLite (default, zero-config) and PostgreSQL (set DATABASE_URL).

Tables
──────
  courses          — course metadata + html_index + html_exam + course_json
  course_modules   — one row per module, html_content + module_json
  course_progress  — learner quiz scores (upsert on learner+course+module)
  course_certificates — completion certificates (issued on final exam pass)
  course_tags      — freeform tags per course (for filtering/search)

Public API (all consumed by course_generator.py)
────────────────────────────────────────────────
  db = CourseDatabase()
  db.init_schema()

  # Save
  course_id = db.save_course(result, html_index, module_htmls, html_exam, course_json)
  db.update_html(course_id, html_index, module_htmls, html_exam)

  # Read
  db.get_course(course_id)                        → dict | None
  db.list_courses(department?, limit?, offset?)   → list[dict]
  db.search_courses(query, department?)           → list[dict]
  db.get_modules(course_id)                       → list[dict]
  db.get_module_by_index(course_id, module_index) → dict | None
  db.get_html_for_download(course_id, key)        → (html_str, filename)
  db.get_module_assessments(module_db_id)         → list[dict]
  db.get_final_exam(course_id)                    → list[dict]

  # Disk (on-demand only)
  db.write_to_disk(course_id, out_dir)            → dict[str, Path]

  # Progress
  db.record_progress(learner_id, course_id, module_id, module_title,
                     department, score, passed, source)
  db.get_learner_progress(learner_id, course_id?) → list[dict]
  db.get_course_progress_summary(course_id)       → dict
  db.get_course_stats(course_id)                  → dict
  db.get_leaderboard(course_id, limit?)           → list[dict]

  # Certificates
  db.issue_certificate(learner_id, course_id, score) → dict
  db.get_certificate(learner_id, course_id)           → dict | None
  db.list_certificates(learner_id)                    → list[dict]

  # Tags
  db.add_tags(course_id, tags)
  db.get_tags(course_id)                          → list[str]
  db.list_courses_by_tag(tag)                     → list[dict]

  # Admin
  db.delete_course(course_id)                     → bool
  db.archive_course(course_id)                    → bool
  db.get_db_stats()                               → dict
  db.vacuum()

Internal helpers (imported by course_generator._update_db_html)
───────────────────────────────────────────────────────────────
  _get_connection()
  _ph()
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

# ── optional psycopg2 ─────────────────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    _PSYCOPG2_OK = True
except ImportError:
    psycopg2 = None  # type: ignore
    psycopg2_extras = None  # type: ignore
    _PSYCOPG2_OK = False

# ── configuration ─────────────────────────────────────────────────────────────
DATABASE_URL      = os.getenv("DATABASE_URL", "").strip()
_DEFAULT_SQLITE   = Path(__file__).resolve().parent.parent / "data" / "courses.db"
_SQLITE_PATH      = Path(os.getenv("SQLITE_DB_PATH", str(_DEFAULT_SQLITE)))

# Module-level SQLite singleton (safe for single-process FastAPI)
_sqlite_conn: Optional[sqlite3.Connection] = None


# ═════════════════════════════════════════════════════════════════════════════
# DRIVER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _is_postgres() -> bool:
    return bool(DATABASE_URL) and _PSYCOPG2_OK


def _ph() -> str:
    """Correct parameter placeholder for the active driver."""
    return "%s" if _is_postgres() else "?"


def _get_connection() -> Any:
    """
    Return a live DB connection.
    • PostgreSQL → new connection per call (not safe to share across threads)
    • SQLite     → module-level singleton with WAL mode
    """
    if _is_postgres():
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)  # type: ignore
        conn.autocommit = False
        return conn

    global _sqlite_conn
    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(
            str(_SQLITE_PATH),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        _sqlite_conn.row_factory = sqlite3.Row
        _sqlite_conn.execute("PRAGMA journal_mode=WAL")
        _sqlite_conn.execute("PRAGMA foreign_keys=ON")
        _sqlite_conn.execute("PRAGMA synchronous=NORMAL")
        _sqlite_conn.execute("PRAGMA cache_size=-32000")  # 32 MB cache
    return _sqlite_conn


@contextmanager
def _tx() -> Generator:
    """Context manager: get a connection, commit on success, rollback on error."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if _is_postgres():
            conn.close()


def _row(row) -> dict:
    """Convert sqlite3.Row / psycopg2 RealDictRow / None → plain dict."""
    if row is None:
        return {}
    return dict(row)


def _rows(cursor) -> list[dict]:
    return [_row(r) for r in cursor.fetchall()]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "general"


def _split_sql(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip()]


# ═════════════════════════════════════════════════════════════════════════════
# SCHEMA
# ═════════════════════════════════════════════════════════════════════════════

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS courses (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    department        TEXT     NOT NULL,
    title             TEXT     NOT NULL DEFAULT '',
    description       TEXT     NOT NULL DEFAULT '',
    duration          TEXT     NOT NULL DEFAULT '',
    level             TEXT     NOT NULL DEFAULT '',
    audience          TEXT     NOT NULL DEFAULT '',
    modules_count     INTEGER  NOT NULL DEFAULT 0,
    final_exam_count  INTEGER  NOT NULL DEFAULT 0,
    index_filename    TEXT     NOT NULL DEFAULT '',
    exam_filename     TEXT     NOT NULL DEFAULT '',
    html_index        TEXT,
    html_exam         TEXT,
    course_json       TEXT,
    is_archived       INTEGER  NOT NULL DEFAULT 0,
    created_at        TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at        TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS course_modules (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    course_id         INTEGER  NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_index      INTEGER  NOT NULL,
    module_id         TEXT     NOT NULL DEFAULT '',
    title             TEXT     NOT NULL DEFAULT '',
    duration          TEXT     NOT NULL DEFAULT '',
    lessons_count     INTEGER  NOT NULL DEFAULT 0,
    quiz_count        INTEGER  NOT NULL DEFAULT 0,
    html_filename     TEXT     NOT NULL DEFAULT '',
    html_content      TEXT,
    module_json       TEXT,
    created_at        TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS course_progress (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    learner_id    TEXT     NOT NULL,
    course_id     INTEGER  NOT NULL,
    module_id     TEXT     NOT NULL,
    module_title  TEXT     NOT NULL DEFAULT '',
    department    TEXT     NOT NULL DEFAULT '',
    score         INTEGER  NOT NULL DEFAULT 0,
    passed        INTEGER  NOT NULL DEFAULT 0,
    attempts      INTEGER  NOT NULL DEFAULT 1,
    source        TEXT     NOT NULL DEFAULT 'html_module',
    completed_at  TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(learner_id, course_id, module_id)
);

CREATE TABLE IF NOT EXISTS course_certificates (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    cert_id       TEXT     NOT NULL UNIQUE,
    learner_id    TEXT     NOT NULL,
    course_id     INTEGER  NOT NULL,
    course_title  TEXT     NOT NULL DEFAULT '',
    department    TEXT     NOT NULL DEFAULT '',
    score         INTEGER  NOT NULL DEFAULT 0,
    issued_at     TEXT     NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(learner_id, course_id)
);

CREATE TABLE IF NOT EXISTS course_tags (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    tag       TEXT    NOT NULL,
    UNIQUE(course_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_modules_course       ON course_modules(course_id, module_index);
CREATE INDEX IF NOT EXISTS idx_progress_learner     ON course_progress(learner_id);
CREATE INDEX IF NOT EXISTS idx_progress_course      ON course_progress(course_id);
CREATE INDEX IF NOT EXISTS idx_progress_lc          ON course_progress(learner_id, course_id);
CREATE INDEX IF NOT EXISTS idx_certs_learner        ON course_certificates(learner_id);
CREATE INDEX IF NOT EXISTS idx_certs_course         ON course_certificates(course_id);
CREATE INDEX IF NOT EXISTS idx_courses_dept         ON courses(department);
CREATE INDEX IF NOT EXISTS idx_courses_archived     ON courses(is_archived);
CREATE INDEX IF NOT EXISTS idx_tags_course          ON course_tags(course_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag             ON course_tags(tag)
"""

_SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS courses (
    id                SERIAL       PRIMARY KEY,
    department        TEXT         NOT NULL,
    title             TEXT         NOT NULL DEFAULT '',
    description       TEXT         NOT NULL DEFAULT '',
    duration          TEXT         NOT NULL DEFAULT '',
    level             TEXT         NOT NULL DEFAULT '',
    audience          TEXT         NOT NULL DEFAULT '',
    modules_count     INTEGER      NOT NULL DEFAULT 0,
    final_exam_count  INTEGER      NOT NULL DEFAULT 0,
    index_filename    TEXT         NOT NULL DEFAULT '',
    exam_filename     TEXT         NOT NULL DEFAULT '',
    html_index        TEXT,
    html_exam         TEXT,
    course_json       TEXT,
    is_archived       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_modules (
    id                SERIAL       PRIMARY KEY,
    course_id         INTEGER      NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    module_index      INTEGER      NOT NULL,
    module_id         TEXT         NOT NULL DEFAULT '',
    title             TEXT         NOT NULL DEFAULT '',
    duration          TEXT         NOT NULL DEFAULT '',
    lessons_count     INTEGER      NOT NULL DEFAULT 0,
    quiz_count        INTEGER      NOT NULL DEFAULT 0,
    html_filename     TEXT         NOT NULL DEFAULT '',
    html_content      TEXT,
    module_json       TEXT,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_progress (
    id            SERIAL       PRIMARY KEY,
    learner_id    TEXT         NOT NULL,
    course_id     INTEGER      NOT NULL,
    module_id     TEXT         NOT NULL,
    module_title  TEXT         NOT NULL DEFAULT '',
    department    TEXT         NOT NULL DEFAULT '',
    score         INTEGER      NOT NULL DEFAULT 0,
    passed        BOOLEAN      NOT NULL DEFAULT FALSE,
    attempts      INTEGER      NOT NULL DEFAULT 1,
    source        TEXT         NOT NULL DEFAULT 'html_module',
    completed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(learner_id, course_id, module_id)
);

CREATE TABLE IF NOT EXISTS course_certificates (
    id            SERIAL       PRIMARY KEY,
    cert_id       TEXT         NOT NULL UNIQUE,
    learner_id    TEXT         NOT NULL,
    course_id     INTEGER      NOT NULL,
    course_title  TEXT         NOT NULL DEFAULT '',
    department    TEXT         NOT NULL DEFAULT '',
    score         INTEGER      NOT NULL DEFAULT 0,
    issued_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(learner_id, course_id)
);

CREATE TABLE IF NOT EXISTS course_tags (
    id        SERIAL  PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    tag       TEXT    NOT NULL,
    UNIQUE(course_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_modules_course   ON course_modules(course_id, module_index);
CREATE INDEX IF NOT EXISTS idx_progress_learner ON course_progress(learner_id);
CREATE INDEX IF NOT EXISTS idx_progress_course  ON course_progress(course_id);
CREATE INDEX IF NOT EXISTS idx_progress_lc      ON course_progress(learner_id, course_id);
CREATE INDEX IF NOT EXISTS idx_certs_learner    ON course_certificates(learner_id);
CREATE INDEX IF NOT EXISTS idx_certs_course     ON course_certificates(course_id);
CREATE INDEX IF NOT EXISTS idx_courses_dept     ON courses(department);
CREATE INDEX IF NOT EXISTS idx_courses_archived ON courses(is_archived);
CREATE INDEX IF NOT EXISTS idx_tags_course      ON course_tags(course_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag         ON course_tags(tag)
"""


# ═════════════════════════════════════════════════════════════════════════════
# CourseDatabase
# ═════════════════════════════════════════════════════════════════════════════

class CourseDatabase:
    """
    All course persistence — HTML stored as TEXT, no disk I/O during generation.
    Disk files written only when explicitly requested via write_to_disk().
    """

    # ─────────────────────────────────────────────────────────────────────────
    # SCHEMA
    # ─────────────────────────────────────────────────────────────────────────

    def init_schema(self) -> None:
        """Create all tables and indexes if they don't exist yet."""
        schema = _SCHEMA_POSTGRES if _is_postgres() else _SCHEMA_SQLITE
        with _tx() as conn:
            cur = conn.cursor()
            for stmt in _split_sql(schema):
                cur.execute(stmt)
        print(f"  [DB] Schema ready ({('PostgreSQL' if _is_postgres() else 'SQLite')})")

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE COURSE  (DB-only; no files written)
    # ─────────────────────────────────────────────────────────────────────────

    def save_course(
        self,
        result: dict,
        html_index: str,
        module_htmls: list[str],
        html_exam: str,
        course_json: dict,
    ) -> int:
        """
        Persist a full course to the DB.
        Returns the new course id (db_course_id).

        All HTML is stored as TEXT.  Zero files written to disk.
        """
        ph = _ph()
        now = _now()

        idx_info       = result.get("index_html", {})
        index_filename = idx_info.get("html_filename", "")
        exam_info      = result.get("final_exam_html", {})
        exam_filename  = exam_info.get("html_filename", "")
        raw_modules    = course_json.get("modules", [])
        mod_meta_list  = result.get("module_htmls", [])

        with _tx() as conn:
            cur = conn.cursor()

            # ── INSERT courses ────────────────────────────────────────────
            cols = (
                "department, title, description, duration, level, audience, "
                "modules_count, final_exam_count, index_filename, exam_filename, "
                "html_index, html_exam, course_json, created_at, updated_at"
            )
            vals = (
                result.get("department", ""),
                result.get("title", ""),
                result.get("description", ""),
                result.get("duration", ""),
                result.get("level", ""),
                result.get("audience", ""),
                result.get("modules_count", len(module_htmls)),
                result.get("final_exam_count", len(course_json.get("final_exam", []))),
                index_filename,
                exam_filename,
                html_index,
                html_exam,
                json.dumps(course_json, ensure_ascii=False),
                now,
                now,
            )
            placeholders = ", ".join([ph] * len(vals))

            if _is_postgres():
                cur.execute(
                    f"INSERT INTO courses ({cols}) VALUES ({placeholders}) RETURNING id",
                    vals,
                )
                course_id = _row(cur.fetchone())["id"]
            else:
                cur.execute(
                    f"INSERT INTO courses ({cols}) VALUES ({placeholders})",
                    vals,
                )
                course_id = cur.lastrowid

            # ── INSERT course_modules ─────────────────────────────────────
            for i, html in enumerate(module_htmls):
                meta        = mod_meta_list[i] if i < len(mod_meta_list) else {}
                raw_mod     = raw_modules[i]   if i < len(raw_modules)   else {}
                mod_index   = i + 1
                mod_id      = meta.get("module_id",     raw_mod.get("module_id",  f"mod_{mod_index}"))
                mod_title   = meta.get("title",         raw_mod.get("title",      f"Module {mod_index}"))
                mod_dur     = meta.get("duration",      raw_mod.get("duration",   ""))
                lessons_cnt = meta.get("lessons_count", len(raw_mod.get("content", {}).get("lessons", [])))
                quiz_cnt    = meta.get("quiz_count",    len(raw_mod.get("quiz",    [])))
                html_fn     = meta.get("html_filename", "")
                mod_json_s  = json.dumps(raw_mod, ensure_ascii=False) if raw_mod else "{}"

                cur.execute(
                    f"""INSERT INTO course_modules
                        (course_id, module_index, module_id, title, duration,
                         lessons_count, quiz_count, html_filename,
                         html_content, module_json, created_at)
                        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})""",
                    (course_id, mod_index, mod_id, mod_title, mod_dur,
                     lessons_cnt, quiz_cnt, html_fn, html, mod_json_s, now),
                )

        print(f"  [DB] Course saved: id={course_id}, modules={len(module_htmls)}")
        return course_id

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE HTML  (re-render with real db_course_id baked into links)
    # ─────────────────────────────────────────────────────────────────────────

    def update_html(
        self,
        course_id: str,
        html_index: str,
        module_htmls: list[str],
        html_exam: str,
    ) -> None:
        """
        Replace stored HTML with versions that contain the real db_course_id
        in all nav links, download buttons, and postProgress() calls.
        Called once after initial save so every URL is correct.
        """
        ph  = _ph()
        now = _now()
        with _tx() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE courses SET html_index={ph}, html_exam={ph}, updated_at={ph} WHERE id={ph}",
                (html_index, html_exam, now, course_id),
            )
            # Fetch module row ids in order
            cur.execute(
                f"SELECT id FROM course_modules WHERE course_id={ph} ORDER BY module_index",
                (course_id,),
            )
            mod_rows = _rows(cur)
            for i, mod_row in enumerate(mod_rows):
                if i < len(module_htmls):
                    cur.execute(
                        f"UPDATE course_modules SET html_content={ph} WHERE id={ph}",
                        (module_htmls[i], mod_row["id"]),
                    )
        print(f"  [DB] HTML updated with db_course_id={course_id} ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # READ — COURSES
    # ─────────────────────────────────────────────────────────────────────────

    def get_course(self, course_id: str) -> Optional[dict]:
        """Full course row including html_index, html_exam, course_json."""
        ph = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM courses WHERE id={ph}", (course_id,))
            row = _row(cur.fetchone())
            if not row:
                return None
            row = self._deserialise_course(row)
            return row
        finally:
            if _is_postgres():
                conn.close()

    def list_courses(
        self,
        department: Optional[str] = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """List courses (metadata only — no HTML blobs)."""
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cols = ("id, department, title, description, duration, level, audience, "
                    "modules_count, final_exam_count, index_filename, exam_filename, "
                    "is_archived, created_at, updated_at")
            wheres, params = [], []

            if not include_archived:
                wheres.append(f"is_archived = {ph}")
                params.append(0 if not _is_postgres() else False)
            if department:
                wheres.append(f"department = {ph}")
                params.append(department)

            where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""

            if _is_postgres():
                cur.execute(
                    f"SELECT {cols} FROM courses {where_sql} "
                    f"ORDER BY id DESC LIMIT {ph} OFFSET {ph}",
                    params + [limit, offset],
                )
            else:
                cur.execute(
                    f"SELECT {cols} FROM courses {where_sql} "
                    f"ORDER BY id DESC LIMIT {ph} OFFSET {ph}",
                    params + [limit, offset],
                )
            return _rows(cur)
        finally:
            if _is_postgres():
                conn.close()

    def search_courses(
        self,
        query: str,
        department: Optional[str] = None,
    ) -> list[dict]:
        """
        Simple full-text search across title + description.
        Uses LIKE on SQLite; can be upgraded to tsvector on PostgreSQL.
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur  = conn.cursor()
            like = f"%{query}%"
            cols = ("id, department, title, description, duration, level, audience, "
                    "modules_count, final_exam_count, is_archived, created_at")

            if department:
                cur.execute(
                    f"SELECT {cols} FROM courses "
                    f"WHERE is_archived=0 AND department={ph} "
                    f"AND (title LIKE {ph} OR description LIKE {ph}) "
                    f"ORDER BY id DESC",
                    (department, like, like),
                )
            else:
                cur.execute(
                    f"SELECT {cols} FROM courses "
                    f"WHERE is_archived=0 "
                    f"AND (title LIKE {ph} OR description LIKE {ph}) "
                    f"ORDER BY id DESC",
                    (like, like),
                )
            return _rows(cur)
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # READ — MODULES
    # ─────────────────────────────────────────────────────────────────────────

    def get_modules(self, course_id: str) -> list[dict]:
        """All modules for a course. Includes html_content and module_json."""
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM course_modules WHERE course_id={ph} ORDER BY module_index",
                (course_id,),
            )
            rows = _rows(cur)
            for row in rows:
                if row.get("module_json"):
                    try:
                        row["module_json"] = json.loads(row["module_json"])
                    except Exception:
                        pass
            return rows
        finally:
            if _is_postgres():
                conn.close()

    def get_module_by_index(self, course_id: str, module_index: int) -> Optional[dict]:
        """Single module by 1-based index."""
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM course_modules WHERE course_id={ph} AND module_index={ph}",
                (course_id, module_index),
            )
            row = _row(cur.fetchone())
            if not row:
                return None
            if row.get("module_json"):
                try:
                    row["module_json"] = json.loads(row["module_json"])
                except Exception:
                    pass
            return row
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # HTML DELIVERY
    # ─────────────────────────────────────────────────────────────────────────

    def get_html_for_download(
        self, course_id: str, key: str
    ) -> tuple[Optional[str], str]:
        """
        Fetch HTML string + suggested filename from DB.

        key:
            "index"        → course dashboard page
            "exam"         → final exam page
            "module:{n}"   → 1-based module index  e.g. "module:3"

        Returns (html_str, filename).  html_str is None if not found.
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()

            if key == "index":
                cur.execute(
                    f"SELECT html_index, index_filename, department FROM courses WHERE id={ph}",
                    (course_id,),
                )
                row = _row(cur.fetchone())
                if not row:
                    return None, "index.html"
                fn = row.get("index_filename") or f"{_slugify(row.get('department','course'))}-index.html"
                return row.get("html_index"), fn

            if key == "exam":
                cur.execute(
                    f"SELECT html_exam, exam_filename, department FROM courses WHERE id={ph}",
                    (course_id,),
                )
                row = _row(cur.fetchone())
                if not row:
                    return None, "final-exam.html"
                fn = row.get("exam_filename") or f"{_slugify(row.get('department','course'))}-final-exam.html"
                return row.get("html_exam"), fn

            if key.startswith("module:"):
                try:
                    mod_index = int(key.split(":", 1)[1])
                except (IndexError, ValueError):
                    return None, "module.html"
                cur.execute(
                    f"SELECT html_content, html_filename FROM course_modules "
                    f"WHERE course_id={ph} AND module_index={ph}",
                    (course_id, mod_index),
                )
                row = _row(cur.fetchone())
                if not row:
                    return None, f"module-{mod_index:02d}.html"
                fn = row.get("html_filename") or f"module-{mod_index:02d}.html"
                return row.get("html_content"), fn

            return None, "file.html"

        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # QUIZ & EXAM EXTRACTION  (from stored JSON)
    # ─────────────────────────────────────────────────────────────────────────

    def get_module_assessments(self, module_db_id: int) -> list[dict]:
        """
        Return quiz questions for a module.
        module_db_id is the PK of course_modules (not module_index).
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT module_json FROM course_modules WHERE id={ph}",
                (module_db_id,),
            )
            row = _row(cur.fetchone())
            if not row:
                return []
            raw = row.get("module_json") or "{}"
            mod = json.loads(raw) if isinstance(raw, str) else raw
            return mod.get("quiz", [])
        finally:
            if _is_postgres():
                conn.close()

    def get_module_assessments_by_index(
        self, course_id: str, module_index: int
    ) -> list[dict]:
        """Quiz questions by course_id + 1-based module_index."""
        mod = self.get_module_by_index(course_id, module_index)
        if not mod:
            return []
        raw = mod.get("module_json") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return []
        return raw.get("quiz", [])

    def get_final_exam(self, course_id: str) -> list[dict]:
        """Final exam questions extracted from stored course_json."""
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT course_json FROM courses WHERE id={ph}",
                (course_id,),
            )
            row = _row(cur.fetchone())
            if not row:
                return []
            raw = row.get("course_json") or "{}"
            cj  = json.loads(raw) if isinstance(raw, str) else raw
            return cj.get("final_exam", [])
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # DISK WRITE  (on-demand only)
    # ─────────────────────────────────────────────────────────────────────────

    def write_to_disk(self, course_id: str, out_dir: Path) -> dict[str, Path]:
        """
        Write all course HTML to `out_dir`.
        Called ONLY when explicitly requested (download-all-files endpoint).
        Returns {key: Path} for each file written.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        written: dict[str, Path] = {}

        html, fn = self.get_html_for_download(course_id, "index")
        if html:
            p = out_dir / fn
            p.write_text(html, encoding="utf-8")
            written["index"] = p
            print(f"  [DB→Disk] index  → {p.name}")

        html, fn = self.get_html_for_download(course_id, "exam")
        if html:
            p = out_dir / fn
            p.write_text(html, encoding="utf-8")
            written["exam"] = p
            print(f"  [DB→Disk] exam   → {p.name}")

        for mod in self.get_modules(course_id):
            idx  = mod["module_index"]
            html, fn = self.get_html_for_download(course_id, f"module:{idx}")
            if html:
                p = out_dir / fn
                p.write_text(html, encoding="utf-8")
                written[f"module_{idx}"] = p
                print(f"  [DB→Disk] mod {idx:02d} → {p.name}")

        print(f"  [DB→Disk] {len(written)} file(s) written to {out_dir}")
        return written

    # ─────────────────────────────────────────────────────────────────────────
    # PROGRESS
    # ─────────────────────────────────────────────────────────────────────────

    def record_progress(
        self,
        learner_id: str,
        course_id: str,
        module_id: str,
        module_title: str,
        department: str,
        score: int,
        passed: bool,
        source: str = "html_module",
    ) -> None:
        """
        Upsert a progress row.
        On conflict (same learner + course + module) the score, passed flag,
        attempt counter, and timestamps are updated.
        """
        ph  = _ph()
        now = _now()
        passed_val = passed if _is_postgres() else int(passed)

        with _tx() as conn:
            cur = conn.cursor()
            if _is_postgres():
                cur.execute(
                    f"""INSERT INTO course_progress
                        (learner_id, course_id, module_id, module_title,
                         department, score, passed, attempts, source,
                         completed_at, updated_at)
                        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},1,{ph},{ph},{ph})
                        ON CONFLICT (learner_id, course_id, module_id)
                        DO UPDATE SET
                            score        = EXCLUDED.score,
                            passed       = EXCLUDED.passed,
                            attempts     = course_progress.attempts + 1,
                            source       = EXCLUDED.source,
                            updated_at   = EXCLUDED.updated_at""",
                    (learner_id, course_id, module_id, module_title,
                     department, score, passed_val, source, now, now),
                )
            else:
                cur.execute(
                    f"""INSERT INTO course_progress
                        (learner_id, course_id, module_id, module_title,
                         department, score, passed, attempts, source,
                         completed_at, updated_at)
                        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},1,{ph},{ph},{ph})
                        ON CONFLICT(learner_id, course_id, module_id)
                        DO UPDATE SET
                            score      = excluded.score,
                            passed     = excluded.passed,
                            attempts   = course_progress.attempts + 1,
                            source     = excluded.source,
                            updated_at = excluded.updated_at""",
                    (learner_id, course_id, module_id, module_title,
                     department, score, passed_val, source, now, now),
                )

    def get_learner_progress(
        self,
        learner_id: str,
        course_id: Optional[int] = None,
    ) -> list[dict]:
        """All progress rows for a learner, optionally filtered by course."""
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            if course_id is not None:
                cur.execute(
                    f"SELECT * FROM course_progress "
                    f"WHERE learner_id={ph} AND course_id={ph} "
                    f"ORDER BY updated_at DESC",
                    (learner_id, course_id),
                )
            else:
                cur.execute(
                    f"SELECT * FROM course_progress WHERE learner_id={ph} "
                    f"ORDER BY updated_at DESC",
                    (learner_id,),
                )
            rows = _rows(cur)
            # normalise passed to bool
            for r in rows:
                r["passed"] = bool(r.get("passed"))
            return rows
        finally:
            if _is_postgres():
                conn.close()

    def get_course_progress_summary(self, course_id: str) -> dict:
        """
        Per-module completion summary for a course: how many learners
        attempted vs passed each module.
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT
                      module_id, module_title,
                      COUNT(*)                                   AS attempts,
                      SUM(CASE WHEN passed THEN 1 ELSE 0 END)   AS passes,
                      ROUND(AVG(score), 1)                       AS avg_score,
                      MAX(score)                                 AS best_score
                    FROM course_progress
                    WHERE course_id = {ph}
                    GROUP BY module_id, module_title
                    ORDER BY module_id""",
                (course_id,),
            )
            return {"course_id": course_id, "modules": _rows(cur)}
        finally:
            if _is_postgres():
                conn.close()

    def get_course_stats(self, course_id: str) -> dict:
        """
        Aggregate stats for a course:
        unique learner count + per-module pass rates + avg scores.
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()

            cur.execute(
                f"""SELECT
                      module_id, module_title,
                      COUNT(*)                                  AS attempts,
                      SUM(CASE WHEN passed THEN 1 ELSE 0 END)  AS passes,
                      ROUND(AVG(score), 1)                      AS avg_score,
                      MAX(score)                                AS best_score,
                      MIN(score)                                AS min_score
                    FROM course_progress
                    WHERE course_id = {ph}
                    GROUP BY module_id, module_title
                    ORDER BY module_id""",
                (course_id,),
            )
            mod_stats = _rows(cur)

            cur.execute(
                f"SELECT COUNT(DISTINCT learner_id) AS n FROM course_progress WHERE course_id={ph}",
                (course_id,),
            )
            n_learners = _row(cur.fetchone()).get("n", 0)

            cur.execute(
                f"SELECT COUNT(*) AS n FROM course_certificates WHERE course_id={ph}",
                (course_id,),
            )
            n_certs = _row(cur.fetchone()).get("n", 0)

            return {
                "course_id":      course_id,
                "unique_learners": n_learners,
                "certificates":    n_certs,
                "modules":         mod_stats,
            }
        finally:
            if _is_postgres():
                conn.close()

    def get_leaderboard(self, course_id: str, limit: int = 10) -> list[dict]:
        """
        Top learners for a course by average score across all passed modules.
        """
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT
                      learner_id,
                      COUNT(*)                                  AS modules_passed,
                      ROUND(AVG(score), 1)                      AS avg_score,
                      MAX(updated_at)                           AS last_activity
                    FROM course_progress
                    WHERE course_id={ph} AND passed=1
                    GROUP BY learner_id
                    ORDER BY avg_score DESC, modules_passed DESC
                    LIMIT {ph}""",
                (course_id, limit),
            )
            return _rows(cur)
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # CERTIFICATES
    # ─────────────────────────────────────────────────────────────────────────

    def issue_certificate(
        self,
        learner_id: str,
        course_id: str,
        score: int,
    ) -> dict:
        """
        Issue a completion certificate.
        Idempotent — returns the existing cert if already issued.
        """
        existing = self.get_certificate(learner_id, course_id)
        if existing:
            return existing

        ph   = _ph()
        now  = _now()
        cert_id = str(uuid.uuid4()).upper().replace("-", "")[:16]

        # Fetch course info for title + department
        course = self.get_course(course_id)
        c_title = course.get("title", "") if course else ""
        c_dept  = course.get("department", "") if course else ""

        with _tx() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""INSERT INTO course_certificates
                    (cert_id, learner_id, course_id, course_title, department, score, issued_at)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})""",
                (cert_id, learner_id, course_id, c_title, c_dept, score, now),
            )

        return {
            "cert_id":     cert_id,
            "learner_id":  learner_id,
            "course_id":   course_id,
            "course_title": c_title,
            "department":  c_dept,
            "score":       score,
            "issued_at":   now,
        }

    def get_certificate(self, learner_id: str, course_id: str) -> Optional[dict]:
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM course_certificates WHERE learner_id={ph} AND course_id={ph}",
                (learner_id, course_id),
            )
            row = _row(cur.fetchone())
            return row if row else None
        finally:
            if _is_postgres():
                conn.close()

    def list_certificates(self, learner_id: str) -> list[dict]:
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM course_certificates WHERE learner_id={ph} ORDER BY issued_at DESC",
                (learner_id,),
            )
            return _rows(cur)
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # TAGS
    # ─────────────────────────────────────────────────────────────────────────

    def add_tags(self, course_id: str, tags: list[str]) -> None:
        """Add freeform tags to a course. Duplicate tags are silently ignored."""
        ph = _ph()
        with _tx() as conn:
            cur = conn.cursor()
            for tag in set(t.strip().lower() for t in tags if t.strip()):
                if _is_postgres():
                    cur.execute(
                        f"INSERT INTO course_tags (course_id, tag) VALUES ({ph},{ph}) "
                        f"ON CONFLICT DO NOTHING",
                        (course_id, tag),
                    )
                else:
                    cur.execute(
                        f"INSERT OR IGNORE INTO course_tags (course_id, tag) VALUES ({ph},{ph})",
                        (course_id, tag),
                    )

    def get_tags(self, course_id: str) -> list[str]:
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT tag FROM course_tags WHERE course_id={ph} ORDER BY tag",
                (course_id,),
            )
            return [r["tag"] for r in _rows(cur)]
        finally:
            if _is_postgres():
                conn.close()

    def list_courses_by_tag(self, tag: str) -> list[dict]:
        ph   = _ph()
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""SELECT c.id, c.department, c.title, c.description,
                           c.modules_count, c.created_at
                    FROM courses c
                    JOIN course_tags t ON t.course_id = c.id
                    WHERE t.tag = {ph} AND c.is_archived = 0
                    ORDER BY c.id DESC""",
                (tag.strip().lower(),),
            )
            return _rows(cur)
        finally:
            if _is_postgres():
                conn.close()

    # ─────────────────────────────────────────────────────────────────────────
    # ADMIN
    # ─────────────────────────────────────────────────────────────────────────

    def delete_course(self, course_id: str) -> bool:
        """Hard-delete a course. Cascades to modules, progress, tags."""
        ph = _ph()
        with _tx() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM courses WHERE id={ph}", (course_id,))
            return cur.rowcount > 0

    def archive_course(self, course_id: str) -> bool:
        """Soft-delete — hides from list but keeps data intact."""
        ph  = _ph()
        now = _now()
        with _tx() as conn:
            cur = conn.cursor()
            archived_val = True if _is_postgres() else 1
            cur.execute(
                f"UPDATE courses SET is_archived={ph}, updated_at={ph} WHERE id={ph}",
                (archived_val, now, course_id),
            )
            return cur.rowcount > 0

    def unarchive_course(self, course_id: str) -> bool:
        ph  = _ph()
        now = _now()
        with _tx() as conn:
            cur = conn.cursor()
            archived_val = False if _is_postgres() else 0
            cur.execute(
                f"UPDATE courses SET is_archived={ph}, updated_at={ph} WHERE id={ph}",
                (archived_val, now, course_id),
            )
            return cur.rowcount > 0

    def get_db_stats(self) -> dict:
        """High-level counts across all tables."""
        conn = _get_connection()
        try:
            cur = conn.cursor()
            stats: dict[str, Any] = {}
            for tbl in ("courses", "course_modules", "course_progress", "course_certificates"):
                cur.execute(f"SELECT COUNT(*) AS n FROM {tbl}")
                stats[tbl] = _row(cur.fetchone()).get("n", 0)
            cur.execute("SELECT COUNT(*) AS n FROM courses WHERE is_archived=0")
            stats["active_courses"] = _row(cur.fetchone()).get("n", 0)
            cur.execute("SELECT COUNT(DISTINCT department) AS n FROM courses")
            stats["departments"] = _row(cur.fetchone()).get("n", 0)
            stats["backend"] = "PostgreSQL" if _is_postgres() else "SQLite"
            if not _is_postgres():
                stats["db_path"] = str(_SQLITE_PATH)
                try:
                    import os as _os
                    stats["db_size_mb"] = round(_os.path.getsize(str(_SQLITE_PATH)) / 1_048_576, 2)
                except Exception:
                    pass
            return stats
        finally:
            if _is_postgres():
                conn.close()

    def vacuum(self) -> None:
        """Reclaim space. SQLite only — runs VACUUM; no-op on PostgreSQL."""
        if _is_postgres():
            return
        conn = _get_connection()
        conn.execute("VACUUM")
        print("  [DB] VACUUM complete")

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _deserialise_course(row: dict) -> dict:
        """Parse course_json TEXT → dict in-place."""
        if row.get("course_json") and isinstance(row["course_json"], str):
            try:
                row["course_json"] = json.loads(row["course_json"])
            except Exception:
                pass
        return row