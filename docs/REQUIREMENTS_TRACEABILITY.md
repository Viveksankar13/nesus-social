# Requirements Traceability Matrix
## Nexus Social — AI-Powered Social Media Platform

> This document maps every assignment requirement to the stage where it is implemented and the evidence (test, file, endpoint, or screenshot) that proves it is done.

| ID | Requirement | Stage | Status | Evidence |
|----|-------------|-------|--------|----------|
| **AUTH-01** | Email + username + password registration | 2 | 🔲 Not started | `POST /api/v1/auth/register`, test `test_register` |
| **AUTH-02** | Email verification via SMTP | 2 | 🔲 Not started | `POST /api/v1/auth/verify-email`, Mailpit screenshot |
| **AUTH-03** | Login — verified users only | 2 | 🔲 Not started | `POST /api/v1/auth/login`, test `test_login_unverified` |
| **AUTH-04** | Logout | 2 | 🔲 Not started | `POST /api/v1/auth/logout` |
| **AUTH-05** | Forgot / reset password | 2 | 🔲 Not started | `POST /api/v1/auth/forgot-password`, `POST /api/v1/auth/reset-password` |
| **AUTH-06** | Argon2id password hashing | 2 | 🔲 Not started | `app/core/security.py`, test `test_password_hash` |
| **AUTH-07** | Strong password policy | 2 | 🔲 Not started | Pydantic validator, Zod client validator |
| **AUTH-08** | 15-min JWT access token, memory only | 2 | 🔲 Not started | `app/core/tokens.py` |
| **AUTH-09** | Rotating opaque refresh token, httpOnly cookie | 2 | 🔲 Not started | `app/core/tokens.py`, test `test_refresh_rotation` |
| **AUTH-10** | Refresh token reuse detection — revoke family | 2 | 🔲 Not started | test `test_refresh_reuse_detection` |
| **AUTH-11** | Next.js rewrites /api/* → backend | 7 | 🔲 Not started | `frontend/next.config.js` rewrites |
| **AUTH-12** | Rate limits: login, register, forgot, resend | 2 | 🔲 Not started | slowapi decorators, test rate limit |
| **AUTH-13** | RBAC: require_user, require_admin | 2 | 🔲 Not started | `app/api/deps.py` |
| **AUTH-14** | Suspended user blocked everywhere | 2/5 | 🔲 Not started | test `test_suspended_user` |
| **SOCIAL-01** | User profile: avatar, bio, location, website | 3 | 🔲 Not started | `GET/PUT /api/v1/users/{id}` |
| **SOCIAL-02** | Create / edit / delete own posts | 3 | 🔲 Not started | `POST/PUT/DELETE /api/v1/posts/{id}` |
| **SOCIAL-03** | Post ≤1000 chars + optional image URL | 3 | 🔲 Not started | Pydantic validator |
| **SOCIAL-04** | Feed: cursor infinite scroll | 3 | 🔲 Not started | `GET /api/v1/posts?cursor=` |
| **SOCIAL-05** | Like toggle (unique per user/post) | 3 | 🔲 Not started | `POST /api/v1/posts/{id}/like`, DB unique constraint |
| **SOCIAL-06** | Comments: create/edit/delete own, one-level replies | 3 | 🔲 Not started | `POST /api/v1/comments` |
| **NOTIF-01** | Notification persistence | 4 | 🔲 Not started | `notifications` table |
| **NOTIF-02** | SSE stream with stream tokens | 4 | 🔲 Not started | `GET /api/v1/notifications/stream` |
| **NOTIF-03** | Admin: real-time login alert | 4 | 🔲 Not started | test `test_admin_login_notification` |
| **NOTIF-04** | Polling fallback every 30s | 4/7 | 🔲 Not started | frontend `useNotifications` hook |
| **ADMIN-01** | Dashboard stat cards | 5 | 🔲 Not started | `GET /api/v1/admin/stats` |
| **ADMIN-02** | Chart data: signups/day, posts/day (30d) | 5 | 🔲 Not started | `GET /api/v1/admin/charts` |
| **ADMIN-03** | Users: search, paginate, suspend, role, delete | 5 | 🔲 Not started | `GET/PUT/DELETE /api/v1/admin/users` |
| **ADMIN-04** | Post/comment management | 5 | 🔲 Not started | `GET/PUT/DELETE /api/v1/admin/posts` |
| **ADMIN-05** | Moderation queue | 5 | 🔲 Not started | `GET /api/v1/admin/moderation` |
| **ADMIN-06** | Activity audit log | 5 | 🔲 Not started | `activity_logs` table |
| **AI-01** | Post generation/improvement — 3 variants + tone | 6 | 🔲 Not started | `POST /api/v1/ai/generate-post` |
| **AI-02** | Post summarization with sentiment | 6 | 🔲 Not started | `POST /api/v1/ai/summarize` |
| **AI-03** | Conversational assistant, streaming, persisted | 6 | 🔲 Not started | `POST /api/v1/ai/chat` |
| **AI-04** | Content moderation — background, structured JSON | 6 | 🔲 Not started | `app/services/ai/moderation.py` |
| **AI-05** | Smart reply suggestions | 6 | 🔲 Not started | `POST /api/v1/ai/smart-replies` |
| **AI-06** | Provider-agnostic ai_service interface | 6 | 🔲 Not started | `app/services/ai/base.py` |
| **AI-07** | Prompt injection defense | 6 | 🔲 Not started | `app/services/ai/prompts.py` |
| **AI-08** | Per-user rate limits + daily quota | 6 | 🔲 Not started | `ai_usage_logs` table |
| **AI-09** | Usage logging (user, feature, latency, tokens) | 6 | 🔲 Not started | `ai_usage_logs` table |
| **DB-01** | All 11 tables with UUID PKs, FKs, constraints | 1 | ✅ Done | Alembic migration `0001_initial_schema.py`, `tests/test_models.py` |
| **DB-02** | Feed indexes | 1 | ✅ Done | `posts` index on `created_at DESC` & `(author_id, created_at DESC)` |
| **DB-03** | ER diagram (Mermaid + PNG/SVG) | 1 | ✅ Done | `docs/ER_DIAGRAM.md`, `docs/diagrams/er_diagram.mmd` |
| **DB-04** | Seed script (admin + --demo) | 1 | ✅ Done | `backend/scripts/seed.py` |
| **UI-01** | Responsive, mobile-first, accessible | 7-9 | 🔲 Not started | Tailwind, ARIA, axe audit |
| **UI-02** | Light/dark mode | 7 | 🔲 Not started | next-themes |
| **UI-03** | Original brand identity: Nexus Social | 7 | 🔲 Not started | Design system, palette |
| **UI-04** | Route protection via Next.js middleware | 7 | 🔲 Not started | `frontend/middleware.ts` |
| **UI-05** | Silent token refresh interceptor | 7 | 🔲 Not started | `frontend/lib/api-client.ts` |
| **QUAL-01** | Backend pytest: all auth flows | 2 | 🔲 Not started | `tests/test_auth.py` |
| **QUAL-02** | Backend pytest: authorization | 3 | 🔲 Not started | `tests/test_authz.py` |
| **QUAL-03** | Playwright E2E smoke test | 10 | 🔲 Not started | `frontend/tests/e2e/smoke.spec.ts` |
| **QUAL-04** | GitHub Actions CI | 0 | ✅ Done | `.github/workflows/ci.yml` |
| **QUAL-05** | Structured JSON logging + request IDs | 10 | 🔲 Not started | `app/core/logging.py` |
| **QUAL-06** | Ruff + ESLint + tsc clean | 0-12 | ✅ Done | Ruff check clean, ESLint clean, tsc clean in Stage 1 |
| **DEPLOY-01** | Backend Dockerfile (multi-stage, non-root) | 11 | 🔲 Not started | `backend/Dockerfile` |
| **DEPLOY-02** | render.yaml blueprint | 0 | ✅ Done | `render.yaml` |
| **DEPLOY-03** | Vercel config + rewrites | 7/11 | 🔲 Not started | `frontend/vercel.json` |
| **DEPLOY-04** | DEPLOYMENT.md step-by-step | 11 | 🔲 Not started | `docs/DEPLOYMENT.md` |
| **DOC-01** | System Documentation PDF | 12 | 🔲 Not started | `docs/pdf/SYSTEM_DOCUMENTATION.pdf` |
| **DOC-02** | SUBMISSION.md with all required items | 12 | 🔲 Not started | `docs/SUBMISSION.md` |
| **SEC-01** | No secrets in repo (secret scan) | 12 | 🔲 Not started | `scripts/secret_scan.py` output |
| **SEC-02** | Security headers | 10 | 🔲 Not started | `app/core/security_headers.py` |
| **SEC-03** | Strict CORS allowlist | 2 | 🔲 Not started | `app/main.py` CORS middleware |
| **SEC-04** | Parameterized queries only | 1-6 | 🔲 Not started | SQLAlchemy ORM (no raw SQL) |
| **SEC-05** | No stack traces to clients | 2 | 🔲 Not started | Global exception handler |

---

*Legend: ✅ Done · 🔄 In Progress · 🔲 Not Started*

*Last updated: Stage 0*
