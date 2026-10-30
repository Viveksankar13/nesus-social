# Requirements Traceability Matrix
## Nexus Social — AI-Powered Social Media Platform

> This document maps every assignment requirement to the stage where it is implemented and the evidence (test, file, endpoint, or screenshot) that proves it is done.

| ID | Requirement | Stage | Status | Evidence |
|----|-------------|-------|--------|----------|
| **AUTH-01** | Email + username + password registration | 2 | ✅ Done | `POST /api/v1/auth/register`, test `test_user_registration_and_verification` |
| **AUTH-02** | Email verification via SMTP | 2 | ✅ Done | `GET /api/v1/auth/verify-email`, `backend/app/services/email_service.py` |
| **AUTH-03** | Login — verified users only | 2 | ✅ Done | `POST /api/v1/auth/login`, test `test_unverified_login_blocked` |
| **AUTH-04** | Logout | 2 | ✅ Done | `POST /api/v1/auth/logout`, revokes refresh token & clears cookie |
| **AUTH-05** | Forgot / reset password | 2 | ✅ Done | `POST /api/v1/auth/forgot-password`, `POST /api/v1/auth/reset-password` |
| **AUTH-06** | Argon2id password hashing | 2 | ✅ Done | `backend/app/core/security.py`, test `test_argon2id_hashing` |
| **AUTH-07** | Strong password policy | 2 | ✅ Done | `validate_password_strength`, test `test_password_policy` |
| **AUTH-08** | 15-min JWT access token, memory only | 2 | ✅ Done | `backend/app/core/tokens.py:create_access_token` |
| **AUTH-09** | Rotating opaque refresh token, httpOnly cookie | 2 | ✅ Done | `POST /api/v1/auth/refresh`, test `test_token_refresh_rotation` |
| **AUTH-10** | Refresh token reuse detection — revoke family | 2 | ✅ Done | test `test_token_reuse_detection_revokes_family` |
| **AUTH-11** | Next.js rewrites /api/* → backend | 7 | ✅ Done | `frontend/next.config.mjs` rewrites to `${backendUrl}/api/:path*` |
| **AUTH-12** | Rate limits: login, register, forgot, resend | 2 | ✅ Done | slowapi decorators on `auth.py` router |
| **AUTH-13** | RBAC: require_user, require_admin | 2 | ✅ Done | `backend/app/api/deps.py` |
| **AUTH-14** | Suspended user blocked everywhere | 2/5 | ✅ Done | `deps.py:require_user`, `auth_service.py:authenticate_user` |
| **SOCIAL-01** | User profile: avatar, bio, location, website | 3/8 | ✅ Done | `GET/PUT /api/v1/users/*`, `src/app/(app)/profile/[username]/page.tsx`, `EditProfileDialog` |
| **SOCIAL-02** | Create / edit / delete own posts | 3/8 | ✅ Done | `POST/PUT/DELETE /api/v1/posts/*`, `src/components/feed/post-composer.tsx`, `post-card.tsx` |
| **SOCIAL-03** | Post ≤1000 chars + optional image URL | 3/8 | ✅ Done | Pydantic validator, `PostComposer` real-time 1000 char counter & image URL toggle |
| **SOCIAL-04** | Feed: cursor infinite scroll | 3/8 | ✅ Done | `GET /api/v1/posts?cursor=`, `src/app/(app)/feed/page.tsx` with `useInfiniteQuery` |
| **SOCIAL-05** | Like toggle (unique per user/post) | 3/8 | ✅ Done | `POST /api/v1/posts/{id}/like`, `PostCard` optimistic like mutation |
| **SOCIAL-06** | Comments: create/edit/delete own, one-level replies | 3/8 | ✅ Done | `POST/GET /api/v1/posts/{id}/comments`, `src/app/(app)/posts/[id]/page.tsx` 1-level replies |
| **NOTIF-01** | Notification persistence | 4/8 | ✅ Done | `notifications` table, `src/app/(app)/notifications/page.tsx` list and mark-read |
| **NOTIF-02** | SSE stream with stream tokens | 4/8 | ✅ Done | `GET /api/v1/notifications/stream`, `NotificationBell` live SSE connection |
| **NOTIF-03** | Admin: real-time login alert | 4/9 | ✅ Done | `test_admin_login_notification_and_debouncing`, `AdminLayout` live SSE `admin_alert` stream |
| **NOTIF-04** | Polling fallback every 30s | 4/8 | ✅ Done | `NotificationBell` 30s background refetch fallback |
| **ADMIN-01** | Dashboard stat cards | 5/9 | ✅ Done | `GET /api/v1/admin/stats`, `src/app/admin/page.tsx` 6 KPI stat cards |
| **ADMIN-02** | Chart data: signups/day, posts/day (30d) | 5/9 | ✅ Done | `GET /api/v1/admin/charts`, `src/app/admin/page.tsx` Recharts 30d time-series |
| **ADMIN-03** | Users: search, paginate, suspend, role, delete | 5/9 | ✅ Done | `src/app/admin/users/page.tsx`, search, pagination, role & suspend dialogs |
| **ADMIN-04** | Post/comment management | 5/9 | ✅ Done | `src/app/admin/content/page.tsx`, posts/comments tabs, bulk moderation actions |
| **ADMIN-05** | Moderation queue | 5/9 | ✅ Done | `src/app/admin/moderation/page.tsx`, AI severity, score, approve/hide/delete |
| **ADMIN-06** | Activity audit log | 5/9 | ✅ Done | `src/app/admin/activity/page.tsx`, audit logs table, JSON inspector |
| **AI-01** | Post generation/improvement — 3 variants + tone | 6/8 | ✅ Done | `POST /api/v1/ai/generate-post`, `PostComposer` AI Assist modal (3 variants + 4 tones) |
| **AI-02** | Post summarization with sentiment (≥3 comments) | 6/8 | ✅ Done | `POST /api/v1/ai/summarize`, `AISummaryCard` with takeaways & sentiment badge |
| **AI-03** | Conversational assistant, streaming, persisted | 6/8 | ✅ Done | `POST /api/v1/ai/chat/*`, `AIChatWidget` floating streaming assistant |
| **AI-04** | Content moderation — background, structured JSON | 6 | ✅ Done | `app/services/ai/moderation.py`, test `test_background_content_moderation_auto_hide` |
| **AI-05** | Smart reply suggestions | 6/8 | ✅ Done | `POST /api/v1/ai/smart-replies`, `SmartRepliesBar` 3 suggestion pills |
| **AI-06** | Provider-agnostic ai_service interface | 6 | ✅ Done | `app/services/ai/base.py`, `gemini_service.py`, `mock_service.py` |
| **AI-07** | Prompt injection defense | 6 | ✅ Done | `app/services/ai/prompts.py`, test `test_prompt_injection_sanitization` |
| **AI-08** | Per-user rate limits + daily quota | 6 | ✅ Done | `ai_usage_logs` table, test `test_daily_quota_limit_exceeded` |
| **AI-09** | Usage logging (user, feature, latency, tokens) | 6 | ✅ Done | `ai_usage_logs` table, tests in `test_ai.py` |
| **DB-01** | All 11 tables with UUID PKs, FKs, constraints | 1 | ✅ Done | Alembic migration `0001_initial_schema.py`, `tests/test_models.py` |
| **DB-02** | Feed indexes | 1 | ✅ Done | `posts` index on `created_at DESC` & `(author_id, created_at DESC)` |
| **DB-03** | ER diagram (Mermaid + PNG/SVG) | 1 | ✅ Done | `docs/ER_DIAGRAM.md`, `docs/diagrams/er_diagram.mmd` |
| **DB-04** | Seed script (admin + --demo) | 1 | ✅ Done | `backend/scripts/seed.py` |
| **UI-01** | Responsive, mobile-first, accessible | 7-9 | ✅ Done | `src/components/ui/*`, responsive layouts, Tailwind tokens |
| **UI-02** | Light/dark mode | 7 | ✅ Done | `next-themes`, `ThemeProvider`, `ThemeToggle` |
| **UI-03** | Original brand identity: Nexus Social | 7 | ✅ Done | Design tokens, `globals.css`, landing page, auth layout |
| **UI-04** | Route protection via Next.js middleware | 7 | ✅ Done | `src/middleware.ts` evaluating `refresh_token` |
| **UI-05** | Silent token refresh interceptor | 7 | ✅ Done | `src/lib/api-client.ts`, deduplicated silent 401 refresh |
| **QUAL-01** | Backend pytest: all auth flows | 2 | ✅ Done | `backend/tests/test_auth.py` (6 tests passing) |
| **QUAL-02** | Backend pytest: authorization | 3 | ✅ Done | `backend/tests/test_social.py` (ownership tests) |
| **QUAL-03** | Playwright E2E smoke test | 10 | ✅ Done | `frontend/tests/e2e/smoke.spec.ts` covering landing, USN registration, login, forgot password, theme, guards |
| **QUAL-04** | GitHub Actions CI | 0 | ✅ Done | `.github/workflows/ci.yml` |
| **QUAL-05** | Structured JSON logging + request IDs | 10 | ✅ Done | `backend/app/core/logging.py`, `RequestIdMiddleware` in `main.py` |
| **QUAL-06** | Ruff + ESLint + tsc clean | 0-12 | ✅ Done | Ruff, ESLint, tsc --noEmit all 0 errors |
| **DEPLOY-01** | Backend Dockerfile (multi-stage, non-root) | 11 | 🔲 Not started | `backend/Dockerfile` |
| **DEPLOY-02** | render.yaml blueprint | 0 | ✅ Done | `render.yaml` |
| **DEPLOY-03** | Vercel config + rewrites | 7/11 | 🔲 Not started | `frontend/vercel.json` |
| **DEPLOY-04** | DEPLOYMENT.md step-by-step | 11 | 🔲 Not started | `docs/DEPLOYMENT.md` |
| **DOC-01** | System Documentation PDF | 12 | 🔲 Not started | `docs/pdf/SYSTEM_DOCUMENTATION.pdf` |
| **DOC-02** | SUBMISSION.md with all required items | 12 | 🔲 Not started | `docs/SUBMISSION.md` |
| **SEC-01** | No secrets in repo (secret scan) | 12 | 🔲 Not started | `scripts/secret_scan.py` output |
| **SEC-02** | Security headers | 10 | ✅ Done | `backend/app/core/security_headers.py` (CSP, HSTS, X-Content-Type, X-Frame) + Next.js headers |
| **SEC-03** | Strict CORS allowlist | 2 | ✅ Done | `backend/app/main.py` CORS middleware |
| **SEC-04** | Parameterized queries only | 1-6 | ✅ Done | SQLAlchemy 2.0 ORM only |
| **SEC-05** | No stack traces to clients | 2 | ✅ Done | `backend/app/main.py` global exception handlers |

---

*Legend: ✅ Done · 🔄 In Progress · 🔲 Not Started*

*Last updated: Stage 10 complete (including Brevo SMTP & Student USN University Identity Integration)*
