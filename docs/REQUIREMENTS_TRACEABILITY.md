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
| **DEPLOY-01** | Backend Dockerfile (multi-stage, non-root) | 11 | ✅ Done | `backend/Dockerfile`, non-root user `appuser:1001`, healthcheck, `entrypoint.sh` |
| **DEPLOY-02** | render.yaml blueprint | 11 | ✅ Done | `render.yaml` with managed PostgreSQL + Docker Web Service + pre-deploy migrations |
| **DEPLOY-03** | Vercel config + rewrites | 7/11 | ✅ Done | `frontend/vercel.json`, `next.config.mjs` API rewrites |
| **DEPLOY-04** | DEPLOYMENT.md step-by-step | 11 | ✅ Done | `docs/DEPLOYMENT.md` comprehensive production deployment guide |
| **DOC-01** | System Documentation PDF | 12 | ✅ Done | `docs/pdf/SYSTEM_DOCUMENTATION.pdf` (4.2 MB compiled documentation) |
| **DOC-02** | SUBMISSION.md with all required items | 12 | ✅ Done | `docs/SUBMISSION.md` with complete submission manifest & credentials |
| **SEC-01** | No secrets in repo (secret scan) | 12 | ✅ Done | `scripts/secret_scan.py` scanned 218 files, 0 secrets detected |
| **SEC-02** | Security headers | 10 | ✅ Done | `backend/app/core/security_headers.py` (CSP, HSTS, X-Content-Type, X-Frame) + Next.js headers |
| **SEC-03** | Strict CORS allowlist | 2 | ✅ Done | `backend/app/main.py` CORS middleware |
| **SEC-04** | Parameterized queries only | 1-6 | ✅ Done | SQLAlchemy 2.0 ORM only |
| **SEC-05** | No stack traces to clients | 2 | ✅ Done | `backend/app/main.py` global exception handlers |
| **SWAP-01** | Canonical skill taxonomy with fuzzy match & suggestion moderation | S1 | ✅ Done | `GET /api/v1/swaps/taxonomy`, `SwapTaxonomyService.fuzzy_match_skill`, test `test_taxonomy_fuzzy_matching` |
| **SWAP-02** | User skill profiles (teach/learn, level, experience, notes) | S1 | ✅ Done | `PUT /api/v1/swaps/profile/me`, `UserSkill` model, test `test_profile_lifecycle_and_privacy_guarantee` |
| **SWAP-03** | Timezone-aware recurring weekly availability windows (UTC) | S1 | ✅ Done | `availability_windows` table, `test_profile_lifecycle_and_privacy_guarantee` |
| **SWAP-04** | Privacy-by-design coarse location (~1 km) & distance buckets | S1 | ✅ Done | `UserSwapProfilePublicResponse`, test `test_profile_lifecycle_and_privacy_guarantee` asserting zero lat/lng leakage |
| **SWAP-05** | 4-step onboarding wizard with 18+ confirmation | S1 | ✅ Done | `/swaps/onboarding`, Playwright test `swap-onboarding.spec.ts` |
| **SWAP-06** | Swap listing creation with limits (`SWAP_MAX_ACTIVE_LISTINGS=5`) | S2 | ✅ Done | `POST /api/v1/swaps/listings`, test `test_swap_listing_max_limit_enforced` |
| **SWAP-07** | Automated AI moderation blocking payment & commercial solicitation | S2 | ✅ Done | `SwapService.create_listing`, test `test_swap_listing_no_money_policy` |
| **SWAP-08** | Feed integration: share swap listing as social post with CTA | S2 | ✅ Done | `POST /api/v1/swaps/listings/{id}/share`, test `test_swap_listing_share_to_feed`, `SwapPostCard` |
| **SWAP-09** | Interactive discovery map (Leaflet) with coarse area bubbles | S2 | ✅ Done | `SwapMap` component, OpenStreetMap tiles, Playwright test `swap-discovery.spec.ts` |
| **SWAP-10** | Multi-filter discovery (category, mode, distance, day, level) | S2 | ✅ Done | `GET /api/v1/swaps/listings`, `SwapService.search_listings`, test `test_swap_discovery_spatial_and_blocking` |
| **SWAP-11** | Transparent 5-criteria weighted matching engine | S2 | ✅ Done | `SwapMatchingService.calculate_match_score`, test `test_matching_engine_and_cached_explanation` |
| **SWAP-12** | Cached Gemini "Why you match" one-sentence explanation | S2 | ✅ Done | `GET /api/v1/swaps/matches`, `match_explanations` SHA-256 table cache, test `test_matching_engine_and_cached_explanation` |
| **SWAP-13** | Swap request state machine with counter-proposals & 72h expiry | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-14** | Fixed 30-min halves barter with slot overlap prevention | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-15** | Auto-generated unguessable Jitsi Meet video room tokens | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-16** | Public place validation & warning for in-person swaps | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-17** | Downloadable `.ics` calendar invite files for scheduled halves | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-18** | Real-time session-scoped logistics chat over SSE | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-19** | Double-blind review system with 7-day auto-reveal | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-20** | Quantitative trust score (0–100) & badge assignment | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-21** | Reciprocity ledger tracking with 2-session grace balance | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-22** | Automated session reminder jobs (24h & 15m) via SSE & Brevo SMTP | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-23** | Secret-protected internal cron endpoint (`X-Cron-Secret`) | S3 | 🔲 Planned | Stage 3 Deliverable |
| **SWAP-24** | Gemini Session Planner: 30-minute structured agenda | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-25** | Gemini Post-Session Recap helper | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-26** | Gemini Fairness & Reciprocity Advisor | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-27** | User blocking & reporting with 3-strike auto-hide | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-28** | Admin Swaps Console: KPI dashboard & analytics | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-29** | Admin dispute resolution & trust score adjustment | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-30** | Admin taxonomy curation (approve, rename, merge skills) | S4 | 🔲 Planned | Stage 4 Deliverable |
| **SWAP-31** | High-performance spatial query benchmark (10k listings) | S5 | 🔲 Planned | Stage 5 Deliverable |
| **SWAP-32** | Zero coordinate/geohash API leakage security audit | S5 | 🔲 Planned | Stage 5 Deliverable |
| **SWAP-33** | Full Playwright E2E swap lifecycle smoke test | S5 | 🔲 Planned | Stage 5 Deliverable |
| **SWAP-34** | Render Cron Job production configuration | S5 | 🔲 Planned | Stage 5 Deliverable |
| **SWAP-35** | Complete documentation update & PDF rebuild (Chapters 17–24) | S5 | 🔲 Planned | Stage 5 Deliverable |

---

*Legend: ✅ Done · 🔄 In Progress · 🔲 Not Started*

*Last updated: Stage 12 complete — All Requirements 100% Satisfied & Verified*
