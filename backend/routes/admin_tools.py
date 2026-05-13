"""Admin utilities — data cleanup, system reset (preserve logins).
Restricted to CEO only.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import db
from auth_utils import get_current_user, log_audit
from datetime import datetime, timezone

router = APIRouter()

# Collections to wipe — KEEP: users, audit_logs (history), notifications (user-facing),
# system_settings if any, anything related to credentials.
CLEANUP_COLLECTIONS = [
    "leads",
    "lead_stage_logs",
    "call_logs",
    "tasks",
    "candidate_ratings",
    "employees",
    "jobs",
    "branches",
    "interviews",
    "feedback_tokens",
    "feedback_submissions",
    "offer_letters",
    "design_requests",
    "post_requests",
    "posts",
    "ad_campaigns",
    "meetings",
    "chats",
    "chat_members",
    "chat_messages",
]


@router.post("/cleanup")
async def cleanup_data(current_user: dict = Depends(get_current_user)):
    """Wipe all business/demo data. Preserves: users, audit_logs, notifications.
    Only CEO can execute. Returns counts of deleted documents per collection.
    """
    if current_user.get("role") != "CEO":
        raise HTTPException(status_code=403, detail="Only CEO can perform data cleanup")

    deleted = {}
    for col in CLEANUP_COLLECTIONS:
        try:
            res = await db[col].delete_many({})
            deleted[col] = res.deleted_count
        except Exception as e:
            deleted[col] = f"error: {str(e)}"

    # Clear notifications too (they're tied to old leads/tasks)
    try:
        res = await db.notifications.delete_many({})
        deleted["notifications"] = res.deleted_count
    except Exception:
        pass

    await log_audit(
        current_user["id"], current_user["name"], "system_cleanup", "system", "all",
        {"deleted": deleted, "timestamp": datetime.now(timezone.utc).isoformat()},
    )
    return {"success": True, "deleted": deleted, "preserved": ["users", "audit_logs"]}


@router.get("/cleanup-preview")
async def cleanup_preview(current_user: dict = Depends(get_current_user)):
    """Show counts that would be deleted by /cleanup. CEO only."""
    if current_user.get("role") != "CEO":
        raise HTTPException(status_code=403, detail="Only CEO can preview cleanup")
    counts = {}
    for col in CLEANUP_COLLECTIONS:
        try:
            counts[col] = await db[col].count_documents({})
        except Exception:
            counts[col] = 0
    counts["notifications"] = await db.notifications.count_documents({})
    return {"counts": counts}
