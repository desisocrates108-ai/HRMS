from fastapi import APIRouter, Depends
from database import db
from auth_utils import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifs = await db.notifications.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return notifs


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": current_user["id"], "read": False})
    return {"count": count}


@router.put("/{notif_id}/read")
async def mark_read(notif_id: str, current_user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notif_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}


@router.put("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All marked as read"}


async def create_notification(user_id: str, title: str, message: str):
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
