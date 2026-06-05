"""Iteration 15 — Backend tests:
1) Soft delete / restore / hard delete on leads
2) Candidate Form public endpoints + uploads + download
3) Manager Round HR-block / assigned-manager / CEO override
"""
import os
import io
import json
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL")
assert BASE, "REACT_APP_BACKEND_URL not set"
BASE = BASE.rstrip("/")
API = f"{BASE}/api"

CEO_EMAIL = "admin@servall.com"
CEO_PASSWORD = "ServallAdmin@123"


# ------------------ fixtures ------------------

@pytest.fixture(scope="session")
def ceo_token():
    r = requests.post(f"{API}/auth/login", json={"email": CEO_EMAIL, "password": CEO_PASSWORD})
    assert r.status_code == 200, f"CEO login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def ceo_id(ceo_token):
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {ceo_token}"})
    assert r.status_code == 200
    return r.json()["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def hr_user(ceo_token):
    """Create a Sr HR user (idempotent by email)."""
    email = f"TEST_hr_{uuid.uuid4().hex[:6]}@servall.com"
    payload = {"name": "TEST HR User", "email": email, "password": "TestHR@1234", "role": "Sr HR"}
    r = requests.post(f"{API}/users", json=payload, headers=_auth(ceo_token))
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create HR user: {r.status_code} {r.text}")
    user_id = r.json().get("id") or r.json().get("user_id")
    # login
    lr = requests.post(f"{API}/auth/login", json={"email": email, "password": "TestHR@1234"})
    assert lr.status_code == 200, lr.text
    return {"id": user_id, "email": email, "token": lr.json()["access_token"]}


@pytest.fixture(scope="session")
def manager_user(ceo_token):
    email = f"TEST_mgr_{uuid.uuid4().hex[:6]}@servall.com"
    payload = {"name": "TEST Manager", "email": email, "password": "TestMgr@1234", "role": "Operations Manager"}
    r = requests.post(f"{API}/users", json=payload, headers=_auth(ceo_token))
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create Manager user: {r.status_code} {r.text}")
    user_id = r.json().get("id") or r.json().get("user_id")
    lr = requests.post(f"{API}/auth/login", json={"email": email, "password": "TestMgr@1234"})
    assert lr.status_code == 200, lr.text
    return {"id": user_id, "email": email, "token": lr.json()["access_token"]}


@pytest.fixture(scope="session")
def other_manager_user(ceo_token):
    email = f"TEST_mgr2_{uuid.uuid4().hex[:6]}@servall.com"
    payload = {"name": "TEST Manager 2", "email": email, "password": "TestMgr@1234", "role": "Operations Manager"}
    r = requests.post(f"{API}/users", json=payload, headers=_auth(ceo_token))
    if r.status_code not in (200, 201):
        pytest.skip(f"Cannot create 2nd Manager user: {r.status_code} {r.text}")
    user_id = r.json().get("id") or r.json().get("user_id")
    lr = requests.post(f"{API}/auth/login", json={"email": email, "password": "TestMgr@1234"})
    assert lr.status_code == 200, lr.text
    return {"id": user_id, "email": email, "token": lr.json()["access_token"]}


def _create_lead(token, name="TEST_Lead"):
    payload = {"name": f"{name}_{uuid.uuid4().hex[:6]}", "phone": f"9{uuid.uuid4().int % 1000000000:09d}",
               "email": f"lead_{uuid.uuid4().hex[:6]}@test.com", "source": "manual", "is_technician": False}
    r = requests.post(f"{API}/leads", json=payload, headers=_auth(token))
    assert r.status_code in (200, 201), r.text
    return r.json()


# ------------------ Auth ------------------

class TestAuth:
    def test_ceo_login(self, ceo_token):
        assert isinstance(ceo_token, str) and len(ceo_token) > 10


# ------------------ Soft delete / restore / hard delete ------------------

class TestLeadSoftDelete:
    def test_create_then_soft_delete(self, ceo_token):
        lead = _create_lead(ceo_token)
        lid = lead["id"]
        # soft delete
        r = requests.post(f"{API}/leads/{lid}/delete", headers=_auth(ceo_token))
        assert r.status_code == 200, r.text

        # not in default list
        r = requests.get(f"{API}/leads", headers=_auth(ceo_token))
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert lid not in ids

        # but in include_deleted=true
        r = requests.get(f"{API}/leads?include_deleted=true", headers=_auth(ceo_token))
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert lid in ids

        # GET /api/leads/deleted returns it
        r = requests.get(f"{API}/leads/deleted", headers=_auth(ceo_token))
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert lid in ids

    def test_restore_lead(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_Restore")
        lid = lead["id"]
        r = requests.post(f"{API}/leads/{lid}/delete", headers=_auth(ceo_token))
        assert r.status_code == 200
        r = requests.post(f"{API}/leads/{lid}/restore", headers=_auth(ceo_token))
        assert r.status_code == 200, r.text
        # appears in default list again
        r = requests.get(f"{API}/leads", headers=_auth(ceo_token))
        assert lid in [x["id"] for x in r.json()]

    def test_hard_delete_requires_soft_delete_first(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_HardDel")
        lid = lead["id"]
        # DELETE without soft delete first → 400
        r = requests.delete(f"{API}/leads/{lid}", headers=_auth(ceo_token))
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        # soft delete then hard delete
        requests.post(f"{API}/leads/{lid}/delete", headers=_auth(ceo_token))
        r = requests.delete(f"{API}/leads/{lid}", headers=_auth(ceo_token))
        assert r.status_code in (200, 204), r.text
        # Now not even in include_deleted=true
        r = requests.get(f"{API}/leads?include_deleted=true", headers=_auth(ceo_token))
        assert lid not in [x["id"] for x in r.json()]


# ------------------ Candidate Form ------------------

class TestCandidateForm:
    def test_send_form_returns_link(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_FormLead")
        lid = lead["id"]
        r = requests.post(f"{API}/candidate-forms/{lid}/send", headers=_auth(ceo_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert "token" in data and len(data["token"]) > 10
        assert "public_url" in data and "/candidate-form/" in data["public_url"]
        assert data["whatsapp"]["dispatched"] is False
        assert "not configured" in (data["whatsapp"].get("reason") or "").lower() or \
               "share link manually" in (data["whatsapp"].get("reason") or "").lower()

        # lead status sent
        r = requests.get(f"{API}/leads/{lid}", headers=_auth(ceo_token))
        assert r.status_code == 200
        assert r.json().get("candidate_form_status") == "sent"

    def test_public_form_get_404_for_bad_token(self):
        r = requests.get(f"{API}/candidate-forms/form/notatoken")
        assert r.status_code == 404

    def test_public_form_get_returns_schema(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_SchemaLead")
        lid = lead["id"]
        r = requests.post(f"{API}/candidate-forms/{lid}/send", headers=_auth(ceo_token))
        token = r.json()["token"]
        r = requests.get(f"{API}/candidate-forms/form/{token}")
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["personal", "education", "employment", "interview", "documents"]:
            assert k in data["schema"], f"missing section {k}"
        assert "candidate" in data
        assert "name" in data["candidate"]

    def test_submit_declaration_false_400(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_NoDeclLead")
        lid = lead["id"]
        token = requests.post(f"{API}/candidate-forms/{lid}/send", headers=_auth(ceo_token)).json()["token"]
        answers = json.dumps({"full_name": "John", "mobile": "9999999999", "email": "j@x.com"})
        r = requests.post(f"{API}/candidate-forms/form/{token}",
                          data={"answers": answers, "declaration": "false"})
        assert r.status_code == 400

    def test_submit_missing_required_400(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_MissReq")
        lid = lead["id"]
        token = requests.post(f"{API}/candidate-forms/{lid}/send", headers=_auth(ceo_token)).json()["token"]
        answers = json.dumps({"full_name": "John"})  # missing mobile/email
        r = requests.post(f"{API}/candidate-forms/form/{token}",
                          data={"answers": answers, "declaration": "true"})
        assert r.status_code == 400

    def test_submit_with_resume_and_full_flow(self, ceo_token):
        lead = _create_lead(ceo_token, "TEST_FullSubmit")
        lid = lead["id"]
        token = requests.post(f"{API}/candidate-forms/{lid}/send", headers=_auth(ceo_token)).json()["token"]
        answers = json.dumps({
            "full_name": "TEST Candidate",
            "mobile": "9876543210",
            "email": "testcand@example.com",
            "city": "Hyderabad",
        })
        files = {"resume": ("resume.pdf", io.BytesIO(b"%PDF-1.4 test pdf content"), "application/pdf")}
        r = requests.post(f"{API}/candidate-forms/form/{token}",
                          data={"answers": answers, "declaration": "true"},
                          files=files)
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True

        # Second submit → 410 gone
        r2 = requests.post(f"{API}/candidate-forms/form/{token}",
                           data={"answers": answers, "declaration": "true"})
        assert r2.status_code == 410

        # GET form → 410
        r3 = requests.get(f"{API}/candidate-forms/form/{token}")
        assert r3.status_code == 410

        # GET state (auth)
        r4 = requests.get(f"{API}/candidate-forms/{lid}", headers=_auth(ceo_token))
        assert r4.status_code == 200
        st = r4.json()
        assert st["status"] == "completed"
        assert st["submission"] is not None
        assert st["submission"]["documents"].get("resume") is not None

        # Lead reflects completion
        r5 = requests.get(f"{API}/leads/{lid}", headers=_auth(ceo_token))
        assert r5.json().get("candidate_form_status") == "completed"
        assert r5.json().get("candidate_form_data", {}).get("full_name") == "TEST Candidate"

        # Download resume
        r6 = requests.get(f"{API}/candidate-forms/{lid}/document/resume", headers=_auth(ceo_token))
        assert r6.status_code == 200, r6.text
        assert len(r6.content) > 5
        # Content-Disposition header should have filename
        cd = r6.headers.get("content-disposition", "")
        assert "resume" in cd.lower()

        # Unknown field → 400
        r7 = requests.get(f"{API}/candidate-forms/{lid}/document/unknown", headers=_auth(ceo_token))
        assert r7.status_code == 400

        # Missing doc (aadhaar not uploaded) → 404
        r8 = requests.get(f"{API}/candidate-forms/{lid}/document/aadhaar", headers=_auth(ceo_token))
        assert r8.status_code == 404


# ------------------ Manager Round permission ------------------

class TestManagerRoundPermission:
    def _setup_lead_in_manager_stage(self, ceo_token, manager_id):
        """Create lead, transition to manager_interview with assigned_manager_id."""
        lead = _create_lead(ceo_token, "TEST_MgrPerm")
        lid = lead["id"]
        interview_form = {
            "interview_date": "2026-02-01",
            "interview_time": "10:00",
            "mode": "in_person",
            "interview_city": "Hyderabad",
            "interview_place": "Office",
        }
        qualified_form = {"experience": "3 years", "location_confirmation": "yes", "salary_expectation": "5LPA", "relocation_preference": "yes"}
        # qualified → hr_interview
        for to_stage, form in [("qualified", qualified_form), ("hr_interview", interview_form)]:
            r = requests.post(f"{API}/leads/{lid}/transition",
                              json={"to_stage": to_stage, "form_data": form},
                              headers=_auth(ceo_token))
            if r.status_code not in (200, 201):
                pytest.skip(f"transition to {to_stage} failed: {r.status_code} {r.text}")
        # Submit HR interview (CEO) so we can move to manager_interview
        from auth_utils import HR_ROUND_CRITERIA
        hr_payload = {"ratings": {k: 4 for k in HR_ROUND_CRITERIA}, "remarks": "TEST"}
        r = requests.post(f"{API}/interviews/{lid}/hr", json=hr_payload, headers=_auth(ceo_token))
        if r.status_code != 200:
            pytest.skip(f"HR submit failed: {r.status_code} {r.text}")
        # now manager_interview
        r = requests.post(f"{API}/leads/{lid}/transition",
                          json={"to_stage": "manager_interview",
                                "form_data": dict(interview_form, manager_id=manager_id)},
                          headers=_auth(ceo_token))
        if r.status_code not in (200, 201):
            pytest.skip(f"transition to manager_interview failed: {r.status_code} {r.text}")
        return lid

    @pytest.fixture(scope="class")
    def manager_lead(self, ceo_token, manager_user):
        return self._setup_lead_in_manager_stage(ceo_token, manager_user["id"])

    def _ratings_payload(self):
        # All 10 manager criteria
        from auth_utils import MANAGER_ROUND_CRITERIA
        return {"ratings": {k: 4 for k in MANAGER_ROUND_CRITERIA}, "remarks": "TEST"}

    def test_hr_blocked_from_manager_round(self, manager_lead, hr_user):
        payload = self._ratings_payload()
        r = requests.post(f"{API}/interviews/{manager_lead}/manager",
                          json=payload, headers=_auth(hr_user["token"]))
        assert r.status_code == 403, f"HR must be blocked: {r.status_code} {r.text}"
        body = (r.json().get("detail") or "").lower()
        assert "hr" in body, f"detail should mention HR: {body}"

    def test_non_assigned_manager_blocked(self, manager_lead, other_manager_user):
        payload = self._ratings_payload()
        r = requests.post(f"{API}/interviews/{manager_lead}/manager",
                          json=payload, headers=_auth(other_manager_user["token"]))
        assert r.status_code == 403, f"non-assigned manager must be blocked: {r.status_code} {r.text}"

    def test_assigned_manager_can_submit(self, manager_lead, manager_user):
        payload = self._ratings_payload()
        r = requests.post(f"{API}/interviews/{manager_lead}/manager",
                          json=payload, headers=_auth(manager_user["token"]))
        assert r.status_code == 200, f"assigned manager submit failed: {r.status_code} {r.text}"

    def test_ceo_can_submit(self, manager_lead, ceo_token):
        payload = self._ratings_payload()
        r = requests.post(f"{API}/interviews/{manager_lead}/manager",
                          json=payload, headers=_auth(ceo_token))
        assert r.status_code == 200, f"CEO override failed: {r.status_code} {r.text}"

    def test_hr_can_submit_hr_round(self, ceo_token, hr_user):
        # create lead and transition to hr_interview stage
        lead = _create_lead(ceo_token, "TEST_HRRound")
        lid = lead["id"]
        interview_form = {
            "interview_date": "2026-02-01",
            "interview_time": "10:00",
            "mode": "in_person",
            "interview_city": "Hyderabad",
            "interview_place": "Office",
        }
        qualified_form = {"experience": "3 years", "location_confirmation": "yes", "salary_expectation": "5LPA", "relocation_preference": "yes"}
        for to_stage, form in [("qualified", qualified_form), ("hr_interview", interview_form)]:
            r = requests.post(f"{API}/leads/{lid}/transition",
                              json={"to_stage": to_stage, "form_data": form},
                              headers=_auth(ceo_token))
            if r.status_code not in (200, 201):
                pytest.skip(f"transition to {to_stage} failed: {r.status_code} {r.text}")
        from auth_utils import HR_ROUND_CRITERIA
        payload = {"ratings": {k: 4 for k in HR_ROUND_CRITERIA}, "remarks": "TEST HR"}
        r = requests.post(f"{API}/interviews/{lid}/hr", json=payload, headers=_auth(hr_user["token"]))
        assert r.status_code == 200, f"HR submit should succeed: {r.status_code} {r.text}"
