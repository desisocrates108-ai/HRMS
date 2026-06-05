# Servall Hiring OS - PRD (Updated Feb 13, 2026)

## Architecture
- Backend: FastAPI, Frontend: React + Shadcn UI, DB: MongoDB, AI: GPT-5.2, Auth: JWT Bearer
- WhatsApp: 11za API (real httpx dispatch, fire-and-forget)
- Public feedback: tokenized single-use links (no auth needed)

## Role Hierarchy
- SUPER (full access): CEO, HR
- MANAGER: Marketing/Operations/Sales/Accounts Manager (+ Franchise Manager allowed for interviews)
- EXECUTOR: Sr HR, Jr HR, Marketing Coordinator, Graphic Designer, Franchise Executive

## Pipeline Model (Feb 2026 restructure — three_months stage added)

### Head Office
`new_lead → qualified → hr_interview → manager_interview → selected → three_months → joined`

### Franchise (Technician)
`new_lead → qualified → hr_interview → selected → three_months → joined`

Parallel states: `hold` (resumable, requires hold_reason), `rejected` (terminal, triggers WhatsApp feedback).

### Stage Transitions
- HR interview → Manager interview requires HR questionnaire submitted + manager_id field.
- Selected requires prior interview round.
- `three_months` auto-saves `three_months_start_date` + `three_months_due_date` (now+90d) AND dispatches WhatsApp Offer Letter + creates `offer_letters` DB record.
- Hold → Selected (or any forward stage) now works (Feb 2026 bug fix).
- Hold pop-up requires mandatory reason.

## Implemented Features

### Feb 2026 — Massive Update (Latest)
- New `three_months` pipeline stage with 90-day notification system
- Offer Letter records auto-generated on three_months transition + WhatsApp dispatch
- Dashboard `lead_split` — HO Total/Today, Franchise Total/Today, 3-Month Due counts
- Dashboard global Date Filter (All/Today/Yesterday/7/30/Month) wired to backend `date_from`, `date_to`, `days`
- Hamburger menu split — Head Office Leads + Franchise Leads (separate pages)
- Hold reason mandatory popup with backend validation
- Hold → Selected transition fix (any forward linear stage from hold's previous)
- Manager assignment at manager_interview stage (`manager_id` required, sets `assigned_manager_id` on lead)
- Manager Round Form role-gated — only Managers + CEO/HR can submit (Sr HR/Jr HR/Coord/Designer = 403)
- Chat → Request Design dialog → creates design_request, notifies all Graphic Designers
- Graphic Designer dashboard panel for chat-origin design requests with status update buttons
- Database menu — HO Employees + Franchise Employees tabs with detail dialog (resume, HR/Mgr reviews, offer letter history, stage history, exit info)
- Task Manager — ALL users can assign tasks to ANY user (no more RBAC blocks)
- CEO Admin Tools panel — Reset/Clear All Business Data (preserves logins + audit logs)
- Removed: Campaigns module (backend route + frontend page deleted), Talent Intel
- Renamed: "Branch Manager" job role → "Franchise Manager"
- Analytics funnel updated to new stage order

### Apr 2026 Phase 2 (preserved)
- Real WhatsApp 11za dispatch (offer_letter, candidate_feedback, employee_exit_feedback templates)
- Public tokenized feedback forms (rejection + exit)
- CEO-only feedback viewer
- Strict interview questionnaires (HR 10 + Manager 10 criteria)
- Branch CRUD with auto-promotion to Active
- Auto-job creation on Employee Exit
- Resume upload + Medical info on lead detail

## Backend API Endpoints (Key)
- `GET /api/dashboard/stats?date_from&date_to&days` — returns `lead_split` block
- `POST /api/leads/{id}/transition` — supports new stage rules
- `POST /api/design-requests` — chat-origin design requests
- `GET /api/offer-letters` + `?lead_id=` filter
- `GET /api/offer-letters/three-months-due` — leads ready for joined conversion
- `POST /api/admin/cleanup` — CEO-only data wipe (preserves users)
- `GET /api/admin/cleanup-preview` — counts before wipe
- `GET/POST/PUT/DELETE /api/designations` — Designation Master CRUD (CEO/HR), blocks delete if referenced
- `POST /api/jobs/{id}/archive` + `POST /api/jobs/{id}/reopen` — close/reopen jobs
- `DELETE /api/jobs/{id}` — Super-only, blocked if leads/employees linked
- `GET /api/employees/pipeline-stats` — stage_counts + summary (HO/Franchise/Total/Joined/Hold/Rejected)
- `POST /api/employees/{id}/transition` — Hold/Rejected require reason
- `GET /api/employees/{id}/history` — stage transition logs
- `GET /api/employees/excel/template` — download import template (.xlsx)
- `GET /api/employees/excel/export` — export filtered employees (.xlsx)
- `POST /api/employees/excel/import` — bulk create from .xlsx (returns created/skipped/errors)
- `DELETE /api/employees/{id}` — Super-only hard delete

## Implemented in Iteration 13 (2026-06-05)
- Designation Master with CRUD + seed of 13 defaults, used by Jobs/Employees dropdowns
- Jobs: Archive, Reopen, Delete (with candidate dependency check)
- Employee Database (originally pipeline, redesigned in Iter 14 → table view)
- Auto-generated EMPxxxx employee codes, manual override allowed (no duplicates)
- Idempotent migration script on startup backfills employee_type/current_stage/status/employee_code
- Excel template / export / import via openpyxl (3.1.5)
- Sidebar "Designations" menu (CEO/HR only)

## Iteration 14 (2026-06-05) — Database Page Redesign
- Removed pipeline view; replaced with CRM-style data table
- 8 filters + global search; eye-icon side drawer with 7 tabs (Basic, Employment, Salary, Stage History, Audit, Documents, Notes)
- Inline stage transitions per row (with Hold/Reject reason dialog)
- Employee notes CRUD endpoints

## Iteration 15 (2026-06-05) — Lead Delete + Candidate Form + Manager Round Fix
- **Lead Soft Delete + Restore + Permanent Delete**
  - POST /api/leads/{id}/delete (CEO/HR/owner)
  - POST /api/leads/{id}/restore (CEO/HR)
  - DELETE /api/leads/{id} (CEO/HR, requires soft-deleted first; blocked if linked employee)
  - GET /api/leads/deleted (CEO/HR)
  - GET /api/leads?include_deleted=true
  - New "Deleted Leads" sidebar (CEO/HR)
- **Candidate Information Form (WhatsApp-shared public form)**
  - POST /api/candidate-forms/{lead_id}/send — generates token, attempts 11za WhatsApp dispatch, falls back to copy link
  - Public GET/POST /api/candidate-forms/form/{token} — schema includes Personal, Education, Employment, Interview, Documents
  - Files (Resume/Aadhaar/PAN/Photo) stored under /app/backend/uploads/candidates/{lead_id}/
  - GET /api/candidate-forms/{lead_id}/document/{field} authenticated download
  - Status badges on lead cards + detail page (Form Not Sent / Sent / Completed)
- **Manager Round Permission Fix**
  - POST /api/interviews/{lead_id}/manager: HR (any role containing 'hr') strictly 403; only assigned_manager_id or CEO override may submit; HR can VIEW only
- 15/15 backend pytest pass; frontend testids verified end-to-end

## Backlog (P1/P2)
- WebSocket real-time chat/notifications
- Excel/PDF analytics exports
- Call recording + AI sentiment
- Scheduled job to auto-create notifications when three_months_due_date passes (currently surfaced on dashboard count, but no push notification)
- WhatsApp template approval reminder banner for CEO/HR
- Designation usage analytics (count of active jobs/employees per designation in DesignationsPage card)
- Bulk stage transition from DatabasePage (multi-select)
- Drag-and-drop kanban view (currently uses Select dropdown for stage moves)
