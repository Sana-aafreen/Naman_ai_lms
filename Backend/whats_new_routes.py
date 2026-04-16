from fastapi import APIRouter, Depends
from datetime import datetime

router = APIRouter()

# Temporary DB
whats_new_db = []

# Dummy auth (replace later)
def get_current_user():
    return {
        "id": "1",
        "name": "Admin",
        "role": "Admin",
        "department": "IT"
    }

# CREATE
@router.post("/api/whats-new")
def create_whats_new(data: dict, current_user=Depends(get_current_user)):
    new_update = {
        "id": len(whats_new_db) + 1,
        "author_id": data.get("author_id"),
        "author_name": data.get("author_name"),
        "author_role": data.get("author_role"),
        "department": data.get("department"),
        "category": data.get("category"),
        "title": data.get("title"),
        "body": data.get("body"),

        # [OK] YOUR REQUIRED CHANGE (already applied)
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "approved_at": None
    }

    whats_new_db.append(new_update)
    return {"message": "Submitted for approval"}


# GET
@router.get("/api/whats-new")
def get_whats_new(include_pending: bool = False):
    if include_pending:
        return whats_new_db
    return [u for u in whats_new_db if u["status"] == "approved"]


# APPROVE
@router.post("/api/whats-new/{id}/approve")
def approve_update(id: int):
    for u in whats_new_db:
        if u["id"] == id:
            u["status"] = "approved"
            u["approved_at"] = datetime.utcnow().isoformat()
            return {"message": "Approved"}
    return {"error": "Not found"}


# REJECT
@router.post("/api/whats-new/{id}/reject")
def reject_update(id: int):
    global whats_new_db
    whats_new_db = [u for u in whats_new_db if u["id"] != id]
    return {"message": "Rejected"}