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
  usn?: string | null;
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
  usn?: string | null;
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
  usn?: string | null;
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

// ── Admin Schemas ────────────────────────────────────────────────────

export interface AdminStatsResponse {
  total_users: number;
  verified_users: number;
  new_users_7d: number;
  total_posts: number;
  total_comments: number;
  total_likes: number;
  flagged_items: number;
}

export interface DailyMetricPoint {
  date: string;
  count: number;
}

export interface ChartDataResponse {
  signups_by_day: DailyMetricPoint[];
  posts_by_day: DailyMetricPoint[];
}

export interface AdminUserResponse {
  id: string;
  email: string;
  username: string;
  usn?: string | null;
  display_name: string;
  role: "user" | "admin";
  is_verified: boolean;
  is_suspended: boolean;
  created_at: string;
  posts_count: number;
  comments_count: number;
}

export interface AdminUserListResponse {
  items: AdminUserResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserRoleUpdate {
  role: "user" | "admin";
}

export interface UserSuspendUpdate {
  is_suspended: boolean;
  reason?: string | null;
}

export interface AdminPostResponse {
  id: string;
  author_id: string;
  author_username: string;
  content: string;
  image_url: string | null;
  is_hidden: boolean;
  is_edited: boolean;
  created_at: string;
  likes_count: number;
  comments_count: number;
}

export interface AdminPostListResponse {
  items: AdminPostResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminCommentResponse {
  id: string;
  post_id: string;
  author_id: string | null;
  author_username: string | null;
  content: string;
  parent_id: string | null;
  is_hidden: boolean;
  created_at: string;
}

export interface AdminCommentListResponse {
  items: AdminCommentResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BulkActionRequest {
  ids: string[];
  action: "hide" | "restore" | "delete";
}

export interface ToggleHideRequest {
  is_hidden: boolean;
}

export interface ModerationItemResponse {
  id: string;
  content_type: "post" | "comment";
  content_id: string;
  category: string;
  severity: string;
  score: number;
  action: string;
  reason: string;
  reviewed: boolean;
  created_at: string;
  content_snippet: string | null;
}

export interface ModerationQueueResponse {
  items: ModerationItemResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ModerationActionRequest {
  action: "approve" | "hide" | "delete";
  notes?: string | null;
}

export interface ActivityLogResponse {
  id: string;
  admin_id: string | null;
  admin_username: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface ActivityLogListResponse {
  items: ActivityLogResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Friendships & Direct Messaging ──────────────────────────────
export interface FriendshipStatusResponse {
  target_user_id: string;
  status: "none" | "pending_sent" | "pending_received" | "friends";
  friendship_id?: string | null;
}

export interface FriendUserResponse {
  friendship_id: string;
  friend: User;
  since: string;
}

export interface FriendRequestResponse {
  id: string;
  sender_id: string;
  receiver_id: string;
  status: string;
  created_at: string;
  sender: User;
  receiver: User;
}

export interface FriendRequestsData {
  incoming: FriendRequestResponse[];
  outgoing: FriendRequestResponse[];
}

export interface DirectMessageResponse {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
  sender: User;
}

export interface ConversationResponse {
  id: string;
  other_user: User;
  last_message: DirectMessageResponse | null;
  unread_count: number;
  updated_at: string;
}

export interface UnreadMessageCountResponse {
  unread_count: number;
}


