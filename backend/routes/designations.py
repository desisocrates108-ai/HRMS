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

OFFICE_TYPES = ["head_office", "franchise"]


class DesignationCreate(BaseModel):
    name: str
    office_type: str  # 'head_office' or 'franchise'
    department: Optional[str] = None
    description: Optional[str] = None


class DesignationUpdate(BaseModel):
    name: Optional[str] = None
    office_type: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


def _norm(name: str) -> str:
    return (name or "").strip()


def _validate_office_type(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in OFFICE_TYPES:
        raise HTTPException(status_code=400, detail=f"office_type must be one of {OFFICE_TYPES}")
    return v


@router.get("")
async def list_designations(
    active_only: bool = False,
    office_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if active_only:
        query["active"] = True
    if office_type:
        query["office_type"] = _validate_office_type(office_type)
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
    office_type = _validate_office_type(data.office_type)
    existing = await db.designations.find_one({"name_lower": name.lower(), "office_type": office_type})
    if existing:
        raise HTTPException(status_code=400, detail="Designation with this name already exists for this office type")
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "name_lower": name.lower(),
        "office_type": office_type,
        "department": _norm(data.department or "") or None,
        "description": _norm(data.description or "") or None,
        "active": True,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.designations.insert_one(item)
    item.pop("_id", None)
    await log_audit(current_user["id"], current_user["name"], "create", "designation", item["id"], {"name": name, "office_type": office_type})
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
    if "office_type" in payload:
        payload["office_type"] = _validate_office_type(payload["office_type"])
    if "name" in payload:
        new_name = _norm(payload["name"])
        if not new_name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        ot = payload.get("office_type")
        if not ot:
            existing = await db.designations.find_one({"id": designation_id}, {"_id": 0, "office_type": 1})
            ot = (existing or {}).get("office_type")
        clash_q = {"name_lower": new_name.lower(), "id": {"$ne": designation_id}}
        if ot:
            clash_q["office_type"] = ot
        clash = await db.designations.find_one(clash_q)
        if clash:
            raise HTTPException(status_code=400, detail="Another designation with this name exists for this office type")
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
# Each entry: (name, office_type)
DEFAULT_DESIGNATIONS = [
    ("Technician", "franchise"),
    ("Service Advisor", "franchise"),
    ("Branch Manager", "franchise"),
    ("Franchise Manager", "franchise"),
    ("Franchise Executive", "franchise"),
    ("Sales Executive", "franchise"),
    ("HR Executive", "head_office"),
    ("Marketing Coordinator", "head_office"),
    ("Graphic Designer", "head_office"),
    ("Operations Manager", "head_office"),
    ("Sales Manager", "head_office"),
    ("Accounts Manager", "head_office"),
    ("Marketing Manager", "head_office"),
    ("Sr HR", "head_office"),
    ("Jr HR", "head_office"),
]


# Heuristic mapping for legacy rows without office_type
_FRANCHISE_HINTS = {"technician", "service advisor", "branch manager", "franchise manager", "franchise executive", "sales executive"}


async def seed_default_designations():
    """Insert any missing default designations and backfill office_type on legacy rows."""
    # Fix legacy single-field unique index (name_lower_1) so duplicate names are
    # allowed across different office_types.
    try:
        await db.designations.drop_index("name_lower_1")
    except Exception:
        pass
    try:
        await db.designations.create_index(
            [("name_lower", 1), ("office_type", 1)],
            unique=True,
            name="name_lower_office_type_unique",
        )
    except Exception:
        pass

    # Backfill office_type for legacy docs
    legacy_count = await db.designations.count_documents({"office_type": {"$exists": False}})
    if legacy_count:
        async for doc in db.designations.find({"office_type": {"$exists": False}}, {"_id": 0, "id": 1, "name": 1}):
            nm = (doc.get("name") or "").lower()
            ot = "franchise" if nm in _FRANCHISE_HINTS else "head_office"
            await db.designations.update_one({"id": doc["id"]}, {"$set": {"office_type": ot}})

    # Insert any default designations that don't exist yet (idempotent per (name, office_type))
    now = datetime.now(timezone.utc).isoformat()
    for name, ot in DEFAULT_DESIGNATIONS:
        exists = await db.designations.find_one({"name_lower": name.lower(), "office_type": ot})
        if exists:
            continue
        await db.designations.insert_one({
            "id": str(uuid.uuid4()),
            "name": name,
            "name_lower": name.lower(),
            "office_type": ot,
            "department": None,
            "description": None,
            "active": True,
            "created_by": "system",
            "created_at": now,
            "updated_at": now,
        })
