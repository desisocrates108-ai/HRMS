from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, require_role, log_audit, ROLE_HIERARCHY
import uuid
from datetime import datetime, timezone, timedelta

router = APIRouter()


class JobCreate(BaseModel):
    role: str
    type: str  # branch or HO
    branch_id: Optional[str] = None
    location: str
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    description: Optional[str] = None
    deadline: Optional[str] = None


class JobUpdate(BaseModel):
    role: Optional[str] = None
    location: Optional[str] = None
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None


@router.get("")
async def list_jobs(
    status: Optional[str] = None,
    type: Optional[str] = None,
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if branch_id:
        query["branch_id"] = branch_id
    jobs = await db.jobs.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return jobs


@router.get("/{job_id}")
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("")
async def create_job(data: JobCreate, current_user: dict = Depends(require_role("super", "manager"))):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        **data.model_dump(),
        "status": "open",
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.jobs.insert_one(job)
    job.pop("_id", None)

    # Auto-create tasks
    tasks_to_create = [
        {"title": f"Create job creatives for {data.role} at {data.location}", "role_target": "Graphic Designer"},
        {"title": f"Post job ads for {data.role} at {data.location}", "role_target": "Marketing Coordinator"},
        {"title": f"Post job listing for {data.role} at {data.location}", "role_target": "Sr HR"},
    ]
    for task_info in tasks_to_create:
        assignee = await db.users.find_one({"role": task_info["role_target"], "is_active": True}, {"_id": 0})
        task = {
            "id": str(uuid.uuid4()),
            "title": task_info["title"],
            "description": f"Auto-created task for job: {data.role}",
            "assigned_to": assignee["id"] if assignee else None,
            "assigned_to_name": assignee["name"] if assignee else "Unassigned",
            "job_id": job_id,
            "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "status": "pending",
            "auto_created": True,
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tasks.insert_one(task)

        # Create notification for assignee
        if assignee:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": assignee["id"],
                "title": "New Task Assigned",
                "message": task_info["title"],
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

    await log_audit(current_user["id"], current_user["name"], "create", "job", job_id, {"role": data.role, "type": data.type})
    return job


@router.put("/{job_id}")
async def update_job(job_id: str, data: JobUpdate, current_user: dict = Depends(require_role("super", "manager"))):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    result = await db.jobs.update_one({"id": job_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    await log_audit(current_user["id"], current_user["name"], "update", "job", job_id, update_data)
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    return job


@router.post("/{job_id}/archive")
async def archive_job(job_id: str, current_user: dict = Depends(require_role("super", "manager"))):
    """Close/Archive a job. Active candidates remain — only closes new applications."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") in ("closed", "archived"):
        raise HTTPException(status_code=400, detail="Job is already closed/archived")
    now = datetime.now(timezone.utc).isoformat()
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": "closed",
            "archived_at": now,
            "archived_by": current_user["id"],
            "archived_by_name": current_user["name"],
            "updated_at": now,
        }},
    )
    await log_audit(current_user["id"], current_user["name"], "archive", "job", job_id, {"role": job.get("role")})
    return await db.jobs.find_one({"id": job_id}, {"_id": 0})


@router.post("/{job_id}/reopen")
async def reopen_job(job_id: str, current_user: dict = Depends(require_role("super", "manager"))):
    """Reopen a closed/archived job."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") == "open":
        raise HTTPException(status_code=400, detail="Job is already open")
    now = datetime.now(timezone.utc).isoformat()
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "open", "updated_at": now}, "$unset": {"archived_at": "", "archived_by": "", "archived_by_name": ""}},
    )
    await log_audit(current_user["id"], current_user["name"], "reopen", "job", job_id, {"role": job.get("role")})
    return await db.jobs.find_one({"id": job_id}, {"_id": 0})


@router.delete("/{job_id}")
async def delete_job(job_id: str, current_user: dict = Depends(require_role("super"))):
    """Delete a job (Super only). Blocked if linked candidates/employees exist."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    lead_count = await db.leads.count_documents({"job_id": job_id})
    if lead_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {lead_count} candidate(s) are linked to this job. Archive it instead.",
        )
    emp_count = await db.employees.count_documents({"job_id": job_id})
    if emp_count:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete — {emp_count} employee(s) are linked to this job. Archive it instead.",
        )
    await db.jobs.delete_one({"id": job_id})
    # Clean auto-created tasks tied to this job
    await db.tasks.delete_many({"job_id": job_id, "auto_created": True})
    await log_audit(current_user["id"], current_user["name"], "delete", "job", job_id, {"role": job.get("role")})
    return {"success": True, "deleted_job_id": job_id}
