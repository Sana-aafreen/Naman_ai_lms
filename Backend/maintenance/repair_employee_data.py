from __future__ import annotations

import argparse
from typing import Any

import mongo_db
from agents.auth import normalize_role


def _canonical_department(doc: dict[str, Any]) -> str:
    dept = str(doc.get("department") or "").strip()
    if dept:
        return dept
    role = normalize_role(doc.get("role"))
    return "Admin" if role == "Admin" else "General"


def _canonical_employee_id(doc: dict[str, Any]) -> str:
    for key in ("gsheet_uid", "id", "userId"):
        val = str(doc.get(key) or "").strip()
        if val:
            return val
    return ""


def repair_employees(*, dry_run: bool) -> dict[str, int]:
    db = mongo_db.get_db()
    col = db["employees"]

    scanned = 0
    updated = 0
    password_backfilled = 0
    id_backfilled = 0
    dept_backfilled = 0
    role_normalized = 0

    for doc in col.find({}):
        scanned += 1
        changes: dict[str, Any] = {}

        canonical_id = _canonical_employee_id(doc)
        if canonical_id:
            if str(doc.get("id") or "").strip() != canonical_id:
                changes["id"] = canonical_id
                id_backfilled += 1
            if str(doc.get("userId") or "").strip() != canonical_id:
                changes["userId"] = canonical_id
            if not str(doc.get("gsheet_uid") or "").strip():
                changes["gsheet_uid"] = canonical_id

        pwd = str(doc.get("password") or "").strip()
        gpwd = str(doc.get("gsheet_password") or "").strip()
        if not pwd and gpwd:
            changes["password"] = gpwd
            password_backfilled += 1
        if not gpwd and pwd:
            changes["gsheet_password"] = pwd

        dept = _canonical_department(doc)
        if str(doc.get("department") or "").strip() != dept:
            changes["department"] = dept
            dept_backfilled += 1

        role = normalize_role(doc.get("role"))
        if str(doc.get("role") or "").strip() != role:
            changes["role"] = role
            role_normalized += 1

        if changes:
            changes["updated_at"] = mongo_db.now_iso()
            updated += 1
            if not dry_run:
                col.update_one({"_id": doc["_id"]}, {"$set": changes})

    return {
        "scanned": scanned,
        "updated": updated,
        "password_backfilled": password_backfilled,
        "id_backfilled": id_backfilled,
        "department_backfilled": dept_backfilled,
        "role_normalized": role_normalized,
        "dry_run": int(dry_run),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair employee documents in MongoDB (one-time backfill).")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report changes without writing.")
    args = parser.parse_args()

    stats = repair_employees(dry_run=bool(args.dry_run))
    mongo_db.safe_print("[Repair] Done:", stats)


if __name__ == "__main__":
    main()
