# 🌐 Nexus Social — AI-Powered Social Media Platform

> A full-stack, production-ready social media platform powered by Google Gemini AI.
> Built with Next.js 14, FastAPI, PostgreSQL, and real-time SSE notifications.

[![CI](https://github.com/YOUR_USERNAME/nexus-social/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/nexus-social/actions/workflows/ci.yml)

## ✨ Features

- **Authentication & University Identity** — Register and login using Email, Username, or **Student USN (University Seat Number / College ID)**, Argon2id hashing, 15-min memory JWTs, rotating httpOnly refresh tokens with reuse family revocation.
- **Brevo SMTP Support** — Automated port 587 STARTTLS / port 465 SSL email delivery for email verification, password reset, and welcome notifications.
- **Social Feed** — Cursor-paginated infinite scroll, posts (≤1000 chars) with image attachments, unique likes with optimistic UI, and threaded one-level comment replies.
- **Real-time Notifications** — Server-Sent Events (SSE) with 60-second single-use stream tokens, live notification bell, and real-time admin login alerts.
- **AI Features** (Google Gemini 2.5 Flash):
  - Post generation & refinement (3 tone variants: Casual, Professional, Funny, Inspirational)
  - Thread summarization with sentiment analysis (triggers on ≥3 comments)
  - Conversational AI assistant (streaming widget, persisted sessions)
  - Automated background content moderation (structured JSON classification)
  - Contextual smart reply suggestions (3 quick-reply pills)
- **Admin Console** — Executive analytics dashboard, Recharts 30-day time-series charts, user management (search, role update, suspend, delete), content moderation queue, and immutable activity audit logs.
- **Security & Hardening** — Full OWASP defensive headers (CSP, HSTS, X-Content-Type, X-Frame-Options), strict CORS allowlist, rate limiting (`slowapi`), non-root Docker container (`appuser:1001`), and comprehensive secret scanning.

## 🏗️ Architecture

```
Browser → Vercel (Next.js) → [/api/* rewrites] → Render (FastAPI) → PostgreSQL
                                                ↘ Gemini API
                                                ↘ SMTP (email)
Browser → [SSE direct] → Render (FastAPI) [CORS]
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| State | TanStack Query, React Hook Form + Zod |
| Motion | Framer Motion, lucide-react, Recharts |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Auth | Argon2id, PyJWT, rotating httpOnly refresh tokens |
| AI | Google Gemini 2.5 Flash via google-genai SDK |
| Email | aiosmtplib + Jinja2 templates |
| Database | PostgreSQL 16 (UUID PKs, proper FKs, feed indexes) |
| Testing | pytest + httpx (backend), Playwright E2E (frontend) |
| CI | GitHub Actions |
| Hosting | Vercel (frontend) + Render (backend + DB) |

## 🚀 Local Development

### Prerequisites

- Docker Desktop (for PostgreSQL + Mailpit)
- Python 3.12+
- Node.js 20+
- Git

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/nexus-social.git
cd nexus-social

# Backend env
cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set GEMINI_API_KEY

# Frontend env
cp frontend/.env.example frontend/.env.local
```

### 2. Start local services

```bash
docker-compose up -d
# PostgreSQL on :5432, Mailpit UI on :8025, Mailpit SMTP on :1025
```

### 3. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed admin + optional demo data
python scripts/seed.py --demo

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### 5. Verify

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/health
- API docs: http://localhost:8000/docs (development only)
- Mailpit: http://localhost:8025

## 🔑 Environment Variables

See [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example) for full documentation.

## 🗄️ Database

```bash
# Create a new migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v --cov=app tests/

# Frontend lint + type-check
cd frontend
npm run lint
npx tsc --noEmit

# E2E smoke test (requires running app)
cd frontend
npx playwright test
```

## 🚢 Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for complete step-by-step instructions.

**Summary:**
- Backend: Render (Docker web service) via `render.yaml` blueprint
- Frontend: Vercel (connects to GitHub, auto-deploys on push)
- Database: Render Managed PostgreSQL

## 👤 Admin Access

The admin account is seeded from environment variables (`ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`). Never hardcode credentials. Set these in your deployment environment.

## 📚 Documentation

- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [ER Diagram](docs/ER_DIAGRAM.md)
- [API Reference](docs/API.md)
- [AI Integration](docs/AI_INTEGRATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [System Documentation PDF](docs/pdf/SYSTEM_DOCUMENTATION.pdf) *(generated)*

## ⚠️ Known Limitations

- Render free tier has cold-start delays (~50s) after inactivity
- SSE uses in-process pub/sub (single instance); see `AI_INTEGRATION.md` for Redis upgrade path
- Image uploads are URL-based (no file storage in v1)

## 📄 License

MIT — see [LICENSE](LICENSE)
