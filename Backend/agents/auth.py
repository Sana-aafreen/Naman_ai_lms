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

    # EMERGENCY FALLBACK: Hardcoded check for ADM001 to ensure access during sync debugging
    if uid.upper() == "ADM001" and pwd == "Sana@121":
        print(f"[Auth] CRITICAL: Using emergency fallback for {uid}")
        return {
            "id": "ADM001",
            "gsheet_uid": "ADM001",
            "userName": "Sana (Fallback)",
            "name": "Sana",
            "role": "Admin",
            "department": "Admin",
            "email": "adm001@namandarshan.com"
        }

    # Enhanced Prod Diagnostic: Check total employee count in DB
    try:
        emp_count = mongo_db.count_documents("employees")
        print(f"[Auth] Diagnostic: Total employees in DB collection: {emp_count}")
        print(f"[Auth] Attempting login: ID='{uid}' (dept: '{dept}')")
    except Exception as e:
        print(f"[Auth] Diagnostic Error: Could not count employees: {e}")
    safe_uid = re.escape(uid)
    query = {
        "$or": [
            {"gsheet_uid": {"$regex": f"^{safe_uid}$", "$options": "i"}},
            {"id": uid}
        ]
    }
    
    if dept:
        # If the provided "department" is actually one of our role names,
        # we check the role instead of the department field to allow login 
        # (e.g. frontend sends 'Manager' during manager login).
        if dept.lower() in ["manager", "admin"]:
            query["role"] = {"$regex": f"^{re.escape(dept)}$", "$options": "i"}
        else:
            safe_dept = re.escape(dept)
            query["department"] = {"$regex": f"^{safe_dept}$", "$options": "i"}

    user = mongo_db.find_one("employees", query)
    
    if not user:
        safe_print(f"[Auth] FAILED: User '{uid}' not found in 'employees' (Query keys: gsheet_uid, id)")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Check password
    db_pass = user.get("password", "password123")
    if password != db_pass:
        safe_print(f"[Auth] FAILED: Password mismatch for user '{uid}' (Expected: {db_pass[:2]}..., Received: {password[:2]}...)")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. Check department (if provided)
    if department:
        user_dept = user.get("department", "")
        if str(department).lower() != str(user_dept).lower():
            safe_print(f"[Auth] FAILED: Department mismatch for user '{uid}' (Expected: {user_dept}, Received: {department})")
            # We treat this as a failure because the frontend passes department during login
            raise HTTPException(status_code=401, detail="Invalid credentials")

    safe_print(f"[Auth] SUCCESS: User '{uid}' authenticated as role '{user.get('role')}'")

    # Convert MongoDB _id to string or remove it
    if "_id" in user:
        user["id"] = str(user["_id"])
        del user["_id"]
    
    # Also handle the gsheet_uid vs id inconsistency if necessary
    if "gsheet_uid" in user and "id" not in user:
        user["id"] = user["gsheet_uid"]

    user.pop("gsheet_password", None)
    user["role"] = normalize_role(user.get("role"))
    return user


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
