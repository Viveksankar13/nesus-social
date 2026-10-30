/**
 * Shared TypeScript types for the Nexus Social frontend.
 * These mirror the Pydantic schemas from the backend.
 * Populated progressively as each stage adds endpoints.
 */

// ── User ────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  username: string;
  display_name: string;
  bio: string | null;
  location: string | null;
  website: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  is_verified: boolean;
  is_suspended: boolean;
  created_at: string;
  updated_at: string;
}

// ── Post ────────────────────────────────────────────────────────────
export interface Post {
  id: string;
  content: string;
  image_url: string | null;
  is_edited: boolean;
  like_count: number;
  comment_count: number;
  is_liked_by_me: boolean;
  author: Pick<User, "id" | "username" | "display_name" | "avatar_url">;
  created_at: string;
  updated_at: string;
}

// ── Comment ─────────────────────────────────────────────────────────
export interface Comment {
  id: string;
  content: string;
  is_edited: boolean;
  parent_id: string | null;
  author: Pick<User, "id" | "username" | "display_name" | "avatar_url">;
  replies?: Comment[];
  created_at: string;
  updated_at: string;
}

// ── Notification ─────────────────────────────────────────────────────
export interface Notification {
  id: string;
  type: "like" | "comment" | "reply" | "moderation" | "admin_login" | "flagged";
  is_read: boolean;
  payload: Record<string, unknown>;
  created_at: string;
}

// ── API Response wrappers ────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  total: number | null;
}

export interface ApiError {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
}

// ── Auth ────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface MeResponse extends User {
  unread_notification_count: number;
}
