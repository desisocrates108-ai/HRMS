from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit, ROLE_HIERARCHY
from routes.notifications import create_notification
import uuid
from datetime import datetime, timezone

router = APIRouter()

MANAGER_ROLES = {"Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager"}
SUPER_ROLES = {"CEO", "HR"}
EXEC_ROLES_ALL = {"Sr HR", "Jr HR", "Marketing Coordinator", "Graphic Designer", "Franchise Executive"}

# Managers can assign to executives in their department; Marketing Coordinator + Designer → Marketing Manager, etc.
MANAGER_DEPT_EXECUTORS = {
    "Marketing Manager": {"Marketing Coordinator", "Graphic Designer"},
    "Operations Manager": {"Franchise Executive"},
    "Sales Manager": set(),
    "Accounts Manager": set(),
}
# Sr/Jr HR can be assigned by CEO/HR only, not managers (shared HR resource)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: str  # now required
    priority: str = "medium"  # low | medium | high | urgent
    due_date: Optional[str] = None
    remarks: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None  # pending | in_progress | completed
    priority: Optional[str] = None
    due_date: Optional[str] = None
    remarks: Optional[str] = None


def _role_level(role: str) -> str:
    return ROLE_HIERARCHY.get(role, {}).get("level", "executor")


def _can_assign(creator: dict, target_role: str) -> bool:
    role = creator.get("role")
    if role in SUPER_ROLES:
        return True  # CEO/HR can assign anyone
    if role in MANAGER_ROLES:
        return target_role in MANAGER_DEPT_EXECUTORS.get(role, set())
    return False  # executives cannot assign


def _compute_status(task: dict) -> str:
    """Add overdue computation based on due_date."""
    if task.get("status") == "completed":
        return "completed"
    if task.get("due_date"):
        try:
            due = datetime.fromisoformat(task["due_date"])
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > due and task.get("status") != "completed":
                return "overdue"
        except Exception:
            pass
    return task.get("status", "pending")


@router.get("")
async def list_tasks(
    scope: Optional[str] = None,  # "my" | "assigned_by_me" | "all"
    status: Optional[str] = None,
    priority: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Task visibility:
    - Executives: auto-restricted to tasks assigned_to them.
    - Managers: can request 'my' (assigned_to them) or 'assigned_by_me'; no all-access.
    - CEO/HR: can request any scope (default: all).
    """
    role = current_user.get("role")
    query = {}

    if role in EXEC_ROLES_ALL:
        query["assigned_to"] = current_user["id"]
    elif role in MANAGER_ROLES:
        if scope == "assigned_by_me":
            query["created_by"] = current_user["id"]
        else:
            # default: my tasks (assigned to me) + tasks I created
            query["$or"] = [{"assigned_to": current_user["id"]}, {"created_by": current_user["id"]}]
    else:  # CEO / HR
        if scope == "my":
            query["assigned_to"] = current_user["id"]
        elif scope == "assigned_by_me":
            query["created_by"] = current_user["id"]
        # else: all

    if status:
        if status == "overdue":
            # computed — fetch all non-completed with past due
            query["status"] = {"$ne": "completed"}
            query["due_date"] = {"$lt": datetime.now(timezone.utc).isoformat()}
        else:
            query["status"] = status
    if priority:
        query["priority"] = priority
    if date_from:
        query.setdefault("created_at", {})["$gte"] = date_from
    if date_to:
        query.setdefault("created_at", {})["$lte"] = date_to

    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    for t in tasks:
        t["status"] = _compute_status(t)
    return tasks


@router.post("")
async def create_task(data: TaskCreate, current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role in EXEC_ROLES_ALL:
        raise HTTPException(status_code=403, detail="Executives cannot assign tasks")

    assignee = await db.users.find_one({"id": data.assigned_to}, {"_id": 0})
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    if not _can_assign(current_user, assignee["role"]):
        raise HTTPException(status_code=403, detail=f"You cannot assign tasks to {assignee['role']}")

    if data.priority not in {"low", "medium", "high", "urgent"}:
        raise HTTPException(status_code=400, detail="Invalid priority")

    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "title": data.title,
        "description": data.description,
        "assigned_to": data.assigned_to,
        "assigned_to_name": assignee["name"],
        "assigned_to_role": assignee["role"],
        "priority": data.priority,
        "due_date": data.due_date,
        "remarks": data.remarks,
        "status": "pending",
        "auto_created": False,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_by_role": current_user["role"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tasks.insert_one(task)
    task.pop("_id", None)

    await create_notification(
        data.assigned_to,
        f"New Task: {data.title}",
        f"Assigned by {current_user['name']} · Priority: {data.priority.upper()}",
    )
    await log_audit(current_user["id"], current_user["name"], "create", "task", task_id, {"title": data.title, "priority": data.priority})
    return task


@router.put("/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    role = current_user.get("role")
    is_owner = task.get("assigned_to") == current_user["id"]
    is_creator = task.get("created_by") == current_user["id"]
    is_super = role in SUPER_ROLES

    if not (is_owner or is_creator or is_super):
        raise HTTPException(status_code=403, detail="Not authorized to update this task")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    # Assignees can ONLY update status + remarks
    if is_owner and not (is_creator or is_super):
        allowed = {"status", "remarks"}
        update_data = {k: v for k, v in update_data.items() if k in allowed}

    if "assigned_to" in update_data and (is_creator or is_super):
        assignee = await db.users.find_one({"id": update_data["assigned_to"]}, {"_id": 0})
        if assignee:
            update_data["assigned_to_name"] = assignee["name"]
            update_data["assigned_to_role"] = assignee["role"]

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if update_data.get("status") == "completed":
        update_data["completed_at"] = update_data["updated_at"]

    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    await log_audit(current_user["id"], current_user["name"], "update", "task", task_id, update_data)

    # Notify creator when assignee updates status
    if is_owner and "status" in update_data and task.get("created_by") and task["created_by"] != current_user["id"]:
        await create_notification(
            task["created_by"],
            f"Task Update: {task['title']}",
            f"{current_user['name']} marked as {update_data['status']}",
        )

    out = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    out["status"] = _compute_status(out)
    return out


@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    role = current_user.get("role")
    if role not in SUPER_ROLES and task.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    await db.tasks.delete_one({"id": task_id})
    await log_audit(current_user["id"], current_user["name"], "delete", "task", task_id)
    return {"message": "Task deleted"}


@router.get("/assignable-users")
async def get_assignable_users(current_user: dict = Depends(get_current_user)):
    """Return users the current user can assign tasks to."""
    role = current_user.get("role")
    if role in SUPER_ROLES:
        users = await db.users.find({"is_active": True, "id": {"$ne": current_user["id"]}}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(200)
    elif role in MANAGER_ROLES:
        targets = list(MANAGER_DEPT_EXECUTORS.get(role, set()))
        if not targets:
            return []
        users = await db.users.find({"role": {"$in": targets}, "is_active": True}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(200)
    else:
        users = []
    return users
