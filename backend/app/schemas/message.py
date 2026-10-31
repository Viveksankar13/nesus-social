"""
Direct Message Schemas
======================
Pydantic schemas for 1-on-1 private messaging and conversations.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class SendMessageRequest(BaseModel):
    """Payload to send a direct message."""

    receiver_id: uuid.UUID
    content: str = Field(min_length=1, max_length=5000, description="Message text content")


class DirectMessageResponse(BaseModel):
    """Direct message item response."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    is_read: bool
    created_at: datetime
    sender: UserResponse

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Summary of a direct conversation channel."""

    id: uuid.UUID
    other_user: UserResponse
    last_message: DirectMessageResponse | None = None
    unread_count: int = 0
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadMessageCountResponse(BaseModel):
    """Total unread messages across all conversations."""

    unread_count: int

