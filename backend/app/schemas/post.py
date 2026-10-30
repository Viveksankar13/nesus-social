"""
Post Schemas
============
Pydantic schemas for posts, feed responses, and like status.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import AuthorSummary


class PostCreate(BaseModel):
    """Payload to create a new post."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Post text (max 1000 chars)",
    )
    image_url: str | None = Field(default=None, max_length=500, description="Optional image URL")

    @field_validator("content")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and ensure content is non-empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Post content cannot be empty or whitespace only")
        return stripped


class PostUpdate(BaseModel):
    """Payload to update an existing post."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Post text (max 1000 chars)",
    )
    image_url: str | None = Field(default=None, max_length=500, description="Optional image URL")

    @field_validator("content")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and ensure content is non-empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Post content cannot be empty or whitespace only")
        return stripped


class PostResponse(BaseModel):
    """Post details including author summary, like/comment counts, and viewer reaction."""

    id: uuid.UUID
    author_id: uuid.UUID
    author: AuthorSummary
    content: str
    image_url: str | None = None
    is_hidden: bool = False
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    has_liked: bool = False

    model_config = ConfigDict(from_attributes=True)


class FeedResponse(BaseModel):
    """Keyset cursor-paginated feed response."""

    items: list[PostResponse]
    next_cursor: str | None = None
    has_more: bool = False


class LikeResponse(BaseModel):
    """Response returned when toggling a like on a post."""

    liked: bool
    likes_count: int
    post_id: uuid.UUID
