"""Authentication helpers for the calendar backend."""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from mongo_db import safe_print

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

security = HTTPBearer(auto_error=False)


# Removed SQLite get_db...


def normalize_role(raw_role: Any) -> str:
    role = str(raw_role or "Employee").strip().lower()
    if role == "admin":
        return "Admin"
    if role == "manager":
        return "Manager"
    return "Employee"


def create_access_token(data: dict[str, Any]) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


import mongo_db

# ... (rest of imports)

def authenticate_user(
    user_id: str,
    user_name: str,
    password: str,
    department: str = "",
) -> dict[str, Any]:
    """Validate employee credentials against the MongoDB employees collection."""
    uid = str(user_id).strip()
    pwd = str(password).strip()
    dept = str(department).strip()

    # Enhanced Prod Diagnostic: Check total employee count in DB
    try:
        emp_count = mongo_db.count_documents("employees")
        print(f"[Auth] Diagnostic: Total employees in DB collection: {emp_count}")
        print(f"[Auth] Attempting login: ID='{uid}' (dept: '{dept}')")
    except Exception as e:
        print(f"[Auth] Diagnostic Error: Could not count employees: {e}")

    safe_uid = re.escape(uid)
    user = mongo_db.find_one(
        "employees",
        {
            "$or": [
                {"gsheet_uid": {"$regex": f"^{safe_uid}$", "$options": "i"}},
                {"id": {"$regex": f"^{safe_uid}$", "$options": "i"}},
                {"userId": {"$regex": f"^{safe_uid}$", "$options": "i"}},
            ]
        },
    )

    if not user:
        safe_print(f"[Auth] FAILED: User not found (user_id='{uid}')")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Check password (support both 'password' and legacy 'gsheet_password')
    candidate_passwords: list[str] = []
    for key in ("password", "gsheet_password"):
        raw = user.get(key)
        if raw is None:
            continue
        val = str(raw).strip()
        if val:
            candidate_passwords.append(val)

    if not candidate_passwords or pwd not in candidate_passwords:
        present = ",".join([k for k in ("password", "gsheet_password") if str(user.get(k) or "").strip()])
        safe_print(
            f"[Auth] FAILED: Password mismatch (user_id='{uid}', present_password_fields='{present or 'none'}')"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. Check department/role scope (if provided)
    if dept:
        # If the provided "department" is actually one of our role names,
        # check role instead of department (frontend uses 'Manager'/'Admin' scope).
        user_role = normalize_role(user.get("role"))
        if dept.lower() in {"manager", "admin"}:
            if user_role.lower() != dept.lower():
                safe_print(
                    f"[Auth] FAILED: Role mismatch (user_id='{uid}', expected_role='{dept}', actual_role='{user_role}')"
                )
                raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            user_dept = str(user.get("department", "") or "").strip()
            if user_dept.lower() != dept.lower():
                safe_print(
                    f"[Auth] FAILED: Department mismatch (user_id='{uid}', expected_department='{dept}', actual_department='{user_dept}')"
                )
                raise HTTPException(status_code=401, detail="Invalid credentials")

    safe_print(f"[Auth] SUCCESS: User '{uid}' authenticated as role '{user.get('role')}'")

    canonical_id = str(user.get("id") or user.get("gsheet_uid") or user.get("userId") or uid).strip()
    canonical_name = str(user.get("name") or user.get("userName") or user_name or "").strip()
    canonical_department = str(user.get("department") or "").strip()
    if not canonical_department:
        canonical_department = "Admin" if normalize_role(user.get("role")) == "Admin" else "General"

    # Return a stable shape for JWT + frontend
    result: dict[str, Any] = {
        "id": canonical_id,
        "userId": canonical_id,
        "gsheet_uid": str(user.get("gsheet_uid") or canonical_id).strip(),
        "userName": canonical_name,
        "name": canonical_name,
        "department": canonical_department,
        "role": normalize_role(user.get("role")),
        "email": str(user.get("email") or "").strip(),
    }

    if user.get("avatar_color"):
        result["avatar_color"] = user.get("avatar_color")

    return result


def authenticate_and_issue_token(
    user_id: str,
    user_name: str,
    password: str,
    department: str = "",
) -> dict[str, Any]:
    employee = authenticate_user(user_id, user_name, password, department)
    token = create_access_token(
        {
            "sub": str(employee["id"]),
            "name": employee.get("name", ""),
            "role": employee.get("role", "Employee"),
            "department": employee.get("department", ""),
            "email": employee.get("email", ""),
        }
    )
    return {"token": token, "user": employee}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """FastAPI dependency that returns the decoded JWT payload."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(credentials.credentials)


def require_role(*roles: str):
    allowed_roles = {normalize_role(role) for role in roles}

    def _dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if normalize_role(user.get("role")) not in allowed_roles:
            expected = ", ".join(sorted(allowed_roles))
            raise HTTPException(status_code=403, detail=f"Role required: {expected}")
        return user

    return _dependency
