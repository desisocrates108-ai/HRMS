from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import db
from auth_utils import get_current_user, ROLE_HIERARCHY, PIPELINE_STAGES, STAGE_LABELS, CEO_HR_ROLES, get_dashboard_type
from routes.notifications import create_notification
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()


async def enrich_leads(leads):
    if not leads:
        return leads
    lead_ids = [l["id"] for l in leads]
    assigned_ids = list(set(l.get("assigned_to") for l in leads if l.get("assigned_to")))
    job_ids = list(set(l.get("job_id") for l in leads if l.get("job_id")))

    all_logs = await db.lead_stage_logs.find({"lead_id": {"$in": lead_ids}}, {"_id": 0}).to_list(10000)
    logs_by_lead = {}
    for log in all_logs:
        logs_by_lead.setdefault(log["lead_id"], []).append(log)

    user_map = {}
    if assigned_ids:
        users = await db.users.find({"id": {"$in": assigned_ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(500)
        user_map = {u["id"]: u for u in users}

    job_map = {}
    if job_ids:
        jobs = await db.jobs.find({"id": {"$in": job_ids}}, {"_id": 0}).to_list(500)
        job_map = {j["id"]: j for j in jobs}

    branch_ids = list(set(j.get("branch_id") for j in job_map.values() if j.get("branch_id")))
    branch_map = {}
    if branch_ids:
        branches = await db.branches.find({"id": {"$in": branch_ids}}, {"_id": 0}).to_list(100)
        branch_map = {b["id"]: b for b in branches}

    for lead in leads:
        lid = lead["id"]
        lead_logs = logs_by_lead.get(lid, [])
        qualified = next((l for l in lead_logs if l.get("to_stage") == "qualified"), None)
        lead["experience"] = qualified["form_data"].get("experience", "") if qualified and qualified.get("form_data") else ""
        lead["salary_expectation"] = qualified["form_data"].get("salary_expectation", "") if qualified and qualified.get("form_data") else ""
        interview = next((l for l in lead_logs if l.get("to_stage") in ("hr_interview", "manager_interview", "awaiting_interview")), None)
        lead["interview_date"] = interview["form_data"].get("interview_date", "") if interview and interview.get("form_data") else ""
        assignee = user_map.get(lead.get("assigned_to"))
        lead["assigned_to_name"] = assignee["name"] if assignee else "Unassigned"
        lead["assigned_to_role"] = assignee.get("role", "") if assignee else ""
        job = job_map.get(lead.get("job_id"))
        lead["job_role"] = job["role"] if job else ""
        lead["job_location"] = job.get("location", "") if job else ""
        if job and job.get("branch_id"):
            branch = branch_map.get(job["branch_id"])
            lead["branch_name"] = branch["name"] if branch else ""
        else:
            lead["branch_name"] = ""
        lead["stage_label"] = STAGE_LABELS.get(lead.get("current_stage"), lead.get("current_stage", ""))
    return leads


def build_pipeline(leads):
    pipeline = {s: 0 for s in PIPELINE_STAGES}
    for l in leads:
        s = l.get("current_stage", "new_lead")
        if s in pipeline:
            pipeline[s] += 1
    return pipeline


def split_by_source(leads):
    by_source = {"meta_ads": [], "job_portal": [], "manual": []}
    for l in leads:
        src = l.get("source", "manual")
        by_source.get(src, by_source["manual"]).append(l)
    return by_source


async def get_overdue_jobs():
    now = datetime.now(timezone.utc).isoformat()
    return await db.jobs.find({"status": "open", "deadline": {"$lt": now, "$ne": None}}, {"_id": 0}).to_list(100)


async def get_franchise_summary():
    """Lightweight franchise (branch) summary for dashboards."""
    branches = await db.branches.find({}, {"_id": 0}).to_list(500)
    upcoming, active = [], []
    branch_ids = [b["id"] for b in branches]
    jobs = await db.jobs.find({"branch_id": {"$in": branch_ids}}, {"_id": 0}).to_list(2000) if branch_ids else []
    open_jobs_by_branch = {}
    for j in jobs:
        if j.get("status") == "open":
            open_jobs_by_branch[j["branch_id"]] = open_jobs_by_branch.get(j["branch_id"], 0) + 1
    employees = await db.employees.find({"branch_id": {"$in": branch_ids}, "status": {"$ne": "left"}}, {"_id": 0}).to_list(2000) if branch_ids else []
    emp_by_branch = {}
    for e in employees:
        emp_by_branch[e["branch_id"]] = emp_by_branch.get(e["branch_id"], 0) + 1
    for b in branches:
        status = "active" if b.get("actual_opening_date") else "upcoming"
        row = {
            "id": b["id"], "name": b["name"], "city": b.get("city", ""), "area": b.get("area", ""),
            "tentative_opening_date": b.get("tentative_opening_date"),
            "actual_opening_date": b.get("actual_opening_date"),
            "status": status,
            "open_jobs": open_jobs_by_branch.get(b["id"], 0),
            "employees": emp_by_branch.get(b["id"], 0),
        }
        (active if status == "active" else upcoming).append(row)
    return {"upcoming": upcoming, "active": active, "total_upcoming": len(upcoming), "total_active": len(active)}


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role", "")
    dash_type = get_dashboard_type(role)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    notif_count = await db.notifications.count_documents({"user_id": current_user["id"], "read": False})

    # ===================== CEO DASHBOARD =====================
    if dash_type == "ceo":
        total_leads = await db.leads.count_documents({})
        total_hirings = await db.employees.count_documents({})
        calls_done = await db.call_logs.count_documents({})

        all_leads = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
        all_leads = await enrich_leads(all_leads)
        tech_leads = [l for l in all_leads if l.get("is_technician")]
        ho_leads = [l for l in all_leads if not l.get("is_technician")]

        tech_jobs = await db.jobs.find({"type": "branch", "status": "open"}, {"_id": 0}).to_list(100)
        ho_jobs = await db.jobs.find({"type": "HO", "status": "open"}, {"_id": 0}).to_list(100)

        # Call tracking
        all_users = await db.users.find({"is_active": True}, {"_id": 0, "password_hash": 0}).to_list(500)
        call_tracking = []
        for u in all_users:
            calls = await db.call_logs.find({"called_by": u["id"]}, {"_id": 0}).to_list(500)
            if not calls:
                continue
            leads_called = {}
            for c in calls:
                lid = c.get("lead_id")
                if lid not in leads_called:
                    li = next((l for l in all_leads if l["id"] == lid), None)
                    leads_called[lid] = {"lead_name": li["name"] if li else "Unknown", "source": li.get("source", "") if li else "", "call_count": 0}
                leads_called[lid]["call_count"] += 1
            call_tracking.append({"id": u["id"], "name": u["name"], "role": u["role"], "total_calls": len(calls), "leads_called": list(leads_called.values())})
        call_tracking.sort(key=lambda x: x["total_calls"], reverse=True)

        overdue = await get_overdue_jobs()
        franchises = await get_franchise_summary()

        return {
            "type": "ceo", "user_level": "super",
            "top_metrics": {"total_leads": total_leads, "total_hirings": total_hirings, "total_employees": total_hirings, "calls_done": calls_done},
            "technician_hiring": {"jobs": tech_jobs, "leads_by_source": split_by_source(tech_leads), "pipeline": build_pipeline(tech_leads), "total_leads": len(tech_leads)},
            "ho_hiring": {"jobs": ho_jobs, "leads_by_source": split_by_source(ho_leads), "pipeline": build_pipeline(ho_leads), "total_leads": len(ho_leads)},
            "call_tracking": call_tracking[:15],
            "overdue_jobs": overdue,
            "franchises": franchises,
            "unread_notifications": notif_count,
        }

    # ===================== HR DASHBOARD =====================
    if dash_type == "hr":
        total_leads = await db.leads.count_documents({})
        total_hirings = await db.employees.count_documents({})
        calls_done = await db.call_logs.count_documents({})

        all_leads = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
        all_leads = await enrich_leads(all_leads)
        tech_leads = [l for l in all_leads if l.get("is_technician")]
        ho_leads = [l for l in all_leads if not l.get("is_technician")]

        # Track assigned leads by handler
        sr_jr_hr_ids = [u["id"] async for u in db.users.find({"role": {"$in": ["Sr HR", "Jr HR"]}, "is_active": True}, {"id": 1, "_id": 0})]
        fde_ids = [u["id"] async for u in db.users.find({"role": "Franchise Executive", "is_active": True}, {"id": 1, "_id": 0})]

        calls_today = await db.call_logs.count_documents({"call_date": {"$gte": today_start}})

        all_jobs = await db.jobs.find({"status": "open"}, {"_id": 0}).to_list(200)
        overdue = await get_overdue_jobs()
        pending_posts = await db.post_requests.count_documents({"status": "pending"})
        pending_reviews = await db.posts.count_documents({"review_status": "pending"})
        franchises = await get_franchise_summary()

        return {
            "type": "hr", "user_level": "super",
            "top_metrics": {"total_leads": total_leads, "total_hirings": total_hirings, "total_employees": total_hirings, "calls_done": calls_done, "calls_today": calls_today},
            "technician_hiring": {"leads_by_source": split_by_source(tech_leads), "pipeline": build_pipeline(tech_leads), "total_leads": len(tech_leads)},
            "ho_hiring": {"leads_by_source": split_by_source(ho_leads), "pipeline": build_pipeline(ho_leads), "total_leads": len(ho_leads)},
            "all_jobs": all_jobs,
            "overdue_jobs": overdue,
            "pending_posts": pending_posts,
            "pending_reviews": pending_reviews,
            "overall_pipeline": build_pipeline(all_leads),
            "franchises": franchises,
            "unread_notifications": notif_count,
        }

    # ===================== MANAGER DASHBOARD =====================
    if dash_type == "manager":
        department = ROLE_HIERARCHY.get(role, {}).get("department", "")

        # Jobs created by this manager
        my_jobs = await db.jobs.find({"created_by": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
        active_jobs = [j for j in my_jobs if j.get("status") == "open"]

        # Enrich jobs with leads count + assigned HR
        for job in my_jobs:
            job["leads_count"] = await db.leads.count_documents({"job_id": job["id"]})
            # Find assigned HR/handlers for this job's leads
            lead_assignees = await db.leads.distinct("assigned_to", {"job_id": job["id"]})
            if lead_assignees:
                handlers = await db.users.find({"id": {"$in": lead_assignees}}, {"_id": 0, "name": 1, "role": 1}).to_list(50)
                job["assigned_hr"] = ", ".join(f"{h['name']}" for h in handlers) if handlers else "None"
            else:
                job["assigned_hr"] = "None"

        # All leads for manager's jobs
        job_ids = [j["id"] for j in my_jobs]
        job_leads = await db.leads.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(1000) if job_ids else []
        job_leads = await enrich_leads(job_leads)

        # Lead insights
        new_leads = sum(1 for l in job_leads if l.get("current_stage") == "new_lead")
        qualified_leads = sum(1 for l in job_leads if l.get("current_stage") == "qualified")
        interviewed = sum(1 for l in job_leads if l.get("current_stage") in ["hr_interview", "manager_interview", "move_ahead", "awaiting_interview", "interview_cleared"])
        hired = await db.employees.count_documents({"created_by": current_user["id"]}) if job_ids else 0

        # Alerts
        alerts = []
        for job in active_jobs:
            if job["leads_count"] == 0:
                alerts.append({"type": "no_leads", "message": f"No leads for {job['role']} at {job.get('location','')}", "job_id": job["id"]})
            if job.get("deadline") and job["deadline"] < datetime.now(timezone.utc).isoformat():
                alerts.append({"type": "overdue", "message": f"Deadline passed for {job['role']}", "job_id": job["id"]})

        # Stuck leads (in same stage for 7+ days)
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        for l in job_leads:
            if l.get("current_stage") in ["new_lead", "qualified"] and l.get("updated_at", "") < seven_days_ago:
                alerts.append({"type": "stuck", "message": f"{l['name']} stuck in {l.get('stage_label','')}", "lead_id": l["id"]})

        # Ownership - who handles leads
        ownership = {}
        for l in job_leads:
            handler = l.get("assigned_to_name", "Unassigned")
            handler_role = l.get("assigned_to_role", "")
            key = f"{handler} ({handler_role})" if handler_role else handler
            if key not in ownership:
                ownership[key] = 0
            ownership[key] += 1

        overdue = await get_overdue_jobs()
        franchises = await get_franchise_summary()

        return {
            "type": "manager", "user_level": "manager", "department": department,
            "top_metrics": {"jobs_created": len(my_jobs), "active_hirings": len(active_jobs), "total_leads": len(job_leads), "new_leads": new_leads, "total_hires": hired},
            "jobs": my_jobs,
            "leads": job_leads[:30],
            "lead_insights": {"new": new_leads, "qualified": qualified_leads, "interviewed": interviewed, "hired": hired},
            "pipeline": build_pipeline(job_leads),
            "alerts": alerts[:10],
            "ownership": ownership,
            "overdue_jobs": overdue,
            "franchises": franchises,
            "unread_notifications": notif_count,
        }

    # ===================== SR/JR HR DASHBOARD =====================
    if dash_type == "sr_jr_hr":
        # See all jobs
        all_jobs = await db.jobs.find({"status": "open"}, {"_id": 0}).to_list(200)

        # My assigned leads (HO only for Sr/Jr HR)
        my_leads = await db.leads.find({"assigned_to": current_user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(500)
        my_leads = await enrich_leads(my_leads)

        calls_today = await db.call_logs.count_documents({"called_by": current_user["id"], "call_date": {"$gte": today_start}})
        total_calls = await db.call_logs.count_documents({"called_by": current_user["id"]})
        recent_calls = await db.call_logs.find({"called_by": current_user["id"]}, {"_id": 0}).sort("call_date", -1).to_list(10)

        # Pending post requests
        my_post_requests = await db.post_requests.find({"requested_by": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)

        return {
            "type": "sr_jr_hr", "user_level": "executor",
            "all_jobs": all_jobs,
            "my_leads": my_leads[:30], "my_leads_count": len(my_leads),
            "my_pipeline": build_pipeline(my_leads),
            "leads_by_source": split_by_source(my_leads),
            "calls_today": calls_today, "total_calls": total_calls,
            "recent_calls": recent_calls,
            "my_post_requests": my_post_requests,
            "franchises": await get_franchise_summary(),
            "unread_notifications": notif_count,
        }

    # ===================== FRANCHISE EXECUTIVE DASHBOARD =====================
    if dash_type == "fde":
        # Technician leads assigned to me
        my_leads = await db.leads.find({"assigned_to": current_user["id"], "is_technician": True}, {"_id": 0}).sort("updated_at", -1).to_list(500)
        my_leads = await enrich_leads(my_leads)

        # FDE jobs: any branch jobs (Franchise Dev Manager removed) — show all branch jobs
        fde_jobs = await db.jobs.find({"type": "branch", "status": "open"}, {"_id": 0}).to_list(100)

        calls_today = await db.call_logs.count_documents({"called_by": current_user["id"], "call_date": {"$gte": today_start}})
        total_calls = await db.call_logs.count_documents({"called_by": current_user["id"]})
        recent_calls = await db.call_logs.find({"called_by": current_user["id"]}, {"_id": 0}).sort("call_date", -1).to_list(10)

        return {
            "type": "fde", "user_level": "executor",
            "jobs": fde_jobs,
            "my_leads": my_leads[:30], "my_leads_count": len(my_leads),
            "my_pipeline": build_pipeline(my_leads),
            "leads_by_source": split_by_source(my_leads),
            "calls_today": calls_today, "total_calls": total_calls,
            "recent_calls": recent_calls,
            "franchises": await get_franchise_summary(),
            "unread_notifications": notif_count,
        }

    # ===================== GRAPHIC DESIGNER DASHBOARD =====================
    if dash_type == "designer":
        pending_requests = await db.post_requests.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(100)
        my_posts = await db.posts.find({"uploaded_by": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
        all_requests = await db.post_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)

        return {
            "type": "designer", "user_level": "executor",
            "pending_requests": pending_requests,
            "my_posts": my_posts,
            "all_requests": all_requests,
            "total_pending": len(pending_requests),
            "total_completed": len(my_posts),
            "franchises": await get_franchise_summary(),
            "unread_notifications": notif_count,
        }

    # ===================== MARKETING COORDINATOR DASHBOARD =====================
    if dash_type == "mktg_coord":
        my_campaigns = await db.ad_campaigns.find({"assigned_to": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
        pending = [c for c in my_campaigns if c.get("status") == "pending"]
        running = [c for c in my_campaigns if c.get("status") == "running"]
        completed = [c for c in my_campaigns if c.get("status") == "completed"]

        return {
            "type": "mktg_coord", "user_level": "executor",
            "campaigns": my_campaigns,
            "pending_count": len(pending),
            "running_count": len(running),
            "completed_count": len(completed),
            "franchises": await get_franchise_summary(),
            "unread_notifications": notif_count,
        }

    # ===================== DEFAULT EXECUTOR DASHBOARD =====================
    my_id = current_user["id"]
    my_leads = await db.leads.find({"assigned_to": my_id}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    my_leads = await enrich_leads(my_leads)
    calls_today = await db.call_logs.count_documents({"called_by": my_id, "call_date": {"$gte": today_start}})
    my_tasks = await db.tasks.find({"assigned_to": my_id, "status": "pending"}, {"_id": 0}).to_list(50)

    return {
        "type": "executor", "user_level": "executor",
        "my_leads": my_leads[:20], "my_leads_count": len(my_leads),
        "my_pipeline": build_pipeline(my_leads),
        "calls_today": calls_today,
        "my_tasks": my_tasks[:10], "pending_tasks_count": len(my_tasks),
        "franchises": await get_franchise_summary(),
        "unread_notifications": notif_count,
    }
