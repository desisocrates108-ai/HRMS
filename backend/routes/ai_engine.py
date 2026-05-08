from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database import db
from auth_utils import get_current_user, log_audit
import os
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_ai_recommendation(job, candidates):
    """Get AI-powered candidate recommendations using GPT-5.2"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return {"error": "AI service not configured", "candidates": candidates[:5]}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"job-recommend-{job['id']}",
            system_message=(
                "You are a hiring recommendation engine for Servall, a two-wheeler servicing company. "
                "Analyze candidates and recommend the best matches for the given job. "
                "Consider location proximity, rating, experience, and past performance. "
                "Return your response as valid JSON with this structure: "
                '{"recommendations": [{"lead_id": "...", "name": "...", "score": 0-100, "reasoning": "..."}], "summary": "..."}'
            )
        ).with_model("openai", "gpt-5.2")

        candidates_info = []
        for c in candidates[:20]:
            candidates_info.append({
                "lead_id": c.get("lead_id", ""),
                "name": c.get("lead_name", ""),
                "rating": c.get("final_rating", 0),
                "interview_score": c.get("interview_score", 0),
                "experience_years": c.get("experience_years", 0),
                "location_city": c.get("location_city", ""),
                "location_area": c.get("location_area", ""),
                "skills": c.get("skills", [])
            })

        prompt = (
            f"Job Details:\n"
            f"- Role: {job.get('role', 'N/A')}\n"
            f"- Type: {job.get('type', 'N/A')}\n"
            f"- Location: {job.get('location', 'N/A')}\n"
            f"- Salary Range: {job.get('salary_range_min', 'N/A')} - {job.get('salary_range_max', 'N/A')}\n\n"
            f"Available Candidates:\n{json.dumps(candidates_info, indent=2)}\n\n"
            f"Recommend top candidates for this job. Rank them by suitability."
        )

        response = await chat.send_message(UserMessage(text=prompt))

        try:
            # Try to parse as JSON
            response_text = str(response)
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response_text[start:end])
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        return {"summary": str(response), "recommendations": []}

    except Exception as e:
        logger.error(f"AI recommendation error: {e}")
        return {"error": str(e), "recommendations": []}


@router.post("/recommend/{job_id}")
async def recommend_candidates(job_id: str, current_user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get candidate ratings sorted by final_rating
    candidates = await db.candidate_ratings.find({}, {"_id": 0}).sort("final_rating", -1).to_list(50)

    if not candidates:
        return {"recommendations": [], "summary": "No rated candidates found in the system yet."}

    result = await get_ai_recommendation(job, candidates)
    await log_audit(current_user["id"], current_user["name"], "ai_recommend", "job", job_id)
    return result


@router.get("/search")
async def search_candidates(
    city: Optional[str] = None,
    area: Optional[str] = None,
    min_rating: Optional[float] = None,
    sort_by: str = "rating",
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if city:
        query["location_city"] = {"$regex": city, "$options": "i"}
    if area:
        query["location_area"] = {"$regex": area, "$options": "i"}
    if min_rating:
        query["final_rating"] = {"$gte": min_rating}

    sort_field = "final_rating" if sort_by == "rating" else "created_at"
    sort_dir = -1

    candidates = await db.candidate_ratings.find(query, {"_id": 0}).sort(sort_field, sort_dir).to_list(100)

    # Enrich with lead data
    for candidate in candidates:
        lead = await db.leads.find_one({"id": candidate.get("lead_id")}, {"_id": 0, "name": 1, "phone": 1, "current_stage": 1})
        if lead:
            candidate["phone"] = lead.get("phone", "")
            candidate["current_stage"] = lead.get("current_stage", "")

    return candidates


@router.get("/top-rated")
async def top_rated_candidates(limit: int = 10, current_user: dict = Depends(get_current_user)):
    candidates = await db.candidate_ratings.find({}, {"_id": 0}).sort("final_rating", -1).to_list(limit)
    return candidates
