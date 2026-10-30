# Nexus Social — Production Deployment Guide

> **Target Environments:**
> - **Backend API & Database:** [Render](https://render.com) (Docker Web Service + Managed PostgreSQL)
> - **Frontend Application:** [Vercel](https://vercel.com) (Next.js 14 App Router)
> - **Email Delivery:** [Brevo](https://www.brevo.com) (SMTP Relay via `smtp-relay.brevo.com`)
> - **AI Engine:** Google Gemini API (`gemini-2.5-flash`)

---

## 1. Production Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │                 User Browser                 │
                  └──────┬────────────────────────────────┬──────┘
                         │                                │
        1. SSR / Static  │               2. Direct SSE    │
        & /api/* Rewrite │                  Connection    │
                         ▼                                │
  ┌──────────────────────────────────────────────┐        │
  │            Vercel Edge Platform              │        │
  │           (Next.js 14 App Router)            │        │
  │  • First-party cookie handling               │        │
  │  • Automatic API rewrite: /api/*             │        │
  └──────────────────────┬───────────────────────┘        │
                         │                                │
            Reverse      │                                │
            Proxy        ▼                                ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                 Render Web Service (Docker)                  │
  │                  (FastAPI + Uvicorn)                         │
  │  • Non-root container (`appuser:1001`)                       │
  │  • Pre-deploy migrations (`alembic upgrade head`)            │
  │  • Security headers (CSP, HSTS, X-Content, X-Frame)          │
  │  • Multi-identifier Student USN / Email / Username auth      │
  └───────┬──────────────────────┬───────────────────────┬───────┘
          │                      │                       │
          ▼                      ▼                       ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────┐
│ Render PostgreSQL│  │  Brevo SMTP Relay  │  │ Google Gemini AI │
│ (Managed AsyncPG)│  │ (smtp-relay.brevo) │  │(gemini-2.5-flash)│
└──────────────────┘  └────────────────────┘  └──────────────────┘
```

---

## 2. Environment Variables Reference

### 2.1 Backend Environment Variables (Render)

| Variable | Required | Example / Default | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **Yes** | `production` | Enables strict validation, HSTS, and suppresses stack traces |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://user:pass@host/db` | Render PostgreSQL URL (auto-converted from `postgres://`) |
| `JWT_SECRET` | **Yes** | *32+ random hex characters* | Cryptographic signing secret for JWT access tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_MINUTES` | No | `15` | Short-lived access token expiry |
| `REFRESH_TOKEN_DAYS` | No | `7` | Rotating refresh token expiry window |
| `FRONTEND_URL` | **Yes** | `https://nexus-social.vercel.app` | Canonical public URL of the Vercel frontend |
| `ALLOWED_ORIGINS` | **Yes** | `https://nexus-social.vercel.app` | CORS allowlist for direct SSE connections & API requests |
| `SMTP_HOST` | **Yes** | `smtp-relay.brevo.com` | Brevo SMTP relay hostname |
| `SMTP_PORT` | **Yes** | `587` | Brevo SMTP submission port (with STARTTLS) |
| `SMTP_USERNAME` | **Yes** | `your-brevo-login@domain.com` | Brevo account email address |
| `SMTP_PASSWORD` | **Yes** | `xsmtpsib-...` | Brevo SMTP master key or API secret |
| `SMTP_FROM_EMAIL` | **Yes** | `noreply@yourdomain.com` | Verified sender address in Brevo console |
| `SMTP_FROM_NAME` | No | `Nexus Social` | Display sender name for notifications |
| `SMTP_USE_TLS` | No | `true` | Enables TLS transport security |
| `GEMINI_API_KEY` | **Yes** | `AIzaSy...` | Google AI Studio API Key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant |
| `AI_DAILY_QUOTA` | No | `100` | Maximum daily AI requests per user |
| `MODERATION_FAIL_MODE` | No | `open` | Fail mode if AI moderation quota exhausted |
| `ADMIN_EMAIL` | **Yes** | `admin@nexussocial.edu` | Seed superadmin email address |
| `ADMIN_USERNAME` | **Yes** | `admin` | Seed superadmin username |
| `ADMIN_PASSWORD` | **Yes** | *Strong password (min 8 chars)* | Seed superadmin initial password |
| `SENTRY_DSN` | No | `https://...@sentry.io/...` | Optional Sentry error monitoring DSN |

### 2.2 Frontend Environment Variables (Vercel)

| Variable | Required | Example | Description |
| :--- | :---: | :--- | :--- |
| `BACKEND_URL` | **Yes** | `https://nexus-social-backend.onrender.com` | Internal target for Next.js server `/api/*` rewrites |
| `NEXT_PUBLIC_BACKEND_URL` | **Yes** | `https://nexus-social-backend.onrender.com` | Target for direct browser SSE connections (`/notifications/stream`) |
| `NEXT_PUBLIC_APP_NAME` | No | `Nexus Social` | Application title display name |

---

## 3. Step 1: Deploy Backend & Database on Render

### Method A: Automated Deployment via Blueprint (`render.yaml`)

1. Push your repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), navigate to **Blueprints** → **New Blueprint Instance**.
3. Connect your repository. Render automatically reads `render.yaml` and sets up:
   - PostgreSQL database: `nexus-social-db`
   - Web Service: `nexus-social-backend` (Docker runtime)
4. Fill in the required dashboard secrets:
   - `GEMINI_API_KEY`: Your key from Google AI Studio.
   - `SMTP_USERNAME` & `SMTP_PASSWORD`: Your Brevo SMTP credentials.
   - `SMTP_FROM_EMAIL`: Your verified sender address.
   - `ADMIN_EMAIL` & `ADMIN_PASSWORD`: Credentials for the administrator account.
5. Click **Apply**. Render provisions the database, builds the Docker container, executes `alembic upgrade head`, and launches the web service.

---

### Method B: Manual Service Creation

1. **Create Managed PostgreSQL Database**:
   - Go to **New** → **PostgreSQL**.
   - Name: `nexus-social-db`.
   - Database: `nexussocial`.
   - User: `nexussocial`.
   - Region: `Oregon` (Free tier).
   - Click **Create Database**.
   - Copy the **Internal Database URL** (`postgres://...`).
2. **Create Docker Web Service**:
   - Go to **New** → **Web Service**.
   - Select your GitHub repository.
   - Runtime: **Docker**.
   - Dockerfile Path: `./backend/Dockerfile`.
   - Docker Context: `./backend`.
   - Region: `Oregon`.
   - Health Check Path: `/health`.
3. **Configure Environment Variables**:
   - Add all environment variables listed in Section 2.1.
   - For `DATABASE_URL`, paste the database connection string. (Nexus Social automatically transforms `postgres://` into `postgresql+asyncpg://`).
4. **Pre-Deploy Migrations**:
   - Set **Pre-Deploy Command** to: `alembic upgrade head`.
5. **Deploy**:
   - Click **Create Web Service**.
   - Wait for the build and deployment to succeed. The health check at `https://<YOUR-RENDER-URL>/health` will return `{"status":"ok"}`.

---

## 4. Step 2: Seed Administrator & Student Demo Data

Once the Render service is running, populate the database with the seed administrator and realistic student profiles:

1. In the Render Dashboard, open `nexus-social-backend` → **Shell**.
2. Run the seed script:
   ```bash
   # Seed default admin only
   python scripts/seed.py

   # Or seed admin + realistic university student profiles with USNs & sample posts
   python scripts/seed.py --demo
   ```
3. Verification output:
   ```
   Checking for admin account (admin@nexussocial.edu)...
   Creating primary admin account...
   Created primary admin @admin (admin@nexussocial.edu)
   Created 4 demo student users with official University Seat Numbers:
     - @aarav_sharma (1MS21CS001)
     - @priya_patel (1RV20EC045)
     - @rohan_verma (1BMS22IS089)
     - @ananya_iyer (1PES21ME032)
   Created demo posts, comments, likes, and notifications.
   Database seeding completed successfully!
   ```

---

## 5. Step 3: Deploy Frontend on Vercel

1. Log in to [Vercel](https://vercel.com) and click **Add New...** → **Project**.
2. Select your GitHub repository.
3. In project configuration:
   - **Framework Preset**: Next.js (auto-detected).
   - **Root Directory**: Click edit and set to `frontend`.
4. Configure Environment Variables:
   - `BACKEND_URL`: `https://nexus-social-backend.onrender.com`
   - `NEXT_PUBLIC_BACKEND_URL`: `https://nexus-social-backend.onrender.com`
   - `NEXT_PUBLIC_APP_NAME`: `Nexus Social`
5. Click **Deploy**.
6. Once deployed, copy your production Vercel domain (e.g. `https://nexus-social.vercel.app`).

---

## 6. Step 4: Finalize Cross-Origin Integration

Now that the Vercel URL is known, update the Render backend to permit secure communication and cookies:

1. In Render Dashboard → `nexus-social-backend` → **Environment**.
2. Set:
   - `FRONTEND_URL`: `https://nexus-social.vercel.app`
   - `ALLOWED_ORIGINS`: `https://nexus-social.vercel.app`
3. Click **Save Changes**. Render will automatically redeploy the service.

---

## 7. Brevo SMTP Email Relay Setup

To ensure deliverability of password resets and university registration emails:

1. Register at [Brevo](https://www.brevo.com).
2. Go to **Settings** → **Senders & IP** → Add and verify your sender email (e.g., `noreply@yourdomain.com` or your institutional email).
3. Go to **SMTP & API** → **SMTP** tab:
   - **SMTP Server**: `smtp-relay.brevo.com`
   - **Port**: `587`
   - **Login**: Your registered Brevo account email
   - **Password**: Generate an SMTP Master Key or API Key.
4. Input these credentials into the Render environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`).
5. Nexus Social's [`email_service.py`](file:///d:/Code/Social_Media/backend/app/services/email_service.py) automatically uses Port 587 with `STARTTLS` to guarantee TLS encryption.

---

## 8. Post-Deployment Smoke Test Protocol

Execute the following verification checklist to confirm system health:

### 1. Backend Probes
```bash
# Health probe
curl -i https://nexus-social-backend.onrender.com/health
# Expected: HTTP/2 200 OK -> {"status":"ok","environment":"production"}

# Readiness probe (verifies database pool)
curl -i https://nexus-social-backend.onrender.com/ready
# Expected: HTTP/2 200 OK -> {"status":"ready","database":"connected"}

# Security headers check
curl -I https://nexus-social-backend.onrender.com/health
# Expected:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Content-Security-Policy: default-src 'self'...
```

### 2. Frontend User Journey
1. **Visit Landing Page**: Navigate to `https://nexus-social.vercel.app/`. Ensure brand graphics, hero section, and AI feature pills load without layout shift.
2. **Student USN Registration**:
   - Click **Get Started**.
   - Register with:
     - Name: `Student Test`
     - Email: `student@test.edu`
     - Student USN / College ID: `1MS22CS999`
     - Username: `student_test`
     - Password: `Password@123`
   - Verify activation email arrives in your inbox with Student USN displayed in the email template.
3. **Multi-Identifier Login**:
   - Log in using Student USN `1MS22CS999` and password.
   - Verify successful redirect to `/feed`.
4. **Social & AI Interaction**:
   - Open post composer, click **AI Assist**, select "Inspirational" tone, and generate 3 variants.
   - Select variant and post.
   - Like the post and write a comment.
5. **Forgot Password Recovery via USN**:
   - Log out, navigate to `/forgot-password`.
   - Enter Student USN `1MS22CS999`.
   - Verify password reset email arrives via Brevo SMTP containing the student's USN and token link.
6. **Admin Console**:
   - Log in with seed admin account (`admin`).
   - Navigate to `/admin`.
   - Verify 6 KPI cards, 30-day signup/post charts, and user directory containing student accounts with USN badges.

---

## 9. Troubleshooting & Operational Notes

### A. Render Free-Tier Cold Starts
- **Behavior**: On Render's free tier, the web service automatically spins down after 15 minutes of inactivity. The next incoming request triggers a cold container start taking approximately **45–50 seconds**.
- **User Impact**: First API request or login will have high latency; browser SSE connection may momentarily retry.
- **Solution**: Set up a free external ping monitor (e.g. [UptimeRobot](https://uptimerobot.com) or [Cron-Job.org](https://cron-job.org)) hitting `https://<YOUR-RENDER-URL>/health` every 10 minutes to keep the container continuously warm.

### B. CORS / Cross-Site Cookie Misconfiguration
- **Symptoms**: `401 Unauthorized` on `/api/v1/auth/refresh` or browser console CORS errors.
- **Resolution**:
  - Ensure all API calls from Next.js use relative paths `/api/*` so requests are proxied first-party through Vercel rewrites.
  - Verify `ALLOWED_ORIGINS` on Render contains the exact Vercel URL with no trailing slash (e.g., `https://nexus-social.vercel.app`).

### C. Direct SSE Streaming Connection
- Next.js Edge rewrites buffer Server-Sent Events. The frontend automatically establishes SSE connections directly to `NEXT_PUBLIC_BACKEND_URL/api/v1/notifications/stream`. Ensure `NEXT_PUBLIC_BACKEND_URL` is set to the full Render backend URL and that Render's `ALLOWED_ORIGINS` includes the Vercel domain.
