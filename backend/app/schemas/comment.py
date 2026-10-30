"""
Comment Schemas
===============
Pydantic schemas for comments, threaded replies, and comment updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import AuthorSummary


class CommentCreate(BaseModel):
    """Payload to add a comment or reply to a post."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Comment text (max 500 chars)",
    )
    parent_id: uuid.UUID | None = Field(
        default=None,
        description="ID of top-level comment to reply to (1-level nesting)",
    )

    @field_validator("content")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and ensure non-empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Comment content cannot be empty or whitespace only")
        return stripped


class CommentUpdate(BaseModel):
    """Payload to edit an existing comment."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Comment text (max 500 chars)",
    )

    @field_validator("content")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace and ensure non-empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Comment content cannot be empty or whitespace only")
        return stripped


class CommentResponse(BaseModel):
    """Structured comment with author details and 1-level threaded replies."""

    id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID | None = None
    author: AuthorSummary | None = None
    parent_id: uuid.UUID | None = None
    content: str
    is_hidden: bool = False
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime
    replies: list[CommentResponse] = []

    model_config = ConfigDict(from_attributes=True)
