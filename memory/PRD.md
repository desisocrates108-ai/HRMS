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

## Backlog (P1/P2)
- WebSocket real-time chat/notifications
- Excel/PDF analytics exports
- Call recording + AI sentiment
- Scheduled job to auto-create notifications when three_months_due_date passes (currently surfaced on dashboard count, but no push notification)
- WhatsApp template approval reminder banner for CEO/HR
