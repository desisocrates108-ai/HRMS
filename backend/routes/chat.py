from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from database import db
from auth_utils import get_current_user, log_audit, ROLE_HIERARCHY
import uuid
import os
import shutil
from datetime import datetime, timezone, timedelta

router = APIRouter()

CHAT_ALLOWED_ROLES = list(ROLE_HIERARCHY.keys())  # All roles have chat access

EDIT_TIME_LIMIT_MINUTES = 15


async def require_chat_access(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in CHAT_ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Chat access is not available for your role")
    return current_user


async def verify_chat_member(chat_id: str, user: dict):
    """Check user is a member of chat, or is CEO (can monitor all)."""
    if user["role"] == "CEO":
        return True
    member = await db.chat_members.find_one({"chat_id": chat_id, "user_id": user["id"]})
    return member is not None


async def get_member_permission(chat_id: str, user_id: str):
    member = await db.chat_members.find_one({"chat_id": chat_id, "user_id": user_id}, {"_id": 0})
    return member


# ==================== MODELS ====================

class CreateChat(BaseModel):
    user_ids: List[str]
    name: Optional[str] = None


class AddMember(BaseModel):
    user_id: str
    permission: str = "can_reply"  # can_reply or view_only
    show_history: bool = True


class UpdatePermission(BaseModel):
    permission: str


class SendMessage(BaseModel):
    text: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None


class EditMessage(BaseModel):
    text: str


# ==================== CHAT CRUD ====================

@router.post("")
async def create_chat(data: CreateChat, current_user: dict = Depends(require_chat_access)):
    if not data.user_ids:
        raise HTTPException(400, "At least one user must be added")

    # Verify all users exist and have chat access
    for uid in data.user_ids:
        u = await db.users.find_one({"id": uid}, {"_id": 0})
        if not u:
            raise HTTPException(400, f"User {uid} not found")
        if u["role"] not in CHAT_ALLOWED_ROLES:
            raise HTTPException(400, f"User {u['name']} does not have chat access")

    chat_type = "direct" if len(data.user_ids) == 1 else "group"

    # For direct chats, check if one already exists
    if chat_type == "direct":
        other_id = data.user_ids[0]
        existing = await db.chats.find_one({"type": "direct"}, {"_id": 0})
        if existing:
            # Check if both users are members
            m1 = await db.chat_members.find_one({"chat_id": existing["id"], "user_id": current_user["id"]})
            m2 = await db.chat_members.find_one({"chat_id": existing["id"], "user_id": other_id})
            if m1 and m2:
                return existing
        # Actually, need a better check - find all direct chats the user is in
        my_direct_chats = await db.chat_members.find({"user_id": current_user["id"]}).to_list(500)
        for mc in my_direct_chats:
            chat = await db.chats.find_one({"id": mc["chat_id"], "type": "direct"}, {"_id": 0})
            if chat:
                other_member = await db.chat_members.find_one({"chat_id": chat["id"], "user_id": other_id})
                if other_member:
                    return chat

    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Generate name for direct chats
    chat_name = data.name
    if chat_type == "direct":
        other = await db.users.find_one({"id": data.user_ids[0]}, {"_id": 0})
        chat_name = None  # Will be resolved on frontend

    chat = {
        "id": chat_id,
        "type": chat_type,
        "name": chat_name,
        "created_by": current_user["id"],
        "created_at": now,
        "last_message": None,
    }
    await db.chats.insert_one(chat)
    chat.pop("_id", None)

    # Add creator as member
    await db.chat_members.insert_one({
        "id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_role": current_user["role"],
        "permission": "can_reply",
        "show_history": True,
        "joined_at": now,
        "added_by": current_user["id"],
    })

    # Add other members
    for uid in data.user_ids:
        u = await db.users.find_one({"id": uid}, {"_id": 0})
        await db.chat_members.insert_one({
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "user_id": uid,
            "user_name": u["name"],
            "user_role": u["role"],
            "permission": "can_reply",
            "show_history": True,
            "joined_at": now,
            "added_by": current_user["id"],
        })

    # System message
    member_names = []
    for uid in data.user_ids:
        u = await db.users.find_one({"id": uid}, {"_id": 0})
        member_names.append(u["name"])
    await db.messages.insert_one({
        "id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "sender_id": "system",
        "sender_name": "System",
        "type": "system",
        "text": f"{current_user['name']} created the chat with {', '.join(member_names)}",
        "file_url": None, "file_name": None,
        "is_edited": False, "is_deleted": False,
        "created_at": now, "edited_at": None,
    })

    await log_audit(current_user["id"], current_user["name"], "create_chat", "chat", chat_id)
    return chat


@router.get("")
async def list_chats(current_user: dict = Depends(require_chat_access)):
    # Get chats the user is a member of
    memberships = await db.chat_members.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(500)
    chat_ids = [m["chat_id"] for m in memberships]

    chats = []
    for cid in chat_ids:
        chat = await db.chats.find_one({"id": cid}, {"_id": 0})
        if not chat:
            continue
        # For direct chats, resolve the other user's name
        if chat["type"] == "direct":
            other = await db.chat_members.find_one(
                {"chat_id": cid, "user_id": {"$ne": current_user["id"]}}, {"_id": 0}
            )
            chat["display_name"] = other["user_name"] if other else "Unknown"
        else:
            chat["display_name"] = chat.get("name") or "Group Chat"

        # Get member count
        chat["member_count"] = await db.chat_members.count_documents({"chat_id": cid})

        # Unread indicator: get last message
        last_msg = await db.messages.find(
            {"chat_id": cid, "is_deleted": False}, {"_id": 0}
        ).sort("created_at", -1).to_list(1)
        if last_msg:
            chat["last_message"] = {
                "text": last_msg[0].get("text", ""),
                "sender_name": last_msg[0].get("sender_name", ""),
                "timestamp": last_msg[0].get("created_at", ""),
                "type": last_msg[0].get("type", "text"),
            }
        chats.append(chat)

    # Sort by last message timestamp
    chats.sort(key=lambda c: c.get("last_message", {}).get("timestamp", "") or "", reverse=True)
    return chats


@router.get("/eligible-users")
async def get_eligible_users(current_user: dict = Depends(require_chat_access)):
    users = await db.users.find(
        {"role": {"$in": CHAT_ALLOWED_ROLES}, "is_active": True, "id": {"$ne": current_user["id"]}},
        {"_id": 0, "password_hash": 0}
    ).to_list(500)
    return users


@router.get("/monitor")
async def monitor_chats(current_user: dict = Depends(require_chat_access)):
    if current_user["role"] != "CEO":
        raise HTTPException(403, "Only CEO can monitor chats")
    chats = await db.chats.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for chat in chats:
        chat["member_count"] = await db.chat_members.count_documents({"chat_id": chat["id"]})
        members = await db.chat_members.find({"chat_id": chat["id"]}, {"_id": 0}).to_list(50)
        chat["members"] = members
        msg_count = await db.messages.count_documents({"chat_id": chat["id"]})
        chat["message_count"] = msg_count
        if chat["type"] == "direct":
            names = [m["user_name"] for m in members]
            chat["display_name"] = " & ".join(names)
        else:
            chat["display_name"] = chat.get("name") or "Group Chat"
    return chats


@router.get("/poll")
async def poll_messages(since: str, current_user: dict = Depends(require_chat_access)):
    # Get user's chat IDs
    memberships = await db.chat_members.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(500)
    chat_ids = [m["chat_id"] for m in memberships]

    if not chat_ids:
        return {"messages": []}

    new_messages = await db.messages.find(
        {"chat_id": {"$in": chat_ids}, "created_at": {"$gt": since}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)

    return {"messages": new_messages}


@router.get("/{chat_id}")
async def get_chat(chat_id: str, current_user: dict = Depends(require_chat_access)):
    if not await verify_chat_member(chat_id, current_user):
        raise HTTPException(403, "Not a member of this chat")

    chat = await db.chats.find_one({"id": chat_id}, {"_id": 0})
    if not chat:
        raise HTTPException(404, "Chat not found")

    members = await db.chat_members.find({"chat_id": chat_id}, {"_id": 0}).to_list(50)
    chat["members"] = members

    if chat["type"] == "direct":
        other = next((m for m in members if m["user_id"] != current_user["id"]), None)
        chat["display_name"] = other["user_name"] if other else "Unknown"
    else:
        chat["display_name"] = chat.get("name") or "Group Chat"

    # Get current user's membership info
    my_membership = next((m for m in members if m["user_id"] == current_user["id"]), None)
    chat["my_permission"] = my_membership["permission"] if my_membership else "can_reply"
    chat["my_show_history"] = my_membership["show_history"] if my_membership else True

    return chat


# ==================== MEMBERS ====================

@router.post("/{chat_id}/members")
async def add_member(chat_id: str, data: AddMember, current_user: dict = Depends(require_chat_access)):
    if not await verify_chat_member(chat_id, current_user):
        raise HTTPException(403, "Not a member of this chat")

    # Check target user
    target = await db.users.find_one({"id": data.user_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "User not found")
    if target["role"] not in CHAT_ALLOWED_ROLES:
        raise HTTPException(400, f"{target['name']} does not have chat access")

    # Check not already member
    existing = await db.chat_members.find_one({"chat_id": chat_id, "user_id": data.user_id})
    if existing:
        raise HTTPException(400, "User is already a member")

    if data.permission not in ["can_reply", "view_only"]:
        raise HTTPException(400, "Permission must be 'can_reply' or 'view_only'")

    now = datetime.now(timezone.utc).isoformat()
    await db.chat_members.insert_one({
        "id": str(uuid.uuid4()),
        "chat_id": chat_id,
        "user_id": data.user_id,
        "user_name": target["name"],
        "user_role": target["role"],
        "permission": data.permission,
        "show_history": data.show_history,
        "joined_at": now,
        "added_by": current_user["id"],
    })

    # Update chat type to group if needed
    member_count = await db.chat_members.count_documents({"chat_id": chat_id})
    if member_count > 2:
        await db.chats.update_one({"id": chat_id}, {"$set": {"type": "group"}})

    # System message
    perm_text = "with reply access" if data.permission == "can_reply" else "as view-only"
    history_text = "with full history" if data.show_history else "seeing new messages only"
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "chat_id": chat_id,
        "sender_id": "system", "sender_name": "System", "type": "system",
        "text": f"{current_user['name']} added {target['name']} {perm_text} ({history_text})",
        "file_url": None, "file_name": None,
        "is_edited": False, "is_deleted": False,
        "created_at": now, "edited_at": None,
    })

    await log_audit(current_user["id"], current_user["name"], "add_chat_member", "chat", chat_id,
                    {"added_user": target["name"], "permission": data.permission, "show_history": data.show_history})
    return {"message": f"{target['name']} added to chat"}


@router.put("/{chat_id}/members/{user_id}")
async def update_member_permission(chat_id: str, user_id: str, data: UpdatePermission, current_user: dict = Depends(require_chat_access)):
    if not await verify_chat_member(chat_id, current_user):
        raise HTTPException(403, "Not a member of this chat")
    if data.permission not in ["can_reply", "view_only"]:
        raise HTTPException(400, "Permission must be 'can_reply' or 'view_only'")

    result = await db.chat_members.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"permission": data.permission}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Member not found")

    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    now = datetime.now(timezone.utc).isoformat()
    await db.messages.insert_one({
        "id": str(uuid.uuid4()), "chat_id": chat_id,
        "sender_id": "system", "sender_name": "System", "type": "system",
        "text": f"{current_user['name']} changed {target['name']}'s permission to {data.permission.replace('_', ' ')}",
        "file_url": None, "file_name": None,
        "is_edited": False, "is_deleted": False,
        "created_at": now, "edited_at": None,
    })

    await log_audit(current_user["id"], current_user["name"], "update_chat_permission", "chat", chat_id,
                    {"user": target["name"], "permission": data.permission})
    return {"message": "Permission updated"}


# ==================== MESSAGES ====================

@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 100, before: Optional[str] = None, current_user: dict = Depends(require_chat_access)):
    if not await verify_chat_member(chat_id, current_user):
        raise HTTPException(403, "Not a member of this chat")

    # Get member's show_history setting
    membership = await db.chat_members.find_one({"chat_id": chat_id, "user_id": current_user["id"]}, {"_id": 0})

    query = {"chat_id": chat_id}

    # If not showing history, only show messages after join date
    if membership and not membership.get("show_history", True):
        query["created_at"] = {"$gte": membership["joined_at"]}

    if before:
        if "created_at" in query:
            query["created_at"]["$lt"] = before
        else:
            query["created_at"] = {"$lt": before}

    messages = await db.messages.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    messages.reverse()  # Oldest first
    return messages


@router.post("/{chat_id}/messages")
async def send_message(chat_id: str, data: SendMessage, current_user: dict = Depends(require_chat_access)):
    membership = await get_member_permission(chat_id, current_user["id"])
    if not membership and current_user["role"] != "CEO":
        raise HTTPException(403, "Not a member of this chat")
    if membership and membership.get("permission") == "view_only":
        raise HTTPException(403, "You have view-only access to this chat")

    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())
    msg_type = "file" if data.file_url else "text"

    message = {
        "id": msg_id,
        "chat_id": chat_id,
        "sender_id": current_user["id"],
        "sender_name": current_user["name"],
        "type": msg_type,
        "text": data.text,
        "file_url": data.file_url,
        "file_name": data.file_name,
        "is_edited": False,
        "is_deleted": False,
        "created_at": now,
        "edited_at": None,
    }
    await db.messages.insert_one(message)
    message.pop("_id", None)

    # Update chat's last message
    await db.chats.update_one({"id": chat_id}, {"$set": {
        "last_message": {"text": data.text[:80], "sender_name": current_user["name"], "timestamp": now, "type": msg_type}
    }})

    return message


@router.put("/{chat_id}/messages/{msg_id}")
async def edit_message(chat_id: str, msg_id: str, data: EditMessage, current_user: dict = Depends(require_chat_access)):
    message = await db.messages.find_one({"id": msg_id, "chat_id": chat_id}, {"_id": 0})
    if not message:
        raise HTTPException(404, "Message not found")
    if message["sender_id"] != current_user["id"]:
        raise HTTPException(403, "Can only edit your own messages")
    if message.get("is_deleted"):
        raise HTTPException(400, "Cannot edit a deleted message")

    created = datetime.fromisoformat(message["created_at"])
    if datetime.now(timezone.utc) - created > timedelta(minutes=EDIT_TIME_LIMIT_MINUTES):
        raise HTTPException(400, f"Edit time limit exceeded ({EDIT_TIME_LIMIT_MINUTES} minutes)")

    now = datetime.now(timezone.utc).isoformat()
    await db.messages.update_one(
        {"id": msg_id},
        {"$set": {"text": data.text, "is_edited": True, "edited_at": now}}
    )
    await log_audit(current_user["id"], current_user["name"], "edit_message", "message", msg_id,
                    {"chat_id": chat_id, "old_text": message["text"][:50], "new_text": data.text[:50]})

    updated = await db.messages.find_one({"id": msg_id}, {"_id": 0})
    return updated


@router.delete("/{chat_id}/messages/{msg_id}")
async def delete_message(chat_id: str, msg_id: str, current_user: dict = Depends(require_chat_access)):
    message = await db.messages.find_one({"id": msg_id, "chat_id": chat_id}, {"_id": 0})
    if not message:
        raise HTTPException(404, "Message not found")
    # Only sender or CEO can delete
    if message["sender_id"] != current_user["id"] and current_user["role"] != "CEO":
        raise HTTPException(403, "Can only delete your own messages")

    now = datetime.now(timezone.utc).isoformat()
    await db.messages.update_one(
        {"id": msg_id},
        {"$set": {"is_deleted": True, "text": "This message was deleted", "edited_at": now}}
    )
    await log_audit(current_user["id"], current_user["name"], "delete_message", "message", msg_id,
                    {"chat_id": chat_id, "original_text": message["text"][:80]})
    return {"message": "Message deleted"}


# ==================== FILE UPLOAD ====================

@router.post("/{chat_id}/upload")
async def upload_file(chat_id: str, file: UploadFile = File(...), current_user: dict = Depends(require_chat_access)):
    membership = await get_member_permission(chat_id, current_user["id"])
    if not membership and current_user["role"] != "CEO":
        raise HTTPException(403, "Not a member of this chat")
    if membership and membership.get("permission") == "view_only":
        raise HTTPException(403, "View-only access")

    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")

    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as f:
        f.write(content)

    file_url = f"/api/uploads/{filename}"
    return {"file_url": file_url, "file_name": file.filename}
