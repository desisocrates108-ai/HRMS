"""Designation Master — centralised CRUD replacing hardcoded JOB_ROLES.
Visible everywhere a role/designation dropdown is needed (Jobs, Employees, etc.).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, require_role, log_audit
import uuid
from datetime import datetime, timezone

router = APIRouter()


class DesignationCreate(BaseModel):
    name: str
    department: Optional[str] = None
    description: Optional[str] = None


class DesignationUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


def _norm(name: str) -> str:
    return (name or "").strip()


@router.get("")
async def list_designations(
    active_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if active_only:
        query["active"] = True
    items = await db.designations.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return items


@router.get("/{designation_id}")
async def get_designation(designation_id: str, current_user: dict = Depends(get_current_user)):
    d = await db.designations.find_one({"id": designation_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Designation not found")
    return d


@router.post("")
async def create_designation(
    data: DesignationCreate,
    current_user: dict = Depends(require_role("super")),
):
    name = _norm(data.name)
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = await db.designations.find_one({"name_lower": name.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Designation with this name already exists")
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "name_lower": name.lower(),
        "department": _norm(data.department or "") or None,
        "description": _norm(data.description or "") or None,
        "active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.designations.insert_one(item)
    item.pop("_id", None)
    await log_audit(current_user["id"], current_user["name"], "create", "designation", item["id"], {"name": name})
    return item


@router.put("/{designation_id}")
async def update_designation(
    designation_id: str,
    data: DesignationUpdate,
    current_user: dict = Depends(require_role("super")),
):
    payload = data.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if "name" in payload:
        new_name = _norm(payload["name"])
        if not new_name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        clash = await db.designations.find_one({"name_lower": new_name.lower(), "id": {"$ne": designation_id}})
        if clash:
            raise HTTPException(status_code=400, detail="Another designation with this name exists")
        payload["name"] = new_name
        payload["name_lower"] = new_name.lower()
    if "department" in payload:
        payload["department"] = _norm(payload.get("department") or "") or None
    if "description" in payload:
        payload["description"] = _norm(payload.get("description") or "") or None
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.designations.update_one({"id": designation_id}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Designation not found")
    await log_audit(current_user["id"], current_user["name"], "update", "designation", designation_id, payload)
    return await db.designations.find_one({"id": designation_id}, {"_id": 0})


@router.delete("/{designation_id}")
async def delete_designation(
    designation_id: str,
    current_user: dict = Depends(require_role("super")),
):
    d = await db.designations.find_one({"id": designation_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Designation not found")
    # Block deletion if referenced by any job or employee
    name = d["name"]
    job_count = await db.jobs.count_documents({"role": name})
    emp_count = await db.employees.count_documents({"role": name})
    if job_count or emp_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — used by {job_count} job(s) and {emp_count} employee(s). Deactivate instead.",
        )
    await db.designations.delete_one({"id": designation_id})
    await log_audit(current_user["id"], current_user["name"], "delete", "designation", designation_id, {"name": name})
    return {"success": True}


# Bulk seed common designations on first run (idempotent)
DEFAULT_DESIGNATIONS = [
    "Technician", "Service Advisor", "Franchise Manager", "HR Executive",
    "Marketing Coordinator", "Graphic Designer", "Franchise Executive",
    "Operations Manager", "Sales Manager", "Accounts Manager", "Marketing Manager",
    "Sr HR", "Jr HR",
]


async def seed_default_designations():
    existing = await db.designations.count_documents({})
    if existing > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = [
        {
            "id": str(uuid.uuid4()),
            "name": n,
            "name_lower": n.lower(),
            "department": None,
            "description": None,
            "active": True,
            "created_by": "system",
            "created_at": now,
            "updated_at": now,
        }
        for n in DEFAULT_DESIGNATIONS
    ]
    if docs:
        await db.designations.insert_many(docs)
