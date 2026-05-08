"""
Phase 1 Pipeline Restructure Tests - Servall Hiring OS

Tests for:
1. Interview criteria endpoints (HR/Manager 10 criteria each)
2. HR/Manager questionnaire submissions with validation
3. Pipeline transitions with hard blocks
4. Hold/resume mechanics
5. Employee segmentation and exit endpoints
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CEO_EMAIL = "admin@servall.com"
CEO_PASSWORD = "ServallAdmin@123"
JR_HR_EMAIL = "jrhr@servall.com"
JR_HR_PASSWORD = "Servall@123"
HR_EMAIL = "hr@servall.com"
HR_PASSWORD = "Servall@123"


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def ceo_token(self):
        """Get CEO auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        assert response.status_code == 200, f"CEO login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def jr_hr_token(self):
        """Get Jr HR auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": JR_HR_EMAIL,
            "password": JR_HR_PASSWORD
        })
        assert response.status_code == 200, f"Jr HR login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_ceo_login(self):
        """Test CEO login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "CEO"


class TestInterviewCriteria:
    """Test GET /api/interviews/criteria endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_criteria_returns_hr_and_manager(self, auth_headers):
        """GET /api/interviews/criteria returns HR (10 items) and Manager (10 items)"""
        response = requests.get(f"{BASE_URL}/api/interviews/criteria", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check HR criteria
        assert "hr" in data
        assert len(data["hr"]) == 10, f"Expected 10 HR criteria, got {len(data['hr'])}"
        
        # Check Manager criteria
        assert "manager" in data
        assert len(data["manager"]) == 10, f"Expected 10 Manager criteria, got {len(data['manager'])}"
        
        # Verify structure (key + label)
        for item in data["hr"]:
            assert "key" in item
            assert "label" in item
        
        for item in data["manager"]:
            assert "key" in item
            assert "label" in item
        
        # Verify specific HR criteria keys
        hr_keys = [c["key"] for c in data["hr"]]
        expected_hr = ["communication_skills", "confidence", "attitude", "basic_understanding",
                       "learning_ability", "stability", "salary_expectation_fit", "cultural_fit",
                       "availability", "overall_impression"]
        assert set(hr_keys) == set(expected_hr), f"HR keys mismatch: {hr_keys}"
        
        # Verify specific Manager criteria keys
        mgr_keys = [c["key"] for c in data["manager"]]
        expected_mgr = ["technical_skills", "problem_solving", "role_knowledge", "practical_exposure",
                        "decision_making", "ownership", "team_fit", "pressure_handling",
                        "growth_potential", "final_recommendation"]
        assert set(mgr_keys) == set(expected_mgr), f"Manager keys mismatch: {mgr_keys}"


class TestHOPipelineTransitions:
    """Test Head Office pipeline: new_lead→qualified→hr_interview→manager_interview→move_ahead→joined"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def ho_lead(self, auth_headers):
        """Create a fresh HO lead (is_technician=false)"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"HO Test Lead {unique_id}",
            "phone": f"9999{unique_id[:6]}",
            "email": f"ho_test_{unique_id}@test.com",
            "is_technician": False,
            "source": "test"
        })
        assert response.status_code == 200, f"Failed to create HO lead: {response.text}"
        return response.json()
    
    def test_ho_lead_starts_at_new_lead(self, auth_headers, ho_lead):
        """HO lead starts at new_lead stage"""
        assert ho_lead["current_stage"] == "new_lead"
        assert ho_lead["is_technician"] == False
    
    def test_ho_transition_new_lead_to_qualified(self, auth_headers, ho_lead):
        """Transition HO lead: new_lead → qualified"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "qualified",
                "form_data": {
                    "experience": "3 years",
                    "location_confirmation": "Yes",
                    "salary_expectation": "50000",
                    "relocation_preference": "No"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "qualified"
    
    def test_ho_transition_qualified_to_hr_interview(self, auth_headers, ho_lead):
        """Transition HO lead: qualified → hr_interview"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hr_interview",
                "form_data": {
                    "interview_date": "2026-01-20",
                    "mode": "in-person"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "hr_interview"
    
    def test_ho_cannot_skip_to_manager_interview_without_hr_questionnaire(self, auth_headers, ho_lead):
        """HARD BLOCK: Cannot move to manager_interview without HR questionnaire"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "manager_interview",
                "form_data": {
                    "interview_date": "2026-01-21",
                    "mode": "in-person"
                }
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "HR interview questionnaire" in response.json().get("detail", "")
    
    def test_submit_hr_questionnaire_for_ho(self, auth_headers, ho_lead):
        """Submit HR questionnaire for HO lead"""
        ratings = {
            "communication_skills": 4,
            "confidence": 5,
            "attitude": 4,
            "basic_understanding": 3,
            "learning_ability": 4,
            "stability": 4,
            "salary_expectation_fit": 3,
            "cultural_fit": 5,
            "availability": 4,
            "overall_impression": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{ho_lead['id']}/hr",
            headers=auth_headers,
            json={"ratings": ratings, "remarks": "Good candidate"}
        )
        assert response.status_code == 200, f"HR submission failed: {response.text}"
        data = response.json()
        assert data["round"] == "hr"
        assert data["avg_rating"] == 4.0  # (4+5+4+3+4+4+3+5+4+4)/10 = 40/10 = 4.0
        assert data["locked"] == False
    
    def test_ho_transition_to_manager_interview_after_hr_questionnaire(self, auth_headers, ho_lead):
        """After HR questionnaire, can move to manager_interview"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "manager_interview",
                "form_data": {
                    "interview_date": "2026-01-22",
                    "mode": "video"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "manager_interview"
    
    def test_ho_cannot_move_ahead_without_manager_questionnaire(self, auth_headers, ho_lead):
        """HARD BLOCK: HO lead cannot move to move_ahead without Manager questionnaire"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "move_ahead",
                "form_data": {}
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Manager interview questionnaire" in response.json().get("detail", "")
    
    def test_submit_manager_questionnaire_for_ho(self, auth_headers, ho_lead):
        """Submit Manager questionnaire for HO lead"""
        ratings = {
            "technical_skills": 4,
            "problem_solving": 5,
            "role_knowledge": 4,
            "practical_exposure": 3,
            "decision_making": 4,
            "ownership": 5,
            "team_fit": 4,
            "pressure_handling": 4,
            "growth_potential": 5,
            "final_recommendation": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{ho_lead['id']}/manager",
            headers=auth_headers,
            json={"ratings": ratings, "remarks": "Strong technical candidate"}
        )
        assert response.status_code == 200, f"Manager submission failed: {response.text}"
        data = response.json()
        assert data["round"] == "manager"
        assert data["avg_rating"] == 4.2  # (4+5+4+3+4+5+4+4+5+4)/10 = 42/10 = 4.2
    
    def test_ho_transition_to_move_ahead_after_manager_questionnaire(self, auth_headers, ho_lead):
        """After Manager questionnaire, can move to move_ahead"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "move_ahead",
                "form_data": {}
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "move_ahead"
    
    def test_ho_transition_to_joined(self, auth_headers, ho_lead):
        """Transition HO lead: move_ahead → joined"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{ho_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "joined",
                "form_data": {
                    "joining_date": "2026-02-01"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "joined"
    
    def test_interview_records_locked_after_joined(self, auth_headers, ho_lead):
        """Interview records should be locked after lead reaches 'joined'"""
        response = requests.get(
            f"{BASE_URL}/api/interviews/{ho_lead['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["hr"]["locked"] == True
        assert data["manager"]["locked"] == True


class TestTechnicianPipelineTransitions:
    """Test Technician pipeline: new_lead→qualified→hr_interview→move_ahead→joined (NO manager_interview)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def tech_lead(self, auth_headers):
        """Create a fresh Technician lead (is_technician=true)"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Tech Test Lead {unique_id}",
            "phone": f"8888{unique_id[:6]}",
            "email": f"tech_test_{unique_id}@test.com",
            "is_technician": True,
            "source": "test"
        })
        assert response.status_code == 200, f"Failed to create Tech lead: {response.text}"
        return response.json()
    
    def test_tech_lead_starts_at_new_lead(self, auth_headers, tech_lead):
        """Tech lead starts at new_lead stage"""
        assert tech_lead["current_stage"] == "new_lead"
        assert tech_lead["is_technician"] == True
    
    def test_tech_transition_to_qualified(self, auth_headers, tech_lead):
        """Transition Tech lead: new_lead → qualified"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "qualified",
                "form_data": {
                    "experience": "2 years",
                    "location_confirmation": "Yes",
                    "salary_expectation": "25000",
                    "relocation_preference": "Yes"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "qualified"
    
    def test_tech_transition_to_hr_interview(self, auth_headers, tech_lead):
        """Transition Tech lead: qualified → hr_interview"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hr_interview",
                "form_data": {
                    "interview_date": "2026-01-20",
                    "mode": "in-person"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "hr_interview"
    
    def test_tech_cannot_move_to_manager_interview(self, auth_headers, tech_lead):
        """Technician pipeline has NO manager_interview stage - should 400"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "manager_interview",
                "form_data": {
                    "interview_date": "2026-01-21",
                    "mode": "video"
                }
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Technician" in response.json().get("detail", "") or "no Manager" in response.json().get("detail", "")
    
    def test_tech_cannot_move_ahead_without_hr_questionnaire(self, auth_headers, tech_lead):
        """HARD BLOCK: Tech lead cannot move to move_ahead without HR questionnaire"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "move_ahead",
                "form_data": {}
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "HR interview questionnaire" in response.json().get("detail", "")
    
    def test_submit_hr_questionnaire_for_tech(self, auth_headers, tech_lead):
        """Submit HR questionnaire for Tech lead"""
        ratings = {
            "communication_skills": 3,
            "confidence": 4,
            "attitude": 5,
            "basic_understanding": 4,
            "learning_ability": 4,
            "stability": 3,
            "salary_expectation_fit": 4,
            "cultural_fit": 4,
            "availability": 5,
            "overall_impression": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{tech_lead['id']}/hr",
            headers=auth_headers,
            json={"ratings": ratings, "remarks": "Good technician candidate"}
        )
        assert response.status_code == 200, f"HR submission failed: {response.text}"
        data = response.json()
        assert data["round"] == "hr"
        assert data["avg_rating"] == 4.0  # (3+4+5+4+4+3+4+4+5+4)/10 = 40/10 = 4.0
    
    def test_tech_cannot_submit_manager_questionnaire(self, auth_headers, tech_lead):
        """Technicians should NOT be able to submit Manager questionnaire"""
        ratings = {
            "technical_skills": 4,
            "problem_solving": 4,
            "role_knowledge": 4,
            "practical_exposure": 4,
            "decision_making": 4,
            "ownership": 4,
            "team_fit": 4,
            "pressure_handling": 4,
            "growth_potential": 4,
            "final_recommendation": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{tech_lead['id']}/manager",
            headers=auth_headers,
            json={"ratings": ratings, "remarks": "Test"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Head Office" in response.json().get("detail", "") or "only for" in response.json().get("detail", "")
    
    def test_tech_transition_to_move_ahead_after_hr_questionnaire(self, auth_headers, tech_lead):
        """After HR questionnaire, Tech can move to move_ahead"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "move_ahead",
                "form_data": {}
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "move_ahead"
    
    def test_tech_transition_to_joined(self, auth_headers, tech_lead):
        """Transition Tech lead: move_ahead → joined"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{tech_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "joined",
                "form_data": {
                    "joining_date": "2026-02-01"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "joined"


class TestHoldAndDeadTransitions:
    """Test hold/dead parallel states and resume mechanics"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def hold_test_lead(self, auth_headers):
        """Create a fresh lead for hold testing"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Hold Test Lead {unique_id}",
            "phone": f"7777{unique_id[:6]}",
            "email": f"hold_test_{unique_id}@test.com",
            "is_technician": False,
            "source": "test"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_move_to_hold_requires_hold_reason(self, auth_headers, hold_test_lead):
        """Moving to 'hold' requires hold_reason in form_data"""
        # First move to qualified
        requests.post(
            f"{BASE_URL}/api/leads/{hold_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "qualified",
                "form_data": {
                    "experience": "2 years",
                    "location_confirmation": "Yes",
                    "salary_expectation": "40000",
                    "relocation_preference": "No"
                }
            }
        )
        
        # Try to move to hold without reason
        response = requests.post(
            f"{BASE_URL}/api/leads/{hold_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hold",
                "form_data": {}
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "hold_reason" in response.json().get("detail", "")
    
    def test_move_to_hold_with_reason(self, auth_headers, hold_test_lead):
        """Moving to 'hold' with hold_reason succeeds"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{hold_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hold",
                "form_data": {
                    "hold_reason": "Candidate requested time to decide"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "hold"
        assert data["previous_stage"] == "qualified"
        assert data["hold_reason"] == "Candidate requested time to decide"
    
    def test_resume_from_hold_to_previous_stage(self, auth_headers, hold_test_lead):
        """Resume from hold back to previous_stage (qualified)"""
        # Get current state
        lead = requests.get(f"{BASE_URL}/api/leads/{hold_test_lead['id']}", headers=auth_headers).json()
        assert lead["current_stage"] == "hold"
        assert lead["previous_stage"] == "qualified"
        
        # Resume to hr_interview (next stage after qualified)
        response = requests.post(
            f"{BASE_URL}/api/leads/{hold_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hr_interview",
                "form_data": {
                    "interview_date": "2026-01-25",
                    "mode": "video"
                }
            }
        )
        assert response.status_code == 200, f"Resume failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "hr_interview"


class TestDeadTransitions:
    """Test dead state transitions and interview locking"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def dead_test_lead(self, auth_headers):
        """Create a fresh lead for dead testing"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Dead Test Lead {unique_id}",
            "phone": f"6666{unique_id[:6]}",
            "email": f"dead_test_{unique_id}@test.com",
            "is_technician": True,
            "source": "test"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_move_to_dead_requires_dead_reason(self, auth_headers, dead_test_lead):
        """Moving to 'dead' requires dead_reason in form_data"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{dead_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "dead",
                "form_data": {}
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "dead_reason" in response.json().get("detail", "")
    
    def test_move_to_dead_with_reason(self, auth_headers, dead_test_lead):
        """Moving to 'dead' with dead_reason succeeds"""
        response = requests.post(
            f"{BASE_URL}/api/leads/{dead_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "dead",
                "form_data": {
                    "dead_reason": "Candidate not interested"
                }
            }
        )
        assert response.status_code == 200, f"Transition failed: {response.text}"
        data = response.json()
        assert data["current_stage"] == "dead"
        assert data["dead_reason"] == "Candidate not interested"


class TestInterviewRecordLocking:
    """Test that interview records get locked on joined/dead"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def lock_test_lead(self, auth_headers):
        """Create a fresh lead for lock testing"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Lock Test Lead {unique_id}",
            "phone": f"5555{unique_id[:6]}",
            "email": f"lock_test_{unique_id}@test.com",
            "is_technician": True,
            "source": "test"
        })
        assert response.status_code == 200
        lead = response.json()
        
        # Progress through pipeline
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=auth_headers, json={
            "to_stage": "qualified",
            "form_data": {"experience": "1 year", "location_confirmation": "Yes", "salary_expectation": "20000", "relocation_preference": "No"}
        })
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=auth_headers, json={
            "to_stage": "hr_interview",
            "form_data": {"interview_date": "2026-01-20", "mode": "in-person"}
        })
        
        # Submit HR questionnaire
        ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude", "basic_understanding",
                                   "learning_ability", "stability", "salary_expectation_fit", "cultural_fit",
                                   "availability", "overall_impression"]}
        requests.post(f"{BASE_URL}/api/interviews/{lead['id']}/hr", headers=auth_headers, json={"ratings": ratings})
        
        return lead
    
    def test_interview_not_locked_before_terminal_state(self, auth_headers, lock_test_lead):
        """Interview records should NOT be locked before joined/dead"""
        response = requests.get(f"{BASE_URL}/api/interviews/{lock_test_lead['id']}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["hr"]["locked"] == False
    
    def test_interview_locked_after_dead(self, auth_headers, lock_test_lead):
        """Interview records should be locked after lead moves to dead"""
        # Move to dead
        response = requests.post(
            f"{BASE_URL}/api/leads/{lock_test_lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "dead",
                "form_data": {"dead_reason": "Failed interview"}
            }
        )
        assert response.status_code == 200
        
        # Check interview is locked
        response = requests.get(f"{BASE_URL}/api/interviews/{lock_test_lead['id']}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["hr"]["locked"] == True


class TestInterviewValidation:
    """Test interview questionnaire validation"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def validation_lead(self, auth_headers):
        """Create a fresh lead for validation testing"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Validation Test Lead {unique_id}",
            "phone": f"4444{unique_id[:6]}",
            "email": f"validation_test_{unique_id}@test.com",
            "is_technician": False,
            "source": "test"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_hr_questionnaire_missing_criteria(self, auth_headers, validation_lead):
        """HR questionnaire must have all 10 criteria"""
        ratings = {
            "communication_skills": 4,
            "confidence": 5,
            # Missing other 8 criteria
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{validation_lead['id']}/hr",
            headers=auth_headers,
            json={"ratings": ratings}
        )
        assert response.status_code == 400
        assert "Missing criteria" in response.json().get("detail", "")
    
    def test_hr_questionnaire_invalid_rating(self, auth_headers, validation_lead):
        """HR questionnaire ratings must be 1-5"""
        ratings = {
            "communication_skills": 6,  # Invalid - out of range
            "confidence": 5,
            "attitude": 4,
            "basic_understanding": 3,
            "learning_ability": 4,
            "stability": 4,
            "salary_expectation_fit": 3,
            "cultural_fit": 5,
            "availability": 4,
            "overall_impression": 4
        }
        response = requests.post(
            f"{BASE_URL}/api/interviews/{validation_lead['id']}/hr",
            headers=auth_headers,
            json={"ratings": ratings}
        )
        assert response.status_code == 400
        assert "1-5" in response.json().get("detail", "")


class TestEmployeeSegmentation:
    """Test employee segmentation endpoints"""
    
    @pytest.fixture(scope="class")
    def ceo_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def jr_hr_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": JR_HR_EMAIL,
            "password": JR_HR_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_segments_summary_structure(self, ceo_headers):
        """GET /api/employees/segments/summary returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/employees/segments/summary", headers=ceo_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "branch" in data
        assert "head_office" in data
        assert "total_active" in data
        assert "total_exited" in data
        
        # Check branch sub-structure
        assert "technician" in data["branch"]
        assert "management" in data["branch"]
        
        # Check head_office sub-structure
        assert "mid_level" in data["head_office"]
        assert "management" in data["head_office"]
    
    def test_exited_employees_forbidden_for_jr_hr(self, jr_hr_headers):
        """GET /api/employees/exited must return 403 for Jr HR"""
        response = requests.get(f"{BASE_URL}/api/employees/exited", headers=jr_hr_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_exited_employees_allowed_for_ceo(self, ceo_headers):
        """GET /api/employees/exited must return list for CEO"""
        response = requests.get(f"{BASE_URL}/api/employees/exited", headers=ceo_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestEmployeeConversion:
    """Test employee conversion from lead"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def conversion_lead(self, auth_headers):
        """Create and progress a lead to move_ahead for conversion testing"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Conversion Test Lead {unique_id}",
            "phone": f"3333{unique_id[:6]}",
            "email": f"conversion_test_{unique_id}@test.com",
            "is_technician": True,
            "source": "test"
        })
        lead = response.json()
        
        # Progress through pipeline
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=auth_headers, json={
            "to_stage": "qualified",
            "form_data": {"experience": "3 years", "location_confirmation": "Yes", "salary_expectation": "30000", "relocation_preference": "No"}
        })
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=auth_headers, json={
            "to_stage": "hr_interview",
            "form_data": {"interview_date": "2026-01-20", "mode": "in-person"}
        })
        
        # Submit HR questionnaire
        ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude", "basic_understanding",
                                   "learning_ability", "stability", "salary_expectation_fit", "cultural_fit",
                                   "availability", "overall_impression"]}
        requests.post(f"{BASE_URL}/api/interviews/{lead['id']}/hr", headers=auth_headers, json={"ratings": ratings})
        
        # Move to move_ahead
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=auth_headers, json={
            "to_stage": "move_ahead",
            "form_data": {}
        })
        
        return lead
    
    def test_convert_lead_requires_move_ahead_stage(self, auth_headers):
        """Lead must be in move_ahead/joined/interview_cleared to convert"""
        # Create a new lead at new_lead stage
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Early Convert Test {unique_id}",
            "phone": f"2222{unique_id[:6]}",
            "is_technician": True,
            "source": "test"
        })
        lead = response.json()
        
        # Try to convert - should fail
        response = requests.post(
            f"{BASE_URL}/api/employees/convert/{lead['id']}",
            headers=auth_headers,
            json={
                "joining_date": "2026-02-01",
                "role": "Technician"
            }
        )
        assert response.status_code == 400
        assert "Move Ahead" in response.json().get("detail", "")
    
    def test_convert_lead_to_employee(self, auth_headers, conversion_lead):
        """Convert lead at move_ahead to employee"""
        response = requests.post(
            f"{BASE_URL}/api/employees/convert/{conversion_lead['id']}",
            headers=auth_headers,
            json={
                "joining_date": "2026-02-01",
                "role": "Technician",
                "branch_id": "branch-001"
            }
        )
        assert response.status_code == 200, f"Conversion failed: {response.text}"
        data = response.json()
        
        # Check derived segmentation
        assert data["category"] == "branch"  # is_technician=True + branch_id → branch
        assert data["employment_type"] == "technician"  # is_technician=True → technician
        assert data["status"] == "active"


class TestEmployeeExit:
    """Test employee exit endpoint"""
    
    @pytest.fixture(scope="class")
    def ceo_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def jr_hr_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": JR_HR_EMAIL,
            "password": JR_HR_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def exit_test_employee(self, ceo_headers):
        """Create a lead and convert to employee for exit testing"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create lead
        response = requests.post(f"{BASE_URL}/api/leads", headers=ceo_headers, json={
            "name": f"Exit Test Lead {unique_id}",
            "phone": f"1111{unique_id[:6]}",
            "is_technician": True,
            "source": "test"
        })
        lead = response.json()
        
        # Progress through pipeline
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=ceo_headers, json={
            "to_stage": "qualified",
            "form_data": {"experience": "2 years", "location_confirmation": "Yes", "salary_expectation": "25000", "relocation_preference": "No"}
        })
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=ceo_headers, json={
            "to_stage": "hr_interview",
            "form_data": {"interview_date": "2026-01-20", "mode": "in-person"}
        })
        
        # Submit HR questionnaire
        ratings = {k: 4 for k in ["communication_skills", "confidence", "attitude", "basic_understanding",
                                   "learning_ability", "stability", "salary_expectation_fit", "cultural_fit",
                                   "availability", "overall_impression"]}
        requests.post(f"{BASE_URL}/api/interviews/{lead['id']}/hr", headers=ceo_headers, json={"ratings": ratings})
        
        # Move to move_ahead
        requests.post(f"{BASE_URL}/api/leads/{lead['id']}/transition", headers=ceo_headers, json={
            "to_stage": "move_ahead",
            "form_data": {}
        })
        
        # Convert to employee
        response = requests.post(
            f"{BASE_URL}/api/employees/convert/{lead['id']}",
            headers=ceo_headers,
            json={
                "joining_date": "2026-01-15",
                "role": "Technician",
                "branch_id": "branch-001"
            }
        )
        return response.json()
    
    def test_exit_forbidden_for_jr_hr(self, jr_hr_headers, exit_test_employee):
        """POST /api/employees/{id}/exit must return 403 for Jr HR"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{exit_test_employee['id']}/exit",
            headers=jr_hr_headers,
            json={
                "exit_date": "2026-01-30",
                "exit_reason": "Personal reasons",
                "exit_type": "resigned"
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_exit_allowed_for_ceo(self, ceo_headers, exit_test_employee):
        """POST /api/employees/{id}/exit marks employee as left for CEO"""
        response = requests.post(
            f"{BASE_URL}/api/employees/{exit_test_employee['id']}/exit",
            headers=ceo_headers,
            json={
                "exit_date": "2026-01-30",
                "exit_reason": "Personal reasons",
                "exit_type": "resigned",
                "remarks": "Left on good terms"
            }
        )
        assert response.status_code == 200, f"Exit failed: {response.text}"
        data = response.json()
        assert data["success"] == True


class TestPipelineStats:
    """Test pipeline stats endpoint with new stages"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_pipeline_stats_includes_new_stages(self, auth_headers):
        """GET /api/leads/pipeline-stats returns counts for new stages"""
        response = requests.get(f"{BASE_URL}/api/leads/pipeline-stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check new stages are present
        expected_stages = ["new_lead", "qualified", "hr_interview", "manager_interview", 
                          "move_ahead", "joined", "hold", "dead"]
        for stage in expected_stages:
            assert stage in data, f"Stage '{stage}' missing from pipeline stats"


class TestSkipStageValidation:
    """Test that skipping stages is not allowed"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_cannot_skip_stages(self, auth_headers):
        """Cannot skip from new_lead directly to hr_interview"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Skip Test Lead {unique_id}",
            "phone": f"0000{unique_id[:6]}",
            "is_technician": False,
            "source": "test"
        })
        lead = response.json()
        
        # Try to skip to hr_interview
        response = requests.post(
            f"{BASE_URL}/api/leads/{lead['id']}/transition",
            headers=auth_headers,
            json={
                "to_stage": "hr_interview",
                "form_data": {
                    "interview_date": "2026-01-20",
                    "mode": "in-person"
                }
            }
        )
        assert response.status_code == 400
        assert "skip" in response.json().get("detail", "").lower() or "next stage" in response.json().get("detail", "").lower()


class TestLeadsCRUD:
    """Test basic leads CRUD still works"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CEO_EMAIL,
            "password": CEO_PASSWORD
        })
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_list_leads(self, auth_headers):
        """GET /api/leads returns list"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_lead(self, auth_headers):
        """POST /api/leads creates lead"""
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"CRUD Test Lead {unique_id}",
            "phone": f"9876{unique_id[:6]}",
            "is_technician": False,
            "source": "test"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"CRUD Test Lead {unique_id}"
        assert data["current_stage"] == "new_lead"
    
    def test_get_lead(self, auth_headers):
        """GET /api/leads/{id} returns lead"""
        # Create a lead first
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(f"{BASE_URL}/api/leads", headers=auth_headers, json={
            "name": f"Get Test Lead {unique_id}",
            "phone": f"8765{unique_id[:6]}",
            "is_technician": False,
            "source": "test"
        })
        lead = create_response.json()
        
        # Get the lead
        response = requests.get(f"{BASE_URL}/api/leads/{lead['id']}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == lead["id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
