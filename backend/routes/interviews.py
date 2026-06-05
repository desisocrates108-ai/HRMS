"""Interview Questionnaire Routes.

Handles HR and Manager round questionnaires with 10 mandatory rating criteria each.
Submissions unlock specific stage transitions in the hiring pipeline.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict
from database import db
from auth_utils import (
    get_current_user, log_audit,
    HR_ROUND_CRITERIA, MANAGER_ROUND_CRITERIA,
    HR_CRITERIA_LABELS, MANAGER_CRITERIA_LABELS,
)
from routes.notifications import create_notification
import uuid
from datetime import datetime, timezone

router = APIRouter()


class InterviewSubmission(BaseModel):
    ratings: Dict[str, int] = Field(..., description="Mapping of criterion_key -> 1..5 rating")
    remarks: Optional[str] = ""


def _validate_ratings(ratings: Dict[str, int], required_keys: list[str]):
    # All 10 criteria must be present and within 1..5
    missing = [k for k in required_keys if k not in ratings]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing criteria: {', '.join(missing)}")
    for k in required_keys:
        v = ratings.get(k)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Rating for '{k}' must be an integer 1-5")
        if iv < 1 or iv > 5:
            raise HTTPException(status_code=400, detail=f"Rating for '{k}' must be 1-5")
    # Normalize to ints
    return {k: int(ratings[k]) for k in required_keys}


def _compute_avg(ratings: Dict[str, int]) -> float:
    if not ratings:
        return 0.0
    return round(sum(ratings.values()) / len(ratings), 2)


@router.get("/criteria")
async def get_criteria(current_user: dict = Depends(get_current_user)):
    """Return the criteria keys + labels for both rounds (used by frontend forms)."""
    return {
        "hr": [{"key": k, "label": HR_CRITERIA_LABELS[k]} for k in HR_ROUND_CRITERIA],
        "manager": [{"key": k, "label": MANAGER_CRITERIA_LABELS[k]} for k in MANAGER_ROUND_CRITERIA],
    }


@router.get("/{lead_id}")
async def get_lead_interviews(lead_id: str, current_user: dict = Depends(get_current_user)):
    """Get all interview submissions for a lead (HR round + Manager round if present)."""
    hr = await db.interviews.find_one({"lead_id": lead_id, "round": "hr"}, {"_id": 0})
    mgr = await db.interviews.find_one({"lead_id": lead_id, "round": "manager"}, {"_id": 0})
    return {"hr": hr, "manager": mgr}


async def _submit_round(
    lead_id: str, round_name: str, criteria: list[str],
    data: InterviewSubmission, current_user: dict
):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if round_name == "manager" and lead.get("is_technician"):
        raise HTTPException(status_code=400, detail="Manager round is only for Head Office roles")

    validated = _validate_ratings(data.ratings, criteria)
    avg = _compute_avg(validated)

    existing = await db.interviews.find_one({"lead_id": lead_id, "round": round_name})
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "lead_id": lead_id,
        "lead_name": lead.get("name"),
        "round": round_name,
        "ratings": validated,
        "avg_rating": avg,
        "remarks": (data.remarks or "").strip(),
        "submitted_by": current_user["id"],
        "submitted_by_name": current_user["name"],
        "submitted_at": now,
        "updated_at": now,
    }
    if existing:
        # Editable — lock logic handled via `locked` flag (we allow edits until lead moves past move_ahead/joined)
        if existing.get("locked"):
            raise HTTPException(status_code=400, detail="Interview record is locked and cannot be edited")
        await db.interviews.update_one(
            {"lead_id": lead_id, "round": round_name},
            {"$set": record}
        )
    else:
        record["id"] = str(uuid.uuid4())
        record["created_at"] = now
        record["locked"] = False
        await db.interviews.insert_one(record)

    await log_audit(
        current_user["id"], current_user["name"],
        f"submit_{round_name}_interview", "lead", lead_id,
        {"avg_rating": avg, "round": round_name},
    )

    # Notify assigned user
    if lead.get("assigned_to") and lead["assigned_to"] != current_user["id"]:
        await create_notification(
            lead["assigned_to"],
            f"{round_name.upper()} Interview Completed",
            f"{current_user['name']} submitted {round_name} round feedback for {lead.get('name')} (avg {avg}/5)",
        )

    doc = await db.interviews.find_one(
        {"lead_id": lead_id, "round": round_name}, {"_id": 0}
    )
    return doc


@router.post("/{lead_id}/hr")
async def submit_hr_round(
    lead_id: str,
    data: InterviewSubmission,
    current_user: dict = Depends(get_current_user),
):
    return await _submit_round(lead_id, "hr", HR_ROUND_CRITERIA, data, current_user)


@router.post("/{lead_id}/manager")
async def submit_manager_round(
    lead_id: str,
    data: InterviewSubmission,
    current_user: dict = Depends(get_current_user),
):
    """Manager Round — only the assigned manager (or CEO override) may submit.
    HR users are EXPLICITLY blocked from submitting Manager Rating/Feedback.
    """
    role = current_user.get("role", "") or ""
    role_lower = role.lower().strip()

    # HR is strictly blocked, no exception
    if role_lower in {"hr", "sr hr", "jr hr", "hr admin", "hr executive"} or "hr" in role_lower.split():
        raise HTTPException(
            status_code=403,
            detail="HR users cannot submit Manager evaluation. Only the assigned Manager (or CEO override) can submit this round.",
        )

    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "assigned_manager_id": 1, "is_technician": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    assigned_mgr_id = lead.get("assigned_manager_id")
    is_assigned = assigned_mgr_id and assigned_mgr_id == current_user["id"]
    is_ceo = role_lower in {"ceo", "super admin", "super_admin"}

    if not (is_assigned or is_ceo):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned Manager (or CEO override) can submit Manager evaluation.",
        )

    return await _submit_round(lead_id, "manager", MANAGER_ROUND_CRITERIA, data, current_user)
