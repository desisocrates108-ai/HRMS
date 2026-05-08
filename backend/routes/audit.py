from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import db
from auth_utils import get_current_user, require_role

router = APIRouter()


@router.get("")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(require_role("super"))
):
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs
