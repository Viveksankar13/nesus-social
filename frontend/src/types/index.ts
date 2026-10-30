/**
 * Shared TypeScript types for Nexus Social Frontend
 * Mirroring backend Pydantic schemas 1:1
 */

// ── User ────────────────────────────────────────────────────────────

export interface AuthorSummary {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

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

export interface UserProfile {
  id: string;
  username: string;
  display_name: string;
  bio: string | null;
  location: string | null;
  website: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  created_at: string;
  posts_count: number;
  likes_received_count: number;
}

export interface UserUpdateData {
  display_name?: string;
  bio?: string | null;
  location?: string | null;
  website?: string | null;
  avatar_url?: string | null;
}

// ── Post ────────────────────────────────────────────────────────────

export interface Post {
  id: string;
  author_id: string;
  author: AuthorSummary;
  content: string;
  image_url: string | null;
  is_hidden: boolean;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
  likes_count: number;
  comments_count: number;
  has_liked: boolean;
}

export interface FeedResponse {
  items: Post[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface LikeResponse {
  liked: boolean;
  likes_count: number;
  post_id: string;
}

export interface PostCreateData {
  content: string;
  image_url?: string | null;
}

// ── Comment ─────────────────────────────────────────────────────────

export interface Comment {
  id: string;
  post_id: string;
  author_id: string | null;
  author: AuthorSummary | null;
  parent_id: string | null;
  content: string;
  is_hidden: boolean;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
  replies: Comment[];
}

export interface CommentCreateData {
  content: string;
  parent_id?: string | null;
}

// ── Notification ─────────────────────────────────────────────────────

export interface Notification {
  id: string;
  user_id: string;
  type: "like" | "comment" | "reply" | "moderation" | "admin_login" | "flagged";
  payload: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  unread_count: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface StreamTokenResponse {
  token: string;
  expires_in: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

// ── AI Schemas ───────────────────────────────────────────────────────

export interface PostGenerateRequest {
  topic?: string | null;
  draft?: string | null;
  tone: "casual" | "professional" | "funny" | "inspirational";
}

export interface PostGenerateResponse {
  variants: string[];
}

export interface PostSummarizeResponse {
  summary: string;
  key_points: string[];
  sentiment: "positive" | "neutral" | "negative" | "mixed";
}

export interface SmartRepliesResponse {
  replies: string[];
}

export interface AIChatMessage {
  id: string;
  session_id: string;
  role: "user" | "model" | "system";
  content: string;
  created_at: string;
}

export interface AIChatSession {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AIChatSessionDetail extends AIChatSession {
  messages: AIChatMessage[];
}

export interface AIQuotaStatus {
  used_today: number;
  daily_quota: number;
  remaining_today: number;
}
