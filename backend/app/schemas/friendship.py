"""
Friendship Schemas
==================
Pydantic schemas for friend requests, friendship listings, and status checks.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserResponse


class FriendRequestResponse(BaseModel):
    """Friend request response schema."""

    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    status: str
    created_at: datetime
    sender: UserResponse
    receiver: UserResponse

    model_config = ConfigDict(from_attributes=True)


class FriendshipStatusResponse(BaseModel):
    """Status between the logged in user and another user."""

    target_user_id: uuid.UUID
    status: str  # "none" | "pending_sent" | "pending_received" | "friends"
    friendship_id: uuid.UUID | None = None


class FriendUserResponse(BaseModel):
    """User who is a friend, with friendship metadata."""

    friendship_id: uuid.UUID
    friend: UserResponse
    since: datetime

    model_config = ConfigDict(from_attributes=True)
