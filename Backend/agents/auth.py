"""Authentication helpers for the calendar backend."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CALENDAR_DB_PATH", BASE_DIR / "calendar.db"))

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

security = HTTPBearer(auto_error=False)


def get_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""
    resolved_path = Path(db_path or DB_PATH)
    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    return conn


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


def authenticate_user(
    user_id: str,
    user_name: str,
    password: str,
    department: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Validate employee credentials against the local employee table."""
    uid = str(user_id).strip()
    name = str(user_name).strip().lower()
    pwd = str(password).strip()
    dept = str(department).strip()

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        query = (
            "SELECT * FROM employees "
            "WHERE gsheet_uid=? AND LOWER(name)=? AND gsheet_password=?"
        )
        params: list[Any] = [uid, name, pwd]
        if dept:
            query += " AND department=?"
            params.append(dept)

        cursor.execute(query, params)
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    employee = dict(row)
    employee.pop("gsheet_password", None)
    employee["role"] = normalize_role(employee.get("role"))
    return employee


def authenticate_and_issue_token(
    user_id: str,
    user_name: str,
    password: str,
    department: str = "",
    db_path: Path | None = None,
) -> dict[str, Any]:
    employee = authenticate_user(user_id, user_name, password, department, db_path)
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
