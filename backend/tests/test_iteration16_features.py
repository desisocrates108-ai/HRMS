"""Iteration 16: Employee Code (manual+unique), Lead job_role, Dashboard Open Positions widget."""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

ADMIN_EMAIL = "admin@servall.com"
ADMIN_PWD = "ServallAdmin@123"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============ EMPLOYEE CODE ============

class TestEmployeeCode:
    def test_missing_employee_code_422(self, H):
        # employee_code is required by pydantic -> 422
        r = requests.post(f"{BASE_URL}/api/employees", headers=H, json={
            "name": "TEST_NoCode", "employee_type": "head_office"
        })
        assert r.status_code in (400, 422), r.text

    def test_empty_employee_code_400(self, H):
        r = requests.post(f"{BASE_URL}/api/employees", headers=H, json={
            "name": "TEST_EmptyCode", "employee_type": "head_office", "employee_code": ""
        })
        assert r.status_code == 400, r.text
        assert "required" in r.json().get("detail", "").lower()

    def test_create_unique_employee_code(self, H):
        code = f"TEST_C_{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{BASE_URL}/api/employees", headers=H, json={
            "name": "TEST_Unique", "employee_type": "head_office", "employee_code": code
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["employee_code"] == code
        emp_id = body["id"]
        # GET back
        g = requests.get(f"{BASE_URL}/api/employees/{emp_id}", headers=H)
        assert g.status_code == 200
        assert g.json()["employee_code"] == code
        # cleanup
        requests.delete(f"{BASE_URL}/api/employees/{emp_id}", headers=H)

    def test_duplicate_employee_code_409(self, H):
        code = f"TEST_D_{uuid.uuid4().hex[:6].upper()}"
        r1 = requests.post(f"{BASE_URL}/api/employees", headers=H, json={
            "name": "TEST_Dup1", "employee_type": "head_office", "employee_code": code
        })
        assert r1.status_code == 200
        emp1 = r1.json()["id"]
        r2 = requests.post(f"{BASE_URL}/api/employees", headers=H, json={
            "name": "TEST_Dup2", "employee_type": "head_office", "employee_code": code
        })
        assert r2.status_code == 409, r2.text
        assert "already exists" in r2.json().get("detail", "").lower()
        requests.delete(f"{BASE_URL}/api/employees/{emp1}", headers=H)

    def test_update_employee_code_conflict_and_success(self, H):
        c1 = f"TEST_U1_{uuid.uuid4().hex[:6].upper()}"
        c2 = f"TEST_U2_{uuid.uuid4().hex[:6].upper()}"
        e1 = requests.post(f"{BASE_URL}/api/employees", headers=H, json={"name": "TEST_U1", "employee_type": "head_office", "employee_code": c1}).json()["id"]
        e2 = requests.post(f"{BASE_URL}/api/employees", headers=H, json={"name": "TEST_U2", "employee_type": "head_office", "employee_code": c2}).json()["id"]
        # Try to update e2 to use c1 -> 409
        r = requests.put(f"{BASE_URL}/api/employees/{e2}", headers=H, json={"employee_code": c1})
        assert r.status_code == 409, r.text
        # Update to new unique value
        c3 = f"TEST_U3_{uuid.uuid4().hex[:6].upper()}"
        r2 = requests.put(f"{BASE_URL}/api/employees/{e2}", headers=H, json={"employee_code": c3})
        assert r2.status_code == 200
        assert r2.json()["employee_code"] == c3
        # Persistence check
        g = requests.get(f"{BASE_URL}/api/employees/{e2}", headers=H).json()
        assert g["employee_code"] == c3
        # Empty -> 400
        r3 = requests.put(f"{BASE_URL}/api/employees/{e2}", headers=H, json={"employee_code": ""})
        assert r3.status_code == 400
        requests.delete(f"{BASE_URL}/api/employees/{e1}", headers=H)
        requests.delete(f"{BASE_URL}/api/employees/{e2}", headers=H)


# ============ LEADS job_role ============

class TestLeadJobRole:
    def test_leads_list_has_job_role(self, H):
        # Create a job
        job = requests.post(f"{BASE_URL}/api/jobs", headers=H, json={
            "role": "TEST_Role_SrvAdv", "type": "HO", "status": "open", "location": "HO"
        })
        assert job.status_code in (200, 201), job.text
        job_id = job.json()["id"]
        # Create lead linked
        l1 = requests.post(f"{BASE_URL}/api/leads", headers=H, json={
            "name": "TEST_LeadLinked", "phone": "9999000111", "job_id": job_id
        })
        assert l1.status_code == 200
        l1_id = l1.json()["id"]
        # Create lead unlinked
        l2 = requests.post(f"{BASE_URL}/api/leads", headers=H, json={
            "name": "TEST_LeadUnlinked", "phone": "9999000222"
        })
        assert l2.status_code == 200
        l2_id = l2.json()["id"]

        # List
        lst = requests.get(f"{BASE_URL}/api/leads", headers=H).json()
        m1 = next((x for x in lst if x["id"] == l1_id), None)
        m2 = next((x for x in lst if x["id"] == l2_id), None)
        assert m1 is not None and m1.get("job_role") == "TEST_Role_SrvAdv"
        assert m2 is not None and m2.get("job_role") is None

        # Single GET
        g1 = requests.get(f"{BASE_URL}/api/leads/{l1_id}", headers=H).json()
        g2 = requests.get(f"{BASE_URL}/api/leads/{l2_id}", headers=H).json()
        assert g1.get("job_role") == "TEST_Role_SrvAdv"
        assert g2.get("job_role") is None

        # cleanup
        requests.post(f"{BASE_URL}/api/leads/{l1_id}/delete", headers=H)
        requests.post(f"{BASE_URL}/api/leads/{l2_id}/delete", headers=H)
        requests.delete(f"{BASE_URL}/api/leads/{l1_id}", headers=H)
        requests.delete(f"{BASE_URL}/api/leads/{l2_id}", headers=H)
        requests.delete(f"{BASE_URL}/api/jobs/{job_id}", headers=H)


# ============ DASHBOARD OPEN POSITIONS ============

class TestOpenPositions:
    def test_open_positions_present_and_accurate(self, H):
        # Create 2 HO Service Advisor jobs + 1 branch Technician job
        role_sa = f"TEST_SA_{uuid.uuid4().hex[:5]}"
        role_tech = f"TEST_TECH_{uuid.uuid4().hex[:5]}"
        j1 = requests.post(f"{BASE_URL}/api/jobs", headers=H, json={
            "role": role_sa, "type": "HO", "status": "open", "location": "HO"
        }).json()
        j2 = requests.post(f"{BASE_URL}/api/jobs", headers=H, json={
            "role": role_sa, "type": "HO", "status": "open", "location": "HO"
        }).json()
        j3 = requests.post(f"{BASE_URL}/api/jobs", headers=H, json={
            "role": role_tech, "type": "branch", "status": "open", "location": "Pune"
        }).json()
        # Link 2 leads to j1
        la = requests.post(f"{BASE_URL}/api/leads", headers=H, json={
            "name": "TEST_AppA", "phone": "9990001001", "job_id": j1["id"]
        }).json()
        lb = requests.post(f"{BASE_URL}/api/leads", headers=H, json={
            "name": "TEST_AppB", "phone": "9990001002", "job_id": j1["id"]
        }).json()

        # Dashboard stats (CEO)
        ds = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=H)
        assert ds.status_code == 200, ds.text
        body = ds.json()
        assert "open_positions" in body, "open_positions key missing"
        op = body["open_positions"]
        assert "head_office" in op and "franchise" in op
        ho_sa = next((r for r in op["head_office"] if r["role"] == role_sa), None)
        fr_tech = next((r for r in op["franchise"] if r["role"] == role_tech), None)
        assert ho_sa is not None, f"HO Service Advisor row missing. head_office={op['head_office']}"
        assert ho_sa["openings"] == 2, f"Expected 2 openings, got {ho_sa['openings']}"
        assert ho_sa["applicants"] == 2, f"Expected 2 applicants, got {ho_sa['applicants']}"
        assert fr_tech is not None, f"Franchise Technician row missing. franchise={op['franchise']}"
        assert fr_tech["openings"] == 1
        assert fr_tech["applicants"] == 0

        # Date filter: future window -> applicants 0
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        ds2 = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=H, params={"date_from": future})
        assert ds2.status_code == 200
        op2 = ds2.json()["open_positions"]
        # openings still present (jobs not date-filtered) but applicants must be 0
        ho_sa2 = next((r for r in op2["head_office"] if r["role"] == role_sa), None)
        assert ho_sa2 is not None
        assert ho_sa2["openings"] == 2
        assert ho_sa2["applicants"] == 0, f"Expected 0 applicants in future window, got {ho_sa2['applicants']}"

        # cleanup
        for lid in (la["id"], lb["id"]):
            requests.post(f"{BASE_URL}/api/leads/{lid}/delete", headers=H)
            requests.delete(f"{BASE_URL}/api/leads/{lid}", headers=H)
        for jid in (j1["id"], j2["id"], j3["id"]):
            requests.delete(f"{BASE_URL}/api/jobs/{jid}", headers=H)
