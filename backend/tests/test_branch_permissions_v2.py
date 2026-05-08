"""
Test Branch Permission Matrix v2 (January 2026)
Tests the updated RBAC for branches:
- GET /api/branches: ALL roles (view-only for Mktg Coord, Designer, FDE)
- POST/PUT /api/branches: CEO, HR, 4 Managers, Sr HR, Jr HR
- DELETE /api/branches: CEO, HR, Sr HR, Jr HR ONLY (Managers now restricted)
- Dashboard franchises field: Added to Sr/Jr HR, FDE, Designer, Mktg Coord
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
    "sr_hr": {"email": "srhr@servall.com", "password": "Servall@123"},
    "jr_hr": {"email": "jrhr@servall.com", "password": "Servall@123"},
    "marketing_mgr": {"email": "marketing.mgr@servall.com", "password": "Servall@123"},
    "ops_mgr": {"email": "ops.mgr@servall.com", "password": "Servall@123"},
    "sales_mgr": {"email": "sales.mgr@servall.com", "password": "Servall@123"},
    "accounts_mgr": {"email": "accounts.mgr@servall.com", "password": "Servall@123"},
    "designer": {"email": "designer@servall.com", "password": "Servall@123"},
    "mktg_coord": {"email": "marketing.coord@servall.com", "password": "Servall@123"},
    "fde": {"email": "franchise.exec@servall.com", "password": "Servall@123"},
}


def get_token(email: str, password: str) -> str:
    """Login and return access_token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    data = resp.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def tokens():
    """Get tokens for all test users"""
    result = {}
    for key, creds in CREDENTIALS.items():
        result[key] = get_token(creds["email"], creds["password"])
    return result


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==================== GET /api/branches - ALL roles allowed ====================

class TestGetBranchesAllRoles:
    """GET /api/branches should return 200 for ALL roles (view-only for some)"""

    def test_get_branches_as_designer(self, tokens):
        """Graphic Designer can view branches"""
        resp = requests.get(f"{BASE_URL}/api/branches", headers=auth_header(tokens["designer"]))
        assert resp.status_code == 200, f"Designer GET branches failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Expected list of branches"
        print(f"Designer GET /api/branches: 200 OK, {len(data)} branches")

    def test_get_branches_as_mktg_coord(self, tokens):
        """Marketing Coordinator can view branches"""
        resp = requests.get(f"{BASE_URL}/api/branches", headers=auth_header(tokens["mktg_coord"]))
        assert resp.status_code == 200, f"Mktg Coord GET branches failed: {resp.text}"
        print("Marketing Coordinator GET /api/branches: 200 OK")

    def test_get_branches_as_fde(self, tokens):
        """Franchise Executive can view branches"""
        resp = requests.get(f"{BASE_URL}/api/branches", headers=auth_header(tokens["fde"]))
        assert resp.status_code == 200, f"FDE GET branches failed: {resp.text}"
        print("Franchise Executive GET /api/branches: 200 OK")


# ==================== POST /api/branches - EDIT_ROLES allowed ====================

class TestPostBranchesPermissions:
    """POST /api/branches: CEO, HR, 4 Managers, Sr HR, Jr HR allowed; Designer/MktgCoord/FDE forbidden"""

    def test_post_branch_as_sr_hr(self, tokens):
        """Sr HR can now create branches (NEW permission)"""
        branch_name = f"TEST_SrHR_Branch_{uuid.uuid4().hex[:6]}"
        payload = {"name": branch_name, "city": "Mumbai", "area": "Andheri"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["sr_hr"]))
        assert resp.status_code == 200, f"Sr HR POST branch failed: {resp.text}"
        data = resp.json()
        assert data["name"] == branch_name
        print(f"Sr HR POST /api/branches: 200 OK, created {branch_name}")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/branches/{data['id']}", headers=auth_header(tokens["sr_hr"]))

    def test_post_branch_as_jr_hr(self, tokens):
        """Jr HR can now create branches (NEW permission)"""
        branch_name = f"TEST_JrHR_Branch_{uuid.uuid4().hex[:6]}"
        payload = {"name": branch_name, "city": "Delhi", "area": "Connaught Place"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["jr_hr"]))
        assert resp.status_code == 200, f"Jr HR POST branch failed: {resp.text}"
        data = resp.json()
        assert data["name"] == branch_name
        print(f"Jr HR POST /api/branches: 200 OK, created {branch_name}")
        # Cleanup
        requests.delete(f"{BASE_URL}/api/branches/{data['id']}", headers=auth_header(tokens["jr_hr"]))

    def test_post_branch_as_marketing_mgr(self, tokens):
        """Marketing Manager can create branches"""
        branch_name = f"TEST_MktgMgr_Branch_{uuid.uuid4().hex[:6]}"
        payload = {"name": branch_name, "city": "Bangalore", "area": "Koramangala"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["marketing_mgr"]))
        assert resp.status_code == 200, f"Marketing Manager POST branch failed: {resp.text}"
        print(f"Marketing Manager POST /api/branches: 200 OK")
        # Cleanup with CEO
        data = resp.json()
        requests.delete(f"{BASE_URL}/api/branches/{data['id']}", headers=auth_header(tokens["ceo"]))

    def test_post_branch_as_designer_forbidden(self, tokens):
        """Graphic Designer cannot create branches (403)"""
        payload = {"name": "TEST_Designer_Branch", "city": "Chennai", "area": "T Nagar"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["designer"]))
        assert resp.status_code == 403, f"Designer POST should be 403, got {resp.status_code}: {resp.text}"
        print("Graphic Designer POST /api/branches: 403 Forbidden (correct)")

    def test_post_branch_as_mktg_coord_forbidden(self, tokens):
        """Marketing Coordinator cannot create branches (403)"""
        payload = {"name": "TEST_MktgCoord_Branch", "city": "Pune", "area": "Kothrud"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["mktg_coord"]))
        assert resp.status_code == 403, f"Mktg Coord POST should be 403, got {resp.status_code}: {resp.text}"
        print("Marketing Coordinator POST /api/branches: 403 Forbidden (correct)")

    def test_post_branch_as_fde_forbidden(self, tokens):
        """Franchise Executive cannot create branches (403)"""
        payload = {"name": "TEST_FDE_Branch", "city": "Hyderabad", "area": "Banjara Hills"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["fde"]))
        assert resp.status_code == 403, f"FDE POST should be 403, got {resp.status_code}: {resp.text}"
        print("Franchise Executive POST /api/branches: 403 Forbidden (correct)")


# ==================== PUT /api/branches - EDIT_ROLES allowed ====================

class TestPutBranchesPermissions:
    """PUT /api/branches: Sr HR, Jr HR can now edit; Designer forbidden"""

    @pytest.fixture
    def test_branch(self, tokens):
        """Create a test branch for PUT tests"""
        branch_name = f"TEST_PUT_Branch_{uuid.uuid4().hex[:6]}"
        payload = {"name": branch_name, "city": "Test City", "area": "Test Area"}
        resp = requests.post(f"{BASE_URL}/api/branches", json=payload, headers=auth_header(tokens["ceo"]))
        assert resp.status_code == 200
        branch = resp.json()
        yield branch
        # Cleanup
        requests.delete(f"{BASE_URL}/api/branches/{branch['id']}", headers=auth_header(tokens["ceo"]))

    def test_put_branch_as_sr_hr(self, tokens, test_branch):
        """Sr HR can now edit branches (NEW permission)"""
        resp = requests.put(
            f"{BASE_URL}/api/branches/{test_branch['id']}",
            json={"city": "Updated by Sr HR"},
            headers=auth_header(tokens["sr_hr"])
        )
        assert resp.status_code == 200, f"Sr HR PUT branch failed: {resp.text}"
        data = resp.json()
        assert data["city"] == "Updated by Sr HR"
        print("Sr HR PUT /api/branches: 200 OK")

    def test_put_branch_as_jr_hr(self, tokens, test_branch):
        """Jr HR can now edit branches (NEW permission)"""
        resp = requests.put(
            f"{BASE_URL}/api/branches/{test_branch['id']}",
            json={"area": "Updated by Jr HR"},
            headers=auth_header(tokens["jr_hr"])
        )
        assert resp.status_code == 200, f"Jr HR PUT branch failed: {resp.text}"
        data = resp.json()
        assert data["area"] == "Updated by Jr HR"
        print("Jr HR PUT /api/branches: 200 OK")

    def test_put_branch_as_designer_forbidden(self, tokens, test_branch):
        """Graphic Designer cannot edit branches (403)"""
        resp = requests.put(
            f"{BASE_URL}/api/branches/{test_branch['id']}",
            json={"city": "Should Fail"},
            headers=auth_header(tokens["designer"])
        )
        assert resp.status_code == 403, f"Designer PUT should be 403, got {resp.status_code}: {resp.text}"
        print("Graphic Designer PUT /api/branches: 403 Forbidden (correct)")


# ==================== DELETE /api/branches - DELETE_ROLES only ====================

class TestDeleteBranchesPermissions:
    """DELETE /api/branches: CEO, HR, Sr HR, Jr HR ONLY; Managers now restricted"""

    def test_delete_branch_as_sr_hr(self, tokens):
        """Sr HR can now delete branches (NEW permission)"""
        # Create branch first
        branch_name = f"TEST_SrHR_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["sr_hr"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Delete as Sr HR
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["sr_hr"]))
        assert del_resp.status_code == 200, f"Sr HR DELETE branch failed: {del_resp.text}"
        print("Sr HR DELETE /api/branches: 200 OK")

    def test_delete_branch_as_jr_hr(self, tokens):
        """Jr HR can now delete branches (NEW permission)"""
        # Create branch first
        branch_name = f"TEST_JrHR_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["jr_hr"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Delete as Jr HR
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["jr_hr"]))
        assert del_resp.status_code == 200, f"Jr HR DELETE branch failed: {del_resp.text}"
        print("Jr HR DELETE /api/branches: 200 OK")

    def test_delete_branch_as_marketing_mgr_forbidden(self, tokens):
        """Marketing Manager cannot delete branches (now restricted)"""
        # Create branch as CEO
        branch_name = f"TEST_MktgMgr_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["ceo"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Try delete as Marketing Manager - should fail
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["marketing_mgr"]))
        assert del_resp.status_code == 403, f"Marketing Manager DELETE should be 403, got {del_resp.status_code}: {del_resp.text}"
        print("Marketing Manager DELETE /api/branches: 403 Forbidden (correct)")
        
        # Cleanup with CEO
        requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ceo"]))

    def test_delete_branch_as_ops_mgr_forbidden(self, tokens):
        """Operations Manager cannot delete branches (now restricted)"""
        # Create branch as CEO
        branch_name = f"TEST_OpsMgr_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["ceo"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Try delete as Ops Manager - should fail
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ops_mgr"]))
        assert del_resp.status_code == 403, f"Ops Manager DELETE should be 403, got {del_resp.status_code}: {del_resp.text}"
        print("Operations Manager DELETE /api/branches: 403 Forbidden (correct)")
        
        # Cleanup with CEO
        requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ceo"]))

    def test_delete_branch_as_sales_mgr_forbidden(self, tokens):
        """Sales Manager cannot delete branches (now restricted)"""
        # Create branch as CEO
        branch_name = f"TEST_SalesMgr_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["ceo"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Try delete as Sales Manager - should fail
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["sales_mgr"]))
        assert del_resp.status_code == 403, f"Sales Manager DELETE should be 403, got {del_resp.status_code}: {del_resp.text}"
        print("Sales Manager DELETE /api/branches: 403 Forbidden (correct)")
        
        # Cleanup with CEO
        requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ceo"]))

    def test_delete_branch_as_accounts_mgr_forbidden(self, tokens):
        """Accounts Manager cannot delete branches (now restricted)"""
        # Create branch as CEO
        branch_name = f"TEST_AcctsMgr_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["ceo"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Try delete as Accounts Manager - should fail
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["accounts_mgr"]))
        assert del_resp.status_code == 403, f"Accounts Manager DELETE should be 403, got {del_resp.status_code}: {del_resp.text}"
        print("Accounts Manager DELETE /api/branches: 403 Forbidden (correct)")
        
        # Cleanup with CEO
        requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ceo"]))

    def test_delete_branch_as_designer_forbidden(self, tokens):
        """Graphic Designer cannot delete branches (403)"""
        # Create branch as CEO
        branch_name = f"TEST_Designer_Delete_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/branches",
            json={"name": branch_name, "city": "Delete City", "area": "Delete Area"},
            headers=auth_header(tokens["ceo"])
        )
        assert create_resp.status_code == 200
        branch_id = create_resp.json()["id"]
        
        # Try delete as Designer - should fail
        del_resp = requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["designer"]))
        assert del_resp.status_code == 403, f"Designer DELETE should be 403, got {del_resp.status_code}: {del_resp.text}"
        print("Graphic Designer DELETE /api/branches: 403 Forbidden (correct)")
        
        # Cleanup with CEO
        requests.delete(f"{BASE_URL}/api/branches/{branch_id}", headers=auth_header(tokens["ceo"]))


# ==================== Dashboard franchises field ====================

class TestDashboardFranchisesField:
    """Dashboard /api/dashboard/stats should include 'franchises' field for Sr/Jr HR, FDE, Designer, Mktg Coord"""

    def test_dashboard_sr_hr_has_franchises(self, tokens):
        """Sr HR dashboard includes 'franchises' field"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(tokens["sr_hr"]))
        assert resp.status_code == 200, f"Sr HR dashboard failed: {resp.text}"
        data = resp.json()
        assert "franchises" in data, f"Sr HR dashboard missing 'franchises' field. Keys: {data.keys()}"
        franchises = data["franchises"]
        assert "upcoming" in franchises, "franchises missing 'upcoming'"
        assert "active" in franchises, "franchises missing 'active'"
        assert isinstance(franchises["upcoming"], list), "franchises.upcoming should be list"
        assert isinstance(franchises["active"], list), "franchises.active should be list"
        print(f"Sr HR dashboard has 'franchises': {franchises.get('total_upcoming', 0)} upcoming, {franchises.get('total_active', 0)} active")

    def test_dashboard_jr_hr_has_franchises(self, tokens):
        """Jr HR dashboard includes 'franchises' field"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(tokens["jr_hr"]))
        assert resp.status_code == 200, f"Jr HR dashboard failed: {resp.text}"
        data = resp.json()
        assert "franchises" in data, f"Jr HR dashboard missing 'franchises' field. Keys: {data.keys()}"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        print(f"Jr HR dashboard has 'franchises': {franchises.get('total_upcoming', 0)} upcoming, {franchises.get('total_active', 0)} active")

    def test_dashboard_fde_has_franchises(self, tokens):
        """Franchise Executive dashboard includes 'franchises' field"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(tokens["fde"]))
        assert resp.status_code == 200, f"FDE dashboard failed: {resp.text}"
        data = resp.json()
        assert "franchises" in data, f"FDE dashboard missing 'franchises' field. Keys: {data.keys()}"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        print(f"FDE dashboard has 'franchises': {franchises.get('total_upcoming', 0)} upcoming, {franchises.get('total_active', 0)} active")

    def test_dashboard_designer_has_franchises(self, tokens):
        """Graphic Designer dashboard includes 'franchises' field"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(tokens["designer"]))
        assert resp.status_code == 200, f"Designer dashboard failed: {resp.text}"
        data = resp.json()
        assert "franchises" in data, f"Designer dashboard missing 'franchises' field. Keys: {data.keys()}"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        print(f"Designer dashboard has 'franchises': {franchises.get('total_upcoming', 0)} upcoming, {franchises.get('total_active', 0)} active")

    def test_dashboard_mktg_coord_has_franchises(self, tokens):
        """Marketing Coordinator dashboard includes 'franchises' field"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_header(tokens["mktg_coord"]))
        assert resp.status_code == 200, f"Mktg Coord dashboard failed: {resp.text}"
        data = resp.json()
        assert "franchises" in data, f"Mktg Coord dashboard missing 'franchises' field. Keys: {data.keys()}"
        franchises = data["franchises"]
        assert "upcoming" in franchises and "active" in franchises
        print(f"Mktg Coord dashboard has 'franchises': {franchises.get('total_upcoming', 0)} upcoming, {franchises.get('total_active', 0)} active")
