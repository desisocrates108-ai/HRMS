"""Iteration 13 — Designation Master CRUD, Jobs Archive/Delete, Employee Pipeline (Database),
Auto EMP codes, Excel template/export/import, Migration backfill.
"""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend .env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@servall.com"
ADMIN_PASSWORD = "ServallAdmin@123"


@pytest.fixture(scope="session")
def auth_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in response: {data}"
    return token


@pytest.fixture(scope="session")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ============ DESIGNATIONS ============
class TestDesignations:
    def test_list_seeded(self, headers):
        r = requests.get(f"{API}/designations", headers=headers, timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 10
        names = [d["name"] for d in items]
        for required in ["Technician", "Service Advisor", "Franchise Manager"]:
            assert required in names, f"Missing seeded designation: {required}"

    def test_create_and_duplicate(self, headers):
        unique = f"TEST_Des_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/designations", headers=headers, json={"name": unique}, timeout=10)
        assert r.status_code == 200, r.text
        des = r.json()
        assert des["name"] == unique
        assert des["active"] is True
        # Duplicate (case-insensitive)
        r2 = requests.post(f"{API}/designations", headers=headers, json={"name": unique.lower()}, timeout=10)
        assert r2.status_code == 400
        # Cleanup
        requests.delete(f"{API}/designations/{des['id']}", headers=headers, timeout=10)

    def test_update_and_delete(self, headers):
        name1 = f"TEST_Upd_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/designations", headers=headers, json={"name": name1}, timeout=10)
        assert r.status_code == 200
        did = r.json()["id"]
        name2 = name1 + "_v2"
        r2 = requests.put(f"{API}/designations/{did}", headers=headers, json={"name": name2, "active": False}, timeout=10)
        assert r2.status_code == 200, r2.text
        upd = r2.json()
        assert upd["name"] == name2
        assert upd["active"] is False
        # Delete (no refs)
        r3 = requests.delete(f"{API}/designations/{did}", headers=headers, timeout=10)
        assert r3.status_code == 200

    def test_delete_blocked_when_in_use(self, headers):
        name = f"TEST_Used_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/designations", headers=headers, json={"name": name}, timeout=10)
        assert r.status_code == 200
        did = r.json()["id"]
        # Create employee referencing it
        emp_r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_RefEmp", "employee_type": "head_office", "role": name,
        }, timeout=10)
        assert emp_r.status_code == 200, emp_r.text
        emp_id = emp_r.json()["id"]
        # Delete designation should fail
        r2 = requests.delete(f"{API}/designations/{did}", headers=headers, timeout=10)
        assert r2.status_code == 400
        # Cleanup
        requests.delete(f"{API}/employees/{emp_id}", headers=headers, timeout=10)


# ============ JOBS ARCHIVE / DELETE ============
class TestJobsLifecycle:
    def test_create_archive_reopen_delete(self, headers):
        # Use seeded designation
        ds = requests.get(f"{API}/designations", headers=headers).json()
        role = ds[0]["name"]
        payload = {
            "role": role, "type": "head_office",
            "location": "TEST_City", "description": "TEST job",
        }
        r = requests.post(f"{API}/jobs", headers=headers, json=payload, timeout=10)
        assert r.status_code == 200, r.text
        job = r.json()
        jid = job["id"]
        assert job["status"] == "open"

        # Archive
        ra = requests.post(f"{API}/jobs/{jid}/archive", headers=headers, timeout=10)
        assert ra.status_code == 200, ra.text
        get_r = requests.get(f"{API}/jobs/{jid}", headers=headers).json()
        assert get_r["status"] == "closed"

        # Reopen
        rr = requests.post(f"{API}/jobs/{jid}/reopen", headers=headers, timeout=10)
        assert rr.status_code == 200, rr.text
        assert requests.get(f"{API}/jobs/{jid}", headers=headers).json()["status"] == "open"

        # Delete
        rd = requests.delete(f"{API}/jobs/{jid}", headers=headers, timeout=10)
        assert rd.status_code == 200, rd.text
        assert requests.get(f"{API}/jobs/{jid}", headers=headers).status_code == 404


# ============ EMPLOYEES (PIPELINE) ============
class TestEmployeesPipeline:
    def test_create_auto_code(self, headers):
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_AutoEmp", "employee_type": "franchise",
        }, timeout=10)
        assert r.status_code == 200, r.text
        e = r.json()
        assert e["employee_code"].startswith("EMP") and len(e["employee_code"]) == 7
        assert e["employee_type"] == "franchise"
        assert e["current_stage"] == "new"
        # Cleanup
        requests.delete(f"{API}/employees/{e['id']}", headers=headers, timeout=10)

    def test_invalid_employee_type(self, headers):
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_BadType", "employee_type": "invalid",
        }, timeout=10)
        assert r.status_code == 400

    def test_manual_code_and_duplicate(self, headers):
        code = f"EMP{uuid.uuid4().hex[:4].upper()}"
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_ManualCode", "employee_type": "head_office", "employee_code": code,
        }, timeout=10)
        assert r.status_code == 200, r.text
        emp_id = r.json()["id"]
        assert r.json()["employee_code"] == code
        # Duplicate
        r2 = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_DupCode", "employee_type": "head_office", "employee_code": code,
        }, timeout=10)
        assert r2.status_code == 400
        requests.delete(f"{API}/employees/{emp_id}", headers=headers, timeout=10)

    def test_pipeline_stats_shape(self, headers):
        r = requests.get(f"{API}/employees/pipeline-stats", headers=headers, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "stage_counts" in data and "summary" in data
        expected_stages = {"new", "qualified", "hr", "manager", "selected", "three_months", "joined", "hold", "rejected"}
        assert set(data["stage_counts"].keys()) == expected_stages
        for k in ["total", "head_office", "franchise", "joined", "hold", "rejected"]:
            assert k in data["summary"]

    def test_transition_hold_requires_reason(self, headers):
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_HoldEmp", "employee_type": "head_office",
        }, timeout=10)
        emp_id = r.json()["id"]
        # Missing reason
        t = requests.post(f"{API}/employees/{emp_id}/transition", headers=headers,
                          json={"to_stage": "hold"}, timeout=10)
        assert t.status_code == 400
        # With reason
        t2 = requests.post(f"{API}/employees/{emp_id}/transition", headers=headers,
                           json={"to_stage": "hold", "hold_reason": "TEST waiting on docs"}, timeout=10)
        assert t2.status_code == 200
        assert t2.json()["current_stage"] == "hold"
        requests.delete(f"{API}/employees/{emp_id}", headers=headers, timeout=10)

    def test_transition_rejected_requires_reason(self, headers):
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_RejEmp", "employee_type": "franchise",
        }, timeout=10)
        emp_id = r.json()["id"]
        t = requests.post(f"{API}/employees/{emp_id}/transition", headers=headers,
                          json={"to_stage": "rejected"}, timeout=10)
        assert t.status_code == 400
        t2 = requests.post(f"{API}/employees/{emp_id}/transition", headers=headers,
                           json={"to_stage": "rejected", "rejection_reason": "TEST not fit"}, timeout=10)
        assert t2.status_code == 200
        assert t2.json()["current_stage"] == "rejected"
        assert t2.json()["status"] == "left"
        requests.delete(f"{API}/employees/{emp_id}", headers=headers, timeout=10)

    def test_transition_joined_sets_active(self, headers):
        r = requests.post(f"{API}/employees", headers=headers, json={
            "name": "TEST_JoinEmp", "employee_type": "head_office",
        }, timeout=10)
        emp_id = r.json()["id"]
        t = requests.post(f"{API}/employees/{emp_id}/transition", headers=headers,
                          json={"to_stage": "joined"}, timeout=10)
        assert t.status_code == 200, t.text
        body = t.json()
        assert body["current_stage"] == "joined"
        assert body["status"] == "active"
        # History
        h = requests.get(f"{API}/employees/{emp_id}/history", headers=headers, timeout=10)
        assert h.status_code == 200
        logs = h.json()
        assert len(logs) >= 2
        assert logs[0]["to_stage"] == "joined"
        requests.delete(f"{API}/employees/{emp_id}", headers=headers, timeout=10)


# ============ EXCEL ============
class TestExcel:
    def test_template_download(self, headers):
        r = requests.get(f"{API}/employees/excel/template", headers=headers, timeout=15)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert len(r.content) > 1000

    def test_export(self, headers):
        r = requests.get(f"{API}/employees/excel/export", headers=headers, timeout=15)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert len(r.content) > 500

    def test_import_with_valid_and_invalid_rows(self, headers):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append([
            "Name", "Phone", "Email", "Employee Type", "Stage", "Designation",
            "Department", "Branch ID", "City", "Area",
            "Joining Date (YYYY-MM-DD)", "Salary", "Employee Code (optional)",
        ])
        ws.append(["TEST_Imp_A", "999", "a@x.com", "head_office", "new", "Technician",
                   "", "", "Mumbai", "", "2025-01-01", 30000, ""])
        ws.append(["TEST_Imp_B", "888", "b@x.com", "franchise", "selected", "Service Advisor",
                   "", "", "Pune", "", "2025-02-01", 25000, ""])
        # Invalid stage
        ws.append(["TEST_Imp_C", "777", "c@x.com", "head_office", "bogus", "", "", "", "", "", "", "", ""])
        # Invalid emp type
        ws.append(["TEST_Imp_D", "666", "d@x.com", "alien", "new", "", "", "", "", "", "", "", ""])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        files = {"file": ("emp.xlsx", buf.getvalue(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        # Don't include content-type in headers for multipart
        h = {"Authorization": headers["Authorization"]}
        r = requests.post(f"{API}/employees/excel/import", headers=h, files=files, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["created"] == 2
        assert body["skipped"] >= 2
        assert len(body["errors"]) >= 2


# ============ MIGRATION (sanity check after restart) ============
class TestMigration:
    def test_existing_employees_have_pipeline_fields(self, headers):
        # All employees returned by API should have employee_type, current_stage, status, employee_code
        r = requests.get(f"{API}/employees", headers=headers, timeout=10)
        assert r.status_code == 200
        for e in r.json():
            assert e.get("employee_type") in ("head_office", "franchise"), f"Missing employee_type on {e.get('id')}"
            assert e.get("current_stage"), f"Missing current_stage on {e.get('id')}"
            assert e.get("status"), f"Missing status on {e.get('id')}"
            assert e.get("employee_code"), f"Missing employee_code on {e.get('id')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
