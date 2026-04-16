"""Authentication helpers for the calendar backend."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

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
    name = str(user_name).strip()
    pwd = str(password).strip()
    dept = str(department).strip()

    print(f"[Auth] Attempting login: ID='{uid}' (department: '{dept}')")

    query = {
        "gsheet_uid": {"$regex": f"^{uid}$", "$options": "i"},
        "gsheet_password": pwd
    }
    # Note: department filtering is regex-based already (case-insensitive)
    if dept:
        query["department"] = {"$regex": f"^{dept}$", "$options": "i"}

    user = mongo_db.find_one("employees", query)
    
    if not user:
        # Diagnostic: check if user exists at all (ignoring password)
        exists = mongo_db.find_one("employees", {"gsheet_uid": {"$regex": f"^{uid}$", "$options": "i"}})
        if exists:
            print(f"[Auth] FAILED: User '{uid}' found, but password or department mismatched.")
        else:
            print(f"[Auth] FAILED: User '{uid}' not found in 'employees' collection.")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    print(f"[Auth] SUCCESS: User '{uid}' authenticated as role '{user.get('role')}'")

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
