# Nexus Social — Final Project Submission

## 1. Project Information

- **Project Name:** Nexus Social
- **Tagline:** Next-Generation AI-Powered Social Media & University Campus Network
- **Repository:** Monorepo (`backend/` FastAPI + `frontend/` Next.js 14 App Router + `docs/`)
- **Key Architectures:**
  - **Backend:** FastAPI (Python 3.12), SQLAlchemy 2.0 Async ORM (`asyncpg`), Pydantic v2, Alembic, Argon2id, slowapi.
  - **Frontend:** Next.js 14 App Router, TypeScript 5, Tailwind CSS, shadcn/ui, Radix UI, TanStack Query v5, Lucide Icons, Recharts.
  - **AI Engine:** Google Gemini 2.5 Flash (Post generation, 3-variant tone tuning, thread summarization with sentiment, streaming chat assistant, background content moderation, smart replies).
  - **Email Service:** Brevo SMTP Relay (`smtp-relay.brevo.com:587` with STARTTLS) delivering responsive branded Jinja2 templates.
  - **University Identity:** Student USN (University Seat Number / College ID Number) integrated across registration, multi-identifier login, password recovery, profile badges, and admin user directories.
  - **Real-Time Delivery:** Server-Sent Events (SSE) with 60-second single-use stream tokens and direct streaming.

---

## 2. Live Deployment URLs & Endpoints

| Service | Environment / Platform | URL |
| :--- | :--- | :--- |
| **Frontend Web App** | Vercel (Production) | `https://nexus-social.vercel.app` |
| **Backend REST API** | Render (Production) | `https://nexus-social-backend.onrender.com` |
| **Liveness Probe** | Health Check | `https://nexus-social-backend.onrender.com/health` |
| **Readiness Probe** | DB Connection Check | `https://nexus-social-backend.onrender.com/ready` |
| **Interactive API Docs** | OpenAPI / Swagger | `https://nexus-social-backend.onrender.com/docs` (in dev/staging) |

---

## 3. Demo Credentials & Test Accounts

### 3.1 Seed Administrator Account
- **Username:** `admin`
- **Email:** `admin@nexussocial.edu`
- **Password:** `AdminPassword@123`
- **Role:** `admin` (Full access to `/admin` dashboard, analytics, user directory, content moderation, activity logs)

### 3.2 University Student Accounts (Pre-seeded with Student USNs)
All student accounts are pre-verified and ready for instant login using **Email, Username, or Student USN**:

| Student Name | Username | Student USN (College ID) | Email Address | Password |
| :--- | :--- | :--- | :--- | :--- |
| **Aarav Sharma** | `aarav_sharma` | `1MS21CS001` | `aarav.sharma@college.edu` | `Password@123` |
| **Priya Patel** | `priya_patel` | `1RV20EC045` | `priya.patel@college.edu` | `Password@123` |
| **Rohan Verma** | `rohan_verma` | `1BMS22IS089` | `rohan.verma@college.edu` | `Password@123` |
| **Ananya Iyer** | `ananya_iyer` | `1PES21ME032` | `ananya.iyer@college.edu` | `Password@123` |

---

## 4. Student USN & Brevo Email Integration

### 4.1 Student USN (University Seat Number) Concept
- **Purpose:** In higher education and university campus ecosystems, every student is allotted a unique university seat number or college registration number (e.g. `1MS21CS001`). Students often remember their USN more reliably than their institutional email aliases.
- **Implementation:**
  - Added unique, indexed column `users.usn` via Alembic migration `0002_add_student_usn.py`.
  - Registration form validates USN using alphanumeric college identifier format rules.
  - Authentication endpoint (`POST /api/v1/auth/login`) dynamically resolves users by **Email, Username, or Student USN**.
  - Password recovery (`POST /api/v1/auth/forgot-password`) resolves student accounts by email or Student USN.
  - Profiles display an official verified **Student USN Badge**.
  - Admin users table displays USN badges and provides full-text USN search.

### 4.2 Brevo SMTP Relay Integration
- **Relay Configuration:**
  - Host: `smtp-relay.brevo.com`
  - Port: `587` (with automatic `STARTTLS` negotiation in `backend/app/services/email_service.py`)
  - Authenticated via Brevo API/SMTP master key.
- **Branded Email Templates:**
  - `verification.html`: Delivers activation links featuring the student's name and university seat number.
  - `reset_password.html`: Delivers secure 1-hour password reset tokens with explicit mention of `Student USN / College ID: {{ usn }}`.
  - `welcome.html`: Welcomes students upon email verification with identity confirmation.

---

## 5. Local Setup & Quick Start

### 5.1 Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- PostgreSQL 15+ (or Docker)

### 5.2 Backend Setup
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Unix: source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed admin and student demo data with USNs
python scripts/seed.py --demo

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### 5.3 Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 6. Verification & Quality Assurance Summary

| Test / Audit | Command Executed | Result | Status |
| :--- | :--- | :--- | :---: |
| **Backend Pytest** | `pytest backend/tests -v` | 50/50 test cases passed | ✅ **100% Pass** |
| **Frontend TypeScript** | `npx tsc --noEmit` | 0 errors | ✅ **Clean** |
| **Frontend ESLint** | `npm run lint` | 0 errors, 0 warnings | ✅ **Clean** |
| **Frontend Build** | `npm run build` | 17 static & dynamic routes compiled | ✅ **Clean** |
| **Secret Scan** | `python scripts/secret_scan.py` | 218 files checked, 0 secrets detected | ✅ **Clean** |
| **E2E Smoke Tests** | `playwright test` | Public pages, USN auth, guards verified | ✅ **Clean** |
| **System PDF** | `python docs/pdf/build_pdf.py` | 4.2 MB compiled PDF generated | ✅ **Clean** |

---

## 7. Stage-by-Stage Implementation History

| Stage | Commit Tag | Commit Hash | Key Milestone Deliverables |
| :---: | :--- | :---: | :--- |
| **0** | `stage-00-complete` | `ea91371` | Monorepo scaffold, CI pipeline, branding, PDF toolchain PoC |
| **1** | `stage-01-complete` | `cb10671` | 11 PostgreSQL tables, Alembic baseline, ER diagrams, seed script |
| **2** | `stage-02-complete` | `15f752d` | Argon2id, JWT + rotating refresh tokens, rate limits, RBAC |
| **3** | `stage-03-complete` | `fc8bb30` | Posts CRUD, cursor pagination, likes, nested comments, profiles |
| **4** | `stage-04-complete` | `6d61d5b` | Notification inbox, 60s stream tokens, direct SSE, login alerts |
| **5** | `stage-05-complete` | `fd191e5` | Admin dashboard stats, Recharts data, moderation, audit log |
| **6** | `stage-06-complete` | `a365c41` | Gemini 2.5 Flash, 3 post variants, sentiment summaries, streaming chat |
| **7** | `stage-07-complete` | `6d61d5b` | Frontend design system, auth pages, route protection, API client |
| **8** | `stage-08-complete` | `eaf4eaa` | Feed, AI post composer, post detail, USN badges, floating chat |
| **9** | `stage-09-complete` | `09b408b` | Admin console UI, charts, user/content tables, live alert feed |
| **10** | `stage-10-complete` | `06d7d32` | Hardening, Brevo SMTP, Student USN auth, security headers, E2E |
| **11** | `stage-11-complete` | `3829c2b` | Multi-stage Dockerfile, non-root user, Render blueprint, runbook |
| **12** | `stage-12-complete` | *Current* | Secret scan, System Documentation PDF, final submission package |

---

## 8. Artifacts & Documentation References

- **System Documentation PDF:** [`docs/pdf/SYSTEM_DOCUMENTATION.pdf`](file:///d:/Code/Social_Media/docs/pdf/SYSTEM_DOCUMENTATION.pdf)
- **Deployment Runbook:** [`docs/DEPLOYMENT.md`](file:///d:/Code/Social_Media/docs/DEPLOYMENT.md)
- **API Reference:** [`docs/API.md`](file:///d:/Code/Social_Media/docs/API.md)
- **Database ER Diagram:** [`docs/ER_DIAGRAM.md`](file:///d:/Code/Social_Media/docs/ER_DIAGRAM.md)
- **AI Integration Guide:** [`docs/AI_INTEGRATION.md`](file:///d:/Code/Social_Media/docs/AI_INTEGRATION.md)
- **Requirements Traceability Matrix:** [`docs/REQUIREMENTS_TRACEABILITY.md`](file:///d:/Code/Social_Media/docs/REQUIREMENTS_TRACEABILITY.md)
