from fastapi import APIRouter, Depends
from database import db
from auth_utils import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter()


@router.post("/create")
async def create_meeting(current_user: dict = Depends(get_current_user)):
    meeting_id = str(uuid.uuid4())[:8]
    meeting_url = f"https://meet.jit.si/servall-{meeting_id}"
    now = datetime.now(timezone.utc).isoformat()
    meeting = {
        "id": str(uuid.uuid4()),
        "meeting_id": meeting_id,
        "meeting_url": meeting_url,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": now,
    }
    await db.meetings.insert_one(meeting)
    meeting.pop("_id", None)
    return meeting


@router.get("/recent")
async def recent_meetings(current_user: dict = Depends(get_current_user)):
    meetings = await db.meetings.find({}, {"_id": 0}).sort("created_at", -1).to_list(10)
    return meetings
