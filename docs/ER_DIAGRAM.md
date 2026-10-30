# ER Diagram — Nexus Social Database

> **Status:** Skeleton — full diagram generated in Stage 1 after all models are defined.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    users {
        uuid id PK
        string email UK
        string username UK
        string display_name
        string hashed_password
        string role
        bool is_verified
        bool is_suspended
        text bio
        string location
        string website
        string avatar_url
        timestamp created_at
        timestamp updated_at
    }

    refresh_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash
        uuid family_id
        string user_agent
        string ip_address
        timestamp expires_at
        bool revoked
        timestamp created_at
    }

    email_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash
        string token_type
        timestamp expires_at
        timestamp used_at
        timestamp created_at
    }

    posts {
        uuid id PK
        uuid author_id FK
        text content
        string image_url
        bool is_hidden
        bool is_edited
        timestamp created_at
        timestamp updated_at
    }

    comments {
        uuid id PK
        uuid post_id FK
        uuid author_id FK
        uuid parent_id FK
        text content
        bool is_hidden
        bool is_edited
        timestamp created_at
        timestamp updated_at
    }

    likes {
        uuid id PK
        uuid user_id FK
        uuid post_id FK
        timestamp created_at
    }

    notifications {
        uuid id PK
        uuid user_id FK
        string type
        jsonb payload
        bool is_read
        timestamp created_at
    }

    moderation_flags {
        uuid id PK
        string content_type
        uuid content_id
        string category
        string severity
        float score
        string action
        text reason
        bool reviewed
        timestamp created_at
    }

    ai_chat_sessions {
        uuid id PK
        uuid user_id FK
        string title
        timestamp created_at
        timestamp updated_at
    }

    ai_chat_messages {
        uuid id PK
        uuid session_id FK
        string role
        text content
        timestamp created_at
    }

    ai_usage_logs {
        uuid id PK
        uuid user_id FK
        string feature
        int latency_ms
        int tokens_used
        string status
        text error
        timestamp created_at
    }

    activity_logs {
        uuid id PK
        uuid admin_id FK
        string action
        string resource_type
        uuid resource_id
        jsonb metadata
        string ip_address
        timestamp created_at
    }

    users ||--o{ refresh_tokens : "has"
    users ||--o{ email_tokens : "has"
    users ||--o{ posts : "authors"
    users ||--o{ comments : "authors"
    users ||--o{ likes : "gives"
    users ||--o{ notifications : "receives"
    users ||--o{ ai_chat_sessions : "owns"
    users ||--o{ ai_usage_logs : "generates"
    users ||--o{ activity_logs : "admin performs"
    posts ||--o{ comments : "has"
    posts ||--o{ likes : "receives"
    comments ||--o{ comments : "parent of"
    ai_chat_sessions ||--o{ ai_chat_messages : "contains"
```

---

## Table Reference

Full column documentation is in `docs/stages/STAGE_01.md` (written in Stage 1).

### Key Constraints

| Table | Constraint | Type |
|-------|-----------|------|
| `users` | `email` | UNIQUE |
| `users` | `username` | UNIQUE |
| `likes` | `(user_id, post_id)` | UNIQUE — prevents duplicate likes |
| `posts` | `len(content) <= 1000` | CHECK constraint |
| `refresh_tokens` | `(user_id, family_id)` | INDEX — for family revocation |

### Key Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| `posts` | `(created_at DESC)` | Feed ordering |
| `posts` | `(author_id, created_at DESC)` | Profile feed |
| `notifications` | `(user_id, is_read)` | Unread count query |
| `moderation_flags` | `(reviewed, action)` | Moderation queue |
| `ai_usage_logs` | `(user_id, created_at)` | Daily quota check |

### ON DELETE Rules

| FK | Rule | Reason |
|----|------|--------|
| `posts.author_id → users.id` | CASCADE | Delete user removes their posts |
| `comments.post_id → posts.id` | CASCADE | Delete post removes its comments |
| `comments.author_id → users.id` | SET NULL | Preserve comment thread structure; mark as [deleted user] |
| `likes.user_id → users.id` | CASCADE | Delete user removes their likes |
| `likes.post_id → posts.id` | CASCADE | Delete post removes its likes |
| `notifications.user_id → users.id` | CASCADE | Delete user removes their notifications |
| `refresh_tokens.user_id → users.id` | CASCADE | Delete user revokes all their sessions |
| `ai_chat_messages.session_id → ai_chat_sessions.id` | CASCADE | Delete session removes messages |
