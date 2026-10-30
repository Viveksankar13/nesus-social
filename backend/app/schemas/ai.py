"""
AI Schemas
==========
Pydantic v2 schemas for all 5 Gemini AI features:
- Post generation and tone adaptation
- Post summarization & sentiment analysis
- Conversational assistant (chat sessions & messages)
- Content moderation check
- Smart replies
- Usage & quota telemetry
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PostGenerateRequest(BaseModel):
    """Request payload for generating or rewriting post content."""

    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str | None = Field(default=None, max_length=300, description="Topic or prompt idea")
    draft: str | None = Field(
        default=None, max_length=1000, description="Existing rough draft to refine"
    )
    tone: Literal["casual", "professional", "funny", "inspirational"] = Field(
        default="casual", description="Desired tone of voice"
    )

    @model_validator(mode="after")
    def validate_content_presence(self) -> "PostGenerateRequest":
        """At least one of topic or draft must be provided."""
        has_topic = bool(self.topic and self.topic.strip())
        has_draft = bool(self.draft and self.draft.strip())
        if not has_topic and not has_draft:
            raise ValueError("Either 'topic' or 'draft' must be provided.")
        return self


class PostGenerateResponse(BaseModel):
    """Response containing 3 distinct post variants."""

    variants: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of generated post variants (typically 3)",
    )


class PostSummarizeRequest(BaseModel):
    """Request payload to summarize a post and its comment thread."""

    post_id: uuid.UUID = Field(..., description="ID of the post to summarize")


class PostSummarizeResponse(BaseModel):
    """Structured summary and sentiment analysis of a post thread."""

    summary: str = Field(..., description="Concise synopsis of the discussion")
    key_points: list[str] = Field(..., description="Key takeaways from post and comments")
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = Field(
        ..., description="Overall sentiment tone of the thread"
    )


class AIChatSessionCreate(BaseModel):
    """Payload to initiate a new AI conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)
    title: str | None = Field(default=None, max_length=150)


class AIChatMessageResponse(BaseModel):
    """Single message in an AI conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class AIChatSessionResponse(BaseModel):
    """Summary of an AI conversation session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AIChatSessionDetailResponse(BaseModel):
    """Full AI conversation session with historical messages."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[AIChatMessageResponse] = Field(default_factory=list)


class AIChatMessageRequest(BaseModel):
    """User message payload for AI assistant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: uuid.UUID = Field(..., description="Target chat session ID")
    message: str = Field(..., min_length=1, max_length=2000, description="User prompt")
    stream: bool = Field(default=False, description="Whether to stream response via SSE")


class SmartRepliesRequest(BaseModel):
    """Request payload for contextual smart replies."""

    post_id: uuid.UUID = Field(..., description="Target post ID")
    comment_id: uuid.UUID | None = Field(
        default=None, description="Optional parent comment ID if replying in a thread"
    )


class SmartRepliesResponse(BaseModel):
    """Smart reply options."""

    replies: list[str] = Field(
        ..., min_length=1, max_length=5, description="3 short contextual reply suggestions"
    )


class ModerationCheckResult(BaseModel):
    """Structured result from content moderation inspection."""

    category: Literal["hate", "harassment", "sexual", "violence", "self-harm", "spam", "other"]
    severity: Literal["low", "medium", "high", "critical"]
    score: float = Field(..., ge=0.0, le=1.0)
    action: Literal["allow", "flag", "block"]
    reason: str


class AIQuotaStatus(BaseModel):
    """User daily quota consumption and limits."""

    used_today: int
    daily_quota: int
    remaining_today: int
