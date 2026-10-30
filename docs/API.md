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
| POST | `/api/v1/auth/register` | None | Register new user |
| POST | `/api/v1/auth/verify-email` | None | Verify email token |
| POST | `/api/v1/auth/resend-verification` | None | Resend verification email |
| POST | `/api/v1/auth/login` | None | Login → tokens |
| POST | `/api/v1/auth/refresh` | Cookie | Rotate refresh token |
| POST | `/api/v1/auth/logout` | Cookie | Revoke refresh token |
| POST | `/api/v1/auth/forgot-password` | None | Request password reset |
| POST | `/api/v1/auth/reset-password` | None | Reset password |
| GET | `/api/v1/auth/me` | Bearer | Get current user |

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
