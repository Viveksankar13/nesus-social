"""
Admin Schemas
=============
Pydantic schemas for the admin management console:
- Analytics stats cards and 30-day time-series charts
- User administration and role/suspension updates
- Content management (posts & comments) and bulk moderation
- Moderation queue and action requests
- Activity audit logging
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Analytics & Stats ────────────────────────────────────────────────────────


class AdminStatsResponse(BaseModel):
    """Aggregate KPI statistics for the admin dashboard."""

    total_users: int
    verified_users: int
    new_users_7d: int
    total_posts: int
    total_comments: int
    total_likes: int
    flagged_items: int


class DailyMetricPoint(BaseModel):
    """Time-series point for 30-day trend charts."""

    date: str = Field(description="ISO date string YYYY-MM-DD")
    count: int


class ChartDataResponse(BaseModel):
    """30-day platform analytics charts for user signups and post creations."""

    signups_by_day: list[DailyMetricPoint]
    posts_by_day: list[DailyMetricPoint]


# ── User Management ──────────────────────────────────────────────────────────


class AdminUserResponse(BaseModel):
    """Detailed user account view for administrative tables."""

    id: uuid.UUID
    email: EmailStr
    username: str
    usn: str | None = None
    display_name: str
    role: str
    is_verified: bool
    is_suspended: bool
    created_at: datetime
    posts_count: int = 0
    comments_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """Paginated list of users for administration."""

    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    """Payload to promote or demote a user's role."""

    role: Literal["user", "admin"]


class UserSuspendUpdate(BaseModel):
    """Payload to suspend or unsuspend a user."""

    is_suspended: bool
    reason: str | None = Field(default=None, max_length=500)


# ── Content Management ───────────────────────────────────────────────────────


class AdminPostResponse(BaseModel):
    """Post representation with moderation flags for administrators."""

    id: uuid.UUID
    author_id: uuid.UUID
    author_username: str
    content: str
    image_url: str | None = None
    is_hidden: bool
    is_edited: bool
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminPostListResponse(BaseModel):
    """Paginated post management list."""

    items: list[AdminPostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminCommentResponse(BaseModel):
    """Comment representation for administrators."""

    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID | None
    author_username: str | None = None
    content: str
    parent_id: uuid.UUID | None = None
    is_hidden: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCommentListResponse(BaseModel):
    """Paginated comments management list."""

    items: list[AdminCommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkActionRequest(BaseModel):
    """Payload to perform bulk moderation across multiple items."""

    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    action: Literal["hide", "restore", "delete"]


class ToggleHideRequest(BaseModel):
    """Payload to toggle the hidden state of content."""

    is_hidden: bool


# ── Moderation Queue ─────────────────────────────────────────────────────────


class ModerationItemResponse(BaseModel):
    """Flagged content review item in the moderation queue."""

    id: uuid.UUID
    content_type: str  # "post" | "comment"
    content_id: uuid.UUID
    category: str
    severity: str
    score: float
    action: str
    reason: str
    reviewed: bool
    created_at: datetime
    content_snippet: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ModerationQueueResponse(BaseModel):
    """Paginated moderation queue response."""

    items: list[ModerationItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ModerationActionRequest(BaseModel):
    """Payload to resolve a flagged item."""

    action: Literal["approve", "hide", "delete"]
    notes: str | None = Field(default=None, max_length=500)


# ── Activity Audit Log ───────────────────────────────────────────────────────


class ActivityLogResponse(BaseModel):
    """Immutable audit trail log entry."""

    id: uuid.UUID
    admin_id: uuid.UUID | None
    admin_username: str | None = None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    details: dict[str, Any]
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityLogListResponse(BaseModel):
    """Paginated activity audit logs."""

    items: list[ActivityLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
