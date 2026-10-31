"""
Direct Messaging Models
=======================
Entities for private 1-on-1 direct conversations and individual messages.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Conversation(Base, UUIDMixin):
    """Direct conversation channel between two users."""

    __tablename__ = "conversations"

    user1_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user2_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationships
    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id], lazy="selectin")
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id], lazy="selectin")
    messages: Mapped[list["DirectMessage"]] = relationship(
        "DirectMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="DirectMessage.created_at",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_conversations_user1_user2"),
        Index("ix_conversations_users", "user1_id", "user2_id"),
    )


class DirectMessage(Base, UUIDMixin):
    """Individual direct message between friends inside a conversation."""

    __tablename__ = "direct_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
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
        index=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], lazy="selectin")

