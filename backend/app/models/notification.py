"""
Notification Model
==================
Entity representing persistent notifications for users and admins.
Stores structured metadata in a JSONB / JSON payload.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Notification(Base, UUIDMixin):
    """Notification entity with flexible JSON payload."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "like" | "comment" | "reply" | "moderation" | "admin_login" | "flagged"

    # Use JSONB on PostgreSQL, fall back to generic JSON on other dialects (e.g. SQLite for testing)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} read={self.is_read}>"
