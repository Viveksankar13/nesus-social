# 🌐 Nexus Social — Comprehensive Codebase & Architecture Guide

> An exhaustive technical manual explaining every framework, library, function, database relationship, and network connection across the Nexus Social platform.

---

## 📑 Table of Contents
1. [System Overview & High-Level Architecture](#1-system-overview--high-level-architecture)
2. [Frameworks & Technologies Used (Why & Purpose)](#2-frameworks--technologies-used-why--purpose)
3. [Network Topology & Communication Flow](#3-network-topology--communication-flow)
4. [Backend Deep Dive (Modules & Functions)](#4-backend-deep-dive-modules--functions)
   - [Core & Security](#41-core--security-backendappcore)
   - [Database Layer & Models](#42-database-layer--models-backendappdb--backendappmodels)
   - [Pydantic Schemas](#43-pydantic-validation-schemas-backendappschemas)
   - [Business Logic Services](#44-business-logic-services-backendappservices)
   - [API Routers](#45-api-routers-backendappapiv1)
5. [Frontend Deep Dive (Components & Architecture)](#5-frontend-deep-dive-components--architecture)
   - [API Client & Interceptor](#51-api-client--interceptor-frontendsrclibapi-clientts)
   - [Authentication Context](#52-authentication-context-frontendsrccontextsauth-contexttsx)
   - [AI Support & Chat Widget](#53-ai-chat-widget-frontendsrccomponentsaiai-chat-widgettsx)
   - [Pages & Routing Structure](#54-pages--routing-structure)
6. [End-to-End Operational Workflows](#6-end-to-end-operational-workflows)
   - [Authentication & Rotating Refresh Tokens](#61-authentication--session-lifecycle)
   - [AI Customer Support & Text Streaming](#62-ai-support-chat-streaming)
   - [Post Creation & Background AI Moderation](#63-post-creation--ai-moderation)
   - [Real-Time Notifications via SSE](#64-real-time-notifications-via-sse)
7. [Database Architecture & Switching (SQLite ⇄ PostgreSQL)](#7-database-architecture--switching-sqlite--postgresql)

---

## 1. System Overview & High-Level Architecture

Nexus Social is built as a modern, decoupled full-stack application:
* **Frontend:** Next.js 14 (App Router, Server & Client Components) deployed on Vercel or run locally on port `3000`.
* **Backend:** FastAPI (Python 3.12, fully asynchronous with `asyncio`) run via Uvicorn on port `8000`.
* **Database:** SQLite (local development zero-overhead) or PostgreSQL 16 (production) accessed through SQLAlchemy 2.0 async ORM.
* **External AI Engine:** Google Gemini 2.5 Flash via the official `google-genai` SDK.
* **Email Gateway:** Brevo (Sendinblue) transactional SMTP relay via port `587` with STARTTLS.

```mermaid
flowchart TD
    User["👤 Browser Client (React / Next.js)"]
    
    subgraph Frontend["Frontend Layer (Next.js - Port 3000)"]
        UI["shadcn/ui + Tailwind CSS"]
        AuthCtx["AuthContext & In-Memory JWT"]
        APIClient["API Client (Fetch Wrapper)"]
        NextRewrites["Next.js /api/* Rewrites Proxy"]
    end
    
    subgraph Backend["Backend Layer (FastAPI - Port 8000)"]
        FastAPI["FastAPI Application"]
        Middlewares["Security Headers + CORS + Limiter"]
        Routers["API Routers (/auth, /posts, /ai, /admin)"]
        Services["Services (Auth, AI, Email, PubSub)"]
    end
    
    subgraph Storage["Persistence & External Services"]
        DB[("Database (SQLite / PostgreSQL)")]
        Gemini["✨ Google Gemini 2.5 Flash API"]
        Brevo["📧 Brevo SMTP Relay (Port 587)"]
    end
    
    User --> UI
    UI --> AuthCtx
    AuthCtx --> APIClient
    APIClient -->|/api/* Requests| NextRewrites
    NextRewrites -->|http://localhost:8000/api/*| FastAPI
    APIClient -.->|Direct SSE Stream| FastAPI
    
    FastAPI --> Middlewares
    Middlewares --> Routers
    Routers --> Services
    Services --> DB
    Services --> Gemini
    Services --> Brevo
```

---

## 2. Frameworks & Technologies Used (Why & Purpose)

### 2.1 Frontend Stack

| Library / Tool | Purpose in Project | Why Chosen? |
| :--- | :--- | :--- |
| **Next.js 14 (App Router)** | Primary Web Framework | Provides server-side rendering, routing layout isolation (`(auth)` vs `(app)`), built-in reverse proxy (`next.config.mjs` rewrites), and optimized production builds. |
| **TypeScript** | Type Safety | Eliminates runtime errors across complex data models (posts, nested comments, user profiles, AI streams). |
| **Tailwind CSS** | Styling Engine | Utility-first CSS allowing rapid development of responsive, accessible dark/light themes without CSS file sprawl. |
| **shadcn/ui & Radix UI** | Headless UI Components | Unstyled accessible primitives (dialogs, dropdowns, toasts, cards) that give complete design control with zero third-party branding. |
| **TanStack Query (React Query)** | Server State Management | Automatically handles caching, cursor pagination, background re-fetching, and optimistic UI updates (e.g. instant post likes). |
| **React Hook Form + Zod** | Form Handling & Validation | Client-side schema validation (email formats, password strength, Student USN patterns) with minimal re-renders. |
| **Lucide React** | Icons | Consistent modern icon set used throughout feed actions, navigation, badges, and AI widgets. |
| **Recharts** | Data Visualizations | Renders interactive analytics charts (30-day active users, post frequency, moderation activity) on the `/admin` dashboard. |
| **Framer Motion** | Micro-Animations | Smooth transitions for modals, feed insertions, and floating launcher buttons. |

### 2.2 Backend Stack

| Library / Tool | Purpose in Project | Why Chosen? |
| :--- | :--- | :--- |
| **FastAPI** | REST & Streaming API Engine | Extremely high performance, built-in async support, automatic OpenAPI/Swagger documentation, and native Pydantic schema validation. |
| **Uvicorn** | ASGI Web Server | Production-grade lightning-fast ASGI server that runs the asynchronous Python event loop. |
| **SQLAlchemy 2.0 (Async)** | Object-Relational Mapper (ORM) | Industry standard Python ORM. Version 2.0 uses modern typed mappings (`Mapped[...]`), async sessions, and supports both SQLite and PostgreSQL. |
| **Alembic** | Database Migrations | Version-controlled schema migrations that safely track alterations (e.g., adding the Student USN column). |
| **Pydantic v2** | Data Validation & Serialization | Rust-accelerated schema validation for all HTTP request bodies and response formatting. |
| **Argon2id (`argon2-cffi`)** | Password Hashing | Winner of the Password Hashing Competition; state-of-the-art memory-hard algorithm immune to GPU cracking. |
| **PyJWT** | JWT Token Issuance & Verification | Generates cryptographic JSON Web Tokens for stateless access authorization and single-use stream tokens. |
| **aiosmtplib & Jinja2** | Asynchronous Email Delivery | Sends HTML emails asynchronously over non-blocking sockets without blocking the FastAPI event loop during HTTP requests. |
| **SlowAPI** | Rate Limiting | Protects sensitive auth and AI endpoints against brute force and denial of service. |
| **Google GenAI SDK (`google-genai`)** | AI Features Integration | Official Google SDK for Gemini 2.5 Flash supporting text generation, structured JSON mode, and streaming. |

---

## 3. Network Topology & Communication Flow

### The First-Party Cookie Proxy Pattern
A critical security challenge in modern web apps is managing `httpOnly` refresh cookies across different domains (e.g., frontend on Vercel and backend on Render).
Nexus Social solves this via **Next.js API Rewrites** (`frontend/next.config.mjs`):

```javascript
async rewrites() {
  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  return [
    {
      source: "/api/:path*",
      destination: `${backendUrl}/api/:path*`,
    },
  ];
}
```

1. The browser makes requests to `http://localhost:3000/api/v1/auth/login`.
2. Next.js internally forwards the request to `http://localhost:8000/api/v1/auth/login`.
3. To the browser, the domain is strictly `localhost:3000` (First-Party).
4. The `httpOnly` `refresh_token` cookie is set on the first-party domain, preventing cross-site cookie blocking and eliminating CORS cookie vulnerabilities.

---

## 4. Backend Deep Dive (Modules & Functions)

### 4.1 Core & Security (`backend/app/core/`)

* **`config.py` (`Settings`)**:
  * Loads and validates environment variables from `.env` via Pydantic `BaseSettings`.
  * Automatically fixes PostgreSQL scheme prefixes (`postgres://` → `postgresql+asyncpg://`) for Render compatibility.
  * Validates security keys in production (rejecting default development secrets).

* **`security.py`**:
  * `hash_password(password: str) -> str`: Hashes plain passwords using Argon2id.
  * `verify_password(plain: str, hashed: str) -> bool`: Constant-time hash verification.
  * `validate_password_strength(password: str) -> tuple[bool, str]`: Enforces 8+ characters, uppercase, lowercase, numbers, and special symbols.

* **`tokens.py`**:
  * `create_access_token(user_id, role) -> str`: Issues short-lived (15-min) JWT access tokens.
  * `create_stream_token(user_id) -> str`: Issues 60-second single-use tokens for SSE streams.
  * `generate_random_token(bytes: int) -> tuple[str, str]`: Generates raw cryptographic tokens and their SHA-256 hashes for email verification and password resets.

* **`security_headers.py` (`SecurityHeadersMiddleware`)**:
  * Injects OWASP defensive headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, Content Security Policy).

---

### 4.2 Database Layer & Models (`backend/app/db/` & `backend/app/models/`)

* **`db/session.py`**:
  * Configures `create_async_engine()` and `async_sessionmaker`.
  * Provides the FastAPI dependency `get_db()`, yielding an async database transaction that auto-commits on success and rolls back on exception.

* **`models/user.py` (`User`)**:
  * Represents registered accounts: `email`, `username`, `usn` (Student University Seat Number), `hashed_password`, `role` (`user` vs `admin`), `is_verified`, `is_suspended`.
  * Includes relationships to posts, comments, likes, notifications, and refresh tokens.

* **`models/post.py` (`Post`)**:
  * Feed content: `content` (up to 1,000 chars), `image_url`, `author_id`, `is_hidden` (moderation state).

* **`models/comment.py` (`Comment`)**:
  * Threaded discussions: `post_id`, `author_id`, `parent_id` (enables 1-level nested replies), `content`.

* **`models/notification.py` (`Notification`)**:
  * In-app notifications: `user_id`, `type` (`like`, `comment`, `reply`, `admin_login`, `friend_request`, `friend_accepted`), `payload` (JSON/JSONB with actor metadata).

* **`models/friendship.py` (`Friendship`)**:
  * User-to-user connections: `sender_id`, `receiver_id`, `status` (`pending`, `accepted`, `rejected`).
  * Unique constraint on `(sender_id, receiver_id)` ensuring single relationship records between user pairs.

* **`models/message.py` (`Conversation`, `DirectMessage`)**:
  * `Conversation`: Canonical 1-on-1 thread between two users (`user1_id`, `user2_id`), indexed with order-invariant uniqueness to prevent duplicate threads.
  * `DirectMessage`: Message instances within a thread: `conversation_id`, `sender_id`, `content` (up to 5,000 characters), `is_read`, and timestamps. Cascades on conversation deletion.

* **`models/ai.py` (`AIChatSession`, `AIChatMessage`, `AIUsageLog`)**:
  * Persists user conversational support sessions, message histories (`user` vs `assistant`), and rate-quota usage telemetry.

---

### 4.3 Pydantic Validation Schemas (`backend/app/schemas/`)

* **`schemas/auth.py`**:
  * `LoginRequest`: Validates sign-in attempts. Features a `@model_validator(mode="before")` that seamlessly accepts both `email_or_username` and `username_or_email`.
  * `RegisterRequest`: Validates username patterns, password complexity, and college USN formatting.
  * `ForgotPasswordRequest` & `ResetPasswordRequest`: Validates recovery tokens and new passwords.

* **`schemas/ai.py`**:
  * `PostGenerateRequest` & `PostGenerateResponse`: Schema for 3 tone-varied post alternatives.
  * `AIChatMessageRequest`: Validates chat prompts and controls streaming toggle (`stream: bool`).

---

### 4.4 Business Logic Services (`backend/app/services/`)

* **`auth_service.py` (`AuthService`)**:
  * `register(db, data)`: Creates unverified user, creates token in `email_tokens`, dispatches verification email.
  * `login(db, req, ...)`: Resolves user by **Email, Username, or Student USN**, verifies password, records rotating refresh token family, and detects replay reuse attacks.
  * `forgot_password(db, identifier)`: Resolves account, creates single-use reset token, sends email.
  * `reset_password(db, token, new_password)`: Verifies token, updates password hash, revokes all active refresh tokens.

* **`email_service.py` (`EmailService`)**:
  * Asynchronously compiles Jinja2 HTML templates (`welcome.html`, `reset_password.html`, `verify_email.html`).
  * Negotiates TLS / STARTTLS with Brevo (`smtp-relay.brevo.com:587`) and sends emails.

* **`ai/gemini_service.py` (`GeminiAIService`)**:
  * Implements `BaseAIService` using `google.genai.Client`.
  * Executes prompt injection defense sanitization (`sanitize_input`).
  * `chat_stream(messages)`: Streams asynchronous text chunks from Gemini 2.5 Flash.
  * `moderate_content(text)`: Runs structured JSON classification on user posts for automated moderation.

---

### 4.5 API Routers (`backend/app/api/v1/`)

| File | Prefix | Key Endpoints | Responsibilities |
| :--- | :--- | :--- | :--- |
| **`auth.py`** | `/auth` | `/login`, `/register`, `/refresh`, `/logout`, `/forgot-password`, `/reset-password` | Authentication lifecycle & cookie management |
| **`users.py`** | `/users` | `/me`, `/{username}`, `/profile` | User profile updates & student badges |
| **`posts.py`** | `/posts` | `GET /feed`, `POST /`, `/{id}/like`, `/{id}/comments` | Cursor-paginated social feed, comments, likes |
| **`ai.py`** | `/ai` | `/generate-post`, `/summarize`, `/smart-replies`, `/chat/sessions`, `/chat/message` | AI post generation, summarization & chat assistant |
| **`notifications.py`** | `/notifications` | `GET /`, `POST /read-all`, `GET /stream` | Notification feed & Server-Sent Events stream |
| **`friends.py`** | `/friends` | `GET /`, `GET /requests`, `GET /status/{uid}`, `POST /request/{uid}`, `POST /accept/{id}`, `POST /reject/{id}`, `DELETE /{uid}` | Friendship system, status checks, pending requests |
| **`messages.py`** | `/messages` | `GET /conversations`, `GET /unread-count`, `GET /{conv_id}`, `POST /send` | 1-on-1 direct messaging, read receipts, live unread counter |
| **`admin.py`** | `/admin` | `/analytics`, `/users`, `/moderation/queue`, `/logs` | Executive dashboard & administrative controls |

---

## 5. Frontend Deep Dive (Components & Architecture)

### 5.1 API Client & Interceptor (`frontend/src/lib/api-client.ts`)

Instead of storing tokens insecurely in `localStorage` (where XSS scripts can steal them), Nexus Social implements **in-memory token storage**:

1. **`inMemoryAccessToken`**: Token lives strictly in JavaScript memory variable.
2. **Automatic Authorization Injection**: Injects `Authorization: Bearer <token>` on all outbound calls.
3. **401 Silent Refresh Deduplication**:
   * If an API call fails with `401 Unauthorized`, `apiFetch` intercepts it.
   * Calls `/api/v1/auth/refresh` using `credentials: "include"` (sending the httpOnly cookie).
   * Deduplicates concurrent requests so 5 simultaneous 401s trigger only **one** refresh network request.
   * Retries the original request seamlessly once the fresh token is received.

---

### 5.2 Authentication Context (`frontend/src/contexts/auth-context.tsx`)

* `AuthProvider`: React Context wrapping the entire application.
* **On Mount (`initAuth`)**: Silently calls `/api/v1/auth/refresh`. If an active session cookie exists, the user is automatically logged in and their profile is fetched from `/users/me`.
* Exposes `login()`, `register()`, `logout()`, `user`, and `isAdmin` flags to all components.

---

### 5.3 AI Support & Chat Widget (`frontend/src/components/ai/ai-chat-widget.tsx`)

* Floating launcher rendered in the bottom-right corner of the app layout.
* Communicates with `/api/v1/ai/chat/message` using `ReadableStream` reader.
* Contains a custom formatting sanitizer:
  ```typescript
  function formatChatMessage(text: string): string {
    return text
      .replace(/\*\*(.*?)\*\*/g, "$1") // Strips raw markdown bolding
      .replace(/\*(.*?)\*/g, "$1")     // Strips raw italics
      .replace(/^#+\s+/gm, "")         // Strips headers
      .replace(/^\s*\*\s+/gm, "• ");   // Replaces raw asterisk bullets with clean dots
  }
  ```
* Provides human-friendly, conversational guidance without robotic markdown asterisks.

---

### 5.4 Pages & Routing Structure

```
frontend/src/app/
├── layout.tsx                # Root HTML layout with ThemeProvider & QueryClientProvider
├── page.tsx                  # Public Landing Page showcasing platform features
├── (auth)/                   # Unauthenticated Routes
│   ├── login/page.tsx        # Login form (Email / Username / USN)
│   ├── register/page.tsx     # Student registration form
│   ├── forgot-password/      # Password recovery initiation
│   └── reset-password/       # Password recovery completion
└── (app)/                    # Authenticated Routes (wrapped in AppLayout & AIChatWidget)
    ├── feed/page.tsx         # Infinite scroll feed with post composer & AI assistance
    ├── profile/[username]/   # User profiles with Student USN verification badge
    ├── notifications/        # Live notification center
    └── admin/page.tsx        # Executive administration dashboard
```

---

## 6. End-to-End Operational Workflows

### 6.1 Authentication & Session Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant Browser as 💻 Next.js Frontend
    participant Server as ⚙️ FastAPI Backend
    participant DB as 🗄️ Database

    User->>Browser: Enters credentials (Email/Username/USN + Password)
    Browser->>Server: POST /api/v1/auth/login
    Server->>DB: Query user by Email OR Username OR USN
    Server->>Server: Verify Argon2id password hash
    Server->>DB: Insert rotating RefreshToken record
    Server-->>Browser: Response 200: { access_token } + Set-Cookie: refresh_token (httpOnly)
    Browser->>Browser: Store access_token in JS memory
    Browser->>Server: GET /api/v1/users/me (Bearer Token)
    Server-->>Browser: User profile object
    Browser->>User: Redirects to /feed (or /admin)
```

---

### 6.2 AI Support Chat Streaming

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant Widget as 💬 AIChatWidget
    participant Server as ⚙️ FastAPI Backend
    participant Gemini as ✨ Gemini 2.5 Flash

    User->>Widget: Types "How do I add my Student USN?"
    Widget->>Server: POST /api/v1/ai/chat/message { session_id, message, stream: true }
    Server->>Server: Verify JWT & decrement daily AI quota
    Server->>Gemini: Stream prompt + sanitized user message
    loop Text Chunk Streaming
        Gemini-->>Server: Yield token chunk
        Server-->>Widget: SSE event: data: {"chunk": "..."}
        Widget->>Widget: formatChatMessage() + update live UI bubble
    end
    Server-->>Widget: data: [DONE]
    Server->>DB: Persist complete user message & AI response
```

---

## 7. Database Architecture & Switching (SQLite ⇄ PostgreSQL)

The backend is built with dialect abstraction using SQLAlchemy 2.0:
* Columns that require PostgreSQL `JSONB` automatically fall back to standard `JSON` on SQLite via `.with_variant(JSON(), "sqlite")`.
* Foreign keys and UUIDs are handled natively across both databases.

### To switch between databases:
Simply edit line 11 in [`backend/.env`](file:///d:/Code/Social_Media/backend/.env):

```env
# ── Local Development (Zero Setup, Single File) ──────────
DATABASE_URL=sqlite+aiosqlite:///./nexus_dev.db

# ── Production / Docker (PostgreSQL 16) ──────────────────
# DATABASE_URL=postgresql+asyncpg://socialmedia:devpassword@localhost:5432/socialmedia
```

