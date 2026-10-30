# Stage 11 — Production Deployment & Containerization

## 1. Executive Summary

Stage 11 establishes the complete production deployment infrastructure, containerization pipeline, and operational guides for Nexus Social across Render, Vercel, Brevo, and Google Gemini:
1. **Multi-Stage Production Dockerfile (`backend/Dockerfile`)**: Hardened Python 3.12-slim container with non-root security isolation (`appuser:1001`), multi-stage dependency extraction, native PostgreSQL client support, container health checks, and dynamic port binding.
2. **Container Entrypoint (`backend/scripts/entrypoint.sh`)**: Multi-mode entrypoint orchestrating database migrations (`alembic upgrade head`), production server execution (`uvicorn`), database seeding (`seed --demo`), and ad-hoc maintenance jobs.
3. **Render Infrastructure as Code (`render.yaml`)**: Declarative blueprint provisioning a Managed PostgreSQL database instance (`nexus-social-db`), Docker web service (`nexus-social-backend`), automatic pre-deploy database migrations, Brevo SMTP relay parameters, and Gemini AI credentials.
4. **Vercel Edge Configuration (`frontend/vercel.json`)**: Configured Next.js 14 deployment specification with automated first-party API rewrites to eliminate cross-site cookie blocking and maintain direct SSE streaming.
5. **Production Deployment Runbook (`docs/DEPLOYMENT.md`)**: Comprehensive operations guide covering Render setup, Vercel integration, Brevo SMTP onboarding, database seeding with Student USNs, smoke test checklists, and cold-start mitigations.

---

## 2. Key Architecture & Deliverables

### 2.1 Multi-Stage Dockerfile (`backend/Dockerfile`)
- **Stage 1 (Builder)**:
  - Base: `python:3.12-slim`.
  - Installs `build-essential`, `libpq-dev`, and compiles Python wheels to `/install` directory.
- **Stage 2 (Runtime)**:
  - Base: `python:3.12-slim`.
  - Copies `/install` packages to `/usr/local` without build toolchains.
  - Creates dedicated unprivileged group and user: `groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -m appuser`.
  - Sets `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `ENVIRONMENT=production`.
  - Includes Docker `HEALTHCHECK` probing `http://localhost:8000/health`.
  - Configured with `ENTRYPOINT ["/app/scripts/entrypoint.sh"]`.

### 2.2 Entrypoint Controller (`backend/scripts/entrypoint.sh`)
Supports standard container lifecycles:
- **Default startup**: Automatically executes `alembic upgrade head` before booting Uvicorn on `${PORT:-8000}`.
- **`migrate`**: Runs migrations and exits cleanly.
- **`seed`**: Runs `python scripts/seed.py "$@"`, enabling one-click database initialization (e.g. `seed --demo`).
- **Pass-through**: Executes arbitrary shell commands for interactive debugging.

### 2.3 Render Infrastructure Blueprint (`render.yaml`)
- **Database**:
  - `name: nexus-social-db`
  - Plan: `free`
  - Region: `oregon`
- **Web Service**:
  - `name: nexus-social-backend`
  - Runtime: `docker`
  - Pre-Deploy: `alembic upgrade head`
  - Automatic `DATABASE_URL` binding using internal connection strings.
  - Integrated Brevo SMTP relay settings (`SMTP_HOST: smtp-relay.brevo.com`, `SMTP_PORT: 587`, `SMTP_USE_TLS: true`).
  - Google Gemini 2.5 Flash API credentials.

### 2.4 Vercel Platform Integration (`frontend/vercel.json` & `next.config.mjs`)
- **API Rewrites**:
  - Requests matching `/api/:path*` are rewritten to `${BACKEND_URL}/api/:path*`.
  - Refresh tokens remain strictly first-party `httpOnly` cookies on the Vercel domain, preventing Safari ITP and Chrome third-party cookie restrictions.
- **Direct Real-Time SSE**:
  - Browser notifications connect directly to `NEXT_PUBLIC_BACKEND_URL/api/v1/notifications/stream` using short-lived stream tokens, bypassing Edge buffering.

### 2.5 University Student Seed Data (`backend/scripts/seed.py`)
- Provides demo student accounts with realistic university seat numbers:
  - `1MS21CS001` (@aarav_sharma)
  - `1RV20EC045` (@priya_patel)
  - `1BMS22IS089` (@rohan_verma)
  - `1PES21ME032` (@ananya_iyer)
- Enables immediate testing of USN login, forgot-password lookup, profile badges, and admin user directory post-deployment.

---

## 3. Verification & Quality Gates

### 3.1 Verification Summary
- **Backend Test Suite**: 50/50 pytest tests passing (`pytest backend/tests`).
- **Frontend Type Safety**: `npx tsc --noEmit` passed with 0 errors.
- **Frontend Code Quality**: `npm run lint` passed with 0 warnings/errors.
- **Frontend Production Build**: `npm run build` compiled 17 routes and middleware successfully.
- **Container Specification**: Dockerfile multi-stage syntax and entrypoint permissions verified.

---

## 4. Requirements Traceability

| Requirement ID | Description | Status | Evidence |
| :--- | :--- | :---: | :--- |
| **DEPLOY-01** | Backend Dockerfile (multi-stage, non-root) | ✅ Done | `backend/Dockerfile`, non-root user `appuser:1001`, healthcheck |
| **DEPLOY-02** | render.yaml blueprint | ✅ Done | `render.yaml` with DB + Web Service + Pre-deploy migrations + Brevo SMTP |
| **DEPLOY-03** | Vercel config + rewrites | ✅ Done | `frontend/vercel.json`, `next.config.mjs` API rewrites |
| **DEPLOY-04** | DEPLOYMENT.md step-by-step | ✅ Done | `docs/DEPLOYMENT.md` comprehensive production deployment guide |
