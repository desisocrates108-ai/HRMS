from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, require_role, log_audit, CEO_HR_ROLES
import uuid
from datetime import datetime, timezone

router = APIRouter()


class EmployeeConvert(BaseModel):
    joining_date: str
    role: str
    branch_id: Optional[str] = None
    department: Optional[str] = None
    # Segmentation: where does this employee sit?
    # category: "branch" | "head_office"
    # employment_type: "technician" | "management" | "mid_level"
    category: Optional[str] = None  # auto-derived if not provided
    employment_type: Optional[str] = None  # auto-derived if not provided
    # Optional extras
    salary: Optional[float] = None
    reporting_manager_id: Optional[str] = None
    employee_code: Optional[str] = None


class EmployeeExit(BaseModel):
    exit_date: str
    exit_reason: str
    exit_type: str = "resigned"  # resigned | terminated | absconding | retired
    remarks: Optional[str] = ""
    auto_create_job: bool = True  # auto-post a job to refill this role/branch


def _derive_segmentation(lead: dict, data: EmployeeConvert) -> tuple[str, str]:
    """Derive (category, employment_type) if not explicitly supplied."""
    category = data.category
    emp_type = data.employment_type

    is_tech = bool(lead.get("is_technician"))
    has_branch = bool(data.branch_id)

    if not category:
        category = "branch" if (is_tech or has_branch) else "head_office"
    if not emp_type:
        if category == "branch":
            emp_type = "technician" if is_tech else "management"
        else:
            emp_type = "management" if (data.role or "").lower() in {
                "ceo", "super admin", "hr", "marketing manager", "operations manager",
                "franchise development manager", "sales manager", "accounts manager",
            } else "mid_level"
    return category, emp_type


@router.get("")
async def list_employees(
    category: Optional[str] = None,
    employment_type: Optional[str] = None,
    status: Optional[str] = None,
    branch_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List active employees. Filter by category/employment_type/status/branch_id/search.
    Search matches name, role, city, department.
    Exited employees are hidden unless explicitly requested.
    """
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$ne": "left"}
    if category:
        query["category"] = category
    if employment_type:
        query["employment_type"] = employment_type
    if branch_id:
        query["branch_id"] = branch_id
    if search:
        regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": regex}, {"role": regex}, {"location_city": regex},
            {"department": regex}, {"phone": regex}, {"email": regex},
        ]
    employees = await db.employees.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return employees


@router.get("/exited")
async def list_exited(current_user: dict = Depends(get_current_user)):
    """Left employees — visible only to CEO / Super Admin / HR."""
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to view exited employees")
    employees = await db.employees.find({"status": "left"}, {"_id": 0}).sort("exit_date", -1).to_list(2000)
    return employees


@router.get("/segments/summary")
async def segments_summary(current_user: dict = Depends(get_current_user)):
    """Counts per segment for dashboard chips."""
    pipeline = [
        {"$match": {"status": {"$ne": "left"}}},
        {"$group": {
            "_id": {"category": "$category", "employment_type": "$employment_type"},
            "count": {"$sum": 1},
        }},
    ]
    rows = await db.employees.aggregate(pipeline).to_list(100)
    summary = {
        "branch": {"technician": 0, "management": 0},
        "head_office": {"mid_level": 0, "management": 0},
        "total_active": 0,
    }
    for r in rows:
        cat = r["_id"].get("category")
        et = r["_id"].get("employment_type")
        if cat in summary and et in summary[cat]:
            summary[cat][et] = r["count"]
            summary["total_active"] += r["count"]
    summary["total_exited"] = await db.employees.count_documents({"status": "left"})
    return summary


@router.post("/convert/{lead_id}")
async def convert_lead_to_employee(
    lead_id: str,
    data: EmployeeConvert,
    current_user: dict = Depends(require_role("super", "manager")),
):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # New pipeline: require selected or joined; legacy: move_ahead, interview_cleared
    allowed_stages = {"selected", "joined", "move_ahead", "interview_cleared"}
    if lead["current_stage"] not in allowed_stages:
        raise HTTPException(
            status_code=400,
            detail="Lead must be in 'Selected' or 'Joined' stage to convert",
        )

    existing = await db.employees.find_one({"lead_id": lead_id})
    if existing:
        raise HTTPException(status_code=400, detail="Lead already converted to employee")

    category, emp_type = _derive_segmentation(lead, data)

    emp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    employee = {
        "id": emp_id,
        "lead_id": lead_id,
        "name": lead["name"],
        "phone": lead.get("phone", ""),
        "email": lead.get("email", ""),
        "joining_date": data.joining_date,
        "role": data.role,
        "branch_id": data.branch_id,
        "department": data.department,
        "category": category,
        "employment_type": emp_type,
        "salary": data.salary,
        "reporting_manager_id": data.reporting_manager_id,
        "employee_code": data.employee_code,
        "location_city": lead.get("location_city"),
        "location_area": lead.get("location_area"),
        "status": "active",
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.employees.insert_one(employee)
    employee.pop("_id", None)

    # Move lead to "joined" stage if not already
    if lead["current_stage"] != "joined":
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"current_stage": "joined", "updated_at": now}},
        )
        await db.lead_stage_logs.insert_one({
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "from_stage": lead["current_stage"],
            "to_stage": "joined",
            "changed_by": current_user["id"],
            "changed_by_name": current_user["name"],
            "form_data": {"joining_date": data.joining_date},
            "timestamp": now,
        })

    await log_audit(
        current_user["id"], current_user["name"],
        "convert_employee", "employee", emp_id,
        {"lead_id": lead_id, "category": category, "employment_type": emp_type},
    )
    return employee


@router.post("/{employee_id}/exit")
async def mark_employee_exit(
    employee_id: str,
    data: EmployeeExit,
    current_user: dict = Depends(require_role("super")),
):
    """Mark an employee as 'Left'. Triggers WhatsApp exit feedback form. CEO/HR only."""
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if emp.get("status") == "left":
        raise HTTPException(status_code=400, detail="Employee already marked as left")

    now = datetime.now(timezone.utc).isoformat()
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "status": "left",
            "exit_date": data.exit_date,
            "exit_reason": data.exit_reason,
            "exit_type": data.exit_type,
            "exit_remarks": data.remarks,
            "exited_by": current_user["id"],
            "updated_at": now,
        }},
    )

    await log_audit(
        current_user["id"], current_user["name"], "employee_exit", "employee", employee_id,
        {"exit_reason": data.exit_reason, "exit_type": data.exit_type},
    )

    # Auto-create job posting to refill the position + notify Sr/Jr HR
    auto_job_id = None
    if data.auto_create_job:
        try:
            from routes.notifications import create_notification
            branch = await db.branches.find_one({"id": emp.get("branch_id")}, {"_id": 0}) if emp.get("branch_id") else None
            location = f"{branch['city']}, {branch['area']}" if branch else (emp.get("location_city") or "Head Office")
            job_id = str(uuid.uuid4())
            is_tech = emp.get("employment_type") == "technician"
            new_job = {
                "id": job_id,
                "role": emp.get("role") or "Position",
                "type": "branch" if is_tech else "head_office",
                "department": emp.get("department"),
                "branch_id": emp.get("branch_id"),
                "location": location,
                "status": "open",
                "deadline": None,
                "auto_created_from_exit": True,
                "exit_employee_id": employee_id,
                "exit_employee_name": emp.get("name"),
                "created_by": current_user["id"],
                "created_by_name": current_user["name"],
                "created_at": now,
                "updated_at": now,
            }
            await db.jobs.insert_one(new_job)
            auto_job_id = job_id

            # Notify all active Sr HR / Jr HR users
            hr_users = await db.users.find(
                {"role": {"$in": ["Sr HR", "Jr HR"]}, "is_active": True},
                {"_id": 0, "id": 1, "name": 1},
            ).to_list(50)
            for u in hr_users:
                await create_notification(
                    u["id"],
                    f"New Opening — {emp.get('role')}",
                    f"{emp.get('name')} exited from {location}. Auto job posting created. Start sourcing.",
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Auto job creation failed: {e}")

    # Fire-and-forget WhatsApp exit feedback with tokenized form link
    try:
        from services.whatsapp import send_exit_feedback
        from routes.feedback import create_feedback_token
        token = await create_feedback_token(
            "exit", employee_id, "employee",
            {"exit_reason": data.exit_reason, "exit_type": data.exit_type},
        )
        await send_exit_feedback(emp, data.exit_reason, token)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"WhatsApp exit dispatch failed: {e}")

    return {"success": True, "employee_id": employee_id, "auto_job_id": auto_job_id}
