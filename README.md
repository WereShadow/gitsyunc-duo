# GitSync Duo 🔗🔥

> **A collaborative project execution and accountability platform designed around: PLAN → ASSIGN → WORK → SUBMIT → VERIFY → REVIEW → COMPLETE.**
>
> *"Don't just track whether someone says they worked. Track the work, make it visible, allow teammates to verify it, and show the team what remains to be done."*

No manual checkboxes. No self-reporting. Objective GitHub activity verification + mandatory peer review before any task is completed.

---

## Table of Contents

- [What is GitSync Duo?](#what-is-gitsync-duo)
- [Core Rule](#core-rule)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Demo Accounts](#demo-accounts)
- [API Reference](#api-reference)
- [Project Modes](#project-modes)
- [How Completion Works](#how-completion-works)
- [Peer Review Workflow](#peer-review-workflow)
- [GitHub Webhook Integration](#github-webhook-integration)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Architecture](#architecture)

---

## What is GitSync Duo?

GitSync Duo pairs two developers together in a **duo** and holds them accountable every single day. Each duo has a daily task — and that task is only marked **COMPLETE** when **both** members have pushed qualifying commits to GitHub before the daily deadline.

Miss a day? Your streak resets to zero. Both deliver? Your streak grows. Simple, ruthless, effective.

---

## Core Rule

`
dailyTask.status = "COMPLETED"
  only when:
    userA.github_verified === true
    AND
    userB.github_verified === true
`

- ❌ You **cannot** manually mark a day complete
- ❌ One person completing their requirement is **not enough**
- ✅ Only the backend `CompletionEngine` can set status to `COMPLETED`
- ✅ If one person satisfies and the other doesn't → status stays `WAITING`
- ✅ If neither satisfies before deadline → status becomes `MISSED` and streak resets

---

## Features

### 🧑‍🤝‍🧑 Duo System
- Create a duo with a unique invite code
- Maximum 2 members per duo
- Configurable daily deadline, timezone, and grace period
- Two project modes: **Separate** and **Shared**

### ✅ Daily Task Tracking
- Automatic daily task creation
- Real-time status: `ACTIVE` → `WAITING` → `COMPLETED` / `MISSED`
- GitHub activity verified automatically — no manual input

### 🐙 GitHub Integration
- Connect via Personal Access Token (PAT)
- Verify commits on specific repos and branches
- Simulate pushes in dev mode without a real GitHub account
- Webhook support for real-time push event processing (HMAC-verified)

### 🔍 Peer Code Review (Shared Mode)
- Submit your task for partner review
- Partner reviews with `APPROVED` or `CHANGES_REQUESTED`
- Self-review is blocked server-side (403)
- Outside-duo reviews are blocked server-side (403)
- Full review audit log with commit details and CI check status

### 🔥 Streaks and Statistics
- Current streak, longest streak, completion rate
- 60-day contribution heatmap calendar
- Per-member GitHub activity breakdown

### 🔔 Notifications
- Deadline warning (2 hours before cutoff)
- Streak milestone alerts
- Partner activity updates

### 📊 Dashboard
- Live progress indicators for both duo members
- Confetti animation on task completion 🎉
- Quick demo user switcher (Alex ↔ Morgan)
- Real-time polling every 30 seconds

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide React |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| **Database** | SQLite (dev) / PostgreSQL via asyncpg (prod) |
| **Auth** | JWT (HS256), bcrypt password hashing |
| **GitHub** | REST API v3, HMAC-SHA256 webhook verification |
| **Crypto** | Fernet symmetric encryption for stored PATs |
| **Testing** | pytest, pytest-asyncio, aiosqlite in-memory |

---

## Project Structure

`
gitsyunc-duo/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                  # Auth dependencies
│   │   │   └── routes/
│   │   │       ├── auth.py              # Register, login, /me
│   │   │       ├── duos.py              # Create/join/update duo
│   │   │       ├── tasks.py             # Daily tasks CRUD
│   │   │       ├── reviews.py           # Peer review submission
│   │   │       ├── github.py            # GitHub connect, verify, simulate
│   │   │       ├── progress.py          # Today's progress, calendar
│   │   │       ├── streaks.py           # Streak data
│   │   │       ├── notifications.py     # Notification management
│   │   │       ├── webhooks.py          # GitHub push webhook handler
│   │   │       └── projects.py          # Project/repo config
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic settings
│   │   │   └── security.py             # JWT, bcrypt, Fernet, HMAC
│   │   ├── models/
│   │   │   ├── database.py             # Async engine, session, init_db
│   │   │   └── entities.py             # All SQLAlchemy ORM models
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── completion_engine.py    # THE authority on task completion
│   │   │   ├── github_service.py       # GitHub API client with retry/backoff
│   │   │   ├── review_service.py       # Peer review enforcement
│   │   │   ├── scheduler.py            # Background deadline worker
│   │   │   ├── seed_service.py         # Dev seed data
│   │   │   ├── simulation_store.py     # In-memory commit simulator
│   │   │   └── verification_service.py # CI check verification
│   │   └── main.py                     # FastAPI app, CORS, lifespan
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_completion_logic.py    # 5 completion scenario tests
│   │   └── test_webhooks_and_security.py # 3 security tests
│   ├── .env.example
│   ├── pytest.ini
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── common/
    │   │   │   ├── NotificationDropdown.tsx
    │   │   │   └── SimulatePushModal.tsx
    │   │   ├── layout/
    │   │   │   ├── Navbar.tsx
    │   │   │   ├── Sidebar.tsx
    │   │   │   └── MobileNav.tsx
    │   │   └── reviews/
    │   │       └── PeerReviewModal.tsx
    │   ├── context/
    │   │   └── AuthContext.tsx
    │   ├── pages/
    │   │   ├── LandingPage.tsx
    │   │   ├── LoginPage.tsx / RegisterPage.tsx
    │   │   ├── OnboardingPage.tsx
    │   │   ├── CreateDuoPage.tsx / JoinDuoPage.tsx
    │   │   ├── DashboardPage.tsx
    │   │   ├── TodaysTaskPage.tsx
    │   │   ├── GitHubActivityPage.tsx
    │   │   ├── CalendarPage.tsx
    │   │   ├── HistoryPage.tsx
    │   │   ├── StatisticsPage.tsx
    │   │   └── SettingsPage.tsx
    │   ├── services/api.ts
    │   ├── types/index.ts
    │   ├── App.tsx
    │   └── main.tsx
    ├── tailwind.config.js
    ├── vite.config.ts
    └── package.json
`

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend Setup

`ash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
`

### Frontend Setup

`ash
cd frontend
npm install
`

### Running the App

**Terminal 1 — Backend (port 8000):**
`ash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
`

**Terminal 2 — Frontend (port 5173):**
`ash
cd frontend
npm run dev
`

Open **http://localhost:5173**

The backend auto-seeds demo data on first startup. No manual database setup needed.

---

## Demo Accounts

| User | Email | Password |
|------|-------|----------|
| **Alex Rivera** | `alex@gitsync.dev` | `password123` |
| **Morgan Chen** | `morgan@gitsync.dev` | `password123` |

Both users have a **14-day active streak** seeded automatically. Use the ⇄ switcher in the navbar to toggle between them instantly.

---

## API Reference

Interactive Swagger docs at **http://localhost:8000/docs**

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, receive JWT |
| GET | `/api/auth/me` | Get current user |

### Duos
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/duos/` | Create a duo |
| POST | `/api/duos/join` | Join via invite code |
| GET | `/api/duos/current` | Get your current duo |
| PUT | `/api/duos/{id}/settings` | Update duo settings |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/today` | Get today's task |
| GET | `/api/tasks/history` | Task history |
| POST | `/api/tasks/{id}/submit` | Submit for peer review |
| POST | `/api/tasks/{id}/verify-project` | Trigger CI verification |

### GitHub
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/github/connect-token` | Connect GitHub PAT |
| GET | `/api/github/status` | Check connection status |
| GET | `/api/github/activity` | Fetch commit activity |
| POST | `/api/github/verify` | Run verification now |
| POST | `/api/github/simulate-push` | Simulate a commit (dev) |

### Progress and Streaks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/progress/today` | Today's duo progress |
| GET | `/api/progress/history` | 60-day calendar data |
| GET | `/api/streaks` | Current streak stats |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhooks/github` | GitHub push webhook (HMAC-verified) |

---

## Project Modes

### ⚡ Separate Mode (default)
Each member works on their own repository. Day completes when both push.

`
day_complete = userA.github_verified AND userB.github_verified
`

### 🤝 Shared Mode
Both members work on the same repository. Day completes when:

`
day_complete =
  userA.github_verified
  AND userB.github_verified
  AND userA.review_status == APPROVED
  AND userB.review_status == APPROVED
  AND project_verification.status == PASSED
`

---

## How Completion Works

`CompletionEngine` in `backend/app/services/completion_engine.py` is the **only** authority that sets `status = "COMPLETED"`. It is called:

1. When GitHub activity is verified (webhook or manual trigger)
2. By the background scheduler every 60 seconds as a fallback
3. After a peer review is submitted (Shared mode)

`
Task Status Flow:

ACTIVE
  ↓ one member verifies
WAITING_FOR_USER_A  or  WAITING_FOR_USER_B
  ↓ both verify (+ review approved in Shared mode)
COMPLETED ✅  →  streak + 1
  OR
MISSED ❌  →  streak resets to 0  (after deadline passes)
`

---

## Peer Review Workflow

Used in **Shared Mode** only:

1. **User A** commits and submits their task for review
2. **User B** gets a notification and opens the review modal
3. User B sees: commit list, changed files, CI check results
4. User B selects `APPROVED` or `CHANGES_REQUESTED` + comment
5. `CHANGES_REQUESTED` → User A revises and re-submits
6. `APPROVED` → CompletionEngine re-evaluates

**Server-side enforcement (cannot be bypassed):**
- Self-review → `403 Forbidden`
- Review by someone outside the duo → `403 Forbidden`

---

## GitHub Webhook Integration

1. GitHub repo → **Settings → Webhooks → Add webhook**
2. Payload URL: `https://your-domain.com/api/webhooks/github`
3. Content type: `application/json`
4. Secret: match your `GITHUB_WEBHOOK_SECRET` in `.env`
5. Events: **Just the push event**

Webhooks are HMAC-SHA256 verified and idempotent (duplicate deliveries ignored via `X-GitHub-Delivery` tracking).

---

## Environment Variables

`env
# Security
SECRET_KEY=your-32-char-secret-for-jwt
FERNET_KEY=your-fernet-key-for-pat-encryption

# Database
DATABASE_URL=sqlite+aiosqlite:///./gitsync.db
# PostgreSQL: postgresql+asyncpg://user:pass@localhost/gitsync

# GitHub
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# CORS
ALLOWED_ORIGINS=http://localhost:5173
`

**Generate a Fernet key:**
`ash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
`

---

## Running Tests

`ash
cd backend
python -m pytest -v
`

| Test | What it verifies |
|------|-----------------|
| `test_completion_separate_projects` | Both verify → COMPLETED; one → WAITING |
| `test_shared_project_mode_and_peer_reviews` | Self-review 403, changes_requested flow, approval → COMPLETED |
| `test_deadline_expiration_and_streak_reset` | Expired deadline → MISSED, streak → 0 |
| `test_wrong_repository_or_branch_ignored` | Wrong repo/branch commits ignored |
| `test_outside_user_cannot_review` | Non-duo user review → 403 |
| `test_github_webhook_signature_verification` | Valid HMAC passes; invalid → 401 |
| `test_duo_max_two_members_rule` | Third join → 400 |
| `test_webhook_idempotency` | Duplicate delivery safely ignored |

All 8 tests pass. ✅

---

## Architecture

`
Browser (React + TypeScript + Tailwind)
  Landing / Login / Dashboard / Task / GitHub / Calendar / Settings
          │
          │ HTTPS + JWT Bearer
          ▼
FastAPI Backend
  /api/auth  /api/duos  /api/tasks  /api/github
  /api/progress  /api/reviews  /api/webhooks
          │
          │  ┌────────────────────────────────┐
          │  │  CompletionEngine  ← THE LAW   │
          │  │  Only setter of "COMPLETED"    │
          │  └────────────────────────────────┘
          │
          │  BackgroundScheduler (every 60s)
          │  → check deadlines → MISSED → streak reset
          │
          │ SQLAlchemy async
          ▼
SQLite (dev) / PostgreSQL (prod)
  users · duos · duo_members · daily_tasks
  daily_user_progress · task_reviews · streaks
  github_accounts · notifications · webhook_events
          ▲
          │ HMAC-verified push webhooks
GitHub.com
`

---

## License

MIT — build something great together.
