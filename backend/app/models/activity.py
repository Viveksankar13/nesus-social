"""
Activity Log Model
==================
Audit trail recording all administrative actions for compliance and accountability.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ActivityLog(Base, UUIDMixin):
    """Immutable audit trail for all admin operations."""

    __tablename__ = "activity_logs"

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "suspend_user" | "unsuspend_user" | "change_role" | "hide_post" | "delete_post" | etc.
    resource_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # "user" | "post" | "comment" | "moderation_flag"
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    # JSONB on PostgreSQL, JSON on SQLite
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    admin: Mapped["User | None"] = relationship("User", foreign_keys=[admin_id])

    __table_args__ = (
        Index("ix_activity_admin_created", "admin_id", "created_at"),
        Index("ix_activity_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActivityLog action={self.action} resource={self.resource_type}:{self.resource_id}>"
        )
