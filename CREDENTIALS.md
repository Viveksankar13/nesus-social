# 🔐 Nexus Social — Platform Credentials & Test Accounts

This document contains all default seed accounts, credentials, and access roles for **Nexus Social**.

---

## 🌐 Live URLs

- **Frontend Application (Vercel):** [https://nesus-social.vercel.app](https://nesus-social.vercel.app)
- **Login Page:** [https://nesus-social.vercel.app/login](https://nesus-social.vercel.app/login)
- **Backend API (Render):** [https://nesus-social-backend.onrender.com](https://nesus-social-backend.onrender.com)
- **API Documentation (Swagger):** [https://nesus-social-backend.onrender.com/docs](https://nesus-social-backend.onrender.com/docs)
- **Database Engine:** Supabase PostgreSQL

---

## 👑 1. Primary Administrator Account

The platform administrator has access to the `/admin` console, user management, listings moderation, activity logs, and dispute triage.

| Property | Value |
| :--- | :--- |
| **Role** | `admin` (Platform Administrator) |
| **Username** | `admin` |
| **Email** | `admin@nexussocial.edu` |
| **Password** | `AdminPassword@123` |
| **Default Dashboard** | `/admin` |

---

## 👤 2. Primary Student / Developer Account

| Property | Value |
| :--- | :--- |
| **Role** | `user` |
| **Username** | `vivek13` |
| **Email** | `viveksankar13@gmail.com` |
| **Student USN** | `24MSRCI045` |
| **Password** | `DemoPassword123!` |
| **Default Dashboard** | `/feed` |

---

## 👥 3. Demo Accounts (Skill Swap & Social Feed)

All demo accounts share the common password: **`DemoPassword123!`**

You can log in using either the **Username**, **Email**, or **Student USN**.

| Display Name | Username | Email | Student USN | Password | Bio / Skills |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dr. Sarah Chen** | `sarah_chen` | `sarah.chen@example.com` | `1MS21CS001` | `DemoPassword123!` | AI & Neural Networks |
| **Marcus Vance** | `marcus_v` | `marcus.vance@example.com` | `1RV20EC045` | `DemoPassword123!` | Full-Stack (Next.js + FastAPI) |
| **Elena Rostova** | `elena_designs` | `elena.rostova@example.com` | `4NI21IS020` | `DemoPassword123!` | Design Systems & UI/UX |
| **Devon Miles** | `devon_codes` | `devon.miles@example.com` | `1PE19CS088` | `DemoPassword123!` | Cloud & Kubernetes |
| **Aiko Tanaka** | `aiko_t` | `aiko.tanaka@example.com` | `1BM22AI012` | `DemoPassword123!` | Data Science & Generative Art |

---

## 🛠️ How to Reset Any Password

If you ever need to reset a password for any user in the Supabase database, run this command from the `backend/` directory:

```powershell
.\.venv\Scripts\python.exe -c "import asyncio; from app.db.session import async_session_factory; from app.models.user import User; from app.core.security import hash_password; from sqlalchemy import select; async def reset(): async with async_session_factory() as s: u = (await s.execute(select(User).where(User.username == 'USERNAME_HERE'))).scalar_one_or_none(); u.hashed_password = hash_password('NEW_PASSWORD_HERE'); await s.commit(); print('Password updated!'); asyncio.run(reset())"
```
*(Replace `USERNAME_HERE` and `NEW_PASSWORD_HERE` with your chosen values).*
