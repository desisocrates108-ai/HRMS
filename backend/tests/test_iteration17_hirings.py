"""Iteration 17 — Designation-based Hirings module backend regression.

Covers:
- Designations office_type CRUD + filter
- Leads create/update with designation_id auto-fill (job_role + is_technician), salary validation
- Hirings endpoints: /api/hirings/{office_type}, /api/hirings/designations/{id}/candidates
- Stage aggregation incl. three_months -> joined merge, legacy job_role lookup
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://hr-positions-widget.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@servall.com"
ADMIN_PASS = "Admin@123"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def hdr(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def created_ids():
    return {"designations": [], "leads": []}


def _cleanup(hdr, created_ids):
    for lid in created_ids["leads"]:
        try:
            requests.post(f"{API}/leads/{lid}/delete", headers=hdr, timeout=10)
            requests.delete(f"{API}/leads/{lid}", headers=hdr, timeout=10)
        except Exception:
            pass
    for did in created_ids["designations"]:
        try:
            requests.delete(f"{API}/designations/{did}", headers=hdr, timeout=10)
        except Exception:
            pass


# ---------------- Designations ----------------

def test_list_designations_have_office_type(hdr):
    r = requests.get(f"{API}/designations", headers=hdr, timeout=15)
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) > 0
    for d in items:
        assert "office_type" in d, f"Designation missing office_type: {d}"
        assert d["office_type"] in ("head_office", "franchise")


def test_create_designation_requires_office_type(hdr, created_ids):
    # Missing office_type -> 422 (Pydantic) or 400
    r = requests.post(f"{API}/designations", headers=hdr,
                      json={"name": f"TEST_NoOT_{uuid.uuid4().hex[:6]}"}, timeout=15)
    assert r.status_code in (400, 422), f"expected 4xx, got {r.status_code} {r.text}"


def test_create_designation_invalid_office_type(hdr):
    r = requests.post(f"{API}/designations", headers=hdr,
                      json={"name": f"TEST_BadOT_{uuid.uuid4().hex[:6]}", "office_type": "remote"}, timeout=15)
    assert r.status_code == 400, r.text


def test_create_designation_dual_office_type_same_name(hdr, created_ids):
    nm = f"TEST_Dual_{uuid.uuid4().hex[:6]}"
    a = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "head_office"}, timeout=15)
    assert a.status_code == 200, a.text
    da = a.json(); created_ids["designations"].append(da["id"])
    assert da["office_type"] == "head_office"
    b = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "franchise"}, timeout=15)
    assert b.status_code == 200, b.text
    db = b.json(); created_ids["designations"].append(db["id"])
    assert db["office_type"] == "franchise"
    # duplicate same name + same office_type -> 400
    c = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "head_office"}, timeout=15)
    assert c.status_code == 400, c.text


def test_filter_designations_by_office_type(hdr):
    r = requests.get(f"{API}/designations?office_type=franchise", headers=hdr, timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    assert all(d["office_type"] == "franchise" for d in items)


# ---------------- Leads with designation_id ----------------

@pytest.fixture(scope="session")
def franchise_designation(hdr, created_ids):
    nm = f"TEST_FrDesg_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "franchise"}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json(); created_ids["designations"].append(d["id"])
    return d


@pytest.fixture(scope="session")
def ho_designation(hdr, created_ids):
    nm = f"TEST_HoDesg_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "head_office"}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json(); created_ids["designations"].append(d["id"])
    return d


def test_create_lead_with_designation_autofills(hdr, created_ids, franchise_designation):
    payload = {
        "name": f"TEST_CandFr_{uuid.uuid4().hex[:6]}", "phone": "9000000001",
        "designation_id": franchise_designation["id"],
        "min_salary": 10000, "max_salary": 20000, "description": "Auto-fill test",
    }
    r = requests.post(f"{API}/leads", headers=hdr, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    lead = r.json(); created_ids["leads"].append(lead["id"])
    assert lead["job_role"] == franchise_designation["name"]
    assert lead["is_technician"] is True
    # GET verify persistence
    g = requests.get(f"{API}/leads/{lead['id']}", headers=hdr, timeout=15)
    assert g.status_code == 200
    assert g.json()["job_role"] == franchise_designation["name"]
    assert g.json()["is_technician"] is True


def test_create_lead_head_office_designation(hdr, created_ids, ho_designation):
    payload = {
        "name": f"TEST_CandHo_{uuid.uuid4().hex[:6]}", "phone": "9000000002",
        "designation_id": ho_designation["id"],
    }
    r = requests.post(f"{API}/leads", headers=hdr, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    lead = r.json(); created_ids["leads"].append(lead["id"])
    assert lead["job_role"] == ho_designation["name"]
    assert lead["is_technician"] is False


def test_create_lead_salary_validation(hdr, ho_designation):
    payload = {
        "name": f"TEST_BadSal_{uuid.uuid4().hex[:6]}", "phone": "9000000003",
        "designation_id": ho_designation["id"], "min_salary": 50000, "max_salary": 1000,
    }
    r = requests.post(f"{API}/leads", headers=hdr, json=payload, timeout=15)
    assert r.status_code == 400, r.text


def test_update_lead_with_designation(hdr, created_ids, ho_designation, franchise_designation):
    # Create with ho
    r = requests.post(f"{API}/leads", headers=hdr, json={
        "name": f"TEST_UpdLead_{uuid.uuid4().hex[:6]}", "phone": "9000000004",
        "designation_id": ho_designation["id"],
    }, timeout=15)
    assert r.status_code == 200, r.text
    lead = r.json(); created_ids["leads"].append(lead["id"])
    # Switch to franchise
    u = requests.put(f"{API}/leads/{lead['id']}", headers=hdr,
                     json={"designation_id": franchise_designation["id"]}, timeout=15)
    assert u.status_code == 200, u.text
    upd = u.json()
    assert upd["is_technician"] is True
    assert upd["job_role"] == franchise_designation["name"]
    # Unset via empty string
    u2 = requests.put(f"{API}/leads/{lead['id']}", headers=hdr,
                      json={"designation_id": "", "job_role": ""}, timeout=15)
    assert u2.status_code == 200, u2.text
    g = requests.get(f"{API}/leads/{lead['id']}", headers=hdr, timeout=15).json()
    assert not g.get("designation_id")


# ---------------- Hirings dashboard ----------------

def test_hirings_invalid_office_type(hdr):
    r = requests.get(f"{API}/hirings/invalid", headers=hdr, timeout=15)
    assert r.status_code == 400


def test_hirings_head_office_shape(hdr):
    r = requests.get(f"{API}/hirings/head_office", headers=hdr, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["office_type"] == "head_office"
    stages = body["stages"]
    assert isinstance(stages, list) and len(stages) == 8
    keys = [s["key"] for s in stages]
    assert "joined" in keys and "three_months" not in keys
    assert "hr_interview" in keys and "manager_interview" in keys
    assert all("label" in s for s in stages)
    assert "designations" in body and isinstance(body["designations"], list)
    assert "summary" in body and "stages" in body["summary"]


def test_hirings_franchise_only_franchise(hdr, franchise_designation):
    r = requests.get(f"{API}/hirings/franchise", headers=hdr, timeout=15)
    assert r.status_code == 200
    body = r.json()
    # the franchise_designation fixture should appear in this list
    names = [d["name"] for d in body["designations"]]
    assert franchise_designation["name"] in names
    # ensure no head_office-only designation slipped in (heuristic: all designation_id buckets are franchise type)
    for d in body["designations"]:
        if d.get("designation_id"):
            assert d["office_type"] == "franchise"


def test_hirings_counts_include_new_lead(hdr, franchise_designation, created_ids):
    # Create a fresh lead under the franchise designation
    r = requests.post(f"{API}/leads", headers=hdr, json={
        "name": f"TEST_CountLead_{uuid.uuid4().hex[:6]}", "phone": "9000000010",
        "designation_id": franchise_designation["id"],
    }, timeout=15)
    assert r.status_code == 200
    created_ids["leads"].append(r.json()["id"])
    h = requests.get(f"{API}/hirings/franchise", headers=hdr, timeout=15).json()
    match = [d for d in h["designations"] if d.get("designation_id") == franchise_designation["id"]]
    assert match, "Designation bucket missing from hirings"
    assert match[0]["counts"]["new_lead"] >= 1
    assert match[0]["total"] >= 1


def test_hirings_legacy_job_role_matches(hdr, ho_designation, created_ids):
    # Create lead with NO designation_id, but job_role matching ho_designation.name (case-insensitive)
    legacy_role = ho_designation["name"].lower()
    r = requests.post(f"{API}/leads", headers=hdr, json={
        "name": f"TEST_LegLead_{uuid.uuid4().hex[:6]}", "phone": "9000000011",
        "is_technician": False, "job_role": legacy_role,
    }, timeout=15)
    assert r.status_code == 200, r.text
    created_ids["leads"].append(r.json()["id"])
    h = requests.get(f"{API}/hirings/head_office", headers=hdr, timeout=15).json()
    match = [d for d in h["designations"] if d.get("designation_id") == ho_designation["id"]]
    assert match, "ho_designation bucket not present"
    assert match[0]["counts"]["new_lead"] >= 1


def test_hirings_candidates_by_designation(hdr, franchise_designation, created_ids):
    # Create a fresh designation+leads to avoid dependency on global state
    nm = f"TEST_CandList_{uuid.uuid4().hex[:6]}"
    d = requests.post(f"{API}/designations", headers=hdr, json={"name": nm, "office_type": "franchise"}, timeout=15).json()
    created_ids["designations"].append(d["id"])

    a = requests.post(f"{API}/leads", headers=hdr, json={
        "name": f"TEST_A_{uuid.uuid4().hex[:6]}", "phone": "9000000020",
        "designation_id": d["id"],
    }, timeout=15).json()
    created_ids["leads"].append(a["id"])

    # Legacy lead — same name, no designation_id, lowercased
    b = requests.post(f"{API}/leads", headers=hdr, json={
        "name": f"TEST_B_{uuid.uuid4().hex[:6]}", "phone": "9000000021",
        "is_technician": True, "job_role": nm.lower(),
    }, timeout=15).json()
    created_ids["leads"].append(b["id"])

    r = requests.get(f"{API}/hirings/designations/{d['id']}/candidates", headers=hdr, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["designation"]["id"] == d["id"]
    ids = {c["id"] for c in body["candidates"]}
    assert a["id"] in ids and b["id"] in ids, f"Expected both candidates present, got {ids}"


def test_jobs_endpoint_soft_remove_still_works(hdr):
    r = requests.get(f"{API}/jobs", headers=hdr, timeout=15)
    # Soft-remove: endpoint should still respond, not 404 — we just check server didn't crash
    assert r.status_code in (200, 403), f"jobs endpoint unexpectedly returned {r.status_code}"


# ---------------- Final cleanup ----------------

def test_zz_cleanup(hdr, created_ids):
    _cleanup(hdr, created_ids)
