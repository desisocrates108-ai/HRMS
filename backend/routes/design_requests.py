"""Design Request routes — allows any user to request a design from the
Graphic Designer team. Visible on Designer's dashboard / panel.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit
from routes.notifications import create_notification
import uuid
from datetime import datetime, timezone

router = APIRouter()

VALID_STATUS = {"pending", "in_progress", "completed"}
VALID_PRIORITY = {"low", "medium", "high", "urgent"}


class DesignRequestCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    branch_department: Optional[str] = None
    priority: str = "medium"
    required_date: Optional[str] = None
    attachment_url: Optional[str] = None


class DesignRequestUpdate(BaseModel):
    status: Optional[str] = None
    remarks: Optional[str] = None
    final_design_url: Optional[str] = None


@router.get("")
async def list_requests(
    status: Optional[str] = None,
    mine: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    role = current_user.get("role")
    if status:
        query["status"] = status
    if mine:
        query["requested_by"] = current_user["id"]
    else:
        # Non-designer non-super users see only their own
        if role not in ("CEO", "HR", "Graphic Designer"):
            query["requested_by"] = current_user["id"]
    items = await db.design_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return items


@router.post("")
async def create_request(data: DesignRequestCreate, current_user: dict = Depends(get_current_user)):
    if data.priority not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail="Invalid priority")
    rid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": rid,
        "title": data.title,
        "description": data.description or "",
        "branch_department": data.branch_department,
        "priority": data.priority,
        "required_date": data.required_date,
        "attachment_url": data.attachment_url,
        "status": "pending",
        "remarks": "",
        "final_design_url": None,
        "requested_by": current_user["id"],
        "requested_by_name": current_user["name"],
        "requested_by_role": current_user["role"],
        "created_at": now,
        "updated_at": now,
    }
    await db.design_requests.insert_one(doc)
    doc.pop("_id", None)

    # Notify all active Graphic Designers
    designers = await db.users.find(
        {"role": "Graphic Designer", "is_active": True}, {"_id": 0, "id": 1}
    ).to_list(50)
    for u in designers:
        await create_notification(
            u["id"],
            f"New Design Request: {data.title}",
            f"Requested by {current_user['name']} · Priority {data.priority.upper()}",
        )
    await log_audit(current_user["id"], current_user["name"], "create", "design_request", rid)
    return doc


@router.put("/{rid}")
async def update_request(rid: str, data: DesignRequestUpdate, current_user: dict = Depends(get_current_user)):
    item = await db.design_requests.find_one({"id": rid}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Design request not found")

    role = current_user.get("role")
    is_owner = item.get("requested_by") == current_user["id"]
    is_designer = role == "Graphic Designer"
    is_super = role in ("CEO", "HR")
    if not (is_owner or is_designer or is_super):
        raise HTTPException(status_code=403, detail="Not authorized")

    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Owners cannot change status — only designer/super can
    if is_owner and not (is_designer or is_super):
        update.pop("status", None)
        update.pop("final_design_url", None)

    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.design_requests.update_one({"id": rid}, {"$set": update})

    # Notify the requester on status change
    if "status" in update and item.get("requested_by") != current_user["id"]:
        await create_notification(
            item["requested_by"],
            f"Design Request Updated: {item.get('title')}",
            f"Status changed to {update['status']} by {current_user['name']}",
        )
    await log_audit(current_user["id"], current_user["name"], "update", "design_request", rid, update)
    out = await db.design_requests.find_one({"id": rid}, {"_id": 0})
    return out


@router.delete("/{rid}")
async def delete_request(rid: str, current_user: dict = Depends(get_current_user)):
    item = await db.design_requests.find_one({"id": rid}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Design request not found")
    role = current_user.get("role")
    if role not in ("CEO", "HR") and item.get("requested_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.design_requests.delete_one({"id": rid})
    await log_audit(current_user["id"], current_user["name"], "delete", "design_request", rid)
    return {"success": True}
