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
from datetime import datetime, timezone

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
    job_id: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location_city: Optional[str] = None
    location_area: Optional[str] = None
    assigned_to: Optional[str] = None
    is_technician: Optional[bool] = None


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
    current_user: dict = Depends(get_current_user),
):
    query = {}
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
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
        ]
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)
    return leads


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
    return lead


@router.post("")
async def create_lead(data: LeadCreate, current_user: dict = Depends(get_current_user)):
    lead_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    lead = {
        "id": lead_id,
        **data.model_dump(),
        "current_stage": "new_lead",
        "previous_stage": None,  # used to resume from hold
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
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    await log_audit(current_user["id"], current_user["name"], "update", "lead", lead_id, update_data)
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
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
        raise HTTPException(status_code=400, detail="Technician pipeline has no Manager Interview stage")

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
        # Linear stage — validate order for this pipeline type
        linear = get_pipeline_stages(is_tech)
        order = get_stage_order(is_tech)

        # If resuming from hold: allow moving back to previous_stage OR forward by one from previous_stage
        effective_current = current_stage
        if current_stage == "hold":
            prev = lead.get("previous_stage") or "new_lead"
            effective_current = prev
        # legacy alias support
        if effective_current == "move_ahead":
            effective_current = "selected"

        if effective_current not in order:
            raise HTTPException(
                status_code=400,
                detail=f"Current stage '{effective_current}' is not valid for this pipeline",
            )
        if to_stage not in order:
            raise HTTPException(
                status_code=400,
                detail=f"Stage '{to_stage}' is not valid for this pipeline",
            )
        cur_idx = order[effective_current]
        tgt_idx = order[to_stage]
        if tgt_idx != cur_idx + 1:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot skip stages. Next stage must be '{linear[cur_idx + 1] if cur_idx + 1 < len(linear) else 'N/A'}'.",
            )

        # HARD BLOCKS (questionnaire enforcement)
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
