# API Reference — Nexus Social

> **Status:** Skeleton — full endpoint documentation written progressively from Stage 2.
> Interactive docs available at `/docs` in development mode.

---

## Base URL

| Environment | URL |
|------------|-----|
| Local | `http://localhost:8000` |
| Production | `https://YOUR_RENDER_SERVICE.onrender.com` |

From the frontend, all requests go to `/api/*` (Next.js rewrite).

---

## Authentication

| Mechanism | Details |
|-----------|---------|
| Access token | `Authorization: Bearer <JWT>` (15-min expiry, in JS memory) |
| Refresh token | `refresh_token` httpOnly cookie (7-day expiry, rotates on use) |
| Stream token | Query param `?token=<short-lived-JWT>` (60s, SSE only) |

---

## Error Schema

All errors use a consistent schema:

```json
{
  "detail": "Human-readable error message"
}
```

Or for validation errors (422):

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error" }
  ]
}
```

---

## Health Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness probe |
| GET | `/ready` | None | Readiness probe (checks DB) |

---

## Authentication Endpoints (`/api/v1/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Register new user (accepts optional/required Student USN) |
| POST | `/api/v1/auth/verify-email` | None | Verify email token via Brevo SMTP link |
| POST | `/api/v1/auth/resend-verification` | None | Resend verification email |
| POST | `/api/v1/auth/login` | None | Login via Email, Username, or Student USN → tokens |
| POST | `/api/v1/auth/refresh` | Cookie | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Cookie | Revoke refresh token |
| POST | `/api/v1/auth/forgot-password` | None | Request password reset via Email or Student USN |
| POST | `/api/v1/auth/reset-password` | None | Reset password with token |
| GET | `/api/v1/auth/me` | Bearer | Get current user profile & USN |

*Detailed request/response schemas in `docs/stages/STAGE_02.md`*

---

## User Endpoints (`/api/v1/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users/{username}` | Optional | Public profile |
| PUT | `/api/v1/users/me` | Bearer | Update own profile |
| PUT | `/api/v1/users/me/password` | Bearer | Change password |

*Detailed schemas in `docs/stages/STAGE_03.md`*

---

## Post Endpoints (`/api/v1/posts`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/posts` | Optional | Feed (cursor paginated) |
| POST | `/api/v1/posts` | Bearer | Create post |
| GET | `/api/v1/posts/{id}` | Optional | Get post detail |
| PUT | `/api/v1/posts/{id}` | Bearer | Edit own post |
| DELETE | `/api/v1/posts/{id}` | Bearer | Delete own post |
| POST | `/api/v1/posts/{id}/like` | Bearer | Toggle like |

---

## Comment Endpoints (`/api/v1/comments`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/posts/{id}/comments` | Optional | List comments |
| POST | `/api/v1/posts/{id}/comments` | Bearer | Create comment |
| PUT | `/api/v1/comments/{id}` | Bearer | Edit own comment |
| DELETE | `/api/v1/comments/{id}` | Bearer | Delete own comment |

---

## Notification Endpoints (`/api/v1/notifications`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/notifications` | Bearer | List notifications |
| PUT | `/api/v1/notifications/{id}/read` | Bearer | Mark read |
| PUT | `/api/v1/notifications/read-all` | Bearer | Mark all read |
| POST | `/api/v1/notifications/stream-token` | Bearer | Get 60s stream token |
| GET | `/api/v1/notifications/stream` | Token (query) | SSE stream |

---

## AI Endpoints (`/api/v1/ai`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/ai/generate-post` | Bearer | Generate post variants |
| POST | `/api/v1/ai/summarize` | Bearer | Summarize post + comments |
| POST | `/api/v1/ai/chat` | Bearer | Chat message (streaming) |
| GET | `/api/v1/ai/sessions` | Bearer | List chat sessions |
| GET | `/api/v1/ai/sessions/{id}` | Bearer | Get session messages |
| POST | `/api/v1/ai/smart-replies` | Bearer | Get reply suggestions |

---

## Admin Endpoints (`/api/v1/admin`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/stats` | Admin | Dashboard stats |
| GET | `/api/v1/admin/charts` | Admin | Chart data |
| GET | `/api/v1/admin/users` | Admin | List users (paginated) |
| GET | `/api/v1/admin/users/{id}` | Admin | User detail |
| PUT | `/api/v1/admin/users/{id}/suspend` | Admin | Suspend/unsuspend |
| PUT | `/api/v1/admin/users/{id}/role` | Admin | Change role |
| DELETE | `/api/v1/admin/users/{id}` | Admin | Delete user |
| GET | `/api/v1/admin/posts` | Admin | All posts (paginated) |
| PUT | `/api/v1/admin/posts/{id}/hide` | Admin | Hide/restore post |
| DELETE | `/api/v1/admin/posts/{id}` | Admin | Delete post |
| GET | `/api/v1/admin/comments` | Admin | All comments |
| PUT | `/api/v1/admin/comments/{id}/hide` | Admin | Hide/restore comment |
| GET | `/api/v1/admin/moderation` | Admin | Moderation queue |
| PUT | `/api/v1/admin/moderation/{id}` | Admin | Review item |
| GET | `/api/v1/admin/activity` | Admin | Activity log |

---

## Cursor Pagination

Feed endpoints use keyset pagination for performance:

```
GET /api/v1/posts?cursor=<opaque_cursor>&limit=20
```

Response:
```json
{
  "items": [...],
  "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0x...",
  "total": null
}
```

The cursor encodes `(created_at, id)` as base64 JSON. `next_cursor` is `null` when there are no more pages.

Admin endpoints use offset pagination:
```
GET /api/v1/admin/users?page=1&limit=20&search=john
```

---

## Skill Swap Economy Endpoints (`/api/v1/swaps`)

### Taxonomy & Profile
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/swaps/taxonomy` | None | List canonical skills & categories |
| POST | `/api/v1/swaps/taxonomy/suggest` | User | Suggest new canonical skill |
| GET | `/api/v1/swaps/profile/me` | User | View own swap profile, availability, location |
| PUT | `/api/v1/swaps/profile/me` | User | Update skills, availability windows, coarse area |
| GET | `/api/v1/swaps/profile/{username}` | User | View public profile with distance bucket only |

### Listings & Discovery
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/swaps/listings` | User | Create listing (anti-money check) |
| GET | `/api/v1/swaps/listings` | User | Spatial discovery search with distance buckets |
| GET | `/api/v1/swaps/listings/me` | User | View own published listings |
| GET | `/api/v1/swaps/listings/{id}` | User | View listing details |
| PUT | `/api/v1/swaps/listings/{id}` | User | Update/pause/close own listing |
| POST | `/api/v1/swaps/listings/{id}/share` | User | Share listing into social feed |
| GET | `/api/v1/swaps/matches` | User | 5-criteria weighted matches with AI reasons |

### Requests & Sessions
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/swaps/requests` | User | Propose swap with up to 3 slots |
| GET | `/api/v1/swaps/requests` | User | View incoming/outgoing proposals |
| POST | `/api/v1/swaps/requests/{id}/accept` | User | Accept proposal & schedule 2-half session |
| POST | `/api/v1/swaps/requests/{id}/counter`| User | Counter-propose alternate slots/mode |
| POST | `/api/v1/swaps/requests/{id}/decline`| User | Decline swap proposal |
| POST | `/api/v1/swaps/requests/{id}/cancel` | User | Cancel outgoing proposal |
| GET | `/api/v1/swaps/sessions/{id}` | Participant | Session details, halves, Jitsi room URL |
| GET | `/api/v1/swaps/sessions/{id}/ics` | Participant | Download `.ics` calendar invite |
| POST | `/api/v1/swaps/sessions/{id}/complete`| Participant | Confirm half completion |
| POST | `/api/v1/swaps/sessions/{id}/dispute` | Participant | Report dispute / no-show |
| GET | `/api/v1/swaps/sessions/{id}/messages`| Participant | Read session chat |
| POST | `/api/v1/swaps/sessions/{id}/messages`| Participant | Send message to session chat |

### Reviews, Trust & Safety
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/swaps/reviews` | Participant | Submit blind mutual review |
| GET | `/api/v1/swaps/trust/{user_id}` | User | View trust score & badges |
| POST | `/api/v1/swaps/reports` | User | Report user, listing, or session |
| POST | `/api/v1/swaps/blocks` | User | Block user |
| DELETE | `/api/v1/swaps/blocks/{user_id}` | User | Unblock user |

### AI Productivity Assistants
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/swaps/sessions/{id}/ai-plan` | Participant | Generate 30-min structured lesson agenda |
| POST | `/api/v1/swaps/sessions/{id}/ai-recap`| Participant | Convert rough notes into action takeaways |
| GET | `/api/v1/swaps/fairness-advice` | User | Reciprocity ledger balance guidance |

### Admin & Cron Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/swaps/stats` | Admin | Skill Swap KPIs & analytics |
| GET | `/api/v1/admin/swaps/listings` | Admin | Moderation directory of swap listings |
| GET | `/api/v1/admin/swaps/disputes` | Admin | Disputes and no-show triage queue |
| POST | `/api/v1/admin/swaps/disputes/{id}/resolve` | Admin | Resolve dispute & adjust trust score |
| POST | `/api/v1/admin/swaps/taxonomy/approve` | Admin | Approve pending user skills |
| POST | `/api/v1/admin/swaps/taxonomy/merge` | Admin | Merge skill synonyms into canonical slug |
| POST | `/api/v1/internal/jobs/{job_name}` | `X-Cron-Secret` | Execute scheduled cron maintenance |

