"""
Iteration 9 - Cleanup Pass Tests
Focus areas:
1. Deprecated role login blocking (Super Admin, Franchise Development Manager, HR Executive)
2. DELETE branch authorization + dependency check
3. Franchises field in CEO/HR/Manager dashboard responses
4. RBAC strictness for feedback + audit endpoints
5. lat/long fields stripped from branch responses
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
CREDENTIALS = {
    "ceo": {"email": "admin@servall.com", "password": "ServallAdmin@123"},
    "hr": {"email": "hr@servall.com", "password": "Servall@123"},
    "marketing_mgr": {"email": "marketing.mgr@servall.com", "password": "Servall@123"},
    "sales_mgr": {"email": "sales.mgr@servall.com", "password": "Servall@123"},
    "jrhr": {"email": "jrhr@servall.com", "password": "Servall@123"},
    "designer": {"email": "designer@servall.com", "password": "Servall@123"},
    "deprecated_superadmin": {"email": "superadmin@servall.com", "password": "Servall@123"},
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def login(session, email, password):
    """Login and return token, or None if failed"""
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token") or data.get("token")
    return None


def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ==================== SECTION 1: DEPRECATED ROLE LOGIN BLOCKING ====================

class TestDeprecatedRoleLogin:
    """Test that deprecated roles (Super Admin, Franchise Dev Manager, HR Executive) cannot login"""

    def test_deprecated_superadmin_login_fails(self, api_client):
        """Login attempt for deprecated 'Super Admin' must FAIL with 'Account is deactivated'"""
        creds = CREDENTIALS["deprecated_superadmin"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        # Should fail - either 401 or 403 with deactivation message
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}: {resp.text}"
        data = resp.json()
        detail = data.get("detail", "").lower()
        # Should mention deactivated or inactive
        assert "deactivat" in detail or "inactive" in detail or "invalid" in detail, f"Expected deactivation message, got: {detail}"
        print(f"✓ Deprecated Super Admin login correctly blocked: {detail}")


class TestValidRoleLogin:
    """Test that valid roles can still login"""

    def test_ceo_login_works(self, api_client):
        """CEO (admin@servall.com) can login"""
        creds = CREDENTIALS["ceo"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        assert resp.status_code == 200, f"CEO login failed: {resp.status_code} - {resp.text}"
        data = resp.json()
        assert "access_token" in data or "token" in data, "No token in response"
        print("✓ CEO login works")

    def test_hr_login_works(self, api_client):
        """HR (hr@servall.com) can login"""
        creds = CREDENTIALS["hr"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        assert resp.status_code == 200, f"HR login failed: {resp.status_code} - {resp.text}"
        print("✓ HR login works")

    def test_jrhr_login_works(self, api_client):
        """Jr HR (jrhr@servall.com) can login"""
        creds = CREDENTIALS["jrhr"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        assert resp.status_code == 200, f"Jr HR login failed: {resp.status_code} - {resp.text}"
        print("✓ Jr HR login works")

    def test_marketing_mgr_login_works(self, api_client):
        """Marketing Manager can login"""
        creds = CREDENTIALS["marketing_mgr"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        assert resp.status_code == 200, f"Marketing Manager login failed: {resp.status_code} - {resp.text}"
        print("✓ Marketing Manager login works")

    def test_designer_login_works(self, api_client):
        """Designer (designer@servall.com) can login"""
        creds = CREDENTIALS["designer"]
        resp = api_client.post(f"{BASE_URL}/api/auth/login", json={"email": creds["email"], "password": creds["password"]})
        assert resp.status_code == 200, f"Designer login failed: {resp.status_code} - {resp.text}"
        print("✓ Designer login works")


# ==================== SECTION 2: BRANCH CRUD - LAT/LONG STRIPPED ====================

class TestBranchLatLongStripped:
    """Test that latitude/longitude fields are NOT present in branch responses"""

    def test_get_branches_no_lat_long(self, api_client):
        """GET /api/branches as CEO returns list, each branch has 'status' but NO 'latitude' or 'longitude'"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/branches", headers=get_auth_header(token))
        assert resp.status_code == 200, f"GET branches failed: {resp.status_code}"
        branches = resp.json()
        
        for branch in branches:
            assert "status" in branch, f"Branch missing 'status' field: {branch}"
            assert "latitude" not in branch, f"Branch should NOT have 'latitude': {branch}"
            assert "longitude" not in branch, f"Branch should NOT have 'longitude': {branch}"
        
        print(f"✓ GET /api/branches returns {len(branches)} branches, none have lat/long")


# ==================== SECTION 3: BRANCH CREATE/UPDATE/DELETE AUTHORIZATION ====================

class TestBranchCreateAuthorization:
    """Test branch creation authorization"""

    def test_manager_can_create_branch(self, api_client):
        """POST /api/branches as Manager (marketing.mgr) must succeed"""
        token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert token, "Marketing Manager login failed"
        
        branch_data = {
            "name": f"TEST_Branch_{uuid.uuid4().hex[:8]}",
            "city": "Test City",
            "area": "Test Area",
            "status": "upcoming"
        }
        resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(token))
        assert resp.status_code in [200, 201], f"Manager branch create failed: {resp.status_code} - {resp.text}"
        created = resp.json()
        assert "id" in created, "Created branch missing 'id'"
        assert "latitude" not in created, "Created branch should NOT have 'latitude'"
        assert "longitude" not in created, "Created branch should NOT have 'longitude'"
        print(f"✓ Manager can create branch: {created['id']}")
        # Store for cleanup
        return created["id"]

    def test_executor_cannot_create_branch(self, api_client):
        """POST /api/branches as Executor (jrhr) must return 403"""
        token = login(api_client, **CREDENTIALS["jrhr"])
        assert token, "Jr HR login failed"
        
        branch_data = {
            "name": f"TEST_Branch_{uuid.uuid4().hex[:8]}",
            "city": "Test City",
            "area": "Test Area"
        }
        resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(token))
        assert resp.status_code == 403, f"Expected 403 for executor branch create, got {resp.status_code}"
        print("✓ Executor (Jr HR) correctly blocked from creating branch")


class TestBranchUpdateAuthorization:
    """Test branch update authorization"""

    def test_manager_can_update_branch(self, api_client):
        """PUT /api/branches/{id} as Manager succeeds"""
        # First create a branch as CEO
        ceo_token = login(api_client, **CREDENTIALS["ceo"])
        assert ceo_token, "CEO login failed"
        
        branch_data = {
            "name": f"TEST_UpdateBranch_{uuid.uuid4().hex[:8]}",
            "city": "Original City",
            "area": "Original Area"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(ceo_token))
        assert create_resp.status_code in [200, 201], f"Branch create failed: {create_resp.text}"
        branch_id = create_resp.json()["id"]
        
        # Now update as Manager
        mgr_token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert mgr_token, "Manager login failed"
        
        update_data = {"city": "Updated City"}
        update_resp = api_client.put(f"{BASE_URL}/api/branches/{branch_id}", json=update_data, headers=get_auth_header(mgr_token))
        assert update_resp.status_code == 200, f"Manager branch update failed: {update_resp.status_code} - {update_resp.text}"
        updated = update_resp.json()
        assert updated["city"] == "Updated City", "City not updated"
        assert "latitude" not in updated, "Updated branch should NOT have 'latitude'"
        print(f"✓ Manager can update branch: {branch_id}")


class TestBranchDeleteAuthorization:
    """Test branch delete authorization - only super level (CEO/HR) can delete"""

    def test_ceo_can_delete_empty_branch(self, api_client):
        """DELETE /api/branches/{id} as CEO works for empty branch"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        # Create a fresh branch
        branch_data = {
            "name": f"TEST_DeleteBranch_{uuid.uuid4().hex[:8]}",
            "city": "Delete City",
            "area": "Delete Area"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(token))
        assert create_resp.status_code in [200, 201], f"Branch create failed: {create_resp.text}"
        branch_id = create_resp.json()["id"]
        
        # Delete it
        delete_resp = api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(token))
        assert delete_resp.status_code == 200, f"CEO branch delete failed: {delete_resp.status_code} - {delete_resp.text}"
        print(f"✓ CEO can delete empty branch: {branch_id}")

    def test_manager_cannot_delete_branch(self, api_client):
        """DELETE /api/branches/{id} as Manager must return 403 (only super level can delete)"""
        # Create branch as CEO
        ceo_token = login(api_client, **CREDENTIALS["ceo"])
        assert ceo_token, "CEO login failed"
        
        branch_data = {
            "name": f"TEST_MgrDeleteBranch_{uuid.uuid4().hex[:8]}",
            "city": "Test City",
            "area": "Test Area"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(ceo_token))
        assert create_resp.status_code in [200, 201]
        branch_id = create_resp.json()["id"]
        
        # Try to delete as Manager
        mgr_token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert mgr_token, "Manager login failed"
        
        delete_resp = api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(mgr_token))
        assert delete_resp.status_code == 403, f"Expected 403 for manager delete, got {delete_resp.status_code}"
        print("✓ Manager correctly blocked from deleting branch")
        
        # Cleanup - delete as CEO
        api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(ceo_token))

    def test_executor_cannot_delete_branch(self, api_client):
        """DELETE /api/branches/{id} as Executor must return 403"""
        # Create branch as CEO
        ceo_token = login(api_client, **CREDENTIALS["ceo"])
        assert ceo_token, "CEO login failed"
        
        branch_data = {
            "name": f"TEST_ExecDeleteBranch_{uuid.uuid4().hex[:8]}",
            "city": "Test City",
            "area": "Test Area"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(ceo_token))
        assert create_resp.status_code in [200, 201]
        branch_id = create_resp.json()["id"]
        
        # Try to delete as Executor (Jr HR)
        exec_token = login(api_client, **CREDENTIALS["jrhr"])
        assert exec_token, "Jr HR login failed"
        
        delete_resp = api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(exec_token))
        assert delete_resp.status_code == 403, f"Expected 403 for executor delete, got {delete_resp.status_code}"
        print("✓ Executor (Jr HR) correctly blocked from deleting branch")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(ceo_token))


class TestBranchDeleteDependencyCheck:
    """Test that branch with active jobs/employees cannot be deleted"""

    def test_delete_branch_with_job_returns_400(self, api_client):
        """DELETE /api/branches/{id} returns 400 if branch has active jobs"""
        ceo_token = login(api_client, **CREDENTIALS["ceo"])
        assert ceo_token, "CEO login failed"
        
        # Create a fresh branch
        branch_data = {
            "name": f"TEST_BranchWithJob_{uuid.uuid4().hex[:8]}",
            "city": "Job City",
            "area": "Job Area"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(ceo_token))
        assert create_resp.status_code in [200, 201]
        branch_id = create_resp.json()["id"]
        
        # Create a job linked to this branch
        job_data = {
            "role": "TEST_Technician",
            "type": "branch",
            "branch_id": branch_id,
            "location": "Job City",
            "status": "open"
        }
        job_resp = api_client.post(f"{BASE_URL}/api/jobs", json=job_data, headers=get_auth_header(ceo_token))
        assert job_resp.status_code in [200, 201], f"Job create failed: {job_resp.text}"
        job_id = job_resp.json()["id"]
        
        # Try to delete branch - should fail with 400
        delete_resp = api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(ceo_token))
        assert delete_resp.status_code == 400, f"Expected 400 for branch with job, got {delete_resp.status_code}"
        detail = delete_resp.json().get("detail", "")
        assert "job" in detail.lower() or "cannot delete" in detail.lower(), f"Expected job dependency message, got: {detail}"
        print(f"✓ DELETE branch with job correctly returns 400: {detail}")
        
        # Cleanup - delete job first, then branch
        api_client.delete(f"{BASE_URL}/api/jobs/{job_id}", headers=get_auth_header(ceo_token))
        api_client.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=get_auth_header(ceo_token))


# ==================== SECTION 4: DASHBOARD FRANCHISES FIELD ====================

class TestDashboardFranchisesField:
    """Test that CEO/HR/Manager dashboards include 'franchises' field with correct structure"""

    def test_ceo_dashboard_has_franchises(self, api_client):
        """GET /api/dashboard/stats as CEO returns 'franchises' object with {upcoming, active, total_upcoming, total_active}"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/dashboard/stats", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Dashboard stats failed: {resp.status_code}"
        data = resp.json()
        
        assert "franchises" in data, "CEO dashboard missing 'franchises' field"
        franchises = data["franchises"]
        assert "upcoming" in franchises, "franchises missing 'upcoming'"
        assert "active" in franchises, "franchises missing 'active'"
        assert "total_upcoming" in franchises, "franchises missing 'total_upcoming'"
        assert "total_active" in franchises, "franchises missing 'total_active'"
        assert isinstance(franchises["upcoming"], list), "'upcoming' should be a list"
        assert isinstance(franchises["active"], list), "'active' should be a list"
        
        # Check per-branch structure has open_jobs and employees
        for branch in franchises["upcoming"] + franchises["active"]:
            assert "open_jobs" in branch, f"Branch missing 'open_jobs': {branch}"
            assert "employees" in branch, f"Branch missing 'employees': {branch}"
        
        print(f"✓ CEO dashboard has franchises: {franchises['total_upcoming']} upcoming, {franchises['total_active']} active")

    def test_hr_dashboard_has_franchises(self, api_client):
        """GET /api/dashboard/stats as HR returns 'franchises' object"""
        token = login(api_client, **CREDENTIALS["hr"])
        assert token, "HR login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/dashboard/stats", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Dashboard stats failed: {resp.status_code}"
        data = resp.json()
        
        assert "franchises" in data, "HR dashboard missing 'franchises' field"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        assert "total_upcoming" in franchises and "total_active" in franchises
        print(f"✓ HR dashboard has franchises: {franchises['total_upcoming']} upcoming, {franchises['total_active']} active")

    def test_manager_dashboard_has_franchises(self, api_client):
        """GET /api/dashboard/stats as Manager returns 'franchises' object"""
        token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert token, "Manager login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/dashboard/stats", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Dashboard stats failed: {resp.status_code}"
        data = resp.json()
        
        assert "franchises" in data, "Manager dashboard missing 'franchises' field"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        assert "total_upcoming" in franchises and "total_active" in franchises
        print(f"✓ Manager dashboard has franchises: {franchises['total_upcoming']} upcoming, {franchises['total_active']} active")


# ==================== SECTION 5: RBAC - FEEDBACK ENDPOINTS ====================

class TestFeedbackRBAC:
    """Test that feedback admin endpoints return 403 for managers and executors (only CEO+HR allowed)"""

    def test_feedback_submissions_manager_returns_403(self, api_client):
        """GET /api/feedback/submissions as Manager returns 403"""
        token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert token, "Manager login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/feedback/submissions", headers=get_auth_header(token))
        assert resp.status_code == 403, f"Expected 403 for manager, got {resp.status_code}"
        print("✓ GET /api/feedback/submissions returns 403 for Manager")

    def test_feedback_submissions_executor_returns_403(self, api_client):
        """GET /api/feedback/submissions as Executor (Jr HR) returns 403"""
        token = login(api_client, **CREDENTIALS["jrhr"])
        assert token, "Jr HR login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/feedback/submissions", headers=get_auth_header(token))
        assert resp.status_code == 403, f"Expected 403 for executor, got {resp.status_code}"
        print("✓ GET /api/feedback/submissions returns 403 for Executor (Jr HR)")

    def test_feedback_submissions_ceo_returns_200(self, api_client):
        """GET /api/feedback/submissions as CEO returns 200"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/feedback/submissions", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Expected 200 for CEO, got {resp.status_code}"
        print("✓ GET /api/feedback/submissions returns 200 for CEO")

    def test_feedback_submissions_hr_returns_200(self, api_client):
        """GET /api/feedback/submissions as HR returns 200"""
        token = login(api_client, **CREDENTIALS["hr"])
        assert token, "HR login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/feedback/submissions", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Expected 200 for HR, got {resp.status_code}"
        print("✓ GET /api/feedback/submissions returns 200 for HR")


# ==================== SECTION 6: RBAC - AUDIT LOGS ====================

class TestAuditLogsRBAC:
    """Test that audit logs return 403 for managers and executors (only super level allowed)"""

    def test_audit_logs_manager_returns_403(self, api_client):
        """GET /api/audit as Manager returns 403 (only super level)"""
        token = login(api_client, **CREDENTIALS["marketing_mgr"])
        assert token, "Manager login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/audit", headers=get_auth_header(token))
        assert resp.status_code == 403, f"Expected 403 for manager, got {resp.status_code}"
        print("✓ GET /api/audit returns 403 for Manager")

    def test_audit_logs_executor_returns_403(self, api_client):
        """GET /api/audit as Executor (Jr HR) returns 403"""
        token = login(api_client, **CREDENTIALS["jrhr"])
        assert token, "Jr HR login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/audit", headers=get_auth_header(token))
        assert resp.status_code == 403, f"Expected 403 for executor, got {resp.status_code}"
        print("✓ GET /api/audit returns 403 for Executor (Jr HR)")

    def test_audit_logs_ceo_returns_200(self, api_client):
        """GET /api/audit as CEO returns 200"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/audit", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Expected 200 for CEO, got {resp.status_code}"
        print("✓ GET /api/audit returns 200 for CEO")


# ==================== SECTION 7: RECRUITMENT OVERVIEW STILL WORKS ====================

class TestRecruitmentOverview:
    """Test that /api/branches/recruitment-overview still works"""

    def test_recruitment_overview_works(self, api_client):
        """GET /api/branches/recruitment-overview still works"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        resp = api_client.get(f"{BASE_URL}/api/branches/recruitment-overview", headers=get_auth_header(token))
        assert resp.status_code == 200, f"Recruitment overview failed: {resp.status_code}"
        data = resp.json()
        
        assert "upcoming" in data, "Missing 'upcoming'"
        assert "active" in data, "Missing 'active'"
        assert "total_upcoming" in data, "Missing 'total_upcoming'"
        assert "total_active" in data, "Missing 'total_active'"
        print(f"✓ GET /api/branches/recruitment-overview works: {data['total_upcoming']} upcoming, {data['total_active']} active")


# ==================== SECTION 8: BRANCH CREATE IGNORES LAT/LONG ====================

class TestBranchCreateIgnoresLatLong:
    """Test that branch creation silently ignores latitude/longitude fields"""

    def test_branch_create_ignores_lat_long(self, api_client):
        """Brand-new branch creation does NOT accept latitude/longitude — they should be silently ignored"""
        token = login(api_client, **CREDENTIALS["ceo"])
        assert token, "CEO login failed"
        
        branch_data = {
            "name": f"TEST_LatLongBranch_{uuid.uuid4().hex[:8]}",
            "city": "LatLong City",
            "area": "LatLong Area",
            "latitude": 12.345,  # Should be ignored
            "longitude": 67.890  # Should be ignored
        }
        resp = api_client.post(f"{BASE_URL}/api/branches", json=branch_data, headers=get_auth_header(token))
        assert resp.status_code in [200, 201], f"Branch create failed: {resp.status_code} - {resp.text}"
        created = resp.json()
        
        # Response should NOT have lat/long
        assert "latitude" not in created, f"Created branch should NOT have 'latitude': {created}"
        assert "longitude" not in created, f"Created branch should NOT have 'longitude': {created}"
        print(f"✓ Branch create ignores lat/long fields: {created['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/branches/{created['id']}", headers=get_auth_header(token))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
