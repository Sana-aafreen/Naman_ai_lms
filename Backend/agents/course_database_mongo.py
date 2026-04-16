# -*- coding: utf-8 -*-
"""
course_database_mongo.py — MongoDB Version of Course Database
==============================================================
Replaces SQLite-based course storage with MongoDB collections.

Collections:
  - courses              → Course metadata + HTML index + exam
  - course_modules       → Individual module content + module JSON
  - course_progress      → Learner quiz scores
  - course_certificates  → Completion certificates
  - course_tags          → Course tags for filtering

All IDs are UUID strings (str). The _id() helper coerces any int/str caller
so legacy code that passes integers is handled gracefully.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pymongo import ASCENDING, DESCENDING

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from mongo_db import (
    get_db,
    insert_one,
    find_one,
    find_many,
    update_one,
    count_documents,
    MongoCollection,
)


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "general"


# ════════════════════════════════════════════════════════════════════════════
# COURSE DATABASE
# ════════════════════════════════════════════════════════════════════════════

class CourseDatabase:
    """MongoDB-backed course store for NamanDarshan LMS."""

    def __init__(self):
        self.db = get_db()

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _id(course_id: Any) -> str:
        """
        Coerce any course_id (int or str) to str.
        Lets legacy callers that pass integers work without crashing.
        """
        return str(course_id)

    # ════════════════════════════════════════════════════════════════════════
    # SCHEMA INIT
    # ════════════════════════════════════════════════════════════════════════

    def init_schema(self) -> None:
        """Ensure all required collections exist (MongoDB creates them lazily)."""
        try:
            existing = set(self.db.list_collection_names())
            for col in ("courses", "course_modules", "course_progress",
                        "course_certificates", "course_tags"):
                if col not in existing:
                    self.db.create_collection(col)
            print("✅ Course database MongoDB collections initialised")
        except Exception as e:
            print(f"⚠️  Warning initialising course database: {e}")

    # ════════════════════════════════════════════════════════════════════════
    # COURSE CRUD
    # ════════════════════════════════════════════════════════════════════════

    def save_course(
        self,
        course_metadata: dict,
        html_index: str,
        module_htmls: dict[str, str],
        html_exam: str,
        course_json: dict,
    ) -> str:
        """
        Persist a complete course and return its UUID string ID.

        Args:
            course_metadata : dict with keys title, department, description, etc.
            html_index      : rendered index page HTML
            module_htmls    : {module_id: html_content} — keyed by module_id string
            html_exam       : rendered final exam HTML
            course_json     : full course structure dict

        Returns:
            course_id (UUID str)
        """
        course_id  = str(uuid.uuid4())
        dept_slug  = _slugify(course_metadata.get("department", "course"))
        now        = datetime.now(timezone.utc).isoformat()

        course_doc: dict[str, Any] = {
            "id":             course_id,
            "title":          course_metadata.get("title", ""),
            "department":     course_metadata.get("department", ""),
            "description":    course_metadata.get("description", ""),
            "duration":       course_metadata.get("duration", ""),
            "level":          course_metadata.get("level", ""),
            "audience":       course_metadata.get("audience", ""),
            "html_index":     html_index,
            "html_exam":      html_exam,
            "index_filename": f"{dept_slug}-index.html",
            "exam_filename":  f"{dept_slug}-final-exam.html",
            "course_json":    course_json,
            "created_at":     now,
            "updated_at":     now,
            "archived":       False,
        }

        insert_one("courses", course_doc)

        # Save each module
        modules_in_json: list[dict] = course_json.get("modules", [])
        # Build a lookup so we can store the module's JSON alongside its HTML
        mod_json_by_id: dict[str, dict] = {
            m.get("module_id", f"mod_{i+1}"): m
            for i, m in enumerate(modules_in_json)
        }

        for i, (module_id, html_content) in enumerate(module_htmls.items(), 1):
            module_doc: dict[str, Any] = {
                "course_id":     course_id,
                "module_id":     module_id,
                "module_index":  i,
                "title":         mod_json_by_id.get(module_id, {}).get("title", f"Module {i}"),
                "html_content":  html_content,
                "html_filename": f"module-{i:02d}.html",
                "module_json":   mod_json_by_id.get(module_id, {}),
                "created_at":    now,
            }
            insert_one("course_modules", module_doc)

        print(f"✅ Course saved to MongoDB: {course_id}  ({len(module_htmls)} modules)")
        return course_id

    # ────────────────────────────────────────────────────────────────────────

    def update_html(
        self,
        course_id: Any,
        html_index: str,
        module_htmls: list[str],          # ordered list matching module_index sort
        html_exam: str,
    ) -> bool:
        """
        Re-write HTML stored in DB after db_course_id is baked into links.

        module_htmls is a list ordered by module_index (1-based).
        """
        course_id = self._id(course_id)
        now = datetime.now(timezone.utc).isoformat()
        try:
            update_one(
                "courses",
                {"id": course_id},
                {"$set": {
                    "html_index": html_index,
                    "html_exam":  html_exam,
                    "updated_at": now,
                }},
            )
            # Fetch modules ordered by index
            modules = find_many(
                "course_modules",
                {"course_id": course_id},
                sort=[("module_index", ASCENDING)],
            )
            for i, mod in enumerate(modules):
                if i < len(module_htmls):
                    update_one(
                        "course_modules",
                        {"_id": mod["_id"]},
                        {"$set": {"html_content": module_htmls[i]}},
                    )
            print(f"✅ update_html: course {course_id} re-rendered ({len(module_htmls)} modules)")
            return True
        except Exception as e:
            print(f"❌ update_html failed: {e}")
            return False

    # ────────────────────────────────────────────────────────────────────────

    def get_course(self, course_id: Any) -> Optional[dict]:
        """Return course document by ID (without large HTML blobs)."""
        course_id = self._id(course_id)
        try:
            doc = find_one("courses", {"id": course_id})
            return doc
        except Exception as e:
            print(f"❌ get_course error: {e}")
            return None

    def list_courses(
        self,
        department: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List courses, stripping large HTML fields for brevity."""
        try:
            query: dict[str, Any] = {"archived": False}
            if department:
                query["department"] = department

            docs = find_many(
                "courses", query,
                limit=limit, skip=offset,
                sort=[("created_at", DESCENDING)],
            )
            # Strip heavy fields from list view
            for d in docs:
                d.pop("html_index",  None)
                d.pop("html_exam",   None)
                d.pop("course_json", None)
            return docs
        except Exception as e:
            print(f"❌ list_courses error: {e}")
            return []

    def search_courses(self, query: str, department: str = "") -> list[dict]:
        """Search by title/description (text index if available, else regex)."""
        try:
            search_filter: dict[str, Any] = {
                "$text": {"$search": query},
                "archived": False,
            }
            if department:
                search_filter["department"] = department
            docs = find_many("courses", search_filter)
            for d in docs:
                d.pop("html_index",  None)
                d.pop("html_exam",   None)
                d.pop("course_json", None)
            return docs
        except Exception:
            # Fallback: regex search (no text index required)
            pattern: dict[str, Any] = {"$regex": query, "$options": "i"}
            fallback: dict[str, Any] = {
                "$or": [{"title": pattern}, {"description": pattern}],
                "archived": False,
            }
            if department:
                fallback["department"] = department
            docs = find_many("courses", fallback)
            for d in docs:
                d.pop("html_index",  None)
                d.pop("html_exam",   None)
                d.pop("course_json", None)
            return docs

    def delete_course(self, course_id: Any) -> bool:
        """Hard-archive a course (soft delete)."""
        course_id = self._id(course_id)
        try:
            return bool(update_one("courses", {"id": course_id}, {"$set": {"archived": True}}))
        except Exception as e:
            print(f"❌ delete_course error: {e}")
            return False

    def archive_course(self, course_id: Any) -> bool:
        """Alias for delete_course (soft delete)."""
        return self.delete_course(course_id)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE OPERATIONS
    # ════════════════════════════════════════════════════════════════════════

    def get_modules(self, course_id: Any) -> list[dict]:
        """Return all module documents for a course (html_content stripped)."""
        course_id = self._id(course_id)
        try:
            docs = find_many(
                "course_modules",
                {"course_id": course_id},
                sort=[("module_index", ASCENDING)],
            )
            for d in docs:
                d.pop("html_content", None)
                d.pop("module_json",  None)
            return docs
        except Exception as e:
            print(f"❌ get_modules error: {e}")
            return []

    def get_module_by_index(self, course_id: Any, module_index: int) -> Optional[dict]:
        """Return a single module document by 1-based index."""
        course_id = self._id(course_id)
        try:
            return find_one("course_modules", {
                "course_id":    course_id,
                "module_index": module_index,
            })
        except Exception as e:
            print(f"❌ get_module_by_index error: {e}")
            return None

    # ════════════════════════════════════════════════════════════════════════
    # HTML DELIVERY
    # ════════════════════════════════════════════════════════════════════════

    def get_html_for_download(
        self, course_id: Any, key: str
    ) -> tuple[Optional[str], str]:
        """
        Fetch HTML string + suggested filename from DB.

        key values:
            "index"       → course dashboard page
            "exam"        → final exam page
            "module:{n}"  → 1-based module index, e.g. "module:3"

        Returns (html_str, filename). html_str is None if not found.
        """
        course_id = self._id(course_id)
        try:
            if key == "index":
                doc = find_one("courses", {"id": course_id})
                if not doc:
                    return None, "index.html"
                fn = doc.get("index_filename") or \
                     f"{_slugify(doc.get('department', 'course'))}-index.html"
                return doc.get("html_index"), fn

            if key == "exam":
                doc = find_one("courses", {"id": course_id})
                if not doc:
                    return None, "final-exam.html"
                fn = doc.get("exam_filename") or \
                     f"{_slugify(doc.get('department', 'course'))}-final-exam.html"
                return doc.get("html_exam"), fn

            if key.startswith("module:"):
                try:
                    mod_index = int(key.split(":", 1)[1])
                except (IndexError, ValueError):
                    return None, "module.html"
                mod = find_one("course_modules", {
                    "course_id":    course_id,
                    "module_index": mod_index,
                })
                if not mod:
                    return None, f"module-{mod_index:02d}.html"
                fn = mod.get("html_filename") or f"module-{mod_index:02d}.html"
                return mod.get("html_content"), fn

        except Exception as e:
            print(f"❌ get_html_for_download error: {e}")
            return None, "error.html"

        return None, "unknown.html"

    # ════════════════════════════════════════════════════════════════════════
    # DISK WRITE  (on-demand only)
    # ════════════════════════════════════════════════════════════════════════

    def write_to_disk(self, course_id: Any, out_dir: Path) -> dict[str, Path]:
        """
        Write all course HTML to `out_dir`.
        Called ONLY when explicitly requested (download-all-files endpoint).
        Returns {key: Path} for each file written.
        """
        course_id = self._id(course_id)
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

        modules = find_many(
            "course_modules",
            {"course_id": course_id},
            sort=[("module_index", ASCENDING)],
        )
        for mod in modules:
            idx = mod["module_index"]
            html, fn = self.get_html_for_download(course_id, f"module:{idx}")
            if html:
                p = out_dir / fn
                p.write_text(html, encoding="utf-8")
                written[f"module_{idx}"] = p
                print(f"  [DB→Disk] mod {idx:02d} → {p.name}")

        print(f"  [DB→Disk] {len(written)} file(s) written to {out_dir}")
        return written

    # ════════════════════════════════════════════════════════════════════════
    # PROGRESS & RESULTS
    # ════════════════════════════════════════════════════════════════════════

    def record_progress(
        self,
        learner_id: str,
        course_id: Any,
        module_id: str,
        module_title: str,
        department: str,
        score: float,
        passed: bool,
        source: str = "web",
    ) -> bool:
        course_id = self._id(course_id)
        try:
            insert_one("course_progress", {
                "learner_id":    learner_id,
                "course_id":     course_id,
                "module_id":     module_id,
                "module_title":  module_title,
                "department":    department,
                "score":         score,
                "passed":        passed,
                "source":        source,
                "timestamp":     datetime.now(timezone.utc).isoformat(),
            })
            print(f"✅ Progress recorded: {learner_id} / {module_id} — {score}%")
            return True
        except Exception as e:
            print(f"❌ record_progress error: {e}")
            return False

    def get_learner_progress(
        self,
        learner_id: str,
        course_id: Any = "",
    ) -> list[dict]:
        """Return all progress records for a learner, optionally filtered by course."""
        try:
            query: dict[str, Any] = {"learner_id": learner_id}
            if course_id:
                query["course_id"] = self._id(course_id)
            return find_many(
                "course_progress", query,
                sort=[("timestamp", DESCENDING)],
            )
        except Exception as e:
            print(f"❌ get_learner_progress error: {e}")
            return []

    def get_course_stats(self, course_id: Any) -> dict:
        """Return aggregated statistics for a course."""
        course_id = self._id(course_id)
        try:
            records = find_many("course_progress", {"course_id": course_id})
            if not records:
                return {
                    "total_attempts":  0,
                    "avg_score":       0,
                    "pass_rate":       0,
                    "unique_learners": 0,
                }
            learners  = {r["learner_id"] for r in records}
            passed    = sum(1 for r in records if r["passed"])
            avg_score = sum(r["score"] for r in records) / len(records)
            return {
                "total_attempts":  len(records),
                "avg_score":       round(avg_score, 1),
                "pass_rate":       int(passed / len(records) * 100),
                "unique_learners": len(learners),
            }
        except Exception as e:
            print(f"❌ get_course_stats error: {e}")
            return {}

    # ════════════════════════════════════════════════════════════════════════
    # CERTIFICATES
    # ════════════════════════════════════════════════════════════════════════

    def issue_certificate(
        self,
        learner_id: str,
        course_id: Any,
        score: float,
    ) -> dict:
        course_id = self._id(course_id)
        try:
            cert: dict[str, Any] = {
                "learner_id":     learner_id,
                "course_id":      course_id,
                "score":          score,
                "issued_at":      datetime.now(timezone.utc).isoformat(),
                "certificate_id": str(uuid.uuid4()),
            }
            insert_one("course_certificates", cert)
            print(f"🏅 Certificate issued: {learner_id} / {course_id}")
            return cert
        except Exception as e:
            print(f"❌ issue_certificate error: {e}")
            return {}

    def get_certificate(self, learner_id: str, course_id: Any) -> Optional[dict]:
        course_id = self._id(course_id)
        try:
            return find_one("course_certificates", {
                "learner_id": learner_id,
                "course_id":  course_id,
            })
        except Exception as e:
            print(f"❌ get_certificate error: {e}")
            return None

    def list_certificates(self, learner_id: str) -> list[dict]:
        try:
            return find_many("course_certificates", {"learner_id": learner_id})
        except Exception as e:
            print(f"❌ list_certificates error: {e}")
            return []

    # ════════════════════════════════════════════════════════════════════════
    # TAGS
    # ════════════════════════════════════════════════════════════════════════

    def add_tags(self, course_id: Any, tags: list[str]) -> bool:
        course_id = self._id(course_id)
        try:
            for tag in tags:
                insert_one("course_tags", {"course_id": course_id, "tag": tag})
            return True
        except Exception as e:
            print(f"❌ add_tags error: {e}")
            return False

    def list_courses_by_tag(self, tag: str) -> list[dict]:
        try:
            tag_docs   = find_many("course_tags", {"tag": tag})
            course_ids = [d["course_id"] for d in tag_docs]
            courses    = []
            for cid in course_ids:
                doc = find_one("courses", {"id": cid})
                if doc:
                    doc.pop("html_index",  None)
                    doc.pop("html_exam",   None)
                    doc.pop("course_json", None)
                    courses.append(doc)
            return courses
        except Exception as e:
            print(f"❌ list_courses_by_tag error: {e}")
            return []

    # ════════════════════════════════════════════════════════════════════════
    # ADMIN / STATS
    # ════════════════════════════════════════════════════════════════════════

    def get_db_stats(self) -> dict:
        """Return row counts across all course collections."""
        try:
            return {
                "total_courses":         count_documents("courses",             {"archived": False}),
                "total_modules":         count_documents("course_modules",      {}),
                "total_learner_records": count_documents("course_progress",     {}),
                "total_certificates":    count_documents("course_certificates", {}),
                "tags":                  count_documents("course_tags",         {}),
            }
        except Exception as e:
            print(f"❌ get_db_stats error: {e}")
            return {}