from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, require_role, can_create_user, hash_password, verify_password, log_audit, ROLE_HIERARCHY
import uuid
from datetime import datetime, timezone

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str
    department: Optional[str] = None
    branch_id: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    branch_id: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    new_password: str


@router.get("")
async def list_users(current_user: dict = Depends(get_current_user)):
    # All authenticated users can see the user list (needed for dropdowns)
    users = await db.users.find({"is_active": True}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(1000)
    return users


@router.get("/roles")
async def get_roles(current_user: dict = Depends(get_current_user)):
    roles = []
    for role_name, info in ROLE_HIERARCHY.items():
        roles.append({
            "name": role_name,
            "level": info["level"],
            "department": info["department"],
            "can_create": can_create_user(current_user["role"], role_name)
        })
    return roles


@router.post("")
async def create_user(data: UserCreate, current_user: dict = Depends(get_current_user)):
    role_info = ROLE_HIERARCHY.get(current_user.get("role"), {})
    # Only CEO and HR can create users
    if current_user["role"] not in ["CEO", "HR"]:
        raise HTTPException(status_code=403, detail="Only CEO and HR can manage users")

    if not can_create_user(current_user["role"], data.role):
        raise HTTPException(status_code=403, detail="You don't have permission to create this role")

    email = data.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    target_role_info = ROLE_HIERARCHY.get(data.role)
    if not target_role_info:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "department": data.department or target_role_info["department"],
        "branch_id": data.branch_id,
        "created_by": current_user["id"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    await log_audit(current_user["id"], current_user["name"], "create_user", "user", user_id, {"role": data.role, "name": data.name})

    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    return user_doc


@router.put("/{user_id}")
async def update_user(user_id: str, data: UserUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["CEO", "HR"]:
        raise HTTPException(status_code=403, detail="Only CEO and HR can manage users")

    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    # Validate email uniqueness if changing email
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower().strip()
        existing = await db.users.find_one({"email": update_data["email"], "id": {"$ne": user_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")

    # Validate role change permissions
    if "role" in update_data:
        if not can_create_user(current_user["role"], update_data["role"]):
            raise HTTPException(status_code=403, detail="Cannot assign this role")
        new_role_info = ROLE_HIERARCHY.get(update_data["role"])
        if new_role_info:
            update_data["department"] = update_data.get("department") or new_role_info["department"]

    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await log_audit(current_user["id"], current_user["name"], "update_user", "user", user_id, update_data)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return user


@router.post("/{user_id}/reset-password")
async def reset_password(user_id: str, data: PasswordReset, current_user: dict = Depends(get_current_user)):
    role_info = ROLE_HIERARCHY.get(current_user.get("role"), {})
    level = role_info.get("level", "executor")

    # Only super-level users can reset passwords
    if level not in ["super"]:
        raise HTTPException(status_code=403, detail="Only CEO/HR can reset passwords")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    await log_audit(current_user["id"], current_user["name"], "reset_password", "user", user_id)
    return {"message": "Password reset successful"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    role_info = ROLE_HIERARCHY.get(current_user.get("role"), {})
    level = role_info.get("level", "executor")

    if level not in ["super"]:
        raise HTTPException(status_code=403, detail="Only CEO/HR can delete users")

    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting yourself
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Prevent deleting CEO
    if target.get("role") == "CEO":
        raise HTTPException(status_code=400, detail="Cannot delete the CEO account")

    # Soft delete (deactivate)
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": False}})
    await log_audit(current_user["id"], current_user["name"], "delete_user", "user", user_id, {"name": target.get("name")})
    return {"message": "User deactivated"}
