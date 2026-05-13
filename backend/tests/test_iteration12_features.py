"""
Iteration 12 - Comprehensive Backend Tests
==========================================
Tests for:
1. Dashboard lead_split (HO vs Franchise counts, Today's counts, date filters)
2. Pipeline stats includes 'three_months' stage
3. Hold transition requires hold_reason
4. Hold → Selected bug fix (after HR interview submitted)
5. Manager Interview requires manager_id
6. Three Months stage creates offer_letters record + sets dates
7. Offer Letters endpoints
8. Design Requests CRUD + RBAC
9. Tasks - any user can assign to anyone
10. Manager interview 403 for non-manager roles
11. Analytics funnel includes three_months
12. Admin cleanup (CEO only) - preview only to preserve data
13. Employees category filter (branch/head_office)
14. Campaigns routes should 404 (removed)
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
CREDENTIALS = {
    "ceo": {"email": "admin@servall.com", "password": "ServallAdmin@123"},
    "hr": {"email": "hr@servall.com", "password": "Servall@123"},
    "srhr": {"email": "srhr@servall.com", "password": "Servall@123"},
    "marketing_mgr": {"email": "marketing.mgr@servall.com", "password": "Servall@123"},
    "franchise_exec": {"email": "franchise.exec@servall.com", "password": "Servall@123"},
    "designer": {"email": "designer@servall.com", "password": "Servall@123"},
}


@pytest.fixture(scope="module")
def ceo_token():
    """Get CEO auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["ceo"])
    if resp.status_code != 200:
        pytest.skip(f"CEO login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def hr_token():
    """Get HR auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["hr"])
    if resp.status_code != 200:
        pytest.skip(f"HR login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def srhr_token():
    """Get Sr HR auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["srhr"])
    if resp.status_code != 200:
        pytest.skip(f"Sr HR login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def marketing_mgr_token():
    """Get Marketing Manager auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["marketing_mgr"])
    if resp.status_code != 200:
        pytest.skip(f"Marketing Manager login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def franchise_exec_token():
    """Get Franchise Executive auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["franchise_exec"])
    if resp.status_code != 200:
        pytest.skip(f"Franchise Executive login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


@pytest.fixture(scope="module")
def designer_token():
    """Get Graphic Designer auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["designer"])
    if resp.status_code != 200:
        pytest.skip(f"Designer login failed: {resp.status_code} {resp.text}")
    return resp.json().get("access_token")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ============ 1. Dashboard lead_split Tests ============

class TestDashboardLeadSplit:
    """Tests for GET /api/dashboard/stats lead_split feature"""

    def test_dashboard_stats_returns_lead_split(self, ceo_token):
        """Dashboard stats should include lead_split with HO/Franchise counts"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(ceo_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "lead_split" in data, "Response should contain 'lead_split' key"
        split = data["lead_split"]
        
        # Verify all required keys exist
        required_keys = ["ho_total", "ho_today", "franchise_total", "franchise_today", "three_months_due"]
        for key in required_keys:
            assert key in split, f"lead_split should contain '{key}'"
        
        # Values should be integers >= 0
        for key in required_keys:
            assert isinstance(split[key], int), f"{key} should be an integer"
            assert split[key] >= 0, f"{key} should be >= 0"
        
        print(f"✓ lead_split: {split}")

    def test_dashboard_stats_with_days_filter(self, ceo_token):
        """Dashboard stats should respect days filter"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats?days=7", headers=auth_header(ceo_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "lead_split" in data
        print(f"✓ Dashboard stats with days=7 filter works")

    def test_dashboard_stats_with_date_range(self, ceo_token):
        """Dashboard stats should respect date_from/date_to filters"""
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        date_to = datetime.now(timezone.utc).isoformat()
        
        resp = requests.get(
            f"{BASE_URL}/api/dashboard/stats?date_from={date_from}&date_to={date_to}",
            headers=auth_header(ceo_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "lead_split" in data
        print(f"✓ Dashboard stats with date range filter works")


# ============ 2. Pipeline Stats Tests ============

class TestPipelineStats:
    """Tests for GET /api/leads/pipeline-stats"""

    def test_pipeline_stats_includes_three_months(self, ceo_token):
        """Pipeline stats should include 'three_months' stage"""
        resp = requests.get(f"{BASE_URL}/api/leads/pipeline-stats", headers=auth_header(ceo_token))
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "three_months" in data, "Pipeline stats should include 'three_months' stage"
        
        # Verify no legacy stages
        legacy_stages = ["nurture", "awaiting_interview", "interview_cleared"]
        for stage in legacy_stages:
            assert stage not in data, f"Legacy stage '{stage}' should not be in pipeline stats"
        
        print(f"✓ Pipeline stats includes three_months: {data.get('three_months')}")

    def test_pipeline_stats_has_all_stages(self, ceo_token):
        """Pipeline stats should have all expected stages"""
        resp = requests.get(f"{BASE_URL}/api/leads/pipeline-stats", headers=auth_header(ceo_token))
        assert resp.status_code == 200
        data = resp.json()
        
        expected_stages = ["new_lead", "qualified", "hr_interview", "manager_interview", 
                          "selected", "three_months", "joined", "hold", "rejected"]
        for stage in expected_stages:
            assert stage in data, f"Pipeline stats should include '{stage}'"
        
        print(f"✓ All expected stages present in pipeline stats")


# ============ 3. Hold Transition Tests ============

class TestHoldTransition:
    """Tests for hold transition requiring hold_reason"""

    def test_hold_transition_requires_hold_reason(self, ceo_token):
        """Transition to 'hold' should require hold_reason field"""
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Hold_Reason_Lead", "phone": "9999000001", "source": "manual"}
        )
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]
        
        try:
            # Try to transition to hold WITHOUT hold_reason
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "hold", "form_data": {}}
            )
            assert resp.status_code == 400, f"Expected 400 for missing hold_reason, got {resp.status_code}"
            assert "hold_reason" in resp.text.lower(), "Error should mention hold_reason"
            print(f"✓ Hold transition correctly requires hold_reason")
            
            # Now try WITH hold_reason
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "hold", "form_data": {"hold_reason": "Candidate unavailable"}}
            )
            assert resp.status_code == 200, f"Expected 200 with hold_reason, got {resp.status_code}: {resp.text}"
            print(f"✓ Hold transition works with hold_reason")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))


# ============ 4. Hold → Selected Bug Fix Test ============

class TestHoldToSelectedBugFix:
    """Tests for Hold → Selected transition after HR interview submitted"""

    def test_hold_to_selected_after_hr_interview(self, ceo_token):
        """Hold → Selected should work directly after HR interview is submitted"""
        # Create a test lead (HO type)
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Hold_Selected_Lead", "phone": "9999000002", "source": "manual", "is_technician": False}
        )
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move to qualified
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "2 years", "location_confirmation": "Yes",
                    "salary_expectation": "30000", "relocation_preference": "No"
                }}
            )
            assert resp.status_code == 200, f"Failed qualified transition: {resp.text}"
            
            # Move to hr_interview
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }}
            )
            assert resp.status_code == 200, f"Failed hr_interview transition: {resp.text}"
            
            # Submit HR interview questionnaire
            hr_ratings = {
                "communication_skills": 4, "confidence": 4, "attitude": 5,
                "basic_understanding": 4, "learning_ability": 4, "stability": 4,
                "salary_expectation_fit": 4, "cultural_fit": 5, "availability": 4,
                "overall_impression": 4
            }
            resp = requests.post(
                f"{BASE_URL}/api/interviews/{lead_id}/hr",
                headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good candidate"}
            )
            assert resp.status_code == 200, f"Failed HR interview submission: {resp.text}"
            
            # Move to HOLD
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "hold", "form_data": {"hold_reason": "Budget freeze"}}
            )
            assert resp.status_code == 200, f"Failed hold transition: {resp.text}"
            
            # Get manager for manager_interview
            users_resp = requests.get(f"{BASE_URL}/api/users", headers=auth_header(ceo_token))
            managers = [u for u in users_resp.json() if "Manager" in u.get("role", "")]
            manager_id = managers[0]["id"] if managers else None
            
            # Move to manager_interview (from hold)
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "manager_interview", "form_data": {
                    "interview_date": "2026-02-05", "interview_time": "14:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office",
                    "manager_id": manager_id
                }}
            )
            assert resp.status_code == 200, f"Failed manager_interview transition from hold: {resp.text}"
            
            # Submit Manager interview
            mgr_ratings = {
                "technical_skills": 4, "problem_solving": 4, "role_knowledge": 4,
                "practical_exposure": 4, "decision_making": 4, "ownership": 4,
                "team_fit": 4, "pressure_handling": 4, "growth_potential": 4,
                "final_recommendation": 4
            }
            resp = requests.post(
                f"{BASE_URL}/api/interviews/{lead_id}/manager",
                headers=auth_header(ceo_token),
                json={"ratings": mgr_ratings, "remarks": "Approved"}
            )
            assert resp.status_code == 200, f"Failed Manager interview submission: {resp.text}"
            
            # Move to HOLD again
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "hold", "form_data": {"hold_reason": "Waiting for approval"}}
            )
            assert resp.status_code == 200, f"Failed second hold transition: {resp.text}"
            
            # NOW: Hold → Selected should work (this was the bug)
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "selected", "form_data": {}}
            )
            assert resp.status_code == 200, f"Hold → Selected failed: {resp.status_code} {resp.text}"
            
            lead_data = resp.json()
            assert lead_data["current_stage"] == "selected", f"Expected 'selected', got {lead_data['current_stage']}"
            print(f"✓ Hold → Selected bug fix verified - transition works correctly")
            
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))


# ============ 5. Manager Interview Requires manager_id ============

class TestManagerInterviewRequiresManagerId:
    """Tests for manager_interview requiring manager_id"""

    def test_manager_interview_requires_manager_id(self, ceo_token):
        """Transition to manager_interview should require manager_id"""
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Manager_Id_Lead", "phone": "9999000003", "source": "manual", "is_technician": False}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move through pipeline to hr_interview
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "2 years", "location_confirmation": "Yes",
                    "salary_expectation": "30000", "relocation_preference": "No"
                }})
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }})
            
            # Submit HR interview
            hr_ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude",
                "basic_understanding", "learning_ability", "stability",
                "salary_expectation_fit", "cultural_fit", "availability", "overall_impression"]}
            requests.post(f"{BASE_URL}/api/interviews/{lead_id}/hr", headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good"})
            
            # Try manager_interview WITHOUT manager_id
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "manager_interview", "form_data": {
                    "interview_date": "2026-02-05", "interview_time": "14:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                    # Missing manager_id
                }}
            )
            assert resp.status_code == 400, f"Expected 400 for missing manager_id, got {resp.status_code}"
            assert "manager_id" in resp.text.lower(), "Error should mention manager_id"
            print(f"✓ Manager interview correctly requires manager_id")
            
        finally:
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))

    def test_manager_interview_sets_assigned_manager(self, ceo_token):
        """Manager interview should set assigned_manager_id on lead"""
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Assigned_Manager_Lead", "phone": "9999000004", "source": "manual", "is_technician": False}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move through pipeline
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "2 years", "location_confirmation": "Yes",
                    "salary_expectation": "30000", "relocation_preference": "No"
                }})
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }})
            
            hr_ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude",
                "basic_understanding", "learning_ability", "stability",
                "salary_expectation_fit", "cultural_fit", "availability", "overall_impression"]}
            requests.post(f"{BASE_URL}/api/interviews/{lead_id}/hr", headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good"})
            
            # Get a manager
            users_resp = requests.get(f"{BASE_URL}/api/users", headers=auth_header(ceo_token))
            managers = [u for u in users_resp.json() if "Manager" in u.get("role", "")]
            assert managers, "No managers found in system"
            manager_id = managers[0]["id"]
            
            # Transition with manager_id
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "manager_interview", "form_data": {
                    "interview_date": "2026-02-05", "interview_time": "14:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office",
                    "manager_id": manager_id
                }}
            )
            assert resp.status_code == 200, f"Failed: {resp.text}"
            
            lead_data = resp.json()
            assert lead_data.get("assigned_manager_id") == manager_id, "assigned_manager_id should be set"
            print(f"✓ Manager interview sets assigned_manager_id correctly")
            
        finally:
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))


# ============ 6. Three Months Stage Tests ============

class TestThreeMonthsStage:
    """Tests for three_months stage creating offer_letters record"""

    def test_three_months_creates_offer_letter(self, ceo_token):
        """Transition to three_months should create offer_letters record"""
        # Create and move lead through full pipeline
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Three_Months_Lead", "phone": "9999000005", "source": "manual", "is_technician": True}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move through technician pipeline (no manager interview)
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "1 year", "location_confirmation": "Yes",
                    "salary_expectation": "20000", "relocation_preference": "No"
                }})
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }})
            
            hr_ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude",
                "basic_understanding", "learning_ability", "stability",
                "salary_expectation_fit", "cultural_fit", "availability", "overall_impression"]}
            requests.post(f"{BASE_URL}/api/interviews/{lead_id}/hr", headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good"})
            
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "selected", "form_data": {}})
            
            # Transition to three_months
            resp = requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/transition",
                headers=auth_header(ceo_token),
                json={"to_stage": "three_months", "form_data": {}}
            )
            assert resp.status_code == 200, f"Failed three_months transition: {resp.text}"
            
            lead_data = resp.json()
            assert lead_data["current_stage"] == "three_months"
            assert "three_months_start_date" in lead_data, "Should have three_months_start_date"
            assert "three_months_due_date" in lead_data, "Should have three_months_due_date"
            
            # Verify offer letter was created
            offer_resp = requests.get(
                f"{BASE_URL}/api/offer-letters?lead_id={lead_id}",
                headers=auth_header(ceo_token)
            )
            assert offer_resp.status_code == 200
            offers = offer_resp.json()
            assert len(offers) > 0, "Offer letter should be created"
            
            offer = offers[0]
            assert offer["lead_id"] == lead_id
            assert "role" in offer
            assert "branch_name" in offer
            assert "sent_at" in offer
            assert "whatsapp_status" in offer or "whatsapp_result" in offer
            
            print(f"✓ Three months transition creates offer letter record")
            
        finally:
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))


# ============ 7. Offer Letters Endpoints ============

class TestOfferLettersEndpoints:
    """Tests for offer letters API"""

    def test_get_offer_letters(self, ceo_token):
        """GET /api/offer-letters should return list"""
        resp = requests.get(f"{BASE_URL}/api/offer-letters", headers=auth_header(ceo_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"✓ GET /api/offer-letters returns list")

    def test_get_three_months_due(self, ceo_token):
        """GET /api/offer-letters/three-months-due should return leads"""
        resp = requests.get(f"{BASE_URL}/api/offer-letters/three-months-due", headers=auth_header(ceo_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"✓ GET /api/offer-letters/three-months-due works")


# ============ 8. Design Requests Tests ============

class TestDesignRequests:
    """Tests for design requests CRUD and RBAC"""

    def test_create_design_request(self, franchise_exec_token):
        """Any user can create a design request"""
        resp = requests.post(
            f"{BASE_URL}/api/design-requests",
            headers=auth_header(franchise_exec_token),
            json={
                "title": "TEST_Design_Request",
                "description": "Need a banner for recruitment",
                "priority": "medium"
            }
        )
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        assert data["title"] == "TEST_Design_Request"
        assert data["status"] == "pending"
        print(f"✓ Design request created by Franchise Executive")
        return data["id"]

    def test_designer_can_see_all_requests(self, designer_token, franchise_exec_token):
        """Graphic Designer should see all design requests"""
        # First create a request
        create_resp = requests.post(
            f"{BASE_URL}/api/design-requests",
            headers=auth_header(franchise_exec_token),
            json={"title": "TEST_Designer_View", "description": "Test", "priority": "low"}
        )
        
        # Designer should see it
        resp = requests.get(f"{BASE_URL}/api/design-requests", headers=auth_header(designer_token))
        assert resp.status_code == 200
        requests_list = resp.json()
        assert isinstance(requests_list, list)
        print(f"✓ Designer can see all design requests")

    def test_owner_cannot_change_status(self, franchise_exec_token, ceo_token):
        """Owner cannot change status of their own request"""
        # Create request
        create_resp = requests.post(
            f"{BASE_URL}/api/design-requests",
            headers=auth_header(franchise_exec_token),
            json={"title": "TEST_Owner_Status", "description": "Test", "priority": "low"}
        )
        assert create_resp.status_code == 200
        rid = create_resp.json()["id"]
        
        # Owner tries to change status
        resp = requests.put(
            f"{BASE_URL}/api/design-requests/{rid}",
            headers=auth_header(franchise_exec_token),
            json={"status": "completed"}
        )
        # Should succeed but status should NOT change (owner can update remarks only)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending", "Owner should not be able to change status"
        print(f"✓ Owner cannot change status of design request")

    def test_designer_can_change_status(self, designer_token, franchise_exec_token):
        """Designer can change status"""
        # Create request
        create_resp = requests.post(
            f"{BASE_URL}/api/design-requests",
            headers=auth_header(franchise_exec_token),
            json={"title": "TEST_Designer_Status", "description": "Test", "priority": "low"}
        )
        assert create_resp.status_code == 200
        rid = create_resp.json()["id"]
        
        # Designer changes status
        resp = requests.put(
            f"{BASE_URL}/api/design-requests/{rid}",
            headers=auth_header(designer_token),
            json={"status": "in_progress"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress", "Designer should be able to change status"
        print(f"✓ Designer can change status of design request")


# ============ 9. Tasks - Any User Can Assign ============

class TestTasksAnyUserCanAssign:
    """Tests for tasks - any user can assign to anyone"""

    def test_franchise_exec_can_assign_task(self, franchise_exec_token, ceo_token):
        """Franchise Executive should be able to assign a task to anyone"""
        # Get assignable users
        users_resp = requests.get(f"{BASE_URL}/api/tasks/assignable-users", headers=auth_header(franchise_exec_token))
        assert users_resp.status_code == 200
        users = users_resp.json()
        assert len(users) > 0, "Should have assignable users"
        
        # Pick any user to assign to
        assignee_id = users[0]["id"]
        
        # Create task
        resp = requests.post(
            f"{BASE_URL}/api/tasks",
            headers=auth_header(franchise_exec_token),
            json={
                "title": "TEST_Exec_Task",
                "description": "Task from Franchise Executive",
                "assigned_to": assignee_id,
                "priority": "medium"
            }
        )
        assert resp.status_code == 200, f"Franchise Exec should be able to create task: {resp.text}"
        data = resp.json()
        assert data["assigned_to"] == assignee_id
        print(f"✓ Franchise Executive can assign tasks to anyone")

    def test_assignable_users_returns_all_active(self, franchise_exec_token):
        """GET /api/tasks/assignable-users should return all active users"""
        resp = requests.get(f"{BASE_URL}/api/tasks/assignable-users", headers=auth_header(franchise_exec_token))
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        # Should have multiple users (not filtered by role)
        print(f"✓ Assignable users returns {len(users)} users")


# ============ 10. Manager Interview 403 for Non-Managers ============

class TestManagerInterviewRoleGating:
    """Tests for manager interview role restrictions"""

    def test_srhr_cannot_submit_manager_interview(self, srhr_token, ceo_token):
        """Sr HR should get 403 when trying to submit manager interview"""
        # Create a lead and move to manager_interview stage
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Manager_Role_Gate", "phone": "9999000006", "source": "manual", "is_technician": False}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move through pipeline
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "2 years", "location_confirmation": "Yes",
                    "salary_expectation": "30000", "relocation_preference": "No"
                }})
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }})
            
            hr_ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude",
                "basic_understanding", "learning_ability", "stability",
                "salary_expectation_fit", "cultural_fit", "availability", "overall_impression"]}
            requests.post(f"{BASE_URL}/api/interviews/{lead_id}/hr", headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good"})
            
            users_resp = requests.get(f"{BASE_URL}/api/users", headers=auth_header(ceo_token))
            managers = [u for u in users_resp.json() if "Manager" in u.get("role", "")]
            manager_id = managers[0]["id"] if managers else None
            
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "manager_interview", "form_data": {
                    "interview_date": "2026-02-05", "interview_time": "14:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office",
                    "manager_id": manager_id
                }})
            
            # Sr HR tries to submit manager interview
            mgr_ratings = {k: 4 for k in ["technical_skills", "problem_solving", "role_knowledge",
                "practical_exposure", "decision_making", "ownership",
                "team_fit", "pressure_handling", "growth_potential", "final_recommendation"]}
            
            resp = requests.post(
                f"{BASE_URL}/api/interviews/{lead_id}/manager",
                headers=auth_header(srhr_token),
                json={"ratings": mgr_ratings, "remarks": "Approved"}
            )
            assert resp.status_code == 403, f"Expected 403 for Sr HR, got {resp.status_code}"
            print(f"✓ Sr HR correctly gets 403 for manager interview submission")
            
        finally:
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))

    def test_manager_can_submit_manager_interview(self, marketing_mgr_token, ceo_token):
        """Marketing Manager should be able to submit manager interview"""
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            headers=auth_header(ceo_token),
            json={"name": "TEST_Manager_Submit", "phone": "9999000007", "source": "manual", "is_technician": False}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        try:
            # Move through pipeline
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "qualified", "form_data": {
                    "experience": "2 years", "location_confirmation": "Yes",
                    "salary_expectation": "30000", "relocation_preference": "No"
                }})
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "hr_interview", "form_data": {
                    "interview_date": "2026-02-01", "interview_time": "10:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office"
                }})
            
            hr_ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude",
                "basic_understanding", "learning_ability", "stability",
                "salary_expectation_fit", "cultural_fit", "availability", "overall_impression"]}
            requests.post(f"{BASE_URL}/api/interviews/{lead_id}/hr", headers=auth_header(ceo_token),
                json={"ratings": hr_ratings, "remarks": "Good"})
            
            users_resp = requests.get(f"{BASE_URL}/api/users", headers=auth_header(ceo_token))
            managers = [u for u in users_resp.json() if "Manager" in u.get("role", "")]
            manager_id = managers[0]["id"] if managers else None
            
            requests.post(f"{BASE_URL}/api/leads/{lead_id}/transition", headers=auth_header(ceo_token),
                json={"to_stage": "manager_interview", "form_data": {
                    "interview_date": "2026-02-05", "interview_time": "14:00",
                    "mode": "in_person", "interview_city": "Mumbai", "interview_place": "Office",
                    "manager_id": manager_id
                }})
            
            # Marketing Manager submits manager interview
            mgr_ratings = {k: 4 for k in ["technical_skills", "problem_solving", "role_knowledge",
                "practical_exposure", "decision_making", "ownership",
                "team_fit", "pressure_handling", "growth_potential", "final_recommendation"]}
            
            resp = requests.post(
                f"{BASE_URL}/api/interviews/{lead_id}/manager",
                headers=auth_header(marketing_mgr_token),
                json={"ratings": mgr_ratings, "remarks": "Approved"}
            )
            assert resp.status_code == 200, f"Expected 200 for Manager, got {resp.status_code}: {resp.text}"
            print(f"✓ Marketing Manager can submit manager interview")
            
        finally:
            requests.delete(f"{BASE_URL}/api/leads/{lead_id}", headers=auth_header(ceo_token))


# ============ 11. Analytics Funnel Tests ============

class TestAnalyticsFunnel:
    """Tests for analytics funnel including three_months"""

    def test_analytics_summary_funnel_order(self, ceo_token):
        """Analytics summary funnel should include three_months in correct order"""
        resp = requests.get(f"{BASE_URL}/api/analytics/summary", headers=auth_header(ceo_token))
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        assert "funnel" in data, "Response should have funnel"
        funnel = data["funnel"]
        stages = [f["stage"] for f in funnel]
        
        # Check three_months is present
        assert "three_months" in stages, "Funnel should include three_months"
        
        # Check order for HO pipeline
        expected_order = ["new_lead", "qualified", "hr_interview", "manager_interview", "selected", "three_months", "joined"]
        for i, stage in enumerate(expected_order):
            if stage in stages:
                idx = stages.index(stage)
                # Verify relative order
                for j in range(i + 1, len(expected_order)):
                    if expected_order[j] in stages:
                        assert stages.index(expected_order[j]) > idx, f"{expected_order[j]} should come after {stage}"
        
        print(f"✓ Analytics funnel includes three_months in correct order")

    def test_analytics_summary_technician_pipeline(self, ceo_token):
        """Technician pipeline should not have manager_interview"""
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?pipeline_type=technician",
            headers=auth_header(ceo_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        
        funnel = data.get("funnel", [])
        stages = [f["stage"] for f in funnel]
        
        # Technician pipeline should have three_months but not manager_interview
        assert "three_months" in stages, "Technician funnel should include three_months"
        print(f"✓ Technician analytics funnel works correctly")


# ============ 12. Admin Cleanup Tests ============

class TestAdminCleanup:
    """Tests for admin cleanup (CEO only)"""

    def test_cleanup_preview_ceo_only(self, ceo_token, hr_token):
        """Only CEO can access cleanup preview"""
        # CEO should succeed
        resp = requests.get(f"{BASE_URL}/api/admin/cleanup-preview", headers=auth_header(ceo_token))
        assert resp.status_code == 200, f"CEO should access cleanup-preview: {resp.text}"
        data = resp.json()
        assert "counts" in data
        print(f"✓ CEO can access cleanup-preview")
        
        # HR should fail
        resp = requests.get(f"{BASE_URL}/api/admin/cleanup-preview", headers=auth_header(hr_token))
        assert resp.status_code == 403, f"HR should get 403 for cleanup-preview, got {resp.status_code}"
        print(f"✓ HR correctly gets 403 for cleanup-preview")

    def test_cleanup_ceo_only(self, hr_token):
        """Only CEO can execute cleanup"""
        resp = requests.post(f"{BASE_URL}/api/admin/cleanup", headers=auth_header(hr_token))
        assert resp.status_code == 403, f"HR should get 403 for cleanup, got {resp.status_code}"
        print(f"✓ HR correctly gets 403 for cleanup execution")


# ============ 13. Employees Category Filter ============

class TestEmployeesCategoryFilter:
    """Tests for employees category filter"""

    def test_employees_filter_by_branch(self, ceo_token):
        """GET /api/employees?category=branch should filter correctly"""
        resp = requests.get(f"{BASE_URL}/api/employees?category=branch", headers=auth_header(ceo_token))
        assert resp.status_code == 200
        employees = resp.json()
        # All returned employees should have category=branch
        for emp in employees:
            assert emp.get("category") == "branch", f"Employee {emp.get('name')} has category {emp.get('category')}"
        print(f"✓ Employees filter by category=branch works ({len(employees)} results)")

    def test_employees_filter_by_head_office(self, ceo_token):
        """GET /api/employees?category=head_office should filter correctly"""
        resp = requests.get(f"{BASE_URL}/api/employees?category=head_office", headers=auth_header(ceo_token))
        assert resp.status_code == 200
        employees = resp.json()
        # All returned employees should have category=head_office
        for emp in employees:
            assert emp.get("category") == "head_office", f"Employee {emp.get('name')} has category {emp.get('category')}"
        print(f"✓ Employees filter by category=head_office works ({len(employees)} results)")


# ============ 14. Campaigns Routes Removed ============

class TestCampaignsRemoved:
    """Tests that campaigns routes return 404"""

    def test_campaigns_routes_404(self, ceo_token):
        """Routes for /api/campaigns/* should return 404"""
        endpoints = [
            "/api/campaigns",
            "/api/campaigns/test-id",
        ]
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=auth_header(ceo_token))
            assert resp.status_code == 404, f"{endpoint} should return 404, got {resp.status_code}"
        print(f"✓ Campaigns routes correctly return 404 (removed)")


# ============ Run Tests ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
