"""Seed script to populate Servall Hiring OS with dummy data"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import bcrypt
import os
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]


def hash_pw(pw):
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def uid():
    return str(uuid.uuid4())


def now_iso(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


async def seed():
    print("Clearing old data (except admin)...")
    admin = await db.users.find_one({"email": "admin@servall.com"})
    
    # Clear collections
    for col in ['branches', 'jobs', 'leads', 'lead_stage_logs', 'call_logs', 'tasks', 'employees', 'candidate_ratings', 'notifications']:
        await db[col].delete_many({})
    # Remove non-admin users
    await db.users.delete_many({"email": {"$ne": "admin@servall.com"}})

    print("Creating users...")
    password = "Servall@123"
    pw_hash = hash_pw(password)
    admin_id = admin["id"] if admin else uid()

    users = [
        {"id": uid(), "email": "srhr@servall.com", "password_hash": pw_hash, "name": "Rajesh Kumar", "role": "Sr HR", "department": "HR", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(55)},
        {"id": uid(), "email": "jrhr@servall.com", "password_hash": pw_hash, "name": "Anjali Verma", "role": "Jr HR", "department": "HR", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(50)},
        {"id": uid(), "email": "marketing.mgr@servall.com", "password_hash": pw_hash, "name": "Vikram Singh", "role": "Marketing Manager", "department": "Marketing", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(45)},
        {"id": uid(), "email": "ops.mgr@servall.com", "password_hash": pw_hash, "name": "Suresh Patil", "role": "Operations Manager", "department": "Operations", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(45)},
        {"id": uid(), "email": "sales.mgr@servall.com", "password_hash": pw_hash, "name": "Meena Iyer", "role": "Sales Manager", "department": "Sales", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(40)},
        {"id": uid(), "email": "accounts.mgr@servall.com", "password_hash": pw_hash, "name": "Ramesh Gupta", "role": "Accounts Manager", "department": "Accounts", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(38)},
        {"id": uid(), "email": "marketing.coord@servall.com", "password_hash": pw_hash, "name": "Arjun Mehta", "role": "Marketing Coordinator", "department": "Marketing", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(30)},
        {"id": uid(), "email": "designer@servall.com", "password_hash": pw_hash, "name": "Sneha Joshi", "role": "Graphic Designer", "department": "Marketing", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(30)},
        {"id": uid(), "email": "franchise.exec@servall.com", "password_hash": pw_hash, "name": "Arun Yadav", "role": "Franchise Executive", "department": "Franchise Development", "branch_id": None, "created_by": admin_id, "is_active": True, "created_at": now_iso(25)},
    ]
    if users:
        await db.users.insert_many(users)
    
    all_users = await db.users.find({}, {"_id": 0}).to_list(100)
    user_map = {u["role"]: u for u in all_users}
    hr_exec = user_map.get("HR Executive", all_users[0])
    designer = user_map.get("Graphic Designer", all_users[0])
    mktg_coord = user_map.get("Marketing Coordinator", all_users[0])
    sr_hr = user_map.get("Sr HR", all_users[0])
    jr_hr = user_map.get("Jr HR", all_users[0])

    print("Creating branches...")
    branches = [
        {"id": uid(), "name": "Servall Koramangala", "city": "Bangalore", "area": "Koramangala", "latitude": 12.9352, "longitude": 77.6245, "tentative_opening_date": "2025-12-01", "actual_opening_date": "2025-12-15", "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(90)},
        {"id": uid(), "name": "Servall Indiranagar", "city": "Bangalore", "area": "Indiranagar", "latitude": 12.9784, "longitude": 77.6408, "tentative_opening_date": "2026-01-15", "actual_opening_date": "2026-01-20", "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(80)},
        {"id": uid(), "name": "Servall Whitefield", "city": "Bangalore", "area": "Whitefield", "latitude": 12.9698, "longitude": 77.7500, "tentative_opening_date": "2026-02-01", "actual_opening_date": "2026-02-10", "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(70)},
        {"id": uid(), "name": "Servall Anna Nagar", "city": "Chennai", "area": "Anna Nagar", "latitude": 13.0850, "longitude": 80.2101, "tentative_opening_date": "2026-03-01", "actual_opening_date": "2026-03-05", "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(50)},
        {"id": uid(), "name": "Servall T. Nagar", "city": "Chennai", "area": "T. Nagar", "latitude": 13.0418, "longitude": 80.2341, "tentative_opening_date": "2026-03-15", "actual_opening_date": None, "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(40)},
        {"id": uid(), "name": "Servall Banjara Hills", "city": "Hyderabad", "area": "Banjara Hills", "latitude": 17.4156, "longitude": 78.4347, "tentative_opening_date": "2026-04-01", "actual_opening_date": None, "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(20)},
        {"id": uid(), "name": "Servall Kothrud", "city": "Pune", "area": "Kothrud", "latitude": 18.5074, "longitude": 73.8077, "tentative_opening_date": "2026-05-01", "actual_opening_date": None, "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(10)},
        {"id": uid(), "name": "Servall Andheri", "city": "Mumbai", "area": "Andheri West", "latitude": 19.1361, "longitude": 72.8366, "tentative_opening_date": "2026-06-01", "actual_opening_date": None, "franchise_owner_id": None, "created_by": admin_id, "created_at": now_iso(5)},
    ]
    await db.branches.insert_many(branches)
    branch_ids = [b["id"] for b in branches]

    print("Creating jobs...")
    jobs = [
        {"id": uid(), "role": "Technician", "type": "branch", "branch_id": branch_ids[0], "location": "Bangalore, Koramangala", "salary_range_min": 15000, "salary_range_max": 25000, "status": "open", "description": "Experienced two-wheeler technician needed", "created_by": admin_id, "created_at": now_iso(30)},
        {"id": uid(), "role": "Technician", "type": "branch", "branch_id": branch_ids[1], "location": "Bangalore, Indiranagar", "salary_range_min": 15000, "salary_range_max": 28000, "status": "open", "description": "Two-wheeler mechanic with 2+ years experience", "created_by": admin_id, "created_at": now_iso(28)},
        {"id": uid(), "role": "Service Advisor", "type": "branch", "branch_id": branch_ids[0], "location": "Bangalore, Koramangala", "salary_range_min": 20000, "salary_range_max": 35000, "status": "open", "description": "Customer-facing service advisor", "created_by": admin_id, "created_at": now_iso(25)},
        {"id": uid(), "role": "Branch Manager", "type": "branch", "branch_id": branch_ids[3], "location": "Chennai, Anna Nagar", "salary_range_min": 40000, "salary_range_max": 60000, "status": "open", "description": "Branch manager for Chennai operations", "created_by": admin_id, "created_at": now_iso(20)},
        {"id": uid(), "role": "Technician", "type": "branch", "branch_id": branch_ids[2], "location": "Bangalore, Whitefield", "salary_range_min": 16000, "salary_range_max": 26000, "status": "open", "description": "Skilled mechanic for Whitefield branch", "created_by": admin_id, "created_at": now_iso(15)},
        {"id": uid(), "role": "Technician", "type": "branch", "branch_id": branch_ids[5], "location": "Hyderabad, Banjara Hills", "salary_range_min": 14000, "salary_range_max": 24000, "status": "open", "description": "Two-wheeler technician for new Hyderabad branch", "created_by": admin_id, "created_at": now_iso(10)},
        {"id": uid(), "role": "Marketing Coordinator", "type": "HO", "branch_id": None, "location": "Bangalore, Head Office", "salary_range_min": 25000, "salary_range_max": 40000, "status": "open", "description": "Digital marketing coordinator for HQ", "created_by": admin_id, "created_at": now_iso(12)},
        {"id": uid(), "role": "HR Executive", "type": "HO", "branch_id": None, "location": "Bangalore, Head Office", "salary_range_min": 22000, "salary_range_max": 35000, "status": "closed", "description": "HR executive for recruitment operations", "created_by": admin_id, "created_at": now_iso(45)},
        {"id": uid(), "role": "Service Advisor", "type": "branch", "branch_id": branch_ids[4], "location": "Chennai, T. Nagar", "salary_range_min": 18000, "salary_range_max": 30000, "status": "on_hold", "description": "Service advisor for upcoming T. Nagar branch", "created_by": admin_id, "created_at": now_iso(8)},
        {"id": uid(), "role": "Technician", "type": "branch", "branch_id": branch_ids[6], "location": "Pune, Kothrud", "salary_range_min": 15000, "salary_range_max": 25000, "status": "open", "description": "Mechanic for Pune branch opening", "created_by": admin_id, "created_at": now_iso(5)},
    ]
    await db.jobs.insert_many(jobs)
    job_ids = [j["id"] for j in jobs]

    print("Creating auto-tasks for jobs...")
    tasks = []
    for job in jobs[:6]:  # Auto tasks for first 6 jobs
        tasks.extend([
            {"id": uid(), "title": f"Create job creatives for {job['role']} at {job['location']}", "description": f"Auto-created for job", "assigned_to": designer["id"], "assigned_to_name": designer["name"], "job_id": job["id"], "deadline": now_iso(-3), "status": random.choice(["completed", "completed", "in_progress"]), "auto_created": True, "created_by": admin_id, "created_at": job["created_at"]},
            {"id": uid(), "title": f"Post job ads for {job['role']} at {job['location']}", "description": f"Auto-created for job", "assigned_to": mktg_coord["id"], "assigned_to_name": mktg_coord["name"], "job_id": job["id"], "deadline": now_iso(-3), "status": random.choice(["completed", "in_progress", "pending"]), "auto_created": True, "created_by": admin_id, "created_at": job["created_at"]},
            {"id": uid(), "title": f"Post job listing for {job['role']} at {job['location']}", "description": f"Auto-created for job", "assigned_to": hr_exec["id"], "assigned_to_name": hr_exec["name"], "job_id": job["id"], "deadline": now_iso(-3), "status": random.choice(["completed", "completed", "pending"]), "auto_created": True, "created_by": admin_id, "created_at": job["created_at"]},
        ])
    # Manual tasks
    tasks.extend([
        {"id": uid(), "title": "Review franchise agreement for Pune", "description": "Legal review needed", "assigned_to": user_map.get("Franchise Development Manager", all_users[0])["id"], "assigned_to_name": "Deepak Reddy", "job_id": None, "deadline": now_iso(-5), "status": "in_progress", "auto_created": False, "created_by": admin_id, "created_at": now_iso(7)},
        {"id": uid(), "title": "Prepare Q2 hiring report", "description": "Quarterly hiring metrics", "assigned_to": sr_hr["id"], "assigned_to_name": sr_hr["name"], "job_id": None, "deadline": now_iso(-2), "status": "pending", "auto_created": False, "created_by": admin_id, "created_at": now_iso(3)},
        {"id": uid(), "title": "Update job descriptions for technician roles", "description": "Standardize JDs across branches", "assigned_to": jr_hr["id"], "assigned_to_name": jr_hr["name"], "job_id": None, "deadline": now_iso(-7), "status": "completed", "auto_created": False, "created_by": admin_id, "created_at": now_iso(14)},
    ])
    await db.tasks.insert_many(tasks)

    print("Creating leads...")
    lead_names = [
        ("Ravi Shankar", "9876543210", "Bangalore", "Koramangala", True),
        ("Mohammed Irfan", "9876543211", "Bangalore", "Indiranagar", True),
        ("Sunil Kumar", "9876543212", "Bangalore", "Whitefield", True),
        ("Venkatesh R", "9876543213", "Chennai", "Anna Nagar", True),
        ("Ganesh Patil", "9876543214", "Pune", "Kothrud", True),
        ("Ajay Yadav", "9876543215", "Hyderabad", "Banjara Hills", True),
        ("Manoj Tiwari", "9876543216", "Bangalore", "Electronic City", True),
        ("Karthik S", "9876543217", "Chennai", "T. Nagar", True),
        ("Prakash Shetty", "9876543218", "Bangalore", "Jayanagar", True),
        ("Dinesh Verma", "9876543219", "Mumbai", "Andheri", True),
        ("Sanjay Gupta", "9876543220", "Bangalore", "HSR Layout", True),
        ("Ramesh B", "9876543221", "Bangalore", "Koramangala", True),
        ("Ashok Reddy", "9876543222", "Hyderabad", "Madhapur", True),
        ("Vijay Kumar", "9876543223", "Chennai", "Velachery", True),
        ("Naveen M", "9876543224", "Bangalore", "Marathahalli", True),
        # Non-technician leads
        ("Priyanka Das", "9876543225", "Bangalore", "Koramangala", False),
        ("Anita Sharma", "9876543226", "Bangalore", "Head Office", False),
        ("Rohit Saxena", "9876543227", "Chennai", "Anna Nagar", False),
        ("Deepa Nair", "9876543228", "Pune", "Kothrud", False),
        ("Siddharth Jain", "9876543229", "Mumbai", "Andheri", False),
    ]

    sources = ["manual", "job_portal", "meta_ads"]
    assignees = [hr_exec, jr_hr, sr_hr]
    leads = []

    for i, (name, phone, city, area, is_tech) in enumerate(lead_names):
        lead_id = uid()
        assignee = random.choice(assignees)
        leads.append({
            "id": lead_id,
            "name": name,
            "phone": phone,
            "email": f"{name.lower().replace(' ', '.')}@gmail.com",
            "location_city": city,
            "location_area": area,
            "source": random.choice(sources),
            "assigned_to": assignee["id"],
            "current_stage": "new_lead",  # Will update below
            "is_technician": is_tech,
            "job_id": random.choice(job_ids[:6]) if is_tech else random.choice(job_ids[6:8]),
            "total_calls": random.randint(0, 5),
            "last_call_date": now_iso(random.randint(0, 10)) if random.random() > 0.3 else None,
            "created_by": assignee["id"],
            "created_at": now_iso(random.randint(2, 25)),
            "updated_at": now_iso(random.randint(0, 5)),
        })

    await db.leads.insert_many(leads)

    # Now move leads through stages with proper logs
    print("Moving leads through pipeline stages...")

    # Lead 0-2: Interview Cleared (full journey)
    for idx in range(3):
        lead = leads[idx]
        lid = lead["id"]
        changer = random.choice(assignees)
        exp = random.randint(2, 8)

        # New -> Qualified
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": None, "to_stage": "new_lead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {}, "timestamp": now_iso(20)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "new_lead", "to_stage": "qualified", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"experience": str(exp), "location_confirmation": True, "salary_expectation": str(random.randint(15000, 30000)), "relocation_preference": "yes"}, "timestamp": now_iso(18)})
        # Qualified -> Awaiting Interview
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "qualified", "to_stage": "awaiting_interview", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"interview_date": "2026-04-05", "mode": "in_person", "interviewer": "Rajesh Kumar"}, "timestamp": now_iso(15)})
        # Awaiting -> Cleared
        score = random.randint(7, 10)
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "awaiting_interview", "to_stage": "interview_cleared", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"interview_score": str(score)}, "timestamp": now_iso(12)})
        await db.leads.update_one({"id": lid}, {"$set": {"current_stage": "interview_cleared"}})

        # Create candidate rating
        exp_score = min(exp / 2, 5)
        sel_score = 3.5
        final = round((score / 2 + exp_score + sel_score) / 3, 2)
        await db.candidate_ratings.insert_one({
            "id": uid(), "lead_id": lid, "lead_name": lead["name"],
            "interview_score": score, "experience_score": round(exp_score, 2),
            "selection_score": sel_score, "final_rating": final,
            "experience_years": exp, "skills": random.sample(["Engine Repair", "Electrical", "Bodywork", "Painting", "Diagnostics", "Suspension", "Brakes", "Transmission"], 3),
            "location_city": lead["location_city"], "location_area": lead["location_area"],
            "created_at": now_iso(12), "updated_at": now_iso(5)
        })

    # Lead 3-5: Awaiting Interview
    for idx in range(3, 6):
        lead = leads[idx]
        lid = lead["id"]
        changer = random.choice(assignees)
        exp = random.randint(1, 6)
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": None, "to_stage": "new_lead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {}, "timestamp": now_iso(15)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "new_lead", "to_stage": "qualified", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"experience": str(exp), "location_confirmation": True, "salary_expectation": str(random.randint(14000, 25000)), "relocation_preference": random.choice(["yes", "no", "maybe"])}, "timestamp": now_iso(12)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "qualified", "to_stage": "awaiting_interview", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"interview_date": "2026-04-15", "mode": random.choice(["in_person", "video", "phone"]), "interviewer": sr_hr["name"]}, "timestamp": now_iso(8)})
        await db.leads.update_one({"id": lid}, {"$set": {"current_stage": "awaiting_interview"}})

    # Lead 6-8: Qualified
    for idx in range(6, 9):
        lead = leads[idx]
        lid = lead["id"]
        changer = random.choice(assignees)
        exp = random.randint(1, 5)
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": None, "to_stage": "new_lead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {}, "timestamp": now_iso(10)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "new_lead", "to_stage": "qualified", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"experience": str(exp), "location_confirmation": True, "salary_expectation": str(random.randint(15000, 22000)), "relocation_preference": "yes"}, "timestamp": now_iso(7)})
        await db.leads.update_one({"id": lid}, {"$set": {"current_stage": "qualified"}})

    # Lead 9-12: New Lead (stay as is)

    # Lead 13-14: Nurture
    for idx in range(13, 15):
        lead = leads[idx]
        lid = lead["id"]
        changer = random.choice(assignees)
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": None, "to_stage": "new_lead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {}, "timestamp": now_iso(14)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "new_lead", "to_stage": "nurture", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"nurture_notes": random.choice(["Candidate interested but needs time", "Currently employed, follow up next month", "Salary expectations high, nurturing"])}, "timestamp": now_iso(10)})
        await db.leads.update_one({"id": lid}, {"$set": {"current_stage": "nurture"}})

    # Lead 15-16: Dead
    for idx in range(15, 17):
        lead = leads[idx]
        lid = lead["id"]
        changer = random.choice(assignees)
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": None, "to_stage": "new_lead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {}, "timestamp": now_iso(12)})
        await db.lead_stage_logs.insert_one({"id": uid(), "lead_id": lid, "from_stage": "new_lead", "to_stage": "dead", "changed_by": changer["id"], "changed_by_name": changer["name"], "form_data": {"dead_reason": random.choice(["not_interested", "salary_mismatch", "location_issue", "hired_elsewhere"])}, "timestamp": now_iso(9)})
        await db.leads.update_one({"id": lid}, {"$set": {"current_stage": "dead"}})

    # Lead 17-19: stay new_lead (non-tech)

    print("Adding call logs...")
    call_logs = []
    for lead in leads[:12]:
        num_calls = random.randint(1, 4)
        for c in range(num_calls):
            call_logs.append({
                "id": uid(), "lead_id": lead["id"],
                "called_by": random.choice(assignees)["id"],
                "called_by_name": random.choice(assignees)["name"],
                "notes": random.choice([
                    "Candidate picked up, discussed role and salary",
                    "No answer, will try again tomorrow",
                    "Candidate confirmed interest, shared job details",
                    "Discussed location and shift timings",
                    "Candidate asked for higher salary, explained benefits",
                    "Scheduled interview for next week",
                    "Follow-up call, candidate still interested",
                ]),
                "call_date": now_iso(random.randint(0, 15)),
                "created_at": now_iso(random.randint(0, 15)),
            })
    if call_logs:
        await db.call_logs.insert_many(call_logs)

    print("Converting top leads to employees...")
    employees = []
    for idx in range(2):  # First 2 cleared leads become employees
        lead = leads[idx]
        employees.append({
            "id": uid(), "lead_id": lead["id"],
            "name": lead["name"], "phone": lead["phone"], "email": lead["email"],
            "joining_date": "2026-04-01" if idx == 0 else "2026-04-08",
            "role": "Technician", "branch_id": branch_ids[idx],
            "department": "Service",
            "created_by": admin_id, "created_at": now_iso(5 + idx * 3),
        })
    await db.employees.insert_many(employees)

    # Add more candidate ratings for technicians in qualified/awaiting stages
    for idx in range(3, 9):
        lead = leads[idx]
        if lead["is_technician"]:
            exp = random.randint(1, 6)
            score = random.randint(5, 8)
            exp_score = min(exp / 2, 5)
            sel = 3.0
            final = round((score / 2 + exp_score + sel) / 3, 2)
            await db.candidate_ratings.insert_one({
                "id": uid(), "lead_id": lead["id"], "lead_name": lead["name"],
                "interview_score": score, "experience_score": round(exp_score, 2),
                "selection_score": sel, "final_rating": final,
                "experience_years": exp,
                "skills": random.sample(["Engine Repair", "Electrical", "Bodywork", "Painting", "Diagnostics", "Suspension", "Brakes"], 2),
                "location_city": lead["location_city"], "location_area": lead["location_area"],
                "created_at": now_iso(8), "updated_at": now_iso(3)
            })

    print("\n" + "="*60)
    print("SEED COMPLETE!")
    print("="*60)
    
    # Print summary
    u_count = await db.users.count_documents({})
    b_count = await db.branches.count_documents({})
    j_count = await db.jobs.count_documents({})
    l_count = await db.leads.count_documents({})
    t_count = await db.tasks.count_documents({})
    e_count = await db.employees.count_documents({})
    r_count = await db.candidate_ratings.count_documents({})
    c_count = await db.call_logs.count_documents({})
    
    print(f"\nUsers: {u_count}")
    print(f"Branches: {b_count}")
    print(f"Jobs: {j_count}")
    print(f"Leads: {l_count}")
    print(f"Tasks: {t_count}")
    print(f"Employees: {e_count}")
    print(f"Candidate Ratings: {r_count}")
    print(f"Call Logs: {c_count}")
    print()

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
