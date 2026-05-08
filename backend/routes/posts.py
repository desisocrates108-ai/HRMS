from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit
from routes.notifications import create_notification
import uuid, os
from datetime import datetime, timezone

router = APIRouter()


class PostRequest(BaseModel):
    job_id: str
    notes: Optional[str] = None


class PostUpload(BaseModel):
    request_id: str
    file_url: str
    file_name: str
    notes: Optional[str] = None


class PostAction(BaseModel):
    action: str  # job_portal or meta_ads
    assigned_to: Optional[str] = None  # for meta_ads, Marketing Coordinator


# Sr/Jr HR creates a post request for a job
@router.post("/request")
async def create_post_request(data: PostRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["Sr HR", "Jr HR", "HR", "CEO"]:
        raise HTTPException(403, "Only HR can request posts")

    job = await db.jobs.find_one({"id": data.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")

    req_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    req = {
        "id": req_id,
        "job_id": data.job_id,
        "role": job.get("role", ""),
        "department": job.get("type", ""),
        "job_info": f"{job.get('role','')} - {job.get('location','')}",
        "notes": data.notes,
        "requested_by": current_user["id"],
        "requested_by_name": current_user["name"],
        "status": "pending",
        "created_at": now,
    }
    await db.post_requests.insert_one(req)
    req.pop("_id", None)

    # Notify all designers
    designers = await db.users.find({"role": "Graphic Designer", "is_active": True}, {"_id": 0}).to_list(50)
    for d in designers:
        await create_notification(d["id"], "New Post Request", f"{current_user['name']} requested a design for {job.get('role','')} at {job.get('location','')}")

    await log_audit(current_user["id"], current_user["name"], "post_request", "post", req_id, {"job": job.get("role")})
    return req


# Designer sees pending requests
@router.get("/requests")
async def list_post_requests(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["Graphic Designer", "HR", "CEO", "Sr HR", "Jr HR"]:
        raise HTTPException(403, "No access")
    query = {} if current_user["role"] in ["HR", "CEO"] else {}
    requests = await db.post_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return requests


# Designer uploads completed post
@router.post("/upload")
async def upload_post(data: PostUpload, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["Graphic Designer", "HR", "CEO"]:
        raise HTTPException(403, "Only designers can upload posts")

    req = await db.post_requests.find_one({"id": data.request_id}, {"_id": 0})
    if not req:
        raise HTTPException(404, "Request not found")

    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    post = {
        "id": post_id,
        "request_id": data.request_id,
        "job_id": req.get("job_id", ""),
        "role": req.get("role", ""),
        "job_info": req.get("job_info", ""),
        "file_url": data.file_url,
        "file_name": data.file_name,
        "notes": data.notes,
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user["name"],
        "requested_by_name": req.get("requested_by_name", ""),
        "review_status": "pending",
        "action": "none",
        "reviewed_by": None,
        "created_at": now,
    }
    await db.posts.insert_one(post)
    post.pop("_id", None)

    # Update request status
    await db.post_requests.update_one({"id": data.request_id}, {"$set": {"status": "completed"}})

    # Notify HR
    hr_users = await db.users.find({"role": {"$in": ["HR", "CEO", "Sr HR", "Jr HR"]}, "is_active": True}, {"_id": 0}).to_list(50)
    for h in hr_users:
        await create_notification(h["id"], "Post Uploaded", f"{current_user['name']} uploaded design for {req.get('role','')}")

    await log_audit(current_user["id"], current_user["name"], "post_upload", "post", post_id)
    return post


# List all posts (HR + Designer)
@router.get("")
async def list_posts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["Graphic Designer", "HR", "CEO", "Sr HR", "Jr HR"]:
        raise HTTPException(403, "No access")
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return posts


# HR decides action on a post
@router.put("/{post_id}/action")
async def post_action(post_id: str, data: PostAction, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["HR", "CEO"]:
        raise HTTPException(403, "Only HR can decide post actions")
    if data.action not in ["job_portal", "meta_ads"]:
        raise HTTPException(400, "Action must be job_portal or meta_ads")

    post = await db.posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(404, "Post not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.posts.update_one({"id": post_id}, {"$set": {
        "review_status": "approved", "action": data.action, "reviewed_by": current_user["name"]
    }})

    # If meta_ads, create campaign for Marketing Coordinator
    if data.action == "meta_ads":
        job = await db.jobs.find_one({"id": post.get("job_id")}, {"_id": 0})
        assignee = None
        if data.assigned_to:
            assignee = await db.users.find_one({"id": data.assigned_to}, {"_id": 0})
        else:
            assignee = await db.users.find_one({"role": "Marketing Coordinator", "is_active": True}, {"_id": 0})

        campaign_id = str(uuid.uuid4())
        campaign = {
            "id": campaign_id,
            "post_id": post_id,
            "post_file_url": post.get("file_url", ""),
            "post_file_name": post.get("file_name", ""),
            "role": post.get("role", ""),
            "location": job.get("location", "") if job else "",
            "platform": "meta_ads",
            "assigned_to": assignee["id"] if assignee else None,
            "assigned_to_name": assignee["name"] if assignee else "Unassigned",
            "status": "pending",
            "created_by": current_user["id"],
            "created_at": now,
        }
        await db.ad_campaigns.insert_one(campaign)

        if assignee:
            await create_notification(assignee["id"], "New Ad Campaign", f"Run Meta Ads for {post.get('role','')} - design ready")

    await log_audit(current_user["id"], current_user["name"], "post_action", "post", post_id, {"action": data.action})
    return {"message": f"Post sent to {data.action.replace('_',' ')}"}


# File upload for designer
@router.post("/upload-file")
async def upload_design_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 10MB)")
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"post-{uuid.uuid4()}{ext}"
    filepath = os.path.join("uploads", filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return {"file_url": f"/api/uploads/{filename}", "file_name": file.filename}
