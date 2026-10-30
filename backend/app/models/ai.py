"""
AI Models
=========
Models supporting the 5 Google Gemini AI features:
- AIChatSession: Conversation session for the friendly assistant.
- AIChatMessage: Messages within a session.
- AIUsageLog: Audit log tracking latency, tokens, quota checks, and errors.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class AIChatSession(Base, UUIDMixin, TimestampMixin):
    """Conversational session between a user and the AI assistant."""

    __tablename__ = "ai_chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(150),
        default="New Conversation",
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[list["AIChatMessage"]] = relationship(
        "AIChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AIChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<AIChatSession id={self.id} user_id={self.user_id} title='{self.title}'>"


class AIChatMessage(Base, UUIDMixin):
    """Single message within an AI chat session."""

    __tablename__ = "ai_chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "user" | "model" | "system"
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    session: Mapped["AIChatSession"] = relationship("AIChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<AIChatMessage id={self.id} role={self.role}>"


class AIUsageLog(Base, UUIDMixin):
    """
    Audit log of all AI API calls.
    Used for quota tracking, cost analysis, and telemetry.
    """

    __tablename__ = "ai_usage_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "post_generate" | "summarize" | "chat" | "moderation" | "smart_replies"
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "success" | "error" | "rate_limited"
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="ai_usage_logs")

    __table_args__ = (
        Index("ix_ai_usage_user_date", "user_id", "created_at"),
        Index("ix_ai_usage_feature_status", "feature", "status"),
    )

    def __repr__(self) -> str:
        return f"<AIUsageLog user_id={self.user_id} feature={self.feature} status={self.status}>"
