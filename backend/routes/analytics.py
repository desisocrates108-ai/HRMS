"""Analytics & System Intelligence routes.

P1 — /api/analytics/funnel, /api/analytics/summary
P2 — /api/analytics/intelligence
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from database import db
from auth_utils import get_current_user, CEO_HR_ROLES
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

router = APIRouter()


def _require_ceo_hr(user: dict):
    role = user.get("role", "")
    # also allow managers for analytics
    if role not in CEO_HR_ROLES and user.get("role") not in (
        "Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager"
    ):
        raise HTTPException(status_code=403, detail="Analytics restricted to CEO/HR/Manager roles")


@router.get("/summary")
async def analytics_summary(
    pipeline_type: Optional[str] = Query(None, description="head_office | technician"),
    days: int = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    _require_ceo_hr(current_user)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    lead_q = {"created_at": {"$gte": since}}
    if pipeline_type == "head_office":
        lead_q["is_technician"] = False
    elif pipeline_type == "technician":
        lead_q["is_technician"] = True
    leads = await db.leads.find(lead_q, {"_id": 0}).to_list(10000)

    # --- Funnel counts ---
    funnel_order_ho = ["new_lead", "qualified", "hr_interview", "manager_interview", "selected", "three_months", "joined"]
    funnel_order_tech = ["new_lead", "qualified", "hr_interview", "selected", "three_months", "joined"]
    order = funnel_order_tech if pipeline_type == "technician" else funnel_order_ho

    # A lead that reached stage X also counted X-1, X-2... Use lead_stage_logs
    lead_ids = [l["id"] for l in leads]
    logs = await db.lead_stage_logs.find({"lead_id": {"$in": lead_ids}}, {"_id": 0}).to_list(50000) if lead_ids else []
    stages_reached = defaultdict(set)  # stage -> set of lead_ids
    for lg in logs:
        stages_reached[lg.get("to_stage")].add(lg["lead_id"])

    # Accumulate so later stages include earlier reach: we actually want distinct lead ids per stage
    funnel = []
    for s in order:
        reached = len(stages_reached.get(s, set()))
        funnel.append({"stage": s, "count": reached})

    # --- Conversion rates ---
    conversions = {}
    if funnel:
        base = funnel[0]["count"] or 1
        for f in funnel:
            conversions[f["stage"]] = round((f["count"] / base) * 100, 1)

    # --- Hold reason breakdown ---
    hold_reasons = Counter()
    dead_reasons = Counter()
    for l in leads:
        if l.get("current_stage") == "hold" and l.get("hold_reason"):
            hold_reasons[l["hold_reason"]] += 1
        if l.get("current_stage") == "dead" and l.get("dead_reason"):
            dead_reasons[l["dead_reason"]] += 1

    # --- Source breakdown ---
    sources = Counter(l.get("source", "manual") for l in leads)

    # --- Avg interview scores ---
    interviews = await db.interviews.find(
        {"lead_id": {"$in": lead_ids}},
        {"_id": 0},
    ).to_list(5000) if lead_ids else []
    hr_scores = [i["avg_rating"] for i in interviews if i.get("round") == "hr" and i.get("avg_rating") is not None]
    mgr_scores = [i["avg_rating"] for i in interviews if i.get("round") == "manager" and i.get("avg_rating") is not None]
    avg_hr = round(sum(hr_scores) / len(hr_scores), 2) if hr_scores else 0
    avg_mgr = round(sum(mgr_scores) / len(mgr_scores), 2) if mgr_scores else 0

    # --- Time to hire (days from new_lead to joined) ---
    time_to_hire_days = []
    by_lead_logs = defaultdict(list)
    for lg in logs:
        by_lead_logs[lg["lead_id"]].append(lg)
    for lid, ls in by_lead_logs.items():
        ls.sort(key=lambda x: x.get("timestamp", ""))
        start = next((x for x in ls if x.get("to_stage") == "new_lead"), None)
        end = next((x for x in ls if x.get("to_stage") == "joined"), None)
        if start and end:
            try:
                s = datetime.fromisoformat(start["timestamp"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(end["timestamp"].replace("Z", "+00:00"))
                time_to_hire_days.append((e - s).total_seconds() / 86400)
            except Exception:
                pass
    avg_tth = round(sum(time_to_hire_days) / len(time_to_hire_days), 1) if time_to_hire_days else 0

    return {
        "window_days": days,
        "pipeline_type": pipeline_type or "all",
        "total_leads": len(leads),
        "funnel": funnel,
        "conversions_pct": conversions,
        "hold_reasons": [{"reason": k, "count": v} for k, v in hold_reasons.most_common()],
        "dead_reasons": [{"reason": k, "count": v} for k, v in dead_reasons.most_common()],
        "sources": [{"source": k, "count": v} for k, v in sources.most_common()],
        "avg_hr_score": avg_hr,
        "avg_manager_score": avg_mgr,
        "hires": funnel[-1]["count"] if funnel else 0,
        "avg_time_to_hire_days": avg_tth,
    }


@router.get("/intelligence")
async def system_intelligence(
    days: int = Query(90, ge=7, le=365),
    current_user: dict = Depends(get_current_user),
):
    """P2 — Best HR interviewer + Weak stage detection."""
    _require_ceo_hr(current_user)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Best HR interviewer: highest hit rate (candidates they cleared who actually became "joined")
    interviews = await db.interviews.find(
        {"submitted_at": {"$gte": since}, "round": "hr"}, {"_id": 0}
    ).to_list(5000)
    by_user = defaultdict(lambda: {"name": "", "count": 0, "avg_score": 0.0, "joined": 0, "dead": 0})
    lead_ids = list({i["lead_id"] for i in interviews})
    leads = await db.leads.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(5000) if lead_ids else []
    lead_stage = {l["id"]: l.get("current_stage") for l in leads}

    for i in interviews:
        uid = i.get("submitted_by")
        if not uid:
            continue
        entry = by_user[uid]
        entry["name"] = i.get("submitted_by_name", uid)
        entry["count"] += 1
        entry["avg_score"] += i.get("avg_rating", 0) or 0
        st = lead_stage.get(i["lead_id"])
        if st == "joined":
            entry["joined"] += 1
        elif st == "dead":
            entry["dead"] += 1

    interviewers = []
    for uid, v in by_user.items():
        avg = round(v["avg_score"] / v["count"], 2) if v["count"] else 0
        hit_rate = round((v["joined"] / v["count"]) * 100, 1) if v["count"] else 0
        interviewers.append({
            "user_id": uid,
            "name": v["name"],
            "interviews_conducted": v["count"],
            "avg_rating_given": avg,
            "candidates_joined": v["joined"],
            "candidates_dead": v["dead"],
            "hit_rate_pct": hit_rate,
        })
    # Only rank those with >= 3 interviews
    qualified_interviewers = [i for i in interviewers if i["interviews_conducted"] >= 3]
    qualified_interviewers.sort(key=lambda x: (x["hit_rate_pct"], x["interviews_conducted"]), reverse=True)
    best_interviewer = qualified_interviewers[0] if qualified_interviewers else None

    # Weak stage detector: highest drop-off in funnel
    all_leads = await db.leads.find({"created_at": {"$gte": since}}, {"_id": 0}).to_list(10000)
    ids = [l["id"] for l in all_leads]
    logs = await db.lead_stage_logs.find({"lead_id": {"$in": ids}}, {"_id": 0}).to_list(50000) if ids else []
    reached = defaultdict(set)
    for lg in logs:
        reached[lg.get("to_stage")].add(lg["lead_id"])
    order = ["new_lead", "qualified", "hr_interview", "manager_interview", "selected", "three_months", "joined"]
    weak_stages = []
    for i in range(len(order) - 1):
        cur = len(reached.get(order[i], set()))
        nxt = len(reached.get(order[i + 1], set()))
        if cur == 0:
            continue
        drop_pct = round(((cur - nxt) / cur) * 100, 1)
        weak_stages.append({
            "from_stage": order[i],
            "to_stage": order[i + 1],
            "from_count": cur,
            "to_count": nxt,
            "drop_pct": drop_pct,
        })
    weak_stages.sort(key=lambda x: x["drop_pct"], reverse=True)

    # Insights
    insights = []
    if best_interviewer:
        insights.append({
            "type": "best_interviewer",
            "message": f"{best_interviewer['name']} has the best hit rate — {best_interviewer['hit_rate_pct']}% of their HR-cleared candidates joined.",
        })
    if weak_stages and weak_stages[0]["drop_pct"] >= 50:
        ws = weak_stages[0]
        insights.append({
            "type": "weak_stage",
            "message": f"High drop-off ({ws['drop_pct']}%) between {ws['from_stage']} → {ws['to_stage']}. Consider reviewing this stage.",
        })

    # Hold reason insights
    hold_counter = Counter(l.get("hold_reason") for l in all_leads if l.get("current_stage") == "hold" and l.get("hold_reason"))
    if hold_counter:
        top_hold = hold_counter.most_common(1)[0]
        insights.append({
            "type": "hold_reason",
            "message": f"Top hold reason: '{top_hold[0]}' ({top_hold[1]} leads). Investigate process gap.",
        })

    return {
        "window_days": days,
        "best_interviewer": best_interviewer,
        "all_interviewers": qualified_interviewers,
        "weak_stages": weak_stages,
        "insights": insights,
    }



# ============ Performance Dashboards (May 2026) ============

def _date_range(date_from: Optional[str], date_to: Optional[str], days: Optional[int]):
    """Return ISO date filter clause. Prefers explicit from/to, falls back to days."""
    if date_from or date_to:
        clause = {}
        if date_from:
            clause["$gte"] = date_from
        if date_to:
            clause["$lte"] = date_to
        return clause
    if days:
        return {"$gte": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()}
    return None


EXEC_ROLES_PERF = ["Sr HR", "Jr HR", "Franchise Executive", "Marketing Coordinator"]


@router.get("/executives")
async def executive_performance(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    days: Optional[int] = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Performance metrics for executives who handle leads."""
    role = current_user.get("role")
    # Executives see only own metrics
    if role in EXEC_ROLES_PERF and role not in ("CEO", "HR") and role not in (
        "Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager"
    ):
        exec_users = await db.users.find({"id": current_user["id"]}, {"_id": 0}).to_list(1)
    else:
        exec_users = await db.users.find(
            {"role": {"$in": EXEC_ROLES_PERF}, "is_active": True},
            {"_id": 0, "id": 1, "name": 1, "role": 1},
        ).to_list(200)

    dr = _date_range(date_from, date_to, days)

    rows = []
    for u in exec_users:
        lead_query = {"assigned_to": u["id"]}
        if dr:
            lead_query["created_at"] = dr
        leads = await db.leads.find(lead_query, {"_id": 0}).to_list(5000)
        total = len(leads)
        called = sum(1 for l in leads if (l.get("total_calls") or 0) > 0)
        stage_counts = Counter(l.get("current_stage") for l in leads)
        by_source = Counter(l.get("source", "manual") for l in leads)
        joined = stage_counts.get("joined", 0)
        rejected = stage_counts.get("rejected", 0) + stage_counts.get("dead", 0)
        hold = stage_counts.get("hold", 0)
        qualified = stage_counts.get("qualified", 0)
        selected = stage_counts.get("selected", 0) + stage_counts.get("move_ahead", 0)
        interview_scheduled = stage_counts.get("hr_interview", 0) + stage_counts.get("manager_interview", 0)

        rows.append({
            "user_id": u["id"],
            "name": u.get("name"),
            "role": u.get("role"),
            "total_leads": total,
            "called": called,
            "pending_calls": total - called,
            "qualified": qualified,
            "interview_scheduled": interview_scheduled,
            "selected": selected,
            "joined": joined,
            "rejected": rejected,
            "hold": hold,
            "conversion_pct": round((joined / total * 100), 1) if total else 0,
            "by_source": {
                "meta_ads": by_source.get("meta_ads", 0),
                "job_portal": by_source.get("job_portal", 0),
                "manual": by_source.get("manual", 0),
            },
        })

    rows.sort(key=lambda x: x["joined"], reverse=True)
    return {"executives": rows, "window": {"days": days, "date_from": date_from, "date_to": date_to}}


@router.get("/executives/{user_id}")
async def executive_detail(
    user_id: str,
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    days: Optional[int] = 90,
    current_user: dict = Depends(get_current_user),
):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exec can only see themselves
    if current_user.get("role") not in ["CEO", "HR", "Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager"]:
        if current_user["id"] != user_id:
            raise HTTPException(status_code=403, detail="Can only view own performance")

    dr = _date_range(date_from, date_to, days)
    lead_q = {"assigned_to": user_id}
    if dr:
        lead_q["created_at"] = dr
    leads = await db.leads.find(lead_q, {"_id": 0}).sort("created_at", -1).to_list(5000)

    # Jobs created by this user
    jobs_q = {"created_by": user_id}
    if dr:
        jobs_q["created_at"] = dr
    jobs = await db.jobs.find(jobs_q, {"_id": 0}).to_list(500)

    return {
        "user": user,
        "leads": leads[:200],
        "total_leads": len(leads),
        "jobs_created": jobs,
        "total_jobs": len(jobs),
        "open_jobs": sum(1 for j in jobs if j.get("status") == "open"),
    }


@router.get("/managers")
async def manager_performance(
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    days: Optional[int] = 90,
    current_user: dict = Depends(get_current_user),
):
    """Manager interview performance (based on /interviews submissions — manager round)."""
    role = current_user.get("role")
    manager_roles = ["Marketing Manager", "Operations Manager", "Sales Manager", "Accounts Manager"]

    if role in manager_roles and role not in ["CEO", "HR"]:
        managers = await db.users.find({"id": current_user["id"]}, {"_id": 0}).to_list(1)
    else:
        managers = await db.users.find(
            {"role": {"$in": manager_roles}, "is_active": True},
            {"_id": 0, "id": 1, "name": 1, "role": 1},
        ).to_list(200)

    dr = _date_range(date_from, date_to, days)

    rows = []
    for m in managers:
        iv_q = {"submitted_by": m["id"], "round": "manager"}
        if dr:
            iv_q["submitted_at"] = dr
        ivs = await db.interviews.find(iv_q, {"_id": 0}).to_list(1000)
        lead_ids = [i["lead_id"] for i in ivs]
        leads = await db.leads.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(1000) if lead_ids else []
        stage_counts = Counter(l.get("current_stage") for l in leads)
        avg_rating = round(sum(i.get("avg_rating", 0) for i in ivs) / len(ivs), 2) if ivs else 0
        rows.append({
            "user_id": m["id"],
            "name": m.get("name"),
            "role": m.get("role"),
            "interviews_completed": len(ivs),
            "approved": stage_counts.get("selected", 0) + stage_counts.get("move_ahead", 0) + stage_counts.get("joined", 0),
            "rejected": stage_counts.get("rejected", 0) + stage_counts.get("dead", 0),
            "hold": stage_counts.get("hold", 0),
            "joined": stage_counts.get("joined", 0),
            "avg_rating": avg_rating,
        })
    rows.sort(key=lambda x: x["interviews_completed"], reverse=True)
    return {"managers": rows}


@router.get("/jobs-performance")
async def jobs_performance(
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    days: Optional[int] = 90,
    current_user: dict = Depends(get_current_user),
):
    """Job-creation + recruitment performance for Sr HR / Jr HR / Franchise Executive."""
    role = current_user.get("role")
    job_roles = ["Sr HR", "Jr HR", "Franchise Executive"]

    if role in job_roles:
        users = await db.users.find({"id": current_user["id"]}, {"_id": 0}).to_list(1)
    else:
        users = await db.users.find(
            {"role": {"$in": job_roles}, "is_active": True},
            {"_id": 0, "id": 1, "name": 1, "role": 1},
        ).to_list(200)

    dr = _date_range(date_from, date_to, days)
    rows = []
    for u in users:
        q = {"created_by": u["id"]}
        if dr:
            q["created_at"] = dr
        jobs = await db.jobs.find(q, {"_id": 0}).to_list(2000)
        if not jobs:
            rows.append({"user_id": u["id"], "name": u["name"], "role": u["role"],
                         "jobs_created": 0, "open_jobs": 0, "closed_jobs": 0,
                         "total_leads": 0, "joined": 0, "pending": 0})
            continue
        job_ids = [j["id"] for j in jobs]
        leads = await db.leads.find({"job_id": {"$in": job_ids}}, {"_id": 0}).to_list(5000)
        joined = sum(1 for l in leads if l.get("current_stage") == "joined")
        pending = len(jobs) - sum(1 for j in jobs if j.get("status") == "closed")
        rows.append({
            "user_id": u["id"], "name": u["name"], "role": u["role"],
            "jobs_created": len(jobs),
            "open_jobs": sum(1 for j in jobs if j.get("status") == "open"),
            "closed_jobs": sum(1 for j in jobs if j.get("status") == "closed"),
            "total_leads": len(leads),
            "joined": joined,
            "pending": pending,
        })
    rows.sort(key=lambda x: x["jobs_created"], reverse=True)
    return {"users": rows}


@router.get("/leads-by-source")
async def leads_by_source(
    source: Optional[str] = None,  # meta_ads | job_portal | manual
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    days: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    """List leads filtered by source + date range."""
    q = {}
    if source:
        q["source"] = source
    dr = _date_range(date_from, date_to, days)
    if dr:
        q["created_at"] = dr
    leads = await db.leads.find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    # Enrich assignee names
    assignee_ids = list({l.get("assigned_to") for l in leads if l.get("assigned_to")})
    users = {u["id"]: u["name"] for u in await db.users.find({"id": {"$in": assignee_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(500)} if assignee_ids else {}
    for l in leads:
        l["assignee_name"] = users.get(l.get("assigned_to"), "")
    return {"leads": leads, "total": len(leads)}
