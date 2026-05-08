"""Public tokenized feedback form routes.

Two forms:
- "rejection" — sent to rejected candidates (lead moved to Dead)
- "exit" — sent to exiting employees

Flow:
  1. When a lead is moved to "dead" OR an employee is marked exited, a feedback_token
     is generated and a WhatsApp message is dispatched containing a link.
  2. The candidate/employee opens the link (no auth) → GET /api/feedback/form/{token}
  3. They submit → POST /api/feedback/{token}
  4. Submission is locked (single-use).

Admin:
- GET /api/feedback/submissions — CEO/Super Admin/HR only (returns all submissions)
- GET /api/feedback/submissions/{id} — detail
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict
from database import db
from auth_utils import get_current_user, CEO_HR_ROLES
import secrets
import uuid
from datetime import datetime, timezone

router = APIRouter()


# --- Form schemas ---
REJECTION_FIELDS = [
    {"key": "understood_reason", "label": "Were you given clear feedback on why you were not selected?", "type": "yes_no"},
    {"key": "interview_experience", "label": "How was your interview experience?", "type": "rating"},
    {"key": "treated_respectfully", "label": "Were you treated respectfully throughout the process?", "type": "yes_no"},
    {"key": "response_time_rating", "label": "Rate our response time", "type": "rating"},
    {"key": "would_reapply", "label": "Would you apply to Servall again?", "type": "yes_no"},
    {"key": "suggestion", "label": "Any suggestions to improve our hiring?", "type": "text"},
]

EXIT_FIELDS = [
    {"key": "primary_reason", "label": "Primary reason for leaving", "type": "text"},
    {"key": "work_satisfaction", "label": "Overall work satisfaction", "type": "rating"},
    {"key": "manager_support", "label": "Support from your manager", "type": "rating"},
    {"key": "team_environment", "label": "Team environment", "type": "rating"},
    {"key": "growth_opportunities", "label": "Growth opportunities", "type": "rating"},
    {"key": "compensation_fair", "label": "Was compensation fair?", "type": "yes_no"},
    {"key": "would_recommend", "label": "Would you recommend Servall as an employer?", "type": "yes_no"},
    {"key": "what_we_could_improve", "label": "What could Servall do better?", "type": "text"},
    {"key": "best_memory", "label": "Best memory from your time here?", "type": "text"},
]

FORMS = {"rejection": REJECTION_FIELDS, "exit": EXIT_FIELDS}


class FeedbackSubmission(BaseModel):
    answers: Dict[str, str] = Field(..., description="answer_key -> string value")


async def create_feedback_token(kind: Literal["rejection", "exit"], subject_id: str, subject_type: Literal["lead", "employee"], meta: dict = None) -> str:
    """Generate and store a single-use feedback token. Returns the token string."""
    token = secrets.token_urlsafe(24)
    await db.feedback_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "token": token,
        "kind": kind,
        "subject_id": subject_id,
        "subject_type": subject_type,
        "meta": meta or {},
        "submitted": False,
        "submission_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return token


# --- Public endpoints (no auth) ---

@router.get("/form/{token}")
async def get_feedback_form(token: str):
    """Return the form structure + subject context (name). Public endpoint."""
    tk = await db.feedback_tokens.find_one({"token": token}, {"_id": 0})
    if not tk:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if tk.get("submitted"):
        raise HTTPException(status_code=410, detail="This form has already been submitted")

    # Fetch subject name for personalization
    subject_name = ""
    if tk["subject_type"] == "lead":
        lead = await db.leads.find_one({"id": tk["subject_id"]}, {"_id": 0, "name": 1})
        subject_name = lead["name"] if lead else ""
    elif tk["subject_type"] == "employee":
        emp = await db.employees.find_one({"id": tk["subject_id"]}, {"_id": 0, "name": 1})
        subject_name = emp["name"] if emp else ""

    return {
        "kind": tk["kind"],
        "subject_name": subject_name,
        "fields": FORMS[tk["kind"]],
    }


@router.post("/{token}")
async def submit_feedback(token: str, data: FeedbackSubmission):
    tk = await db.feedback_tokens.find_one({"token": token}, {"_id": 0})
    if not tk:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if tk.get("submitted"):
        raise HTTPException(status_code=410, detail="This form has already been submitted")

    # Validate all required keys are present (non-text fields must be non-empty)
    fields = FORMS[tk["kind"]]
    for f in fields:
        if f["type"] != "text":
            v = data.answers.get(f["key"])
            if v is None or v == "":
                raise HTTPException(status_code=400, detail=f"Missing answer: {f['label']}")

    sub_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Copy subject name for analytics
    subject_name = ""
    subject_phone = ""
    if tk["subject_type"] == "lead":
        lead = await db.leads.find_one({"id": tk["subject_id"]}, {"_id": 0})
        if lead:
            subject_name = lead.get("name", "")
            subject_phone = lead.get("phone", "")
    elif tk["subject_type"] == "employee":
        emp = await db.employees.find_one({"id": tk["subject_id"]}, {"_id": 0})
        if emp:
            subject_name = emp.get("name", "")
            subject_phone = emp.get("phone", "")

    await db.feedback_submissions.insert_one({
        "id": sub_id,
        "token": token,
        "kind": tk["kind"],
        "subject_id": tk["subject_id"],
        "subject_type": tk["subject_type"],
        "subject_name": subject_name,
        "subject_phone": subject_phone,
        "meta": tk.get("meta", {}),
        "answers": data.answers,
        "submitted_at": now,
    })
    await db.feedback_tokens.update_one(
        {"token": token},
        {"$set": {"submitted": True, "submission_id": sub_id, "submitted_at": now}},
    )
    return {"success": True, "message": "Thank you for your feedback!"}


# --- Admin endpoints (CEO/HR only) ---

@router.get("/submissions")
async def list_submissions(
    kind: Optional[Literal["rejection", "exit"]] = None,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Only CEO/HR can view feedback submissions")
    query = {}
    if kind:
        query["kind"] = kind
    subs = await db.feedback_submissions.find(query, {"_id": 0}).sort("submitted_at", -1).to_list(1000)
    return subs


@router.get("/submissions/summary")
async def submissions_summary(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in CEO_HR_ROLES:
        raise HTTPException(status_code=403, detail="Only CEO/HR can view feedback summary")
    rejection_count = await db.feedback_submissions.count_documents({"kind": "rejection"})
    exit_count = await db.feedback_submissions.count_documents({"kind": "exit"})
    pending_tokens = await db.feedback_tokens.count_documents({"submitted": False})
    return {
        "rejection_count": rejection_count,
        "exit_count": exit_count,
        "pending_invitations": pending_tokens,
        "total": rejection_count + exit_count,
    }
