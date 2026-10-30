"""
Notification Schemas
====================
Pydantic schemas for persistent notifications, unread counts,
and SSE stream authentication tokens.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Structured notification representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: str = Field(description="Event category: like, comment, reply, admin_login, etc.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Metadata payload")
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated list of notifications with unread count."""

    items: list[NotificationResponse]
    unread_count: int
    next_cursor: str | None = None
    has_more: bool = False


class StreamTokenResponse(BaseModel):
    """Short-lived single-purpose token for Server-Sent Events stream."""

    token: str
    expires_in: int = 60


class UnreadCountResponse(BaseModel):
    """Current count of unread notifications for badge rendering."""

    unread_count: int
