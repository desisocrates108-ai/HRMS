import requests
import sys
import json
from datetime import datetime

class ServallAPITester:
    def __init__(self, base_url="https://hrms-db-enhance.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_data = None
        self.created_entities = {
            'branches': [],
            'jobs': [],
            'leads': [],
            'tasks': [],
            'users': [],
            'chats': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30, allow_redirects=False)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30, allow_redirects=False)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30, allow_redirects=False)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30, allow_redirects=False)

            # Handle redirects manually to preserve auth headers
            if response.status_code in [301, 302, 307, 308]:
                redirect_url = response.headers.get('Location')
                print(f"   Redirect to: {redirect_url}")
                if redirect_url:
                    if method == 'GET':
                        response = requests.get(redirect_url, headers=test_headers, timeout=30)
                    elif method == 'POST':
                        response = requests.post(redirect_url, json=data, headers=test_headers, timeout=30)
                    elif method == 'PUT':
                        response = requests.put(redirect_url, json=data, headers=test_headers, timeout=30)
                    elif method == 'DELETE':
                        response = requests.delete(redirect_url, headers=test_headers, timeout=30)

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

    def test_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@servall.com", "password": "ServallAdmin@123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   Logged in as: {self.user_data.get('name', 'Unknown')} ({self.user_data.get('role', 'Unknown')})")
            return True
        return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_dashboard_stats(self):
        """Test dashboard stats with new CEO structure"""
        success, response = self.run_test(
            "Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        if success:
            print(f"   Dashboard type: {response.get('type', 'unknown')}")
            
            # Check for CEO/HR dashboard structure
            if response.get('type') in ['ceo', 'hr']:
                # Verify top metrics
                top_metrics = response.get('top_metrics', {})
                required_metrics = ['total_leads', 'total_hirings', 'total_employees', 'calls_done']
                for metric in required_metrics:
                    if metric in top_metrics:
                        print(f"   ✅ {metric}: {top_metrics[metric]}")
                    else:
                        print(f"   ❌ Missing metric: {metric}")
                        
                # Verify technician hiring section
                tech_hiring = response.get('technician_hiring', {})
                if tech_hiring:
                    print(f"   ✅ Technician hiring section present")
                    print(f"      - Jobs: {len(tech_hiring.get('jobs', []))}")
                    print(f"      - Total leads: {tech_hiring.get('total_leads', 0)}")
                    leads_by_source = tech_hiring.get('leads_by_source', {})
                    for source in ['meta_ads', 'job_portal', 'manual']:
                        count = len(leads_by_source.get(source, []))
                        print(f"      - {source}: {count} leads")
                else:
                    print(f"   ❌ Missing technician hiring section")
                    
                # Verify HO hiring section
                ho_hiring = response.get('ho_hiring', {})
                if ho_hiring:
                    print(f"   ✅ HO hiring section present")
                    print(f"      - Jobs: {len(ho_hiring.get('jobs', []))}")
                    print(f"      - Total leads: {ho_hiring.get('total_leads', 0)}")
                else:
                    print(f"   ❌ Missing HO hiring section")
                    
                # Verify call tracking
                call_tracking = response.get('call_tracking', [])
                if call_tracking:
                    print(f"   ✅ Call tracking present: {len(call_tracking)} executives")
                    for exec_data in call_tracking[:3]:  # Show first 3
                        print(f"      - {exec_data.get('name', 'Unknown')}: {exec_data.get('total_calls', 0)} calls")
                else:
                    print(f"   ❌ Missing call tracking section")
                    
                # Check lead enrichment in first few leads
                all_leads = []
                if tech_hiring.get('leads_by_source'):
                    for source_leads in tech_hiring['leads_by_source'].values():
                        all_leads.extend(source_leads[:2])  # Take first 2 from each source
                        
                if all_leads:
                    print(f"   ✅ Testing lead enrichment on {len(all_leads)} leads:")
                    for lead in all_leads:
                        enrichment_fields = ['experience', 'salary_expectation', 'interview_date', 'assigned_to_name', 'stage_label', 'branch_name']
                        present_fields = [f for f in enrichment_fields if f in lead and lead[f]]
                        print(f"      - {lead.get('name', 'Unknown')}: {len(present_fields)}/{len(enrichment_fields)} enriched fields")
                        
            else:
                print(f"   Dashboard type: {response.get('type', 'unknown')} (not CEO/HR)")
                
        return success

    def test_branches(self):
        """Test branch operations"""
        # List branches
        success, branches = self.run_test(
            "List Branches",
            "GET",
            "branches",
            200
        )
        if not success:
            return False

        # Create branch
        branch_data = {
            "name": f"Test Branch {datetime.now().strftime('%H%M%S')}",
            "city": "Mumbai",
            "area": "Andheri",
            "latitude": 19.1136,
            "longitude": 72.8697
        }
        success, branch = self.run_test(
            "Create Branch",
            "POST",
            "branches",
            200,
            data=branch_data
        )
        if success and 'id' in branch:
            self.created_entities['branches'].append(branch['id'])
            print(f"   Created branch: {branch['name']} (ID: {branch['id']})")
        return success

    def test_jobs(self):
        """Test job operations"""
        # List jobs
        success, jobs = self.run_test(
            "List Jobs",
            "GET",
            "jobs",
            200
        )
        if not success:
            return False

        # Create job
        job_data = {
            "role": "Service Technician",
            "type": "branch",
            "location": "Mumbai, Andheri",
            "salary_range_min": 25000,
            "salary_range_max": 35000,
            "description": "Two-wheeler service technician position"
        }
        success, job = self.run_test(
            "Create Job",
            "POST",
            "jobs",
            200,
            data=job_data
        )
        if success and 'id' in job:
            self.created_entities['jobs'].append(job['id'])
            print(f"   Created job: {job['role']} (ID: {job['id']})")
            
            # Test get specific job
            success, _ = self.run_test(
                "Get Job Details",
                "GET",
                f"jobs/{job['id']}",
                200
            )
        return success

    def test_leads(self):
        """Test lead operations"""
        # List leads
        success, leads = self.run_test(
            "List Leads",
            "GET",
            "leads",
            200
        )
        if not success:
            return False

        # Test pipeline stats
        success, stats = self.run_test(
            "Pipeline Stats",
            "GET",
            "leads/pipeline-stats",
            200
        )
        if not success:
            return False

        # Create lead
        lead_data = {
            "name": f"Test Candidate {datetime.now().strftime('%H%M%S')}",
            "phone": "9876543210",
            "email": f"test{datetime.now().strftime('%H%M%S')}@example.com",
            "location_city": "Mumbai",
            "location_area": "Andheri",
            "source": "manual",
            "is_technician": True
        }
        success, lead = self.run_test(
            "Create Lead",
            "POST",
            "leads",
            200,
            data=lead_data
        )
        if success and 'id' in lead:
            self.created_entities['leads'].append(lead['id'])
            print(f"   Created lead: {lead['name']} (ID: {lead['id']})")
            
            # Test stage transition
            transition_data = {
                "to_stage": "qualified",
                "form_data": {
                    "experience": "2",
                    "location_confirmation": "yes",
                    "salary_expectation": "30000",
                    "relocation_preference": "no"
                }
            }
            success, _ = self.run_test(
                "Stage Transition to Qualified",
                "POST",
                f"leads/{lead['id']}/transition",
                200,
                data=transition_data
            )
            
            if success:
                # Test another stage transition
                interview_data = {
                    "to_stage": "awaiting_interview",
                    "form_data": {
                        "interview_date": "2024-12-20",
                        "mode": "in-person",
                        "interviewer": "HR Manager"
                    }
                }
                success, _ = self.run_test(
                    "Stage Transition to Awaiting Interview",
                    "POST",
                    f"leads/{lead['id']}/transition",
                    200,
                    data=interview_data
                )
                
                if success:
                    # Test interview cleared
                    cleared_data = {
                        "to_stage": "interview_cleared",
                        "form_data": {
                            "interview_score": "8"
                        }
                    }
                    success, _ = self.run_test(
                        "Stage Transition to Interview Cleared",
                        "POST",
                        f"leads/{lead['id']}/transition",
                        200,
                        data=cleared_data
                    )
            
            # Test call log
            call_data = {
                "notes": "Initial screening call completed. Candidate seems interested."
            }
            success, _ = self.run_test(
                "Add Call Log",
                "POST",
                f"leads/{lead['id']}/calls",
                200,
                data=call_data
            )
            
            # Test get call logs
            success, _ = self.run_test(
                "Get Call Logs",
                "GET",
                f"leads/{lead['id']}/calls",
                200
            )
            
            # Test lead history
            success, _ = self.run_test(
                "Get Lead History",
                "GET",
                f"leads/{lead['id']}/history",
                200
            )
        
        return success

    def test_tasks(self):
        """Test task operations"""
        # List tasks
        success, tasks = self.run_test(
            "List Tasks",
            "GET",
            "tasks",
            200
        )
        if not success:
            return False

        # Test my tasks
        success, my_tasks = self.run_test(
            "My Tasks",
            "GET",
            "tasks/my",
            200
        )
        if not success:
            return False

        # Create task
        task_data = {
            "title": f"Test Task {datetime.now().strftime('%H%M%S')}",
            "description": "This is a test task created by automated testing",
            "deadline": "2024-12-25T10:00:00Z"
        }
        success, task = self.run_test(
            "Create Task",
            "POST",
            "tasks",
            200,
            data=task_data
        )
        if success and 'id' in task:
            self.created_entities['tasks'].append(task['id'])
            print(f"   Created task: {task['title']} (ID: {task['id']})")
            
            # Update task status
            update_data = {
                "status": "in_progress"
            }
            success, _ = self.run_test(
                "Update Task Status",
                "PUT",
                f"tasks/{task['id']}",
                200,
                data=update_data
            )
        
        return success

    def test_users(self):
        """Test user operations with role-based access"""
        # List users - should work for ALL authenticated users now
        success, users = self.run_test(
            "List Users",
            "GET",
            "users",
            200
        )
        if not success:
            return False
        
        print(f"   Found {len(users)} users")

        # Get roles
        success, roles = self.run_test(
            "Get Roles",
            "GET",
            "users/roles",
            200
        )
        if not success:
            return False

        # Create user (only CEO/HR should be able to do this)
        user_data = {
            "email": f"test{datetime.now().strftime('%H%M%S')}@servall.com",
            "password": "TestPassword123!",
            "name": f"Test User {datetime.now().strftime('%H%M%S')}",
            "role": "HR Executive",
            "department": "HR"
        }
        success, user = self.run_test(
            "Create User (CEO)",
            "POST",
            "users",
            200,
            data=user_data
        )
        if success and 'id' in user:
            self.created_entities['users'].append(user['id'])
            print(f"   Created user: {user['name']} (ID: {user['id']})")
        
        return success

    def test_ai_endpoints(self):
        """Test AI-related endpoints"""
        # Test AI search
        success, _ = self.run_test(
            "AI Search",
            "GET",
            "ai/search?query=technician&location=mumbai",
            200
        )
        if not success:
            return False

        # Test top rated candidates
        success, _ = self.run_test(
            "Top Rated Candidates",
            "GET",
            "ai/top-rated",
            200
        )
        
        return success

    def test_employees(self):
        """Test employee operations"""
        # List employees
        success, employees = self.run_test(
            "List Employees",
            "GET",
            "employees",
            200
        )
        return success

    def test_chat_role_access(self):
        """Test role-based access to chat endpoints"""
        print("\n🔐 Testing Chat Role-Based Access Control...")
        
        # Test with different user roles
        test_users = [
            {"email": "admin@servall.com", "password": "ServallAdmin@123", "role": "CEO", "should_have_access": True},
            {"email": "designer@servall.com", "password": "Servall@123", "role": "Graphic Designer", "should_have_access": True},
            {"email": "hr.exec@servall.com", "password": "Servall@123", "role": "HR Executive", "should_have_access": False},
            {"email": "srhr@servall.com", "password": "Servall@123", "role": "Sr HR", "should_have_access": True}
        ]
        
        all_passed = True
        for user_info in test_users:
            # Login as this user
            success, response = self.run_test(
                f"Login as {user_info['role']}",
                "POST",
                "auth/login",
                200,
                data={"email": user_info["email"], "password": user_info["password"]}
            )
            
            if not success:
                print(f"❌ Failed to login as {user_info['role']}")
                all_passed = False
                continue
                
            # Set token for this user
            old_token = self.token
            self.token = response.get('access_token')
            
            # Test chat access
            success, chat_response = self.run_test(
                f"Chat Access for {user_info['role']}",
                "GET",
                "chat",
                200 if user_info['should_have_access'] else 403
            )
            
            if user_info['should_have_access'] and not success:
                print(f"❌ {user_info['role']} should have chat access but was denied")
                all_passed = False
            elif not user_info['should_have_access'] and success:
                print(f"✅ {user_info['role']} access control working correctly (correctly denied)")
            elif user_info['should_have_access'] and success:
                print(f"✅ {user_info['role']} access control working correctly (correctly allowed)")
            else:
                print(f"❌ {user_info['role']} access control failed - unexpected result")
                all_passed = False
            
            # Restore original token
            self.token = old_token
            
        return all_passed

    def test_chat_operations(self):
        """Test chat CRUD operations"""
        print("\n💬 Testing Chat Operations...")
        
        # Ensure we're logged in as CEO for full access
        if not self.test_login():
            return False
            
        # Test eligible users endpoint
        success, eligible_users = self.run_test(
            "Get Eligible Users",
            "GET",
            "chat/eligible-users",
            200
        )
        if not success or not eligible_users:
            print("❌ Failed to get eligible users")
            return False
            
        print(f"   Found {len(eligible_users)} eligible users")
        
        # Test list chats (should be empty initially or show existing)
        success, chats = self.run_test(
            "List Chats",
            "GET",
            "chat",
            200
        )
        if not success:
            return False
            
        print(f"   Found {len(chats)} existing chats")
        
        # Create a direct chat with first eligible user
        if eligible_users:
            target_user = eligible_users[0]
            chat_data = {
                "user_ids": [target_user["id"]]
            }
            success, chat = self.run_test(
                "Create Direct Chat",
                "POST",
                "chat",
                200,
                data=chat_data
            )
            if success and 'id' in chat:
                self.created_entities['chats'].append(chat['id'])
                print(f"   Created direct chat: {chat['id']}")
                
                # Test get chat details
                success, chat_detail = self.run_test(
                    "Get Chat Details",
                    "GET",
                    f"chat/{chat['id']}",
                    200
                )
                if not success:
                    return False
                    
                # Test get messages
                success, messages = self.run_test(
                    "Get Chat Messages",
                    "GET",
                    f"chat/{chat['id']}/messages",
                    200
                )
                if not success:
                    return False
                    
                print(f"   Chat has {len(messages)} messages")
                
                # Test send message
                message_data = {
                    "text": f"Test message from automated testing at {datetime.now().isoformat()}"
                }
                success, message = self.run_test(
                    "Send Message",
                    "POST",
                    f"chat/{chat['id']}/messages",
                    200,
                    data=message_data
                )
                if not success:
                    return False
                    
                message_id = message.get('id')
                print(f"   Sent message: {message_id}")
                
                # Test edit message (within 15 minutes)
                edit_data = {
                    "text": "Edited test message"
                }
                success, edited_msg = self.run_test(
                    "Edit Message",
                    "PUT",
                    f"chat/{chat['id']}/messages/{message_id}",
                    200,
                    data=edit_data
                )
                if success:
                    print("   ✅ Message editing works")
                
                # Test delete message
                success, _ = self.run_test(
                    "Delete Message",
                    "DELETE",
                    f"chat/{chat['id']}/messages/{message_id}",
                    200
                )
                if success:
                    print("   ✅ Message deletion works")
                    
        # Create group chat with multiple users
        if len(eligible_users) >= 2:
            group_data = {
                "user_ids": [u["id"] for u in eligible_users[:2]],
                "name": f"Test Group {datetime.now().strftime('%H%M%S')}"
            }
            success, group_chat = self.run_test(
                "Create Group Chat",
                "POST",
                "chat",
                200,
                data=group_data
            )
            if success and 'id' in group_chat:
                self.created_entities['chats'].append(group_chat['id'])
                print(f"   Created group chat: {group_chat['id']}")
                
                # Test add member with view_only permission
                if len(eligible_users) >= 3:
                    add_member_data = {
                        "user_id": eligible_users[2]["id"],
                        "permission": "view_only",
                        "show_history": False
                    }
                    success, _ = self.run_test(
                        "Add Member (View Only)",
                        "POST",
                        f"chat/{group_chat['id']}/members",
                        200,
                        data=add_member_data
                    )
                    if success:
                        print("   ✅ Member addition works")
                        
                        # Test update member permission
                        permission_data = {
                            "permission": "can_reply"
                        }
                        success, _ = self.run_test(
                            "Update Member Permission",
                            "PUT",
                            f"chat/{group_chat['id']}/members/{eligible_users[2]['id']}",
                            200,
                            data=permission_data
                        )
                        if success:
                            print("   ✅ Permission update works")
                            
        return True

    def test_chat_monitoring(self):
        """Test CEO monitoring capabilities"""
        print("\n👁️ Testing CEO Monitoring...")
        
        # Ensure we're logged in as CEO
        if not self.test_login():
            return False
            
        # Test monitor endpoint (CEO only)
        success, monitor_data = self.run_test(
            "CEO Monitor Chats",
            "GET",
            "chat/monitor",
            200
        )
        if success:
            print(f"   CEO can monitor {len(monitor_data)} chats")
            
        # Test with non-CEO user (should fail)
        # Login as designer
        success, response = self.run_test(
            "Login as Designer",
            "POST",
            "auth/login",
            200,
            data={"email": "designer@servall.com", "password": "Servall@123"}
        )
        if success:
            old_token = self.token
            self.token = response.get('access_token')
            
            # Try to access monitor endpoint (should fail)
            success, _ = self.run_test(
                "Designer Monitor Access (Should Fail)",
                "GET",
                "chat/monitor",
                403
            )
            if success:
                print("   ✅ Non-CEO users correctly blocked from monitoring")
            else:
                print("   ❌ Non-CEO user was able to access monitoring")
                
            # Restore CEO token
            self.token = old_token
            
        return True

    def test_chat_polling(self):
        """Test chat polling functionality"""
        print("\n🔄 Testing Chat Polling...")
        
        # Test polling endpoint
        since_time = datetime.now().isoformat()
        success, poll_data = self.run_test(
            "Chat Polling",
            "GET",
            f"chat/poll?since={since_time}",
            200
        )
        if success:
            messages = poll_data.get('messages', [])
            print(f"   Polling returned {len(messages)} new messages")
            
        return success

    def test_notifications(self):
        """Test notification system"""
        # Test unread count
        success, response = self.run_test(
            "Get Unread Notifications Count",
            "GET",
            "notifications/unread-count",
            200
        )
        if success:
            count = response.get('count', 0)
            print(f"   Unread notifications: {count}")
        
        # Test get all notifications
        success, notifications = self.run_test(
            "Get All Notifications",
            "GET",
            "notifications",
            200
        )
        if success:
            print(f"   Total notifications: {len(notifications)}")
            
        return success

    def test_role_based_dashboard_access(self):
        """Test dashboard access for different user roles"""
        print("\n🔐 Testing Role-Based Dashboard Access...")
        
        test_users = [
            {"email": "admin@servall.com", "password": "ServallAdmin@123", "role": "CEO", "expected_type": "ceo"},
            {"email": "hr@servall.com", "password": "Servall@123", "role": "HR", "expected_type": "hr"},
            {"email": "marketing.mgr@servall.com", "password": "Servall@123", "role": "Marketing Manager", "expected_type": "manager"},
            {"email": "srhr@servall.com", "password": "Servall@123", "role": "Sr HR", "expected_type": "sr_jr_hr"},
            {"email": "franchise.exec@servall.com", "password": "Servall@123", "role": "Franchise Executive", "expected_type": "fde"},
            {"email": "designer@servall.com", "password": "Servall@123", "role": "Graphic Designer", "expected_type": "designer"},
            {"email": "marketing.coord@servall.com", "password": "Servall@123", "role": "Marketing Coordinator", "expected_type": "mktg_coord"}
        ]
        
        all_passed = True
        original_token = self.token
        
        for user_info in test_users:
            # Login as this user
            success, response = self.run_test(
                f"Login as {user_info['role']}",
                "POST",
                "auth/login",
                200,
                data={"email": user_info["email"], "password": user_info["password"]}
            )
            
            if not success:
                print(f"❌ Failed to login as {user_info['role']}")
                all_passed = False
                continue
                
            # Set token for this user
            self.token = response.get('access_token')
            
            # Test dashboard access
            success, dashboard_response = self.run_test(
                f"Dashboard Access for {user_info['role']}",
                "GET",
                "dashboard/stats",
                200
            )
            
            if success:
                actual_type = dashboard_response.get('type', 'unknown')
                if actual_type == user_info['expected_type']:
                    print(f"✅ {user_info['role']} dashboard type correct: {actual_type}")
                    
                    # Test specific dashboard features based on role
                    if actual_type == 'ceo':
                        self.verify_ceo_dashboard_features(dashboard_response)
                    elif actual_type == 'hr':
                        self.verify_hr_dashboard_features(dashboard_response)
                    elif actual_type == 'manager':
                        self.verify_manager_dashboard_features(dashboard_response)
                    elif actual_type == 'sr_jr_hr':
                        self.verify_sr_jr_hr_dashboard_features(dashboard_response)
                    elif actual_type == 'fde':
                        self.verify_fde_dashboard_features(dashboard_response)
                    elif actual_type == 'designer':
                        self.verify_designer_dashboard_features(dashboard_response)
                    elif actual_type == 'mktg_coord':
                        self.verify_mktg_coord_dashboard_features(dashboard_response)
                        
                else:
                    print(f"❌ {user_info['role']} dashboard type mismatch: expected {user_info['expected_type']}, got {actual_type}")
                    all_passed = False
            else:
                print(f"❌ {user_info['role']} failed to access dashboard")
                all_passed = False
                
            # Test notifications access
            success, notif_response = self.run_test(
                f"Notifications Access for {user_info['role']}",
                "GET",
                "notifications/unread-count",
                200
            )
            
            if success:
                print(f"✅ {user_info['role']} can access notifications")
            else:
                print(f"❌ {user_info['role']} cannot access notifications")
                all_passed = False
                
            # Test users list access (should work for all roles now)
            success, users_response = self.run_test(
                f"Users List Access for {user_info['role']}",
                "GET",
                "users",
                200
            )
            
            if success:
                print(f"✅ {user_info['role']} can access users list")
            else:
                print(f"❌ {user_info['role']} cannot access users list")
                all_passed = False
        
        # Restore original token
        self.token = original_token
        return all_passed

    def verify_ceo_dashboard_features(self, response):
        """Verify CEO dashboard specific features"""
        print("      🔍 Verifying CEO dashboard features...")
        
        # Check for split tabs structure
        tech_hiring = response.get('technician_hiring', {})
        ho_hiring = response.get('ho_hiring', {})
        call_tracking = response.get('call_tracking', [])
        overdue_jobs = response.get('overdue_jobs', [])
        
        if tech_hiring:
            print(f"      ✅ Technician hiring tab present")
        else:
            print(f"      ❌ Missing technician hiring tab")
            
        if ho_hiring:
            print(f"      ✅ HO hiring tab present")
        else:
            print(f"      ❌ Missing HO hiring tab")
            
        if call_tracking:
            print(f"      ✅ Call tracking present ({len(call_tracking)} executives)")
        else:
            print(f"      ❌ Missing call tracking")
            
        if overdue_jobs:
            print(f"      ✅ Overdue alerts present ({len(overdue_jobs)} jobs)")
        else:
            print(f"      ℹ️ No overdue jobs (expected)")

    def verify_hr_dashboard_features(self, response):
        """Verify HR dashboard specific features"""
        print("      🔍 Verifying HR dashboard features...")
        
        pending_posts = response.get('pending_posts', 0)
        pending_reviews = response.get('pending_reviews', 0)
        overall_pipeline = response.get('overall_pipeline', {})
        
        print(f"      ✅ Pending posts: {pending_posts}")
        print(f"      ✅ Pending reviews: {pending_reviews}")
        
        if overall_pipeline:
            print(f"      ✅ Overall pipeline present")
        else:
            print(f"      ❌ Missing overall pipeline")

    def verify_manager_dashboard_features(self, response):
        """Verify Manager dashboard specific features"""
        print("      🔍 Verifying Manager dashboard features...")
        
        jobs = response.get('jobs', [])
        alerts = response.get('alerts', [])
        ownership = response.get('ownership', {})
        lead_insights = response.get('lead_insights', {})
        
        print(f"      ✅ Jobs created: {len(jobs)}")
        print(f"      ✅ Alerts: {len(alerts)}")
        print(f"      ✅ Lead ownership tracking: {len(ownership)} handlers")
        
        if lead_insights:
            print(f"      ✅ Lead insights present")
        else:
            print(f"      ❌ Missing lead insights")

    def verify_sr_jr_hr_dashboard_features(self, response):
        """Verify Sr/Jr HR dashboard specific features"""
        print("      🔍 Verifying Sr/Jr HR dashboard features...")
        
        my_leads = response.get('my_leads', [])
        my_pipeline = response.get('my_pipeline', {})
        leads_by_source = response.get('leads_by_source', {})
        my_post_requests = response.get('my_post_requests', [])
        
        print(f"      ✅ Assigned leads: {len(my_leads)}")
        print(f"      ✅ Post requests: {len(my_post_requests)}")
        
        if my_pipeline:
            print(f"      ✅ Pipeline by source present")
        else:
            print(f"      ❌ Missing pipeline by source")

    def verify_fde_dashboard_features(self, response):
        """Verify Franchise Executive dashboard specific features"""
        print("      🔍 Verifying FDE dashboard features...")
        
        jobs = response.get('jobs', [])
        my_leads = response.get('my_leads', [])
        calls_today = response.get('calls_today', 0)
        
        print(f"      ✅ Technician leads: {len(my_leads)}")
        print(f"      ✅ Branch jobs: {len(jobs)}")
        print(f"      ✅ Calls today: {calls_today}")

    def verify_designer_dashboard_features(self, response):
        """Verify Graphic Designer dashboard specific features"""
        print("      🔍 Verifying Designer dashboard features...")
        
        pending_requests = response.get('pending_requests', [])
        my_posts = response.get('my_posts', [])
        total_pending = response.get('total_pending', 0)
        total_completed = response.get('total_completed', 0)
        
        print(f"      ✅ Pending requests: {total_pending}")
        print(f"      ✅ Completed uploads: {total_completed}")

    def verify_mktg_coord_dashboard_features(self, response):
        """Verify Marketing Coordinator dashboard specific features"""
        print("      🔍 Verifying Marketing Coordinator dashboard features...")
        
        campaigns = response.get('campaigns', [])
        pending_count = response.get('pending_count', 0)
        running_count = response.get('running_count', 0)
        completed_count = response.get('completed_count', 0)
        
        print(f"      ✅ Campaigns: {len(campaigns)} total")
        print(f"      ✅ Pending: {pending_count}, Running: {running_count}, Completed: {completed_count}")

    def test_post_panel_api(self):
        """Test Post Panel API endpoints"""
        print("\n🎨 Testing Post Panel API...")
        
        # Test as HR user first
        success, response = self.run_test(
            "Login as HR",
            "POST",
            "auth/login",
            200,
            data={"email": "hr@servall.com", "password": "Servall@123"}
        )
        
        if not success:
            return False
            
        original_token = self.token
        self.token = response.get('access_token')
        
        # Test get post requests
        success, requests = self.run_test(
            "Get Post Requests",
            "GET",
            "posts/requests",
            200
        )
        if success:
            print(f"   Found {len(requests)} post requests")
        
        # Test get posts
        success, posts = self.run_test(
            "Get Posts",
            "GET",
            "posts",
            200
        )
        if success:
            print(f"   Found {len(posts)} posts")
        
        # Test as Designer
        success, response = self.run_test(
            "Login as Designer",
            "POST",
            "auth/login",
            200,
            data={"email": "designer@servall.com", "password": "Servall@123"}
        )
        
        if success:
            self.token = response.get('access_token')
            
            # Test designer access to requests
            success, designer_requests = self.run_test(
                "Designer Get Post Requests",
                "GET",
                "posts/requests",
                200
            )
            if success:
                print(f"   Designer can see {len(designer_requests)} requests")
        
        # Restore original token
        self.token = original_token
        return True

    def test_campaigns_api(self):
        """Test Campaigns API endpoints"""
        print("\n📢 Testing Campaigns API...")
        
        # Test as Marketing Coordinator
        success, response = self.run_test(
            "Login as Marketing Coordinator",
            "POST",
            "auth/login",
            200,
            data={"email": "marketing.coord@servall.com", "password": "Servall@123"}
        )
        
        if not success:
            return False
            
        original_token = self.token
        self.token = response.get('access_token')
        
        # Test get campaigns
        success, campaigns = self.run_test(
            "Get Campaigns",
            "GET",
            "campaigns",
            200
        )
        if success:
            print(f"   Found {len(campaigns)} campaigns")
            
            # Test update campaign status if campaigns exist
            if campaigns:
                campaign_id = campaigns[0]['id']
                success, updated_campaign = self.run_test(
                    "Update Campaign Status",
                    "PUT",
                    f"campaigns/{campaign_id}",
                    200,
                    data={"status": "running"}
                )
                if success:
                    print(f"   ✅ Campaign status updated")
        
        # Restore original token
        self.token = original_token
        return True

    def test_meetings_api(self):
        """Test Meetings API endpoints"""
        print("\n🎥 Testing Meetings API...")
        
        # Test create meeting
        success, meeting = self.run_test(
            "Create Meeting",
            "POST",
            "meetings/create",
            200
        )
        if success:
            meeting_url = meeting.get('meeting_url', '')
            if 'jitsi' in meeting_url.lower():
                print(f"   ✅ Jitsi meeting created: {meeting_url}")
            else:
                print(f"   ❌ Invalid meeting URL: {meeting_url}")
        
        # Test recent meetings
        success, recent = self.run_test(
            "Get Recent Meetings",
            "GET",
            "meetings/recent",
            200
        )
        if success:
            print(f"   Found {len(recent)} recent meetings")
        
        return success

    def test_chat_all_roles(self):
        """Test chat access for ALL roles as specified"""
        print("\n💬 Testing Chat Access for ALL Roles...")
        
        test_users = [
            {"email": "admin@servall.com", "password": "ServallAdmin@123", "role": "CEO"},
            {"email": "hr@servall.com", "password": "Servall@123", "role": "HR"},
            {"email": "marketing.mgr@servall.com", "password": "Servall@123", "role": "Marketing Manager"},
            {"email": "srhr@servall.com", "password": "Servall@123", "role": "Sr HR"},
            {"email": "franchise.exec@servall.com", "password": "Servall@123", "role": "Franchise Executive"},
            {"email": "designer@servall.com", "password": "Servall@123", "role": "Graphic Designer"},
            {"email": "marketing.coord@servall.com", "password": "Servall@123", "role": "Marketing Coordinator"}
        ]
        
        original_token = self.token
        all_passed = True
        
        for user_info in test_users:
            # Login as this user
            success, response = self.run_test(
                f"Login as {user_info['role']}",
                "POST",
                "auth/login",
                200,
                data={"email": user_info["email"], "password": user_info["password"]}
            )
            
            if not success:
                print(f"❌ Failed to login as {user_info['role']}")
                all_passed = False
                continue
                
            # Set token for this user
            self.token = response.get('access_token')
            
            # Test chat access - ALL roles should have access now
            success, chat_response = self.run_test(
                f"Chat Access for {user_info['role']}",
                "GET",
                "chat",
                200
            )
            
            if success:
                print(f"✅ {user_info['role']} has chat access")
            else:
                print(f"❌ {user_info['role']} denied chat access")
                all_passed = False
        
        # Restore original token
        self.token = original_token
        return all_passed

    def test_user_management_restrictions(self):
        """Test user management restrictions for different roles"""
        print("\n🔒 Testing User Management Restrictions...")
        
        # Test with HR Executive (should NOT be able to create users)
        success, response = self.run_test(
            "Login as HR Executive",
            "POST",
            "auth/login",
            200,
            data={"email": "hr.exec@servall.com", "password": "Servall@123"}
        )
        
        if not success:
            return False
            
        original_token = self.token
        self.token = response.get('access_token')
        
        # Try to create user (should fail)
        user_data = {
            "email": f"restricted_test{datetime.now().strftime('%H%M%S')}@servall.com",
            "password": "TestPassword123!",
            "name": "Restricted Test User",
            "role": "HR Executive",
            "department": "HR"
        }
        success, _ = self.run_test(
            "Create User as HR Executive (Should Fail)",
            "POST",
            "users",
            403,  # Should be forbidden
            data=user_data
        )
        
        if success:
            print("✅ HR Executive correctly blocked from creating users")
        else:
            print("❌ HR Executive was able to create users (should be blocked)")
            
        # Test with Marketing Manager (should NOT be able to create users)
        success, response = self.run_test(
            "Login as Marketing Manager",
            "POST",
            "auth/login",
            200,
            data={"email": "marketing.mgr@servall.com", "password": "Servall@123"}
        )
        
        if success:
            self.token = response.get('access_token')
            
            success, _ = self.run_test(
                "Create User as Marketing Manager (Should Fail)",
                "POST",
                "users",
                403,  # Should be forbidden
                data=user_data
            )
            
            if success:
                print("✅ Marketing Manager correctly blocked from creating users")
            else:
                print("❌ Marketing Manager was able to create users (should be blocked)")
        
        # Restore original token
        self.token = original_token
        return True

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Servall API Testing...")
        print(f"Base URL: {self.base_url}")
        
        # Test authentication first
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False

        # Test auth endpoints
        self.test_auth_me()
        
        # Test dashboard with new structure
        self.test_dashboard_stats()
        
        # Test notifications system
        self.test_notifications()
        
        # Test role-based access for all 7 roles
        self.test_role_based_dashboard_access()
        
        # Test user management restrictions
        self.test_user_management_restrictions()
        
        # Test new features
        print("\n" + "="*50)
        print("🆕 TESTING NEW FEATURES")
        print("="*50)
        self.test_post_panel_api()
        self.test_campaigns_api()
        self.test_meetings_api()
        self.test_chat_all_roles()
        
        # Test all modules
        self.test_branches()
        self.test_jobs()
        self.test_leads()
        self.test_tasks()
        self.test_users()
        self.test_ai_endpoints()
        self.test_employees()
        
        # Test chat functionality
        print("\n" + "="*50)
        print("🗨️  TESTING CHAT SYSTEM")
        print("="*50)
        self.test_chat_role_access()
        self.test_chat_operations()
        self.test_chat_monitoring()
        self.test_chat_polling()
        
        # Print final results
        print(f"\n📊 Test Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.created_entities['jobs']:
            print(f"\n📝 Created entities for further testing:")
            for entity_type, ids in self.created_entities.items():
                if ids:
                    print(f"   {entity_type}: {ids}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = ServallAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())