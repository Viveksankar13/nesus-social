"""
User Schemas
============
Pydantic schemas for user profiles and user account representations.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    """Public and authenticated user profile response."""

    id: uuid.UUID
    email: EmailStr
    username: str
    display_name: str
    bio: str | None = None
    location: str | None = None
    website: str | None = None
    avatar_url: str | None = None
    role: str
    is_verified: bool
    is_suspended: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Payload for updating own profile."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)
