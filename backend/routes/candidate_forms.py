"""Candidate Information Form — public tokenised form sent via WhatsApp.

Flow:
1. HR clicks "Send Candidate Form" on a lead → POST /api/candidate-forms/{lead_id}/send
   - Generates secure token, stores candidate_form_tokens doc, marks lead.candidate_form_status="sent"
   - Dispatches WhatsApp template (if configured) else returns the public link for manual share.
2. Candidate opens https://<app>/candidate-form/{token} (no auth):
   - GET /api/candidate-forms/form/{token}  → form schema + lead context
   - POST /api/candidate-forms/form/{token} (multipart) → submits answers + uploads
3. On submission:
   - Files saved to /app/backend/uploads/candidates/{lead_id}/
   - candidate_form_submissions doc created
   - lead.candidate_form_status="completed", lead.candidate_form_data merged in
   - HR assigned to lead notified
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from database import db
from auth_utils import get_current_user, log_audit, CEO_HR_ROLES
from routes.notifications import create_notification
import os
import uuid
import secrets
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_ROOT = Path("/app/backend/uploads/candidates")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_DOC_FIELDS = ["resume", "aadhaar", "pan", "photo"]
ALLOWED_DOC_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"}
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB per file

FORM_SCHEMA = {
    "personal": [
        {"key": "full_name", "label": "Full Name", "type": "text", "required": True},
        {"key": "mobile", "label": "Mobile Number", "type": "tel", "required": True},
        {"key": "alternate_mobile", "label": "Alternate Mobile", "type": "tel"},
        {"key": "email", "label": "Email Address", "type": "email", "required": True},
        {"key": "dob", "label": "Date of Birth", "type": "date"},
        {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
        {"key": "marital_status", "label": "Marital Status", "type": "select", "options": ["Single", "Married", "Other"]},
        {"key": "current_address", "label": "Current Address", "type": "textarea"},
        {"key": "permanent_address", "label": "Permanent Address", "type": "textarea"},
        {"key": "city", "label": "City", "type": "text"},
        {"key": "state", "label": "State", "type": "text"},
    ],
    "education": [
        {"key": "highest_qualification", "label": "Highest Qualification", "type": "text"},
        {"key": "specialization", "label": "Specialization", "type": "text"},
        {"key": "passing_year", "label": "Passing Year", "type": "text"},
        {"key": "percentage", "label": "Percentage / Grade", "type": "text"},
    ],
    "employment": [
        {"key": "current_company", "label": "Current Company", "type": "text"},
        {"key": "current_designation", "label": "Current Designation", "type": "text"},
        {"key": "total_experience", "label": "Total Experience (years)", "type": "text"},
        {"key": "relevant_experience", "label": "Relevant Experience (years)", "type": "text"},
        {"key": "current_salary", "label": "Current Salary (CTC)", "type": "text"},
        {"key": "expected_salary", "label": "Expected Salary (CTC)", "type": "text"},
        {"key": "notice_period", "label": "Notice Period", "type": "text"},
    ],
    "interview": [
        {"key": "position_applied", "label": "Position Applied For", "type": "text"},
        {"key": "preferred_location", "label": "Preferred Location", "type": "text"},
        {"key": "available_joining_date", "label": "Available Joining Date", "type": "date"},
    ],
    "documents": [
        {"key": "resume", "label": "Resume", "type": "file", "accept": ".pdf,.doc,.docx"},
        {"key": "aadhaar", "label": "Aadhaar Card", "type": "file", "accept": ".pdf,.jpg,.jpeg,.png"},
        {"key": "pan", "label": "PAN Card", "type": "file", "accept": ".pdf,.jpg,.jpeg,.png"},
        {"key": "photo", "label": "Passport Photo", "type": "file", "accept": ".jpg,.jpeg,.png"},
    ],
}


# =========================== HR: send form ===========================

class SendFormRequest(BaseModel):
    pass


def _build_public_form_url(token: str) -> str:
    base = (os.environ.get("PUBLIC_APP_URL")
            or os.environ.get("FRONTEND_URL")
            or "").rstrip("/")
    return f"{base}/candidate-form/{token}" if base else f"/candidate-form/{token}"


@router.post("/{lead_id}/send")
async def send_candidate_form(
    lead_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate a public form link and dispatch via WhatsApp (or return link for manual share)."""
    if current_user.get("role") not in CEO_HR_ROLES and "HR" not in (current_user.get("role") or ""):
        # Allow CEO + HR roles only
        if current_user.get("role") not in CEO_HR_ROLES:
            raise HTTPException(status_code=403, detail="Only CEO/HR can send candidate forms")

    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Reuse outstanding (unsubmitted) token if present
    existing = await db.candidate_form_tokens.find_one({"lead_id": lead_id, "submitted": False}, {"_id": 0})
    if existing:
        token = existing["token"]
    else:
        token = secrets.token_urlsafe(24)
        await db.candidate_form_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "token": token,
            "lead_id": lead_id,
            "submitted": False,
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    now = datetime.now(timezone.utc).isoformat()
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "candidate_form_status": "sent",
            "candidate_form_sent_at": now,
            "candidate_form_sent_by": current_user["name"],
            "updated_at": now,
        }},
    )

    public_url = _build_public_form_url(token)
    whatsapp_result = {"dispatched": False, "reason": "skipped"}
    try:
        api_url = os.environ.get("WHATSAPP_API_URL")
        auth_token = os.environ.get("WHATSAPP_AUTH_TOKEN")
        if api_url and auth_token and lead.get("phone"):
            from services.whatsapp import _send_template
            template = os.environ.get("WHATSAPP_CANDIDATE_FORM_TEMPLATE", "candidate_information_form")
            result = await _send_template(
                phone=lead["phone"],
                template=template,
                body_values=[lead.get("name") or "Candidate"],
                button_url_path=f"candidate-form/{token}",
                callback=f"candidate_form:{lead_id}",
            )
            whatsapp_result = {"dispatched": True, "result": result}
        else:
            whatsapp_result = {"dispatched": False, "reason": "WhatsApp not configured — share link manually"}
    except Exception as e:
        logger.warning(f"[CandidateForm] WhatsApp dispatch failed: {e}")
        whatsapp_result = {"dispatched": False, "reason": str(e)}

    await log_audit(
        current_user["id"], current_user["name"],
        "send_candidate_form", "lead", lead_id,
        {"token": token, "whatsapp": whatsapp_result.get("dispatched")},
    )

    return {
        "success": True,
        "token": token,
        "public_url": public_url,
        "whatsapp": whatsapp_result,
        "candidate_phone": lead.get("phone"),
        "candidate_name": lead.get("name"),
    }


# =========================== Public form endpoints ===========================

@router.get("/form/{token}")
async def get_candidate_form(token: str):
    tk = await db.candidate_form_tokens.find_one({"token": token}, {"_id": 0})
    if not tk:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if tk.get("submitted"):
        raise HTTPException(status_code=410, detail="This form has already been submitted")
    lead = await db.leads.find_one({"id": tk["lead_id"]}, {"_id": 0, "name": 1, "phone": 1, "email": 1})
    return {
        "schema": FORM_SCHEMA,
        "candidate": {
            "name": (lead or {}).get("name", ""),
            "phone": (lead or {}).get("phone", ""),
            "email": (lead or {}).get("email", ""),
        },
    }


@router.post("/form/{token}")
async def submit_candidate_form(
    token: str,
    request: Request,
    answers: str = Form(..., description="JSON-encoded field answers"),
    declaration: str = Form("true"),
    resume: Optional[UploadFile] = File(None),
    aadhaar: Optional[UploadFile] = File(None),
    pan: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None),
):
    tk = await db.candidate_form_tokens.find_one({"token": token}, {"_id": 0})
    if not tk:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    if tk.get("submitted"):
        raise HTTPException(status_code=410, detail="This form has already been submitted")

    if (declaration or "").lower() not in ("true", "1", "yes"):
        raise HTTPException(status_code=400, detail="Declaration must be accepted")

    try:
        parsed = json.loads(answers or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid answers payload")

    # Soft validation: required fields
    required_personal = [f["key"] for f in FORM_SCHEMA["personal"] if f.get("required")]
    for key in required_personal:
        if not str(parsed.get(key, "")).strip():
            raise HTTPException(status_code=400, detail=f"Missing required field: {key}")

    lead_id = tk["lead_id"]
    lead_folder = UPLOAD_ROOT / lead_id
    lead_folder.mkdir(parents=True, exist_ok=True)

    stored_docs: dict = {}
    uploads = {"resume": resume, "aadhaar": aadhaar, "pan": pan, "photo": photo}
    for field, upload in uploads.items():
        if not upload:
            continue
        original = upload.filename or field
        ext = Path(original).suffix.lower()
        if ext and ext not in ALLOWED_DOC_EXTS:
            raise HTTPException(status_code=400, detail=f"{field}: file type {ext} not allowed")
        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"{field}: max file size is 8 MB")
        safe_name = f"{field}_{int(datetime.now(timezone.utc).timestamp())}{ext or ''}"
        dest = lead_folder / safe_name
        dest.write_bytes(content)
        stored_docs[field] = {
            "filename": original,
            "stored_as": safe_name,
            "path": str(dest.relative_to(Path("/app/backend"))),
            "size": len(content),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

    submission_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    submission_doc = {
        "id": submission_id,
        "lead_id": lead_id,
        "token": token,
        "answers": parsed,
        "documents": stored_docs,
        "submitted_at": now,
    }
    await db.candidate_form_submissions.insert_one(submission_doc)
    await db.candidate_form_tokens.update_one(
        {"token": token},
        {"$set": {"submitted": True, "submitted_at": now, "submission_id": submission_id}},
    )

    # Merge into lead
    lead_update = {
        "candidate_form_status": "completed",
        "candidate_form_completed_at": now,
        "candidate_form_data": parsed,
        "candidate_form_documents": stored_docs,
        "updated_at": now,
    }
    # Soft sync some convenience fields
    if parsed.get("email") and not (await db.leads.find_one({"id": lead_id}, {"_id": 0, "email": 1}) or {}).get("email"):
        lead_update["email"] = parsed["email"]
    if parsed.get("city"):
        lead_update["location_city"] = parsed["city"]
    await db.leads.update_one({"id": lead_id}, {"$set": lead_update})

    # Notify the assigned HR (or creator)
    lead_doc = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    notify_user_id = lead_doc.get("assigned_to") or lead_doc.get("created_by")
    if notify_user_id:
        await create_notification(
            notify_user_id,
            "Candidate Form Completed",
            f"{lead_doc.get('name', 'Candidate')} submitted the information form.",
        )

    return {"success": True, "message": "Thank you! Your information has been submitted."}


# =========================== Authenticated lookups ===========================

@router.get("/{lead_id}")
async def get_candidate_form_state(lead_id: str, current_user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    submission = await db.candidate_form_submissions.find_one({"lead_id": lead_id}, {"_id": 0}, sort=[("submitted_at", -1)])
    pending_token = await db.candidate_form_tokens.find_one({"lead_id": lead_id, "submitted": False}, {"_id": 0})
    public_url = _build_public_form_url(pending_token["token"]) if pending_token else None
    return {
        "status": lead.get("candidate_form_status") or "not_sent",
        "sent_at": lead.get("candidate_form_sent_at"),
        "completed_at": lead.get("candidate_form_completed_at"),
        "submission": submission,
        "pending_public_url": public_url,
    }


@router.get("/{lead_id}/document/{field}")
async def download_candidate_document(
    lead_id: str,
    field: str,
    current_user: dict = Depends(get_current_user),
):
    if field not in ALLOWED_DOC_FIELDS:
        raise HTTPException(status_code=400, detail="Invalid document field")
    submission = await db.candidate_form_submissions.find_one({"lead_id": lead_id}, {"_id": 0}, sort=[("submitted_at", -1)])
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found")
    docs = submission.get("documents", {})
    doc = docs.get(field)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not uploaded")
    # path stored relative to /app/backend/uploads parent
    full_path = Path("/app/backend") / doc["path"]
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(path=str(full_path), filename=doc.get("filename") or full_path.name)
