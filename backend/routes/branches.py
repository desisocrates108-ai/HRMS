from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit
import uuid
from datetime import datetime, timezone

router = APIRouter()

# Permission matrix for branch operations
EDIT_ROLES = {
    "CEO", "HR",
    "Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager",
    "Sr HR", "Jr HR",
}
DELETE_ROLES = {"CEO", "HR", "Sr HR", "Jr HR"}


def _require_edit(user: dict):
    if user.get("role") not in EDIT_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to create/edit branches")


def _require_delete(user: dict):
    if user.get("role") not in DELETE_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to delete branches")


class BranchCreate(BaseModel):
    name: str
    city: str
    area: str
    tentative_opening_date: Optional[str] = None
    actual_opening_date: Optional[str] = None
    franchise_owner_id: Optional[str] = None
    status: Optional[str] = None  # "upcoming" | "active" — auto-derived from actual_opening_date if None


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    tentative_opening_date: Optional[str] = None
    actual_opening_date: Optional[str] = None
    franchise_owner_id: Optional[str] = None
    status: Optional[str] = None


def _derive_status(branch: dict) -> str:
    """Derive status. Auto-promotes upcoming→active when tentative_opening_date is today or past."""
    actual = branch.get("actual_opening_date")
    if actual:
        return "active"
    tentative = branch.get("tentative_opening_date")
    if tentative:
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            if tentative <= today:
                return "active"
        except Exception:
            pass
    # explicit override last (only honor 'active' override; 'upcoming' is default)
    if branch.get("status") == "active":
        return "active"
    return "upcoming"


async def _auto_promote_branches():
    """Promote upcoming branches whose tentative_opening_date is today or earlier.
    Persist the status change + set actual_opening_date=tentative_opening_date when passing."""
    today = datetime.now(timezone.utc).date().isoformat()
    # Find upcoming (or unset) branches with past tentative dates
    cursor = db.branches.find({
        "$or": [{"status": "upcoming"}, {"status": {"$exists": False}}],
        "tentative_opening_date": {"$lte": today, "$ne": None},
        "actual_opening_date": {"$in": [None, ""]},
    })
    async for b in cursor:
        await db.branches.update_one(
            {"id": b["id"]},
            {"$set": {"status": "active", "actual_opening_date": b["tentative_opening_date"], "auto_activated_at": datetime.now(timezone.utc).isoformat()}},
        )


@router.get("")
async def list_branches(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    await _auto_promote_branches()
    branches = await db.branches.find({}, {"_id": 0}).to_list(1000)
    for b in branches:
        b["status"] = _derive_status(b)
        # Strip legacy fields from response
        b.pop("latitude", None)
        b.pop("longitude", None)
    if status:
        branches = [b for b in branches if b["status"] == status]
    return branches


@router.get("/recruitment-overview")
async def recruitment_overview(current_user: dict = Depends(get_current_user)):
    """Per-branch hiring snapshot: open jobs, leads, hires — for upcoming + active."""
    branches = await db.branches.find({}, {"_id": 0}).to_list(1000)
    for b in branches:
        b["status"] = _derive_status(b)
        b.pop("latitude", None)
        b.pop("longitude", None)
    branch_ids = [b["id"] for b in branches]

    jobs = await db.jobs.find({"branch_id": {"$in": branch_ids}}, {"_id": 0}).to_list(2000) if branch_ids else []
    jobs_by_branch = {}
    for j in jobs:
        jobs_by_branch.setdefault(j["branch_id"], []).append(j)

    job_ids = [j["id"] for j in jobs]
    leads = await db.leads.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(5000) if job_ids else []
    leads_by_job = {}
    for lead in leads:
        leads_by_job.setdefault(lead["job_id"], []).append(lead)

    employees = await db.employees.find({"branch_id": {"$in": branch_ids}, "status": {"$ne": "left"}}, {"_id": 0}).to_list(5000) if branch_ids else []
    emp_by_branch = {}
    for e in employees:
        emp_by_branch.setdefault(e["branch_id"], []).append(e)

    rows = []
    for b in branches:
        bjobs = jobs_by_branch.get(b["id"], [])
        bleads = []
        hired_from_leads = 0
        for j in bjobs:
            jl = leads_by_job.get(j["id"], [])
            bleads.extend(jl)
            hired_from_leads += sum(1 for ld in jl if ld.get("current_stage") == "joined")
        open_jobs = sum(1 for j in bjobs if j.get("status") == "open")
        total_hires = len(emp_by_branch.get(b["id"], []))
        rows.append({
            **b,
            "open_jobs": open_jobs,
            "total_jobs": len(bjobs),
            "active_leads": len([ld for ld in bleads if ld.get("current_stage") not in ("dead", "joined")]),
            "total_leads": len(bleads),
            "hired": total_hires,
            "hired_from_leads": hired_from_leads,
        })
    rows.sort(key=lambda r: (r["status"] != "upcoming", r.get("tentative_opening_date") or ""))
    return {
        "upcoming": [r for r in rows if r["status"] == "upcoming"],
        "active": [r for r in rows if r["status"] == "active"],
        "total_upcoming": sum(1 for r in rows if r["status"] == "upcoming"),
        "total_active": sum(1 for r in rows if r["status"] == "active"),
    }


@router.get("/{branch_id}")
async def get_branch(branch_id: str, current_user: dict = Depends(get_current_user)):
    branch = await db.branches.find_one({"id": branch_id}, {"_id": 0})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    branch["status"] = _derive_status(branch)
    branch.pop("latitude", None)
    branch.pop("longitude", None)
    return branch


@router.post("")
async def create_branch(data: BranchCreate, current_user: dict = Depends(get_current_user)):
    _require_edit(current_user)
    branch_id = str(uuid.uuid4())
    branch = {
        "id": branch_id,
        **data.model_dump(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.branches.insert_one(branch)
    await log_audit(current_user["id"], current_user["name"], "create", "branch", branch_id, {"name": data.name})
    branch.pop("_id", None)
    branch["status"] = _derive_status(branch)
    return branch


@router.put("/{branch_id}")
async def update_branch(branch_id: str, data: BranchUpdate, current_user: dict = Depends(get_current_user)):
    _require_edit(current_user)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.branches.update_one({"id": branch_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    await log_audit(current_user["id"], current_user["name"], "update", "branch", branch_id, update_data)
    branch = await db.branches.find_one({"id": branch_id}, {"_id": 0})
    branch["status"] = _derive_status(branch)
    branch.pop("latitude", None)
    branch.pop("longitude", None)
    return branch


@router.delete("/{branch_id}")
async def delete_branch(branch_id: str, current_user: dict = Depends(get_current_user)):
    _require_delete(current_user)
    # Safety: don't delete a branch with active jobs/employees
    job_count = await db.jobs.count_documents({"branch_id": branch_id})
    emp_count = await db.employees.count_documents({"branch_id": branch_id, "status": {"$ne": "left"}})
    if job_count > 0 or emp_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete branch — has {job_count} job(s) and {emp_count} active employee(s). Remove or reassign first.",
        )
    result = await db.branches.delete_one({"id": branch_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    await log_audit(current_user["id"], current_user["name"], "delete", "branch", branch_id)
    return {"message": "Branch deleted"}
