from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import os
import logging

from routes.auth import router as auth_router, seed_admin
from routes.branches import router as branches_router
from routes.jobs import router as jobs_router
from routes.leads import router as leads_router
from routes.tasks import router as tasks_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router
from routes.ai_engine import router as ai_router
from routes.employees import router as employees_router
from routes.audit import router as audit_router
from routes.chat import router as chat_router
from routes.notifications import router as notifications_router
from routes.posts import router as posts_router
from routes.campaigns import router as campaigns_router
from routes.meetings import router as meetings_router
from routes.interviews import router as interviews_router
from routes.feedback import router as feedback_router
from routes.analytics import router as analytics_router
from database import client, db

app = FastAPI(title="Servall Hiring OS", redirect_slashes=False)

# API router with /api prefix
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(branches_router, prefix="/branches", tags=["Branches"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(leads_router, prefix="/leads", tags=["Leads"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(ai_router, prefix="/ai", tags=["AI Engine"])
api_router.include_router(employees_router, prefix="/employees", tags=["Employees"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(posts_router, prefix="/posts", tags=["Posts"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(meetings_router, prefix="/meetings", tags=["Meetings"])
api_router.include_router(interviews_router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])


@api_router.get("/")
async def root():
    return {"message": "Servall Hiring OS API"}


@api_router.get("/notifications")
async def get_notifications():
    from auth_utils import get_current_user
    return []


app.include_router(api_router)

# Serve uploaded files
from fastapi.staticfiles import StaticFiles
import os
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# CORS - allow all origins since we use Bearer token auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    logger.info("Starting Servall Hiring OS...")
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.branches.create_index("id", unique=True)
    await db.jobs.create_index("id", unique=True)
    await db.leads.create_index("id", unique=True)
    await db.leads.create_index("current_stage")
    await db.leads.create_index("assigned_to")
    await db.tasks.create_index("id", unique=True)
    await db.tasks.create_index("assigned_to")
    await db.employees.create_index("id", unique=True)
    await db.candidate_ratings.create_index("lead_id")
    await db.candidate_ratings.create_index("final_rating")
    await db.audit_logs.create_index("timestamp")
    await db.lead_stage_logs.create_index("lead_id")
    await db.call_logs.create_index("lead_id")
    await db.notifications.create_index("user_id")
    await db.post_requests.create_index("status")
    await db.posts.create_index("review_status")
    await db.ad_campaigns.create_index("assigned_to")
    await db.meetings.create_index("created_at")
    await db.interviews.create_index([("lead_id", 1), ("round", 1)], unique=True)
    await db.interviews.create_index("submitted_by")
    await db.feedback_tokens.create_index("token", unique=True)
    await db.feedback_tokens.create_index("subject_id")
    await db.feedback_submissions.create_index("token", unique=True)
    await db.feedback_submissions.create_index("kind")

    # Seed admin
    await seed_admin()
    logger.info("Servall Hiring OS started successfully")


@app.on_event("shutdown")
async def shutdown():
    client.close()
