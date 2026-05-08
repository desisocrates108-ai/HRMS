from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from database import db
from auth_utils import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    get_current_user, get_jwt_secret, JWT_ALGORITHM, log_audit
)
import jwt
import uuid
import os
from datetime import datetime, timezone

router = APIRouter()


class LoginInput(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(input_data: LoginInput):
    email = input_data.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(input_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")

    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])

    user_data = {k: v for k, v in user.items() if k != "password_hash"}
    await log_audit(user["id"], user["name"], "login", "user", user["id"])
    return {"user": user_data, "access_token": access_token, "refresh_token": refresh_token}


@router.post("/logout")
async def logout():
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/refresh")
async def refresh(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("refresh_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access_token = create_access_token(user["id"], user["email"])
        return {"access_token": access_token, "message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@servall.com").lower().strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "ServallAdmin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Admin (CEO)",
            "role": "CEO",
            "department": "Management",
            "branch_id": None,
            "created_by": None,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
