"""
Authentication Request and Response Schemas
===========================================
Pydantic v2 schemas for all auth workflows:
- Registration, Login, Token Refresh, Logout
- Email verification and password resets
"""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_strength

UsernameStr = Annotated[
    str,
    Field(min_length=3, max_length=50, description="Alphanumeric username with underscores"),
]


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    username: UsernameStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    usn: str | None = Field(
        default=None,
        max_length=50,
        description="University Seat Number (USN) / Student College ID Number",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        clean_v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_]+$", clean_v):
            raise ValueError("Username may only contain letters, numbers, and underscores.")
        return clean_v

    @field_validator("usn")
    @classmethod
    def validate_usn(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip().upper()
            if not clean:
                return None
            if len(clean) < 3:
                raise ValueError("Student USN must be at least 3 characters.")
            if not re.match(r"^[A-Z0-9_-]+$", clean):
                raise ValueError("Student USN may only contain letters, numbers, hyphens, and underscores.")
            return clean
        return None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    email_or_username: str = Field(
        min_length=3,
        max_length=255,
        description="Email address, username, or Student USN",
    )
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Payload for email address verification."""

    token: str = Field(min_length=16, description="Verification token from email")


class ResendVerificationRequest(BaseModel):
    """Payload to request a new verification email."""

    email: str = Field(
        min_length=3,
        max_length=255,
        description="Registered email address or Student USN",
    )


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate password reset."""

    email: str = Field(
        min_length=3,
        max_length=255,
        description="Registered email address or Student USN",
    )


class ResetPasswordRequest(BaseModel):
    """Payload to set a new password with a reset token."""

    token: str = Field(min_length=16)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v


class ChangePasswordRequest(BaseModel):
    """Payload for authenticated users to update their password."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v


class TokenResponse(BaseModel):
    """Access token response payload."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


class MessageResponse(BaseModel):
    """Generic status/message response."""

    message: str
    detail: str | None = None

    model_config = ConfigDict(extra="ignore")
