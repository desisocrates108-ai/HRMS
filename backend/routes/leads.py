from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import (
    get_current_user, log_audit,
    PIPELINE_STAGES, STAGE_FORM_REQUIREMENTS,
    get_pipeline_stages, get_stage_order, PARALLEL_STAGES,
)
from routes.notifications import create_notification
import uuid
import os
from datetime import datetime, timezone, timedelta

router = APIRouter()


class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    location_city: Optional[str] = None
    location_area: Optional[str] = None
    source: str = "manual"
    assigned_to: Optional[str] = None
    is_technician: bool = False
    job_id: Optional[str] = None  # deprecated — kept for backward compat
    designation_id: Optional[str] = None
    job_role: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    description: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location_city: Optional[str] = None
    location_area: Optional[str] = None
    assigned_to: Optional[str] = None
    is_technician: Optional[bool] = None
    job_id: Optional[str] = None
    job_role: Optional[str] = None
    designation_id: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    description: Optional[str] = None


class StageTransition(BaseModel):
    to_stage: str
    form_data: dict


class CallLogCreate(BaseModel):
    notes: str


@router.get("")
async def list_leads(
    stage: Optional[str] = None,
    assigned_to: Optional[str] = None,
    source: Optional[str] = None,
    is_technician: Optional[bool] = None,
    job_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    include_deleted: bool = False,
    current_user: dict = Depends(get_current_user),
):
    query = {} if include_deleted else {"deleted": {"$ne": True}}
    if stage:
        query["current_stage"] = stage
    if assigned_to:
        query["assigned_to"] = assigned_to
    if source:
        query["source"] = source
    if is_technician is not None:
        query["is_technician"] = is_technician
    if job_id:
        query["job_id"] = job_id
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to
        query["created_at"] = date_q
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
        ]
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)
    # Enrich each lead with job_role (designation): prefer manual job_role on lead,
    # fallback to role of the linked job (if any), else None
    job_ids = list({l.get("job_id") for l in leads if l.get("job_id") and not l.get("job_role")})
    role_map = {}
    if job_ids:
        jobs = await db.jobs.find({"id": {"$in": job_ids}}, {"_id": 0, "id": 1, "role": 1}).to_list(len(job_ids))
        role_map = {j["id"]: j.get("role") for j in jobs}
    for l in leads:
        if not l.get("job_role"):
            l["job_role"] = role_map.get(l.get("job_id")) if l.get("job_id") else None
    return leads


@router.get("/deleted")
async def list_deleted_leads(current_user: dict = Depends(get_current_user)):
    """List soft-deleted leads. CEO/HR only."""
    from auth_utils import CEO_HR_ROLES
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Only CEO/HR can view deleted leads")
    leads = await db.leads.find({"deleted": True}, {"_id": 0}).sort("deleted_at", -1).to_list(5000)
    return leads


@router.post("/{lead_id}/delete")
async def soft_delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete a lead. Allowed: CEO, HR, or lead assignee/creator."""
    from auth_utils import CEO_HR_ROLES
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.get("deleted"):
        raise HTTPException(status_code=400, detail="Lead is already deleted")
    role = current_user.get("role")
    is_owner = current_user["id"] in (lead.get("assigned_to"), lead.get("created_by"))
    if role not in CEO_HR_ROLES and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this lead")
    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "deleted": True,
            "deleted_at": now,
            "deleted_by": current_user["id"],
            "deleted_by_name": current_user["name"],
            "updated_at": now,
        }},
    )
    await log_audit(
        current_user["id"], current_user["name"],
        "soft_delete", "lead", lead_id,
        {"name": lead.get("name"), "phone": lead.get("phone")},
    )
    return {"success": True, "lead_id": lead_id}


@router.post("/{lead_id}/restore")
async def restore_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Restore a soft-deleted lead. CEO only."""
    from auth_utils import CEO_HR_ROLES
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Only CEO/HR can restore leads")
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.get("deleted"):
        raise HTTPException(status_code=400, detail="Lead is not deleted")
    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "restored_at": now,
            "restored_by": current_user["id"],
            "restored_by_name": current_user["name"],
            "updated_at": now,
        }, "$unset": {"deleted": "", "deleted_at": "", "deleted_by": "", "deleted_by_name": ""}},
    )
    await log_audit(current_user["id"], current_user["name"], "restore", "lead", lead_id, {"name": lead.get("name")})
    return {"success": True, "lead_id": lead_id}


@router.delete("/{lead_id}")
async def hard_delete_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Permanently delete a lead (CEO only). Must be soft-deleted first."""
    from auth_utils import CEO_HR_ROLES
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Only CEO can permanently delete leads")
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.get("deleted"):
        raise HTTPException(status_code=400, detail="Soft-delete the lead first before permanent deletion")
    # Block if linked to employee (already converted)
    emp_link = await db.employees.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
    if emp_link:
        raise HTTPException(status_code=400, detail="Cannot delete: lead is linked to an employee record")
    await db.leads.delete_one({"id": lead_id})
    await db.lead_stage_logs.delete_many({"lead_id": lead_id})
    await db.interviews.delete_many({"lead_id": lead_id})
    await db.candidate_form_tokens.delete_many({"lead_id": lead_id})
    await db.candidate_form_submissions.delete_many({"lead_id": lead_id})
    await log_audit(current_user["id"], current_user["name"], "hard_delete", "lead", lead_id, {"name": lead.get("name")})
    return {"success": True, "lead_id": lead_id}


@router.get("/pipeline-stats")
async def pipeline_stats(current_user: dict = Depends(get_current_user)):
    pipeline = [{"$group": {"_id": "$current_stage", "count": {"$sum": 1}}}]
    results = await db.leads.aggregate(pipeline).to_list(100)
    stats = {stage: 0 for stage in PIPELINE_STAGES}
    for r in results:
        if r["_id"] in stats:
            stats[r["_id"]] = r["count"]
    return stats


@router.get("/{lead_id}")
async def get_lead(lead_id: str, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Enrich: prefer manual job_role on lead, fallback to linked job's role
    if not lead.get("job_role"):
        if lead.get("job_id"):
            job = await db.jobs.find_one({"id": lead["job_id"]}, {"_id": 0, "role": 1})
            lead["job_role"] = job.get("role") if job else None
        else:
            lead["job_role"] = None
    return lead


@router.post("")
async def create_lead(data: LeadCreate, current_user: dict = Depends(get_current_user)):
    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload = data.model_dump()

    # Resolve designation -> auto-fill job_role and is_technician
    if payload.get("designation_id"):
        desg = await db.designations.find_one({"id": payload["designation_id"]}, {"_id": 0})
        if not desg:
            raise HTTPException(status_code=404, detail="Designation not found")
        if not desg.get("active", True):
            raise HTTPException(status_code=400, detail="Designation is inactive")
        # Auto-fill role + segment from designation
        payload["job_role"] = desg.get("name") or payload.get("job_role")
        if desg.get("office_type") == "franchise":
            payload["is_technician"] = True
        elif desg.get("office_type") == "head_office":
            payload["is_technician"] = False

    # Validate salary range
    if payload.get("min_salary") is not None and payload.get("max_salary") is not None:
        if payload["min_salary"] > payload["max_salary"]:
            raise HTTPException(status_code=400, detail="Min salary cannot exceed max salary")

    # Drop null/empty designation_id to avoid storing empty string
    if not payload.get("designation_id"):
        payload.pop("designation_id", None)
    if not payload.get("job_role"):
        payload.pop("job_role", None)

    lead = {
        "id": lead_id,
        **payload,
        "current_stage": "new_lead",
        "previous_stage": None,
        "total_calls": 0,
        "last_call_date": None,
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
    }
    await db.leads.insert_one(lead)
    lead.pop("_id", None)

    await db.lead_stage_logs.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "from_stage": None,
        "to_stage": "new_lead",
        "changed_by": current_user["id"],
        "changed_by_name": current_user["name"],
        "form_data": {},
        "timestamp": now,
    })

    await log_audit(current_user["id"], current_user["name"], "create", "lead", lead_id, {"name": data.name})

    if data.assigned_to:
        await create_notification(
            data.assigned_to,
            "New Lead Assigned",
            f"Lead '{data.name}' has been assigned to you by {current_user['name']}",
        )

    return lead


@router.put("/{lead_id}")
async def update_lead(lead_id: str, data: LeadUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    unset_fields = {}
    # Allow explicit unset of job_id via empty string
    if data.model_fields_set and "job_id" in data.model_fields_set and (data.job_id is None or data.job_id == ""):
        update_data.pop("job_id", None)
        unset_fields["job_id"] = ""
    # Allow explicit unset of job_role via empty string
    if data.model_fields_set and "job_role" in data.model_fields_set and (data.job_role is None or data.job_role.strip() == ""):
        update_data.pop("job_role", None)
        unset_fields["job_role"] = ""
    elif "job_role" in update_data:
        update_data["job_role"] = update_data["job_role"].strip()
    # Designation handling: auto-fill job_role + is_technician from designation
    if data.model_fields_set and "designation_id" in data.model_fields_set and (data.designation_id is None or data.designation_id == ""):
        update_data.pop("designation_id", None)
        unset_fields["designation_id"] = ""
    elif update_data.get("designation_id"):
        desg = await db.designations.find_one({"id": update_data["designation_id"]}, {"_id": 0})
        if not desg:
            raise HTTPException(status_code=404, detail="Designation not found")
        # Auto-fill role + is_technician from the new designation
        if not update_data.get("job_role"):
            update_data["job_role"] = desg.get("name")
        if desg.get("office_type") == "franchise":
            update_data["is_technician"] = True
        elif desg.get("office_type") == "head_office":
            update_data["is_technician"] = False
    # Salary validation
    if "min_salary" in update_data and "max_salary" in update_data:
        if update_data["min_salary"] is not None and update_data["max_salary"] is not None:
            if update_data["min_salary"] > update_data["max_salary"]:
                raise HTTPException(status_code=400, detail="Min salary cannot exceed max salary")
    if not update_data and not unset_fields:
        raise HTTPException(status_code=400, detail="No data to update")
    # Validate job_id exists if provided
    if update_data.get("job_id"):
        job_exists = await db.jobs.find_one({"id": update_data["job_id"]}, {"_id": 0, "id": 1, "role": 1})
        if not job_exists:
            raise HTTPException(status_code=404, detail="Job not found")
    mongo_update = {}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        mongo_update["$set"] = update_data
    if unset_fields:
        mongo_update["$unset"] = unset_fields
    result = await db.leads.update_one({"id": lead_id}, mongo_update)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    await log_audit(current_user["id"], current_user["name"], "update", "lead", lead_id, {**update_data, **({"unset": list(unset_fields.keys())} if unset_fields else {})})
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Enrich: prefer manual job_role on lead; fallback to linked job's role
    if not lead.get("job_role") and lead.get("job_id"):
        j = await db.jobs.find_one({"id": lead["job_id"]}, {"_id": 0, "role": 1})
        lead["job_role"] = j.get("role") if j else None
    elif not lead.get("job_role"):
        lead["job_role"] = None
    return lead


async def _trigger_whatsapp_feedback(lead: dict, reason: str):
    """Dispatch WhatsApp feedback form link on Dead. Fire-and-forget."""
    try:
        from services.whatsapp import send_rejection_feedback
        from routes.feedback import create_feedback_token
        token = await create_feedback_token("rejection", lead["id"], "lead", {"reason": reason})
        await send_rejection_feedback(lead, reason, token)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"WhatsApp dispatch failed: {e}")


async def _trigger_offer_letter(lead: dict, current_user: dict):
    """On three_months → save offer letter record + dispatch WhatsApp offer letter."""
    try:
        from services.whatsapp import send_offer_letter
        job = await db.jobs.find_one({"id": lead.get("job_id")}, {"_id": 0}) if lead.get("job_id") else None
        branch = None
        if job and job.get("branch_id"):
            branch = await db.branches.find_one({"id": job["branch_id"]}, {"_id": 0})
        role = (job or {}).get("role") or "Position"
        department = (job or {}).get("department") or ""
        branch_name = (branch or {}).get("name") or "Head Office"
        now = datetime.now(timezone.utc).isoformat()
        offer_id = str(uuid.uuid4())
        wa_result = await send_offer_letter(lead, role, branch_name)
        await db.offer_letters.insert_one({
            "id": offer_id,
            "lead_id": lead["id"],
            "candidate_name": lead.get("name"),
            "candidate_phone": lead.get("phone"),
            "role": role,
            "department": department,
            "branch_name": branch_name,
            "branch_id": (branch or {}).get("id"),
            "job_id": lead.get("job_id"),
            "sent_at": now,
            "sent_by": current_user["id"],
            "sent_by_name": current_user["name"],
            "whatsapp_status": wa_result.get("status") if isinstance(wa_result, dict) else None,
            "whatsapp_result": wa_result if isinstance(wa_result, dict) else None,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Offer letter dispatch failed: {e}")


@router.post("/{lead_id}/transition")
async def transition_lead(
    lead_id: str, data: StageTransition, current_user: dict = Depends(get_current_user)
):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    current_stage = lead["current_stage"]
    to_stage = data.to_stage
    is_tech = bool(lead.get("is_technician", False))

    if to_stage not in PIPELINE_STAGES and to_stage != "dead":
        raise HTTPException(status_code=400, detail="Invalid stage")

    # Normalize legacy 'dead' to 'rejected'
    if to_stage == "dead":
        to_stage = "rejected"

    if to_stage == current_stage:
        raise HTTPException(status_code=400, detail="Already in this stage")

    # Technicians do not have manager_interview
    if is_tech and to_stage == "manager_interview":
        raise HTTPException(status_code=400, detail="Franchise pipeline has no Manager Interview stage")

    # Validate required form fields for the target stage
    required_fields = STAGE_FORM_REQUIREMENTS.get(to_stage, [])
    for field in required_fields:
        val = data.form_data.get(field)
        if val is None or val == "":
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    # HOLD can be entered from any active (linear) stage — not from rejected
    if to_stage == "hold":
        if current_stage in ("rejected", "dead"):
            raise HTTPException(status_code=400, detail="Cannot move Rejected leads to Hold")
        # keep previous_stage so we can resume
        new_previous = current_stage if current_stage != "hold" else lead.get("previous_stage")
    # REJECTED can be entered from any stage
    elif to_stage in ("rejected", "dead"):
        new_previous = lead.get("previous_stage")
    else:
        # Linear stage — for resuming from HOLD, allow any forward stage
        linear = get_pipeline_stages(is_tech)
        order = get_stage_order(is_tech)

        if to_stage not in order:
            raise HTTPException(
                status_code=400,
                detail=f"Stage '{to_stage}' is not valid for this pipeline",
            )

        # Resuming from hold: allow ANY linear stage (forward from previous), not just one-step
        if current_stage == "hold":
            prev = lead.get("previous_stage") or "new_lead"
            if prev == "move_ahead":
                prev = "selected"
            prev_idx = order.get(prev, 0)
            tgt_idx = order[to_stage]
            # Allow resuming to prev_stage or any forward stage (so Hold→Selected works)
            if tgt_idx < prev_idx:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot move backward. Hold was paused at '{linear[prev_idx]}'.",
                )
        else:
            effective_current = current_stage
            if effective_current == "move_ahead":
                effective_current = "selected"
            if effective_current not in order:
                raise HTTPException(
                    status_code=400,
                    detail=f"Current stage '{effective_current}' is not valid for this pipeline",
                )
            cur_idx = order[effective_current]
            tgt_idx = order[to_stage]
            if tgt_idx != cur_idx + 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot skip stages. Next stage must be '{linear[cur_idx + 1] if cur_idx + 1 < len(linear) else 'N/A'}'.",
                )

        # HARD BLOCKS (questionnaire enforcement) — skip if resuming from hold (form already done before)
        if current_stage != "hold":
            if to_stage == "manager_interview":
                # HO only — must have HR interview submitted
                hr_done = await db.interviews.find_one({"lead_id": lead_id, "round": "hr"})
                if not hr_done:
                    raise HTTPException(
                        status_code=400,
                        detail="HR interview questionnaire must be submitted before Manager Interview",
                    )
            if to_stage == "selected":
                # Must have prior round submitted
                if is_tech:
                    hr_done = await db.interviews.find_one({"lead_id": lead_id, "round": "hr"})
                    if not hr_done:
                        raise HTTPException(
                            status_code=400,
                            detail="HR interview questionnaire must be submitted before Selected",
                        )
                else:
                    mgr_done = await db.interviews.find_one({"lead_id": lead_id, "round": "manager"})
                    if not mgr_done:
                        raise HTTPException(
                            status_code=400,
                            detail="Manager interview questionnaire must be submitted before Selected",
                        )

        new_previous = None  # reset previous_stage once back on linear track

    # Apply update
    update = {
        "current_stage": to_stage,
        "previous_stage": new_previous,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if to_stage == "hold":
        update["hold_reason"] = data.form_data.get("hold_reason")
        update["hold_at"] = datetime.now(timezone.utc).isoformat()
    if to_stage in ("rejected", "dead"):
        update["rejection_reason"] = data.form_data.get("rejection_reason") or data.form_data.get("dead_reason")
        update["rejected_at"] = datetime.now(timezone.utc).isoformat()
    if to_stage in ("hr_interview", "manager_interview"):
        update[f"{to_stage}_details"] = {
            "interview_date": data.form_data.get("interview_date"),
            "interview_time": data.form_data.get("interview_time"),
            "interview_city": data.form_data.get("interview_city"),
            "interview_place": data.form_data.get("interview_place"),
            "mode": data.form_data.get("mode"),
            "scheduled_by": current_user["id"],
            "scheduled_by_name": current_user["name"],
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
        }
    if to_stage == "manager_interview":
        manager_id = data.form_data.get("manager_id")
        if manager_id:
            mgr = await db.users.find_one({"id": manager_id}, {"_id": 0, "name": 1, "role": 1})
            update["assigned_manager_id"] = manager_id
            update["assigned_manager_name"] = mgr["name"] if mgr else ""
            update["assigned_manager_role"] = mgr["role"] if mgr else ""
    if to_stage == "three_months":
        now = datetime.now(timezone.utc)
        update["three_months_start_date"] = now.isoformat()
        update["three_months_due_date"] = (now + timedelta(days=90)).isoformat()
    if to_stage == "joined":
        update["joined_at"] = datetime.now(timezone.utc).isoformat()

    # Lock interview records once lead has moved past decision point
    if to_stage in ("joined", "rejected", "dead"):
        await db.interviews.update_many(
            {"lead_id": lead_id}, {"$set": {"locked": True}}
        )

    await db.leads.update_one({"id": lead_id}, {"$set": update})

    await db.lead_stage_logs.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "from_stage": current_stage,
        "to_stage": to_stage,
        "changed_by": current_user["id"],
        "changed_by_name": current_user["name"],
        "form_data": data.form_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    await log_audit(
        current_user["id"], current_user["name"], "stage_transition", "lead", lead_id,
        {"from": current_stage, "to": to_stage, "form_data": data.form_data},
    )

    # On Rejected → trigger WhatsApp rejection feedback link
    if to_stage in ("rejected", "dead"):
        reason = data.form_data.get("rejection_reason") or data.form_data.get("dead_reason", "")
        await _trigger_whatsapp_feedback(lead, reason)

    # On Manager Interview → notify the assigned manager
    if to_stage == "manager_interview":
        mgr_id = data.form_data.get("manager_id")
        if mgr_id and mgr_id != current_user["id"]:
            await create_notification(
                mgr_id,
                f"Manager Interview Assigned: {lead.get('name')}",
                f"You have been assigned to interview {lead.get('name')}. Please review and conduct the interview.",
            )

    # On Three Months → trigger offer letter via WhatsApp + DB record
    if to_stage == "three_months":
        await _trigger_offer_letter(lead, current_user)

    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return lead


@router.get("/{lead_id}/history")
async def get_lead_history(lead_id: str, current_user: dict = Depends(get_current_user)):
    logs = await db.lead_stage_logs.find({"lead_id": lead_id}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    return logs


@router.post("/{lead_id}/calls")
async def add_call_log(lead_id: str, data: CallLogCreate, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    call_log = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "called_by": current_user["id"],
        "called_by_name": current_user["name"],
        "notes": data.notes,
        "call_date": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.call_logs.insert_one(call_log)

    await db.leads.update_one(
        {"id": lead_id},
        {
            "$inc": {"total_calls": 1},
            "$set": {"last_call_date": datetime.now(timezone.utc).isoformat()},
        },
    )

    await log_audit(current_user["id"], current_user["name"], "add_call", "lead", lead_id)
    call_log.pop("_id", None)
    return call_log


@router.get("/{lead_id}/calls")
async def get_call_logs(lead_id: str, current_user: dict = Depends(get_current_user)):
    logs = await db.call_logs.find({"lead_id": lead_id}, {"_id": 0}).sort("call_date", -1).to_list(100)
    return logs



# ---------------- Resume Upload + Medical Info ----------------

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "resumes")
os.makedirs(UPLOADS_DIR, exist_ok=True)
ALLOWED_RESUME_EXT = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}


class MedicalInfo(BaseModel):
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_notes: Optional[str] = None


@router.post("/{lead_id}/resume")
async def upload_resume(
    lead_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_RESUME_EXT:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_RESUME_EXT)}")

    stored_name = f"{lead_id}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOADS_DIR, stored_name)
    content = await file.read()
    # 10 MB limit
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    with open(path, "wb") as f:
        f.write(content)

    public_path = f"/api/uploads/resumes/{stored_name}"
    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "resume_url": public_path,
            "resume_filename": file.filename,
            "resume_uploaded_at": now,
            "resume_uploaded_by": current_user["id"],
            "updated_at": now,
        }},
    )
    await log_audit(current_user["id"], current_user["name"], "upload_resume", "lead", lead_id, {"filename": file.filename})
    return {"resume_url": public_path, "filename": file.filename}


@router.put("/{lead_id}/medical")
async def update_medical_info(
    lead_id: str,
    data: MedicalInfo,
    current_user: dict = Depends(get_current_user),
):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    medical = {k: v for k, v in data.model_dump().items() if v is not None}
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"medical_info": medical, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await log_audit(current_user["id"], current_user["name"], "update_medical", "lead", lead_id)
    return {"medical_info": medical}
