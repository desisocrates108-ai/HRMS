"""Hirings module — Designation-based hiring dashboard.

Replaces the old Job-based workflow with a Designation-based grouping.
Routes:
  GET  /api/hirings/{office_type}            -> designations + stage counts
  GET  /api/hirings/designations/{designation_id}/candidates  -> leads for designation
  GET  /api/hirings/designations/by-name/{name}/candidates    -> legacy leads with job_role string
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database import db
from auth_utils import get_current_user

router = APIRouter()

OFFICE_TYPES = {"head_office", "franchise"}

# Stages displayed in the Hirings UI with friendly labels.
# Internal stage values are kept as-is; we only relabel for display.
HIRING_STAGES = [
    {"key": "new_lead",          "label": "New"},
    {"key": "qualified",         "label": "Qualified"},
    {"key": "hr_interview",      "label": "Interview Scheduled"},
    {"key": "manager_interview", "label": "Interview Completed"},
    {"key": "hold",              "label": "Hold"},
    {"key": "selected",          "label": "Selected"},
    {"key": "joined",            "label": "Joined"},  # three_months is merged into Joined
    {"key": "rejected",          "label": "Rejected"},
]
# Map internal stage -> hiring display key (collapses three_months into joined)
STAGE_DISPLAY_MAP = {
    "new_lead": "new_lead",
    "qualified": "qualified",
    "hr_interview": "hr_interview",
    "manager_interview": "manager_interview",
    "hold": "hold",
    "selected": "selected",
    "three_months": "joined",
    "joined": "joined",
    "rejected": "rejected",
}


def _empty_counts() -> dict:
    return {s["key"]: 0 for s in HIRING_STAGES}


def _validate_office_type(value: str) -> str:
    v = (value or "").strip().lower()
    if v not in OFFICE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid office_type. Use 'head_office' or 'franchise'.")
    return v


async def _collect_designation_buckets(office_type: str) -> dict:
    """Return {key -> {designation_id|None, name, office_type, counts:{...}, total}} for an office_type.
    Buckets are keyed on lowercase designation name (so legacy leads with only
    job_role string still group with the proper designation).
    """
    # Active designations for this office_type
    desgs = await db.designations.find(
        {"office_type": office_type},
        {"_id": 0, "id": 1, "name": 1, "office_type": 1, "active": 1, "department": 1, "description": 1},
    ).sort("name", 1).to_list(2000)

    buckets: dict[str, dict] = {}
    name_to_id: dict[str, str] = {}
    for d in desgs:
        key = (d.get("name") or "").strip().lower()
        if not key:
            continue
        name_to_id[key] = d["id"]
        buckets[key] = {
            "designation_id": d["id"],
            "name": d["name"],
            "office_type": d["office_type"],
            "active": d.get("active", True),
            "department": d.get("department"),
            "description": d.get("description"),
            "counts": _empty_counts(),
            "total": 0,
        }

    # Pull all relevant leads (this office_type / is_technician segment)
    is_tech = office_type == "franchise"
    lead_q = {"deleted": {"$ne": True}, "is_technician": is_tech}
    cursor = db.leads.find(
        lead_q,
        {"_id": 0, "id": 1, "designation_id": 1, "job_id": 1, "job_role": 1, "current_stage": 1},
    )

    # Pre-fetch jobs roles for legacy fallback
    leads = await cursor.to_list(20000)
    job_ids = list({l.get("job_id") for l in leads if l.get("job_id") and not l.get("job_role")})
    job_role_map: dict[str, str] = {}
    if job_ids:
        async for j in db.jobs.find({"id": {"$in": job_ids}}, {"_id": 0, "id": 1, "role": 1}):
            job_role_map[j["id"]] = (j.get("role") or "").strip()

    for l in leads:
        # Resolve effective bucket key
        bkey = None
        bname = None
        if l.get("designation_id"):
            # Direct mapping: find that designation in our list
            for k, b in buckets.items():
                if b["designation_id"] == l["designation_id"]:
                    bkey = k
                    bname = b["name"]
                    break
            if bkey is None:
                # Lead points to a designation belonging to another office_type — skip
                continue
        else:
            # Legacy fallback: job_role string -> match by name (case-insensitive)
            role_str = (l.get("job_role") or "").strip()
            if not role_str and l.get("job_id"):
                role_str = job_role_map.get(l["job_id"]) or ""
            if not role_str:
                continue
            key = role_str.lower()
            if key in buckets:
                bkey = key
                bname = buckets[key]["name"]
            else:
                # Create an "ad-hoc" bucket for an unknown role string
                buckets[key] = {
                    "designation_id": None,
                    "name": role_str,
                    "office_type": office_type,
                    "active": True,
                    "department": None,
                    "description": None,
                    "counts": _empty_counts(),
                    "total": 0,
                }
                bkey = key
                bname = role_str

        stg = l.get("current_stage") or "new_lead"
        disp = STAGE_DISPLAY_MAP.get(stg)
        if not disp:
            continue
        buckets[bkey]["counts"][disp] += 1
        buckets[bkey]["total"] += 1

    return buckets


@router.get("/{office_type}")
async def get_hiring_dashboard(office_type: str, current_user: dict = Depends(get_current_user)):
    ot = _validate_office_type(office_type)
    buckets = await _collect_designation_buckets(ot)
    # Order: real designations first (by total desc, then name), legacy/ad-hoc after
    rows = list(buckets.values())
    rows.sort(key=lambda r: (r["designation_id"] is None, -r["total"], r["name"].lower()))
    summary = {
        "designations": len(rows),
        "candidates": sum(r["total"] for r in rows),
        "stages": _empty_counts(),
    }
    for r in rows:
        for k, v in r["counts"].items():
            summary["stages"][k] += v
    return {
        "office_type": ot,
        "stages": HIRING_STAGES,
        "designations": rows,
        "summary": summary,
    }


@router.get("/designations/{designation_id}/candidates")
async def list_candidates_by_designation(
    designation_id: str,
    stage: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    desg = await db.designations.find_one({"id": designation_id}, {"_id": 0})
    if not desg:
        raise HTTPException(status_code=404, detail="Designation not found")
    is_tech = desg.get("office_type") == "franchise"
    lead_q = {"deleted": {"$ne": True}, "is_technician": is_tech}
    # Match either by direct designation_id OR by legacy job_role string (case-insensitive)
    name_lower = (desg.get("name") or "").strip().lower()
    lead_q["$or"] = [
        {"designation_id": designation_id},
        {"job_role": {"$regex": f"^{name_lower}$", "$options": "i"}},
    ]
    if stage:
        # Translate display-stage back to internal stage(s)
        internal_stages = [k for k, v in STAGE_DISPLAY_MAP.items() if v == stage]
        if internal_stages:
            lead_q["current_stage"] = {"$in": internal_stages}
    leads = await db.leads.find(lead_q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    # Enrich every lead with effective job_role
    for l in leads:
        if not l.get("job_role"):
            l["job_role"] = desg.get("name")
    return {
        "designation": desg,
        "candidates": leads,
    }
