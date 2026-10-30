"""
Token Models
============
Models for:
- RefreshToken: Rotating opaque refresh tokens with family tracking and reuse detection.
- EmailToken: Single-use verification and password-reset tokens.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, UUIDMixin):
    """
    Rotating refresh token entity.
    Stores only the SHA-256 hash of the token.
    family_id allows revoking an entire token chain if reuse is detected.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_family_revoked", "family_id", "revoked"),)

    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(UTC) > self.expires_at

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"


class EmailToken(Base, UUIDMixin):
    """
    Opaque single-use tokens for email verification and password reset.
    Stores SHA-256 hash; 32 random bytes generated at runtime.
    """

    __tablename__ = "email_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    token_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "verify_email" | "reset_password"

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="email_tokens")

    def is_valid(self) -> bool:
        """Check if token is neither expired nor previously used."""
        return self.used_at is None and datetime.now(UTC) <= self.expires_at

    def __repr__(self) -> str:
        return f"<EmailToken type={self.token_type} user_id={self.user_id}>"
