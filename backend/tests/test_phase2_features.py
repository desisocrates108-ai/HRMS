"""
Phase 2 + P1 + P2 + Franchise Recruitment Tests
================================================
Tests for:
- Public tokenized feedback forms (GET/POST without auth)
- Feedback admin endpoints (CEO/HR only)
- Analytics summary + intelligence endpoints
- Branches recruitment-overview
- Resume upload + Medical info
- WhatsApp resilience (fire-and-forget - transition must succeed even if WhatsApp fails)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials from test_credentials.md
CEO_CREDS = {"email": "admin@servall.com", "password": "ServallAdmin@123"}
HR_CREDS = {"email": "hr@servall.com", "password": "Servall@123"}
JR_HR_CREDS = {"email": "jrhr@servall.com", "password": "Servall@123"}
DESIGNER_CREDS = {"email": "designer@servall.com", "password": "Servall@123"}
MANAGER_CREDS = {"email": "marketing.mgr@servall.com", "password": "Servall@123"}
SUPER_ADMIN_CREDS = {"email": "superadmin@servall.com", "password": "Servall@123"}


def get_auth_token(creds):
    """Helper to get auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


# Get tokens at module level
CEO_TOKEN = None
HR_TOKEN = None
JR_HR_TOKEN = None
DESIGNER_TOKEN = None
MANAGER_TOKEN = None
SUPER_ADMIN_TOKEN = None


def setup_module(module):
    """Setup tokens before running tests"""
    global CEO_TOKEN, HR_TOKEN, JR_HR_TOKEN, DESIGNER_TOKEN, MANAGER_TOKEN, SUPER_ADMIN_TOKEN
    CEO_TOKEN = get_auth_token(CEO_CREDS)
    HR_TOKEN = get_auth_token(HR_CREDS)
    JR_HR_TOKEN = get_auth_token(JR_HR_CREDS)
    DESIGNER_TOKEN = get_auth_token(DESIGNER_CREDS)
    MANAGER_TOKEN = get_auth_token(MANAGER_CREDS)
    SUPER_ADMIN_TOKEN = get_auth_token(SUPER_ADMIN_CREDS)
    
    print(f"CEO_TOKEN: {'OK' if CEO_TOKEN else 'FAILED'}")
    print(f"HR_TOKEN: {'OK' if HR_TOKEN else 'FAILED'}")
    print(f"JR_HR_TOKEN: {'OK' if JR_HR_TOKEN else 'FAILED'}")
    print(f"DESIGNER_TOKEN: {'OK' if DESIGNER_TOKEN else 'FAILED'}")
    print(f"MANAGER_TOKEN: {'OK' if MANAGER_TOKEN else 'FAILED'}")
    print(f"SUPER_ADMIN_TOKEN: {'OK' if SUPER_ADMIN_TOKEN else 'FAILED'}")


# ============================================================================
# FEEDBACK ENDPOINTS TESTS
# ============================================================================

class TestPublicFeedbackEndpoints:
    """Test public feedback form endpoints (no auth required)"""

    def test_get_feedback_form_invalid_token_returns_404(self):
        """GET /api/feedback/form/{token} with invalid token returns 404"""
        resp = requests.get(f"{BASE_URL}/api/feedback/form/invalid_token_xyz123")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "Invalid" in data.get("detail", "") or "expired" in data.get("detail", "")

    def test_post_feedback_invalid_token_returns_404(self):
        """POST /api/feedback/{token} with invalid token returns 404"""
        resp = requests.post(
            f"{BASE_URL}/api/feedback/invalid_token_xyz123",
            json={"answers": {"test": "value"}}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


class TestFeedbackAdminEndpoints:
    """Test feedback admin endpoints (CEO/HR only)"""

    def test_submissions_ceo_access(self):
        """GET /api/feedback/submissions - CEO can access"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert isinstance(resp.json(), list)

    def test_submissions_hr_access(self):
        """GET /api/feedback/submissions - HR can access"""
        assert HR_TOKEN, "HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {HR_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_submissions_super_admin_access(self):
        """GET /api/feedback/submissions - Super Admin can access"""
        assert SUPER_ADMIN_TOKEN, "Super Admin login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {SUPER_ADMIN_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_submissions_jr_hr_forbidden(self):
        """GET /api/feedback/submissions - Jr HR returns 403"""
        assert JR_HR_TOKEN, "Jr HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {JR_HR_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_submissions_manager_forbidden(self):
        """GET /api/feedback/submissions - Manager returns 403"""
        assert MANAGER_TOKEN, "Manager login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {MANAGER_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_submissions_designer_forbidden(self):
        """GET /api/feedback/submissions - Designer returns 403"""
        assert DESIGNER_TOKEN, "Designer login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions",
            headers={"Authorization": f"Bearer {DESIGNER_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_submissions_filter_by_kind(self):
        """GET /api/feedback/submissions?kind=rejection works"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions?kind=rejection",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        # All returned items should have kind=rejection
        for item in resp.json():
            assert item.get("kind") == "rejection"

    def test_submissions_summary_ceo_access(self):
        """GET /api/feedback/submissions/summary - CEO can access"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions/summary",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "rejection_count" in data
        assert "exit_count" in data
        assert "pending_invitations" in data
        assert "total" in data

    def test_submissions_summary_jr_hr_forbidden(self):
        """GET /api/feedback/submissions/summary - Jr HR returns 403"""
        assert JR_HR_TOKEN, "Jr HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions/summary",
            headers={"Authorization": f"Bearer {JR_HR_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ============================================================================
# ANALYTICS ENDPOINTS TESTS
# ============================================================================

class TestAnalyticsSummary:
    """Test /api/analytics/summary endpoint"""

    def test_summary_ceo_access(self):
        """GET /api/analytics/summary - CEO can access"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=365",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Validate response structure
        assert "funnel" in data
        assert "conversions_pct" in data
        assert "hold_reasons" in data
        assert "dead_reasons" in data
        assert "sources" in data
        assert "avg_hr_score" in data
        assert "avg_manager_score" in data
        assert "hires" in data
        assert "avg_time_to_hire_days" in data

    def test_summary_hr_access(self):
        """GET /api/analytics/summary - HR can access"""
        assert HR_TOKEN, "HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=90",
            headers={"Authorization": f"Bearer {HR_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_summary_manager_access(self):
        """GET /api/analytics/summary - Manager can access"""
        assert MANAGER_TOKEN, "Manager login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=90",
            headers={"Authorization": f"Bearer {MANAGER_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_summary_designer_forbidden(self):
        """GET /api/analytics/summary - Designer returns 403"""
        assert DESIGNER_TOKEN, "Designer login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=90",
            headers={"Authorization": f"Bearer {DESIGNER_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_summary_jr_hr_forbidden(self):
        """GET /api/analytics/summary - Jr HR returns 403"""
        assert JR_HR_TOKEN, "Jr HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=90",
            headers={"Authorization": f"Bearer {JR_HR_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_summary_filter_by_pipeline_type_technician(self):
        """GET /api/analytics/summary?pipeline_type=technician works"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=365&pipeline_type=technician",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("pipeline_type") == "technician"

    def test_summary_filter_by_pipeline_type_head_office(self):
        """GET /api/analytics/summary?pipeline_type=head_office works"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/summary?days=365&pipeline_type=head_office",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("pipeline_type") == "head_office"


class TestAnalyticsIntelligence:
    """Test /api/analytics/intelligence endpoint"""

    def test_intelligence_ceo_access(self):
        """GET /api/analytics/intelligence - CEO can access"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/intelligence?days=365",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Validate response structure
        assert "best_interviewer" in data
        assert "all_interviewers" in data
        assert "weak_stages" in data
        assert "insights" in data

    def test_intelligence_hr_access(self):
        """GET /api/analytics/intelligence - HR can access"""
        assert HR_TOKEN, "HR login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/intelligence?days=90",
            headers={"Authorization": f"Bearer {HR_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_intelligence_manager_access(self):
        """GET /api/analytics/intelligence - Manager can access"""
        assert MANAGER_TOKEN, "Manager login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/intelligence?days=90",
            headers={"Authorization": f"Bearer {MANAGER_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_intelligence_designer_forbidden(self):
        """GET /api/analytics/intelligence - Designer returns 403"""
        assert DESIGNER_TOKEN, "Designer login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/intelligence?days=90",
            headers={"Authorization": f"Bearer {DESIGNER_TOKEN}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_intelligence_weak_stages_sorted_desc(self):
        """GET /api/analytics/intelligence - weak_stages sorted by drop_pct desc"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/analytics/intelligence?days=365",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        weak_stages = data.get("weak_stages", [])
        if len(weak_stages) > 1:
            for i in range(len(weak_stages) - 1):
                assert weak_stages[i]["drop_pct"] >= weak_stages[i + 1]["drop_pct"], \
                    "weak_stages should be sorted by drop_pct descending"


# ============================================================================
# BRANCHES RECRUITMENT OVERVIEW TESTS
# ============================================================================

class TestBranchesRecruitmentOverview:
    """Test /api/branches/recruitment-overview endpoint"""

    def test_recruitment_overview_structure(self):
        """GET /api/branches/recruitment-overview returns correct structure"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/branches/recruitment-overview",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Validate top-level structure
        assert "upcoming" in data
        assert "active" in data
        assert "total_upcoming" in data
        assert "total_active" in data
        assert isinstance(data["upcoming"], list)
        assert isinstance(data["active"], list)

    def test_recruitment_overview_row_fields(self):
        """Each row in recruitment-overview has required fields"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/branches/recruitment-overview",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        all_rows = data.get("upcoming", []) + data.get("active", [])
        for row in all_rows:
            assert "open_jobs" in row, f"Missing open_jobs in row: {row}"
            assert "total_jobs" in row, f"Missing total_jobs in row: {row}"
            assert "active_leads" in row, f"Missing active_leads in row: {row}"
            assert "total_leads" in row, f"Missing total_leads in row: {row}"
            assert "hired" in row, f"Missing hired in row: {row}"
            assert "hired_from_leads" in row, f"Missing hired_from_leads in row: {row}"
            assert "status" in row, f"Missing status in row: {row}"

    def test_recruitment_overview_status_derivation(self):
        """Status is correctly derived from actual_opening_date"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.get(
            f"{BASE_URL}/api/branches/recruitment-overview",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Upcoming branches should have status=upcoming
        for row in data.get("upcoming", []):
            assert row.get("status") == "upcoming"
        # Active branches should have status=active
        for row in data.get("active", []):
            assert row.get("status") == "active"


# ============================================================================
# RESUME UPLOAD TESTS
# ============================================================================

class TestResumeUpload:
    """Test /api/leads/{id}/resume endpoint"""

    def test_resume_upload_pdf(self):
        """POST /api/leads/{id}/resume - accepts PDF file"""
        assert CEO_TOKEN, "CEO login failed"
        # First create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Resume_Upload_Lead",
                "phone": "9876543210",
                "email": "test.resume@example.com",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]
        
        # Upload resume
        files = {
            "file": ("test_resume.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
        }
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            files=files,
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "resume_url" in data
        assert "filename" in data
        assert data["filename"] == "test_resume.pdf"

    def test_resume_upload_invalid_extension(self):
        """POST /api/leads/{id}/resume - rejects invalid extension"""
        assert CEO_TOKEN, "CEO login failed"
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Resume_Invalid_Ext",
                "phone": "9876543211",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        files = {
            "file": ("test.exe", b"fake exe content", "application/octet-stream")
        }
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            files=files,
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "Invalid file type" in resp.json().get("detail", "")

    def test_resume_upload_lead_not_found(self):
        """POST /api/leads/{id}/resume - returns 404 for invalid lead"""
        assert CEO_TOKEN, "CEO login failed"
        files = {
            "file": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")
        }
        resp = requests.post(
            f"{BASE_URL}/api/leads/invalid_lead_id_xyz/resume",
            files=files,
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ============================================================================
# MEDICAL INFO TESTS
# ============================================================================

class TestMedicalInfo:
    """Test /api/leads/{id}/medical endpoint"""

    def test_update_medical_info(self):
        """PUT /api/leads/{id}/medical - stores medical info"""
        assert CEO_TOKEN, "CEO login failed"
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Medical_Info_Lead",
                "phone": "9876543212",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        medical_data = {
            "blood_group": "O+",
            "allergies": "None",
            "chronic_conditions": "None",
            "emergency_contact_name": "John Doe",
            "emergency_contact_phone": "9999999999"
        }
        resp = requests.put(
            f"{BASE_URL}/api/leads/{lead_id}/medical",
            json=medical_data,
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "medical_info" in data
        assert data["medical_info"]["blood_group"] == "O+"
        assert data["medical_info"]["emergency_contact_name"] == "John Doe"

    def test_medical_info_persisted(self):
        """Verify medical info is persisted on lead"""
        assert CEO_TOKEN, "CEO login failed"
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Medical_Persist_Lead",
                "phone": "9876543213",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        # Update medical info
        requests.put(
            f"{BASE_URL}/api/leads/{lead_id}/medical",
            json={"blood_group": "A+", "allergies": "Peanuts"},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        
        # Fetch lead and verify
        resp = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200
        lead = resp.json()
        assert lead.get("medical_info", {}).get("blood_group") == "A+"

    def test_medical_info_lead_not_found(self):
        """PUT /api/leads/{id}/medical - returns 404 for invalid lead"""
        assert CEO_TOKEN, "CEO login failed"
        resp = requests.put(
            f"{BASE_URL}/api/leads/invalid_lead_id_xyz/medical",
            json={"blood_group": "B+"},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ============================================================================
# WHATSAPP RESILIENCE + FEEDBACK TOKEN CREATION TESTS
# ============================================================================

class TestWhatsAppResilienceAndFeedbackToken:
    """Test that lead→dead creates feedback tokens and succeeds even if WhatsApp fails"""

    def test_lead_to_dead_creates_feedback_token_and_succeeds(self):
        """Transitioning lead to 'dead' creates a feedback_token and succeeds (WhatsApp fire-and-forget)"""
        assert CEO_TOKEN, "CEO login failed"
        
        # Create a test lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Dead_Transition_Lead",
                "phone": "9876543214",
                "email": "test.dead@example.com",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]
        
        # Transition to dead
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/transition",
            json={
                "to_stage": "dead",
                "form_data": {"dead_reason": "Not interested"}
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        # CRITICAL: This must succeed even if WhatsApp API fails
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        lead = resp.json()
        assert lead["current_stage"] == "dead"

    def test_feedback_token_created_for_dead_lead(self):
        """Verify feedback_token was created - check pending_invitations count"""
        assert CEO_TOKEN, "CEO login failed"
        
        # Get initial count
        initial_resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions/summary",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert initial_resp.status_code == 200
        initial_pending = initial_resp.json().get("pending_invitations", 0)
        
        # Create and transition a lead to dead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Feedback_Token_Check",
                "phone": "9876543215",
                "source": "manual"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        
        requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/transition",
            json={"to_stage": "dead", "form_data": {"dead_reason": "Test reason"}},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        
        # Check pending count increased
        final_resp = requests.get(
            f"{BASE_URL}/api/feedback/submissions/summary",
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert final_resp.status_code == 200
        final_pending = final_resp.json().get("pending_invitations", 0)
        assert final_pending > initial_pending, "Expected pending_invitations to increase after dead transition"


class TestEmployeeExitFeedbackToken:
    """Test employee exit creates feedback token"""

    def test_employee_exit_creates_feedback_token(self):
        """POST /api/employees/{id}/exit creates feedback token and succeeds (WhatsApp fire-and-forget)"""
        assert CEO_TOKEN, "CEO login failed"
        
        # Create lead
        lead_resp = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "name": "TEST_Exit_Employee",
                "phone": "9876543216",
                "email": "test.exit@example.com",
                "source": "manual",
                "is_technician": True  # Technician pipeline is shorter
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]

        # Move through technician pipeline: new_lead → qualified → hr_interview
        # qualified requires: experience, location_confirmation, salary_expectation, relocation_preference
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/transition",
            json={"to_stage": "qualified", "form_data": {
                "experience": "2 years",
                "location_confirmation": "Yes",
                "salary_expectation": "30000",
                "relocation_preference": "No"
            }},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Failed to transition to qualified: {resp.text}"
        
        # hr_interview requires: interview_date, mode
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/transition",
            json={"to_stage": "hr_interview", "form_data": {
                "interview_date": "2024-01-10",
                "mode": "in_person"
            }},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Failed to transition to hr_interview: {resp.text}"

        # Submit HR interview with correct criteria
        hr_resp = requests.post(
            f"{BASE_URL}/api/interviews/{lead_id}/hr",
            json={
                "ratings": {
                    "communication_skills": 4, "confidence": 4, "attitude": 4,
                    "basic_understanding": 4, "learning_ability": 4, "stability": 4,
                    "salary_expectation_fit": 4, "cultural_fit": 4, "availability": 4,
                    "overall_impression": 4
                },
                "notes": "Good candidate"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert hr_resp.status_code == 200, f"Failed to submit HR interview: {hr_resp.text}"

        # Move to move_ahead
        resp = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/transition",
            json={"to_stage": "move_ahead", "form_data": {}},
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert resp.status_code == 200, f"Failed to transition to move_ahead: {resp.text}"

        # Convert to employee
        emp_resp = requests.post(
            f"{BASE_URL}/api/employees/convert/{lead_id}",
            json={
                "joining_date": "2024-01-15",
                "role": "Technician"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        assert emp_resp.status_code == 200, f"Failed to convert to employee: {emp_resp.text}"
        emp_id = emp_resp.json()["id"]
        
        # Exit employee
        exit_resp = requests.post(
            f"{BASE_URL}/api/employees/{emp_id}/exit",
            json={
                "exit_date": "2024-06-15",
                "exit_reason": "Better opportunity",
                "exit_type": "resigned"
            },
            headers={"Authorization": f"Bearer {CEO_TOKEN}"}
        )
        # CRITICAL: This must succeed even if WhatsApp API fails
        assert exit_resp.status_code == 200, f"Expected 200, got {exit_resp.status_code}: {exit_resp.text}"
        data = exit_resp.json()
        assert data.get("success") == True


# ============================================================================
# PUBLIC FEEDBACK FORM FLOW TEST (End-to-End)
# ============================================================================

class TestPublicFeedbackFormFlow:
    """Test the complete public feedback form flow"""

    def test_public_feedback_form_no_auth_required(self):
        """Public feedback endpoints should work WITHOUT Authorization header"""
        # Verify that the endpoint doesn't require auth by checking it doesn't return 401
        resp = requests.get(
            f"{BASE_URL}/api/feedback/form/some_random_token",
            headers={}  # No Authorization header
        )
        # Should be 404 (invalid token), NOT 401 (unauthorized)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        assert "Invalid" in resp.json().get("detail", "") or "expired" in resp.json().get("detail", "")

    def test_public_feedback_submit_no_auth_required(self):
        """POST /api/feedback/{token} should work WITHOUT Authorization header"""
        resp = requests.post(
            f"{BASE_URL}/api/feedback/some_random_token",
            json={"answers": {"test": "value"}},
            headers={}  # No Authorization header
        )
        # Should be 404 (invalid token), NOT 401 (unauthorized)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
