"""Offer Letter records — generated when a lead enters the 3-month stage.
Each record references a lead, candidate metadata, role/department, and WhatsApp send status.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from database import db
from auth_utils import get_current_user, CEO_HR_ROLES
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
async def list_offer_letters(
    lead_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    items = await db.offer_letters.find(query, {"_id": 0}).sort("sent_at", -1).to_list(2000)
    return items


@router.get("/three-months-due")
async def three_months_due(current_user: dict = Depends(get_current_user)):
    """Leads whose three_months tracking is due (≥90 days since start)."""
    now = datetime.now(timezone.utc).isoformat()
    leads = await db.leads.find(
        {"current_stage": "three_months", "three_months_due_date": {"$lte": now}},
        {"_id": 0},
    ).sort("three_months_due_date", 1).to_list(500)
    return leads
