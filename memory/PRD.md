# Servall Hiring OS - PRD (Updated May 1, 2026)

## Architecture
- Backend: FastAPI, Frontend: React + Shadcn UI, DB: MongoDB, AI: GPT-5.2, Auth: JWT Bearer
- WhatsApp: 11za API (real httpx dispatch, fire-and-forget)
- Public feedback: tokenized single-use links (no auth needed)

## Role Hierarchy
- SUPER (full access): CEO, HR
- MANAGER: Marketing/Operations/Sales/Accounts Manager
- EXECUTOR: Sr HR, Jr HR, Marketing Coordinator, Graphic Designer, Franchise Executive

## Pipeline Model (renamed May 2026)
### Head Office
`new_lead → qualified → hr_interview → manager_interview → selected → joined`
Parallel states: `hold` (resumable), `rejected` (terminal, triggers WhatsApp feedback).

### Technician / Branch (shown as "Franchise" in dashboards)
`new_lead → qualified → hr_interview → selected → joined`
Parallel states: `hold`, `rejected`.

Legacy aliases: `move_ahead` → `selected`, `dead` → `rejected` (backward compat preserved).

### Interview Questionnaires
- HR Round (10 criteria), Manager Round (10 criteria, HO only). 1–5 stars + remarks.
- Hard blocks: manager_interview needs HR; selected needs prior round.
- Records lock on `joined`/`rejected`.

## Branch Permission Matrix (May 2026)
- VIEW (GET): All 11 roles
- CREATE/EDIT (POST/PUT): CEO, HR, 4 Managers, Sr HR, Jr HR
- DELETE: CEO, HR, Sr HR, Jr HR ONLY

## Implemented Features

### Phase 1 (Apr 17, 2026)
- Restructured pipelines (HO vs Tech) with hold/dead parallel states
- HR & Manager questionnaire forms with 10-criterion star ratings
- Backend hard blocks on stage transitions
- Employee DB segmentation (branch/head_office × tech/mid/mgmt)
- Employee exit endpoint (CEO/HR only)

### Phase 2 (Apr 27, 2026)
- **Real WhatsApp 11za dispatch** — fire-and-forget httpx POST with template + URL substitution
- **Public tokenized feedback forms** — single-use, no auth
  - Rejection feedback (6 questions): clarity, experience, respect, response time, would-reapply, suggestion
  - Exit feedback (9 questions): reasons, satisfaction, manager support, growth, compensation fairness, would-recommend, improvements, best memory
- Auto-trigger on Dead/Exit → token created → WhatsApp sent
- **CEO-only feedback viewer** — `/feedback-submissions` page with rejection/exit tabs, detail dialog
- 410 response for already-submitted forms

### P1 (Apr 27, 2026)
- **Analytics endpoint** `/api/analytics/summary` — funnel, conversion %, hold/dead reasons, sources, avg interview scores, avg time-to-hire
- **Resume upload** on lead detail (PDF/DOC/DOCX/JPG/PNG, 10MB limit)
- **Medical info** on lead detail (blood group, allergies, emergency contacts)
- **Analytics page** with funnel chart, KPIs, leaderboard, weak stage detector

### P2 (Apr 27, 2026)
- **System Intelligence** `/api/analytics/intelligence` — best HR interviewer (≥3 interviews, ranked by hit rate), weak stage detector (drop-off %), auto-generated insights

### Franchise Recruitment (Apr 27, 2026)
- Branch `status` derived: `upcoming` (no actual_opening_date) vs `active`
- `/api/branches/recruitment-overview` — per-franchise: open_jobs, total_jobs, active_leads, hired
- `/franchises` page with Upcoming/Active tabs and stat tiles per franchise

### Core HRMS (legacy)
- Auth, Branch/Job/Lead CRUD, Task automation, AI recommendations
- 8 unique role dashboards (CEO, HR, Manager, Sr/Jr HR, FDE, Designer, Marketing Coord, Generic)
- Post Panel, Campaigns, Meetings (Jitsi), Internal Chat, Notifications, Audit Logs

## Backlog

### P1
- WebSocket real-time chat/notifications (currently polled)
- Excel/PDF reports for analytics

### P2
- Call recording + AI sentiment
- Talent heatmaps (location-based candidate density)
- Gamification (HR leaderboard with points)
