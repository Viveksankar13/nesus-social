# Deployment Guide — Nexus Social

> **Status:** Skeleton — step-by-step instructions written in Stage 11 after deployment is complete.

---

## Architecture Summary

```
Browser
  ↓
Vercel (Next.js 14 — free tier)
  ├── /api/* → [rewrites] → Render FastAPI
  └── SSE direct connection → Render FastAPI
         ↓
Render (FastAPI — free tier)
  ├── Managed PostgreSQL (Render — free tier)
  ├── Gemini API (Google)
  └── SMTP (Gmail / Brevo / Resend)
```

---

## Prerequisites

- GitHub account + repository
- Render account (https://render.com) — free tier
- Vercel account (https://vercel.com) — free tier
- Google AI Studio account for Gemini API key
- SMTP credentials (one of):
  - Gmail App Password
  - Brevo API key (SMTP)
  - Resend SMTP credentials

---

## Step 1: Database (Render)

1. Log in to Render → **New → PostgreSQL**
2. Name: `socialmedia-db`
3. Region: Oregon (closest to free tier)
4. Plan: **Free**
5. Click **Create Database**
6. Copy the **Internal Database URL** (starts with `postgres://`) — you'll need this for the backend

---

## Step 2: Backend (Render)

*Full step-by-step instructions written in Stage 11 after Dockerfile is complete.*

High-level:
1. Create a new **Web Service** on Render
2. Connect to GitHub repository
3. Set **Environment: Docker**
4. Set all environment variables from `backend/.env.example`
5. Set `DATABASE_URL` from Step 1
6. Set `GEMINI_API_KEY` from Google AI Studio
7. Set `JWT_SECRET` to a random 32+ char string
8. Deploy → wait for health check to pass at `/health`
9. Run `alembic upgrade head` via Render Shell
10. Run `python scripts/seed.py` via Render Shell

---

## Step 3: Frontend (Vercel)

*Full step-by-step instructions written in Stage 11 after Vercel config is complete.*

High-level:
1. Import GitHub repository in Vercel
2. Framework: Next.js (auto-detected)
3. Root directory: `frontend`
4. Set environment variables:
   - `BACKEND_URL` = your Render backend URL
   - `NEXT_PUBLIC_BACKEND_URL` = your Render backend URL
   - `NEXT_PUBLIC_APP_NAME` = `Nexus Social`
5. Deploy

---

## Cold Start Warning (Render Free Tier)

> ⚠️ **Render free tier instances sleep after 15 minutes of inactivity.**
> The first request after sleep triggers a cold start that takes **~50 seconds**.
>
> **Impact:**
> - First login/API call after inactivity will be slow
> - SSE connection may fail on first attempt (client reconnects automatically)
>
> **Mitigation:**
> - Add a cron ping service (free) to keep the instance warm
> - Or upgrade to Render Starter ($7/month) for always-on

---

## CORS & SSE Configuration

The SSE stream (`/api/v1/notifications/stream`) connects **directly** from the browser to the Render backend, bypassing the Next.js rewrite (SSE doesn't work through rewrites in production).

**Configuration required:**
- `ALLOWED_ORIGINS` must include the Vercel URL (e.g., `https://nexus-social.vercel.app`)
- `NEXT_PUBLIC_BACKEND_URL` must be set to the Render backend URL (e.g., `https://socialmedia-backend.onrender.com`)
- FastAPI CORS middleware allows `NEXT_PUBLIC_BACKEND_URL` specifically for SSE

---

## Production Smoke Test Checklist

After deployment, verify:

- [ ] `GET https://your-backend.onrender.com/health` → `{"status":"ok"}`
- [ ] Frontend loads at Vercel URL
- [ ] Register a new user → email arrives (Mailpit locally / SMTP in prod)
- [ ] Verify email → can now log in
- [ ] Create a post → appears in feed
- [ ] Like a post → count increments
- [ ] Comment on a post → appears
- [ ] AI generate post → 3 variants appear
- [ ] Admin login → access `/admin` dashboard
- [ ] Admin receives login notification

---

## Railway Alternative

Railway (https://railway.app) is an alternative to Render:

| Feature | Render | Railway |
|---------|--------|---------|
| Free PostgreSQL | 1GB, sleeps | $5 credit/month |
| Cold starts | ~50s | ~10s |
| Deploy from Docker | Yes | Yes |
| Managed PostgreSQL | Yes | Yes |
| Pricing (paid) | $7/month (starter) | ~$5-10/month |

To deploy on Railway instead of Render:
1. Create a Railway project
2. Add PostgreSQL plugin
3. Deploy backend as Docker service
4. Set the same environment variables
5. Update `ALLOWED_ORIGINS` and `FRONTEND_URL` accordingly

No code changes required — Railway provides `DATABASE_URL` in the same `postgres://` format that the app auto-converts.
