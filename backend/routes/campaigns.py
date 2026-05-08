from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit
import uuid
from datetime import datetime, timezone

router = APIRouter()


class CampaignUpdate(BaseModel):
    status: str  # pending, running, completed


@router.get("")
async def list_campaigns(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "Marketing Coordinator":
        campaigns = await db.ad_campaigns.find({"assigned_to": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    elif current_user["role"] in ["HR", "CEO"]:
        campaigns = await db.ad_campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    else:
        raise HTTPException(403, "No access to campaigns")
    return campaigns


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, data: CampaignUpdate, current_user: dict = Depends(get_current_user)):
    if data.status not in ["pending", "running", "completed"]:
        raise HTTPException(400, "Invalid status")
    result = await db.ad_campaigns.update_one({"id": campaign_id}, {"$set": {"status": data.status}})
    if result.matched_count == 0:
        raise HTTPException(404, "Campaign not found")
    await log_audit(current_user["id"], current_user["name"], "update_campaign", "campaign", campaign_id, {"status": data.status})
    campaign = await db.ad_campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return campaign
