import requests
import sys
import json
from datetime import datetime

class RoleBasedTester:
    def __init__(self, base_url="https://hrms-lead-delete.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login_user(self, email, password, expected_role):
        """Login and return token"""
        success, response = self.run_test(
            f"Login as {expected_role}",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            user_data = response.get('user', {})
            actual_role = user_data.get('role', 'Unknown')
            if actual_role == expected_role:
                print(f"   ✅ Logged in as: {user_data.get('name', 'Unknown')} ({actual_role})")
                return response['access_token'], user_data
            else:
                print(f"   ❌ Role mismatch: Expected {expected_role}, got {actual_role}")
                return None, None
        return None, None

    def test_dashboard_type(self, token, expected_type, role_name):
        """Test dashboard returns correct type for role"""
        success, response = self.run_test(
            f"Dashboard for {role_name}",
            "GET",
            "dashboard/stats",
            200,
            token=token
        )
        if success:
            dashboard_type = response.get('type', 'unknown')
            user_level = response.get('user_level', 'unknown')
            if dashboard_type == expected_type:
                print(f"   ✅ Dashboard type: {dashboard_type} (level: {user_level})")
                return True, response
            else:
                print(f"   ❌ Dashboard type mismatch: Expected {expected_type}, got {dashboard_type}")
                return False, response
        return False, {}

    def test_user_management_access(self, token, role_name, should_have_access):
        """Test user management access based on role"""
        success, response = self.run_test(
            f"User Management Access for {role_name}",
            "GET",
            "users",
            200 if should_have_access else 403,
            token=token
        )
        if should_have_access and success:
            print(f"   ✅ {role_name} can access user management")
            return True, response
        elif not should_have_access and not success:
            print(f"   ✅ {role_name} correctly blocked from user management")
            return True, {}
        else:
            print(f"   ❌ Unexpected access result for {role_name}")
            return False, {}

    def test_audit_logs_access(self, token, role_name, should_have_access):
        """Test audit logs access based on role"""
        success, response = self.run_test(
            f"Audit Logs Access for {role_name}",
            "GET",
            "audit",
            200 if should_have_access else 403,
            token=token
        )
        if should_have_access and success:
            print(f"   ✅ {role_name} can access audit logs")
            return True, response
        elif not should_have_access and not success:
            print(f"   ✅ {role_name} correctly blocked from audit logs")
            return True, {}
        else:
            print(f"   ❌ Unexpected access result for {role_name}")
            return False, {}

    def test_user_crud_operations(self, token, role_name):
        """Test user CRUD operations"""
        print(f"\n🔧 Testing User CRUD for {role_name}...")
        
        # Test create user
        user_data = {
            "email": f"test{datetime.now().strftime('%H%M%S')}@servall.com",
            "password": "TestPassword123!",
            "name": f"Test User {datetime.now().strftime('%H%M%S')}",
            "role": "HR Executive",
            "department": "HR"
        }
        success, user = self.run_test(
            f"Create User by {role_name}",
            "POST",
            "users",
            200,
            data=user_data,
            token=token
        )
        
        if not success:
            return False
            
        user_id = user.get('id')
        if not user_id:
            print("   ❌ No user ID returned")
            return False
            
        # Test edit user
        edit_data = {"name": f"Updated {user['name']}"}
        success, _ = self.run_test(
            f"Edit User by {role_name}",
            "PUT",
            f"users/{user_id}",
            200,
            data=edit_data,
            token=token
        )
        
        if not success:
            return False
            
        # Test password reset (only for super level)
        if role_name in ["CEO", "Sr HR"]:
            reset_data = {"new_password": "NewPassword123!"}
            success, _ = self.run_test(
                f"Reset Password by {role_name}",
                "POST",
                f"users/{user_id}/reset-password",
                200,
                data=reset_data,
                token=token
            )
            
            if not success:
                return False
                
        # Test delete user (only for super level)
        if role_name in ["CEO", "Sr HR"]:
            success, _ = self.run_test(
                f"Delete User by {role_name}",
                "DELETE",
                f"users/{user_id}",
                200,
                token=token
            )
            
            if not success:
                return False
                
        return True

    def run_role_based_tests(self):
        """Run comprehensive role-based tests"""
        print("🚀 Starting Role-Based Dashboard Testing...")
        print(f"Base URL: {self.base_url}")
        
        # Test credentials from test_credentials.md
        test_cases = [
            {
                "email": "admin@servall.com",
                "password": "ServallAdmin@123", 
                "role": "CEO",
                "expected_dashboard": "ceo",
                "user_management": True,
                "audit_access": True,
                "can_crud_users": True
            },
            {
                "email": "srhr@servall.com",
                "password": "Servall@123",
                "role": "Sr HR", 
                "expected_dashboard": "hr",
                "user_management": True,
                "audit_access": True,
                "can_crud_users": True
            },
            {
                "email": "marketing.mgr@servall.com",
                "password": "Servall@123",
                "role": "Marketing Manager",
                "expected_dashboard": "manager", 
                "user_management": True,
                "audit_access": False,
                "can_crud_users": False
            },
            {
                "email": "hr.exec@servall.com", 
                "password": "Servall@123",
                "role": "HR Executive",
                "expected_dashboard": "executor",
                "user_management": False,
                "audit_access": False,
                "can_crud_users": False
            }
        ]
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"🧪 Testing Role: {test_case['role']}")
            print(f"{'='*60}")
            
            # Login
            token, user_data = self.login_user(
                test_case['email'], 
                test_case['password'], 
                test_case['role']
            )
            
            if not token:
                print(f"❌ Failed to login as {test_case['role']}")
                continue
                
            # Test dashboard type
            dashboard_success, dashboard_data = self.test_dashboard_type(
                token, 
                test_case['expected_dashboard'], 
                test_case['role']
            )
            
            # Test user management access
            user_mgmt_success, _ = self.test_user_management_access(
                token,
                test_case['role'],
                test_case['user_management']
            )
            
            # Test audit logs access
            audit_success, _ = self.test_audit_logs_access(
                token,
                test_case['role'], 
                test_case['audit_access']
            )
            
            # Test CRUD operations if allowed
            crud_success = True
            if test_case['can_crud_users']:
                crud_success = self.test_user_crud_operations(token, test_case['role'])
            
            # Store results
            self.test_results.append({
                "role": test_case['role'],
                "login": token is not None,
                "dashboard": dashboard_success,
                "user_management": user_mgmt_success,
                "audit_access": audit_success,
                "crud_operations": crud_success,
                "dashboard_data": dashboard_data
            })
        
        # Print summary
        print(f"\n{'='*60}")
        print("📊 ROLE-BASED TEST SUMMARY")
        print(f"{'='*60}")
        
        for result in self.test_results:
            print(f"\n🎭 {result['role']}:")
            print(f"   Login: {'✅' if result['login'] else '❌'}")
            print(f"   Dashboard: {'✅' if result['dashboard'] else '❌'}")
            print(f"   User Management: {'✅' if result['user_management'] else '❌'}")
            print(f"   Audit Access: {'✅' if result['audit_access'] else '❌'}")
            print(f"   CRUD Operations: {'✅' if result['crud_operations'] else '❌'}")
            
            # Show dashboard specifics
            if result['dashboard_data']:
                data = result['dashboard_data']
                print(f"   Dashboard Type: {data.get('type', 'unknown')}")
                print(f"   User Level: {data.get('user_level', 'unknown')}")
                
                # Show role-specific data
                if data.get('type') == 'ceo':
                    print(f"   Branch Stats: {len(data.get('branch_stats', []))} branches")
                    print(f"   Total Leads: {data.get('total_leads', 0)}")
                elif data.get('type') == 'hr':
                    print(f"   Pending Interviews: {len(data.get('interviews_pending', []))}")
                    print(f"   Total Users: {data.get('total_users', 0)}")
                elif data.get('type') == 'manager':
                    print(f"   Team Members: {data.get('team_count', 0)}")
                    print(f"   Department: {data.get('department', 'unknown')}")
                elif data.get('type') == 'executor':
                    print(f"   My Leads: {data.get('my_leads_count', 0)}")
                    print(f"   Follow-ups Needed: {data.get('followups_count', 0)}")
        
        print(f"\n📈 Overall Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = RoleBasedTester()
    success = tester.run_role_based_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())