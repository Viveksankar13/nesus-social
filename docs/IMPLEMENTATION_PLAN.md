# 🌐 Nexus Social — Living Implementation Plan

> **AI-Powered Social Media Platform** · Stage-gated build · Last updated: Stage 0

---

## Platform Overview

**Nexus Social** is a full-stack social media platform powered by Google Gemini AI. Users post content, react, comment, and receive real-time notifications. An AI assistant helps with writing, moderation happens automatically in the background, and admins manage everything from a dedicated analytics console.

**Brand identity:** Warm indigo-violet gradient primary · Rose accent for engagement · Clean Inter typography · Subtle mesh backgrounds for depth.

---

## Stage Progress

| Stage | Name | Status | Commit |
|-------|------|--------|--------|
| **0** | Planning & Scaffold | ✅ **Done** | `stage-00-complete` |
| **1** | Database Layer | 🔲 Not started | — |
| **2** | Authentication Backend | 🔲 Not started | — |
| **3** | Core Social Backend | 🔲 Not started | — |
| **4** | Notifications & Real-time | 🔲 Not started | — |
| **5** | Admin Backend | 🔲 Not started | — |
| **6** | Gemini AI Service | 🔲 Not started | — |
| **7** | Frontend Foundation | 🔲 Not started | — |
| **8** | User App UI | 🔲 Not started | — |
| **9** | Admin Console UI | 🔲 Not started | — |
| **10** | Hardening | 🔲 Not started | — |
| **11** | Deployment | 🔲 Not started | — |
| **12** | Documentation & Submission | 🔲 Not started | — |

---

## Global Assumptions & Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| A1 | **Brand name: Nexus Social** | Evokes interconnection; available; memorable |
| A2 | **Color palette: Indigo (#6366f1) primary + Rose (#f43f5e) accent** | Warm-but-modern; accessible contrast on white and dark backgrounds |
| A3 | **UUID v4 for all PKs** | No sequential ID leakage; globally unique across environments |
| A4 | **In-process pub/sub for SSE (Stage 4)** | Sufficient for single-instance deployment; documented Redis upgrade path |
| A5 | **Render free tier for backend** | Cost-appropriate; document cold-start caveats |
| A6 | **`gemini-2.5-flash` default model** | Balanced speed/quality/cost for social media use-case |
| A7 | **`MODERATION_FAIL_MODE=open`** | Allow content when AI is down; can be changed per deployment |
| A8 | **One-level comment replies only** | Avoids N+1 tree queries; simpler UX for v1 |
| A9 | **Image URLs (no file uploads in v1)** | Avoids storage complexity; noted as future improvement |
| A10 | **`tailwindcss-animate` plugin** | Powers shadcn/ui animations without extra deps |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Gemini API breaking change | Medium | High | Check google-genai changelog before Stage 6; use model-agnostic service interface |
| Render cold starts (~50s) | High | Medium | Document; SSE client has reconnect logic; polling fallback covers it |
| WeasyPrint system lib issues on Windows | High | Low | build_pdf.py has Playwright fallback; documented |
| Render free DB limits (1GB) | Low | Medium | Demo data is capped; documented in DEPLOYMENT.md |
| SSE cross-origin for Vercel→Render | Medium | High | Configured in Stage 4 with CORS + stream tokens |

---

## Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Required | Default | Description |
|----------|---------|---------|-------------|
| `ENVIRONMENT` | No | `development` | `development`, `test`, or `production` |
| `DATABASE_URL` | **Yes** | — | PostgreSQL URL (auto-converts `postgres://` → `postgresql+asyncpg://`) |
| `JWT_SECRET` | **Yes** | — | Min 32 chars; use `openssl rand -hex 32` |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_DAYS` | No | `7` | Refresh token lifetime |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL (for email links) |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated CORS origins |
| `SMTP_HOST` | No | `localhost` | SMTP host (Mailpit locally) |
| `SMTP_PORT` | No | `1025` | SMTP port |
| `SMTP_USERNAME` | No | `` | SMTP username |
| `SMTP_PASSWORD` | No | `` | SMTP password |
| `SMTP_FROM_EMAIL` | No | `noreply@nexussocial.dev` | Sender email |
| `SMTP_FROM_NAME` | No | `Nexus Social` | Sender display name |
| `SMTP_USE_TLS` | No | `false` | Enable TLS (true for Gmail/Brevo) |
| `GEMINI_API_KEY` | **Yes** | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `AI_DAILY_QUOTA` | No | `100` | Max AI calls per user per day |
| `MODERATION_FAIL_MODE` | No | `open` | `open` or `closed` when Gemini unavailable |
| `ADMIN_EMAIL` | **Yes** | — | Seed admin email |
| `ADMIN_USERNAME` | **Yes** | — | Seed admin username |
| `ADMIN_PASSWORD` | **Yes** | — | Seed admin password (strong!) |
| `RATE_LIMIT_LOGIN` | No | `5/minute` | Login rate limit |
| `RATE_LIMIT_REGISTER` | No | `3/minute` | Register rate limit |
| `RATE_LIMIT_FORGOT_PASSWORD` | No | `3/minute` | Forgot password rate limit |
| `RATE_LIMIT_AI` | No | `20/minute` | AI endpoint rate limit |

### Frontend (`frontend/.env.local`)
| Variable | Required | Description |
|----------|---------|-------------|
| `BACKEND_URL` | **Yes** | Backend URL for Next.js rewrites (server-side) |
| `NEXT_PUBLIC_BACKEND_URL` | **Yes** | Backend URL for SSE connections (browser) |
| `NEXT_PUBLIC_APP_NAME` | No | App display name (default: `Nexus Social`) |

---

## Detailed Stage Plans

---

### Stage 0 — Planning & Scaffold ✅

**Goal:** Create the project skeleton, configure all tooling, prove the PDF toolchain works.

**Checklist:**
- [x] Brand name and design decisions logged
- [x] `docs/IMPLEMENTATION_PLAN.md` written (this file)
- [x] `docs/REQUIREMENTS_TRACEABILITY.md` created
- [x] Monorepo folder structure scaffolded
- [x] `docker-compose.yml` (PostgreSQL 16 + Mailpit)
- [x] `scripts/init-db.sql` (pgcrypto, uuid-ossp extensions)
- [x] `backend/` Python project scaffolded
  - [x] `pyproject.toml` (ruff, mypy, pytest config)
  - [x] `requirements.txt` + `requirements-dev.txt`
  - [x] `app/main.py` — FastAPI app with /health + /ready
  - [x] `app/core/config.py` — pydantic-settings, env validation, fail-fast
  - [x] `app/core/logging.py` — structured JSON + dev formatter
  - [x] `alembic.ini` + `alembic/env.py` (async-ready skeleton)
  - [x] `tests/test_health.py` — passes without DB
  - [x] `scripts/seed.py` — skeleton
- [x] `frontend/` Next.js 14 project scaffolded
  - [x] `package.json` with all required dependencies
  - [x] `tsconfig.json`, `.eslintrc.json`
  - [x] `next.config.ts` — rewrites + security headers
  - [x] `tailwind.config.ts` — Nexus design tokens
  - [x] `src/app/globals.css` — CSS variables, dark mode
  - [x] `src/app/layout.tsx` — fonts, metadata, OG tags
  - [x] `src/app/page.tsx` — scaffold landing page
  - [x] `src/types/index.ts` — shared TypeScript types
  - [x] `src/lib/utils.ts` — cn(), timeAgo(), etc.
  - [x] Auth layout + placeholder pages
  - [x] 404 page
- [x] `render.yaml` blueprint
- [x] `.gitignore` (no secrets, no node_modules, no .env)
- [x] `backend/.env.example` + `frontend/.env.example`
- [x] `README.md` skeleton
- [x] `.github/workflows/ci.yml` skeleton
- [x] `docs/pdf/build_pdf.py` PDF toolchain
- [x] `docs/pdf/style.css` PDF styles
- [x] `docs/stages/STAGE_00.md` written
- [ ] Git repo initialized and first commit made
- [ ] `stage-00-complete` tag pushed
- [x] Stage Report posted

**Files Created:**
```
.gitignore                           docker-compose.yml
render.yaml                          README.md
scripts/init-db.sql
backend/.env.example                 frontend/.env.example
backend/pyproject.toml               backend/requirements.txt
backend/requirements-dev.txt         backend/alembic.ini
backend/alembic/env.py
backend/app/main.py                  backend/app/core/config.py
backend/app/core/logging.py
backend/tests/test_health.py         backend/tests/conftest.py
backend/scripts/seed.py
frontend/package.json                frontend/tsconfig.json
frontend/next.config.ts              frontend/tailwind.config.ts
frontend/src/app/layout.tsx          frontend/src/app/page.tsx
frontend/src/app/globals.css
frontend/src/app/(auth)/layout.tsx
frontend/src/app/(auth)/login/page.tsx
frontend/src/app/(auth)/register/page.tsx
frontend/src/app/not-found.tsx
frontend/src/lib/utils.ts            frontend/src/types/index.ts
frontend/playwright.config.ts
.github/workflows/ci.yml
docs/IMPLEMENTATION_PLAN.md          docs/REQUIREMENTS_TRACEABILITY.md
docs/pdf/build_pdf.py                docs/pdf/style.css
docs/stages/STAGE_00.md
```

**Endpoints:** `/health`, `/ready` (scaffold only)
**Tests:** `test_health.py` (2 tests — no DB needed)
**Acceptance Criteria:** All files exist, backend runs, /health returns 200, PDF sample generates

**Manual Demo Steps:**
1. `docker-compose up -d` → Postgres on :5432, Mailpit on :8025
2. `cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload`
3. `curl http://localhost:8000/health` → `{"status":"ok"}`
4. `cd frontend && npm install && npm run dev` → http://localhost:3000 shows scaffold landing
5. `cd docs/pdf && python build_pdf.py --sample` → SAMPLE_STAGE0.pdf generated

**Complexity:** Low · **Dependencies:** None

---

### Stage 1 — Database Layer 🔲

**Goal:** Define all 11 database tables as SQLAlchemy models, generate Alembic migrations, add indexes and constraints, write a seed script, and produce the ER diagram.

**Checklist:**
- [ ] `app/db/base.py` — declarative Base with UUID PK mixin
- [ ] `app/db/session.py` — async engine + session factory + `get_db` dependency
- [ ] `app/models/user.py` — `users` table
- [ ] `app/models/token.py` — `refresh_tokens`, `email_tokens`
- [ ] `app/models/post.py` — `posts`
- [ ] `app/models/comment.py` — `comments`
- [ ] `app/models/like.py` — `likes` (UNIQUE user_id+post_id)
- [ ] `app/models/notification.py` — `notifications` (JSONB payload)
- [ ] `app/models/moderation.py` — `moderation_flags`
- [ ] `app/models/ai.py` — `ai_chat_sessions`, `ai_chat_messages`, `ai_usage_logs`
- [ ] `app/models/activity.py` — `activity_logs`
- [ ] `alembic/env.py` updated to import all models
- [ ] Alembic migration: `alembic revision --autogenerate -m "initial schema"`
- [ ] Feed index: `posts(created_at DESC)`, `posts(author_id, created_at DESC)`
- [ ] `scripts/seed.py` — full implementation with Argon2 admin user
- [ ] `app/main.py` — /ready endpoint checks DB connectivity
- [ ] `tests/test_models.py` — model instantiation, constraint tests
- [ ] `docs/ER_DIAGRAM.md` — Mermaid erDiagram source
- [ ] `docs/diagrams/er_diagram.mmd` — Mermaid source file

**Tables:**
| Table | Key Columns | Constraints |
|-------|------------|------------|
| `users` | id, email, username, display_name, hashed_password, role, is_verified, is_suspended, bio, location, website, avatar_url | UNIQUE email, UNIQUE username |
| `refresh_tokens` | id, user_id, token_hash, family_id, user_agent, ip_address, expires_at, revoked | INDEX user_id |
| `email_tokens` | id, user_id, token_hash, token_type, expires_at, used_at | INDEX user_id, INDEX token_hash |
| `posts` | id, author_id, content, image_url, is_hidden, is_edited | CHECK len(content)≤1000 |
| `comments` | id, post_id, author_id, parent_id, content, is_hidden, is_edited | FK post_id, FK parent_id |
| `likes` | id, user_id, post_id | UNIQUE(user_id, post_id) |
| `notifications` | id, user_id, type, payload (JSONB), is_read | INDEX(user_id, is_read) |
| `moderation_flags` | id, content_type, content_id, category, severity, score, action, reason, reviewed | INDEX(reviewed, action) |
| `ai_chat_sessions` | id, user_id, title, created_at | FK user_id |
| `ai_chat_messages` | id, session_id, role, content, created_at | FK session_id |
| `ai_usage_logs` | id, user_id, feature, latency_ms, tokens_used, status, error | INDEX(user_id, created_at) |
| `activity_logs` | id, admin_id, action, resource_type, resource_id, metadata (JSONB), ip | INDEX(admin_id, created_at) |

**Tests:** Model creation, UNIQUE constraint on likes, FK cascade behavior
**Acceptance Criteria:** `alembic upgrade head` succeeds, seed runs, /ready returns 200, ER diagram renders

---

### Stage 2 — Authentication Backend 🔲

**Goal:** Full auth flow: register → verify email → login → refresh → logout → forgot/reset password. All with security hardening.

**Checklist:**
- [ ] `app/core/security.py` — Argon2id hash/verify, password policy validator
- [ ] `app/core/tokens.py` — JWT access token, opaque refresh token, stream tokens
- [ ] `app/services/email_service.py` — aiosmtplib + Jinja2 templates
- [ ] `app/templates/emails/` — verification.html, reset_password.html, welcome.html
- [ ] `app/services/auth_service.py` — all auth business logic
- [ ] `app/schemas/auth.py` — RegisterRequest, LoginRequest, TokenResponse, etc.
- [ ] `app/api/v1/auth.py` — all auth endpoints
- [ ] `app/api/deps.py` — `require_user`, `require_admin`, `get_current_user`
- [ ] Rate limiting on all auth endpoints (slowapi)
- [ ] Global exception handler (no stack traces to clients)
- [ ] Request ID middleware
- [ ] `tests/test_auth.py` — full coverage per QUAL-01
- [ ] `docs/stages/STAGE_02.md`

**Endpoints:**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/verify-email` | None | Verify email with token |
| POST | `/api/v1/auth/resend-verification` | None | Resend verification email |
| POST | `/api/v1/auth/login` | None | Login → access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Cookie | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Cookie | Revoke refresh token |
| POST | `/api/v1/auth/forgot-password` | None | Send reset email |
| POST | `/api/v1/auth/reset-password` | None | Set new password with token |
| GET | `/api/v1/auth/me` | Bearer | Get current user |

**Tests:** register, verify, login-unverified, login, refresh rotation, reuse detection, logout, forgot/reset, rate limits, password policy

---

### Stage 3 — Core Social Backend 🔲

**Goal:** Profiles, posts (CRUD), comments, likes, cursor-paginated feed, ownership enforcement.

**Checklist:**
- [ ] `app/services/post_service.py`
- [ ] `app/services/comment_service.py`
- [ ] `app/services/user_service.py`
- [ ] `app/api/v1/users.py`
- [ ] `app/api/v1/posts.py`
- [ ] `app/api/v1/comments.py`
- [ ] `app/api/v1/likes.py`
- [ ] Cursor pagination (keyset on `created_at + id`)
- [ ] Ownership checks (can't edit others' posts/comments)
- [ ] `tests/test_social.py`, `tests/test_authz.py`
- [ ] No N+1 queries (use `selectinload` / `joinedload`)

**Endpoints:** CRUD for users, posts, comments, likes; paginated feed

---

### Stage 4 — Notifications & Real-time 🔲

**Goal:** SSE stream with stream tokens, persistence, admin login alerts, polling fallback.

**Checklist:**
- [ ] `app/services/notification_service.py` — create, mark read, list
- [ ] `app/services/pubsub.py` — in-process pub/sub interface + implementation
- [ ] `app/api/v1/notifications.py` — list, mark read, stream, stream-token
- [ ] Admin login notification trigger in auth_service
- [ ] Stream token: 60-second single-purpose JWT
- [ ] SSE: heartbeat every 20s, CORS for `NEXT_PUBLIC_BACKEND_URL`
- [ ] `tests/test_notifications.py`

---

### Stage 5 — Admin Backend 🔲

**Goal:** All admin management endpoints, stats, charts, moderation queue, audit log.

**Checklist:**
- [ ] `app/api/v1/admin/` — stats, users, posts, comments, moderation, activity
- [ ] Stats: total users, verified, new 7d, posts, comments, likes, flagged
- [ ] Charts: signups/day, posts/day (last 30 days)
- [ ] Every admin action written to `activity_logs`
- [ ] Bulk actions (hide/delete multiple posts/comments)
- [ ] `tests/test_admin.py`

---

### Stage 6 — Gemini AI Service 🔲

**Goal:** All five AI features behind a provider-agnostic interface. Mocked tests.

**Pre-coding:** Check current google-genai SDK docs for model names and API changes.

**Checklist:**
- [ ] `app/services/ai/base.py` — abstract AIService interface
- [ ] `app/services/ai/gemini_service.py` — Gemini implementation
- [ ] `app/services/ai/mock_service.py` — mock for tests
- [ ] `app/services/ai/prompts.py` — all versioned prompts
- [ ] Post generation: 3 variants + tone
- [ ] Summarization: summary + key points + sentiment
- [ ] Conversational assistant: streaming + session persistence
- [ ] Content moderation: background task, JSON output, block/flag/allow
- [ ] Smart replies: 3 short suggestions
- [ ] `app/api/v1/ai.py` — all AI endpoints
- [ ] Usage logging in `ai_usage_logs`
- [ ] Per-user rate limits + daily quota
- [ ] `docs/AI_INTEGRATION.md`
- [ ] `tests/test_ai.py` (mocked Gemini)

---

### Stage 7 — Frontend Foundation 🔲

**Goal:** Design system, auth pages, token handling, route guards, API client.

**Checklist:**
- [ ] shadcn/ui components (Button, Input, Card, Toast, Dialog, etc.)
- [ ] `src/lib/api-client.ts` — fetch wrapper + silent refresh interceptor
- [ ] `src/contexts/auth-context.tsx` — AuthProvider, useAuth
- [ ] `src/middleware.ts` — route protection by role
- [ ] Auth pages: login, register, verify-email, forgot-password, reset-password
- [ ] `src/components/ui/` — full shadcn/ui set
- [ ] Theme toggle (next-themes)
- [ ] TanStack Query provider

---

### Stage 8 — User App UI 🔲

**Goal:** Feed, post composer with AI, post detail, profiles, notifications, AI chat widget.

**Checklist:**
- [ ] Feed page: infinite scroll, post cards, skeleton loaders
- [ ] Post composer: textarea + AI generate button + 3 variant preview
- [ ] Post detail: comments, smart replies, AI summary (≥3 comments)
- [ ] Profile page: own + public; edit profile
- [ ] Notifications page + live bell
- [ ] Floating AI chat widget (streaming)
- [ ] Optimistic updates for likes and comments

---

### Stage 9 — Admin Console UI 🔲

**Goal:** Admin layout with sidebar, dashboard charts, user/content tables, moderation queue.

**Checklist:**
- [ ] Admin layout: dark sidebar, dense tables
- [ ] Dashboard: 6 stat cards + 2 Recharts line charts
- [ ] Users table: search, paginate, actions (suspend, role, delete)
- [ ] Posts/comments table: hide, restore, delete, bulk
- [ ] Moderation queue: flagged items with scores, approve/hide/delete
- [ ] Live login alert feed (SSE)
- [ ] Activity log table

---

### Stage 10 — Hardening 🔲

**Goal:** Security headers, a11y pass, E2E smoke test, full test run.

**Checklist:**
- [ ] Security headers middleware (backend)
- [ ] Next.js security headers (already in next.config.ts — verify)
- [ ] Accessibility audit (axe-core / eslint-plugin-jsx-a11y)
- [ ] Lighthouse performance pass
- [ ] Playwright E2E: register → verify → login → post → like → comment
- [ ] Full test run — all green
- [ ] Structured JSON logging + request IDs complete
- [ ] Optional Sentry hook via `SENTRY_DSN`

---

### Stage 11 — Deployment 🔲

**Goal:** Deploy to Render + Vercel. Prove it works end-to-end in production.

**Checklist:**
- [ ] `backend/Dockerfile` (multi-stage, non-root, pre-deploy migrations)
- [ ] `render.yaml` finalized
- [ ] Render web service deployed + DB provisioned
- [ ] `alembic upgrade head` run on Render
- [ ] `scripts/seed.py` run on Render
- [ ] Vercel project created + env vars set + rewrites deployed
- [ ] Production smoke test: /health 200, register, login, post, AI feature
- [ ] `docs/DEPLOYMENT.md` — complete step-by-step

---

### Stage 12 — Documentation & Submission 🔲

**Goal:** Generate the full system documentation PDF, write SUBMISSION.md, secret scan.

**Checklist:**
- [ ] All `docs/stages/STAGE_XX.md` files complete
- [ ] `docs/ER_DIAGRAM.md` finalized
- [ ] `docs/AI_INTEGRATION.md` finalized
- [ ] `docs/API.md` finalized
- [ ] `docs/DEPLOYMENT.md` finalized
- [ ] `python docs/pdf/build_pdf.py` → SYSTEM_DOCUMENTATION.pdf
- [ ] `docs/SUBMISSION.md` with all required items
- [ ] Secret scan: `scripts/secret_scan.py`
- [ ] Final README reviewed
- [ ] All requirements traced in REQUIREMENTS_TRACEABILITY.md

---

## Decisions & Deviations Log

| Stage | Date | Decision |
|-------|------|----------|
| 0 | 2026-10-30 | Brand name "Nexus Social" chosen — warm social identity with indigo/rose palette |
| 0 | 2026-10-30 | `tailwindcss-animate` added as dependency for shadcn/ui animations |
| 0 | 2026-10-30 | Python tools (git, node, docker) not on PATH in shell — noted for user action |

## Known Issues

| # | Issue | Stage | Severity |
|---|-------|-------|----------|
| KI-1 | Git, Node.js, Docker not on system PATH — user must install / add to PATH | 0 | **Blocking for verification** |
| KI-2 | WeasyPrint requires GTK/Pango system libraries — Playwright fallback used on Windows | 0 | Low (workaround in place) |
| KI-3 | `tailwindcss-animate` not in package.json yet — add before Stage 7 install | 0 | Low |
