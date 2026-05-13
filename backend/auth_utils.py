import bcrypt
import jwt
import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends
from database import db

JWT_ALGORITHM = "HS256"

ROLE_HIERARCHY = {
    "CEO": {"level": "super", "rank": 1, "department": "Management"},
    "HR": {"level": "super", "rank": 2, "department": "HR"},
    "Marketing Manager": {"level": "manager", "rank": 4, "department": "Marketing"},
    "Operations Manager": {"level": "manager", "rank": 4, "department": "Operations"},
    "Sales Manager": {"level": "manager", "rank": 4, "department": "Sales"},
    "Accounts Manager": {"level": "manager", "rank": 4, "department": "Accounts"},
    "Sr HR": {"level": "executor", "rank": 5, "department": "HR"},
    "Jr HR": {"level": "executor", "rank": 5, "department": "HR"},
    "Marketing Coordinator": {"level": "executor", "rank": 6, "department": "Marketing"},
    "Graphic Designer": {"level": "executor", "rank": 6, "department": "Marketing"},
    "Franchise Executive": {"level": "executor", "rank": 6, "department": "Franchise Development"},
}

CEO_HR_ROLES = ["CEO", "HR"]

# PIPELINE MODEL (Feb 2026 restructure — added three_months stage)
# Head Office: new_lead → qualified → hr_interview → manager_interview → selected → three_months → joined
# Franchise:    new_lead → qualified → hr_interview → selected → three_months → joined
# Parallel:    hold, rejected (can be entered from any active stage)
HO_LINEAR_STAGES = ["new_lead", "qualified", "hr_interview", "manager_interview", "selected", "three_months", "joined"]
TECH_LINEAR_STAGES = ["new_lead", "qualified", "hr_interview", "selected", "three_months", "joined"]
PARALLEL_STAGES = ["hold", "rejected"]

# All stages (union)
PIPELINE_STAGES = list(dict.fromkeys(HO_LINEAR_STAGES + TECH_LINEAR_STAGES + PARALLEL_STAGES))

STAGE_LABELS = {
    "new_lead": "New",
    "qualified": "Qualified",
    "hr_interview": "HR",
    "manager_interview": "Manager",
    "selected": "Selected",
    "three_months": "3 Months",
    "joined": "Joined",
    "hold": "Hold",
    "rejected": "Rejected",
    # legacy aliases (read-only display only)
    "move_ahead": "Selected",
    "dead": "Rejected",
}

# Form field requirements per target stage
STAGE_FORM_REQUIREMENTS = {
    "qualified": ["experience", "location_confirmation", "salary_expectation", "relocation_preference"],
    "hr_interview": ["interview_date", "interview_time", "mode", "interview_city", "interview_place"],
    "manager_interview": ["interview_date", "interview_time", "mode", "interview_city", "interview_place", "manager_id"],
    "selected": [],
    "three_months": [],
    "hold": ["hold_reason"],
    "joined": [],
    "rejected": ["rejection_reason"],
}

# Interview round criteria (10 each) — used by interviews.py
HR_ROUND_CRITERIA = [
    "communication_skills",
    "confidence",
    "attitude",
    "basic_understanding",
    "learning_ability",
    "stability",
    "salary_expectation_fit",
    "cultural_fit",
    "availability",
    "overall_impression",
]

MANAGER_ROUND_CRITERIA = [
    "technical_skills",
    "problem_solving",
    "role_knowledge",
    "practical_exposure",
    "decision_making",
    "ownership",
    "team_fit",
    "pressure_handling",
    "growth_potential",
    "final_recommendation",
]

HR_CRITERIA_LABELS = {
    "communication_skills": "Communication Skills",
    "confidence": "Confidence",
    "attitude": "Attitude",
    "basic_understanding": "Basic Understanding",
    "learning_ability": "Learning Ability",
    "stability": "Stability (Job Hopping Check)",
    "salary_expectation_fit": "Salary Expectation Fit",
    "cultural_fit": "Cultural Fit",
    "availability": "Availability / Joining Timeline",
    "overall_impression": "Overall Impression",
}

MANAGER_CRITERIA_LABELS = {
    "technical_skills": "Technical Skills",
    "problem_solving": "Problem Solving",
    "role_knowledge": "Role Knowledge",
    "practical_exposure": "Practical Exposure",
    "decision_making": "Decision Making",
    "ownership": "Ownership",
    "team_fit": "Team Fit",
    "pressure_handling": "Pressure Handling",
    "growth_potential": "Growth Potential",
    "final_recommendation": "Final Recommendation",
}


def get_pipeline_stages(is_technician: bool):
    return TECH_LINEAR_STAGES if is_technician else HO_LINEAR_STAGES


def get_stage_order(is_technician: bool):
    stages = get_pipeline_stages(is_technician)
    return {s: i for i, s in enumerate(stages)}


def get_jwt_secret():
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24), "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*allowed_roles_or_levels):
    async def check_role(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "")
        role_info = ROLE_HIERARCHY.get(user_role, {})
        user_level = role_info.get("level", "")
        if user_role not in allowed_roles_or_levels and user_level not in allowed_roles_or_levels:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return check_role


def can_create_user(creator_role: str, target_role: str) -> bool:
    creator_info = ROLE_HIERARCHY.get(creator_role)
    target_info = ROLE_HIERARCHY.get(target_role)
    if not creator_info or not target_info:
        return False
    if creator_info["level"] == "executor":
        return False
    if creator_role == "CEO":
        return True
    if creator_role == "HR":
        return target_role != "CEO"
    if creator_info["level"] == "manager":
        return target_info["level"] == "executor" and target_info["department"] == creator_info["department"]
    return False


def get_dashboard_type(role):
    if role == "CEO":
        return "ceo"
    if role == "HR":
        return "hr"
    if ROLE_HIERARCHY.get(role, {}).get("level") == "manager":
        return "manager"
    if role in ["Sr HR", "Jr HR"]:
        return "sr_jr_hr"
    if role == "Franchise Executive":
        return "fde"
    if role == "Graphic Designer":
        return "designer"
    if role == "Marketing Coordinator":
        return "mktg_coord"
    return "executor"


async def log_audit(user_id, user_name, action, entity_type, entity_id, details=None):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_name": user_name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
