"""
Skill Swap Economy Database Models
==================================
SQLAlchemy 2.0 models representing the Hyper-Local Skill Swap Economy:
- Canonical skills taxonomy and user skill competencies
- User swap profiles with privacy-preserving coarse coordinates (~1 km)
- Weekly availability windows and blackout intervals
- Swap listings, proposals (requests), and 30-minute halves sessions
- Session logistics chat, double-blind reviews, and mutual user blocks
- Trust scores, reciprocity ledger, match explanations, and job runs
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin

# Cross-dialect JSON type (falls back to generic JSON on non-PG for tests)
JSONType = JSON().with_variant(JSONB, "postgresql")


class Skill(Base, UUIDMixin):
    """Canonical skill taxonomy entry."""

    __tablename__ = "skills"

    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), index=True, default="active", nullable=False
    )  # active, pending, rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user_skills: Mapped[list["UserSkill"]] = relationship(
        "UserSkill", back_populates="skill", cascade="all, delete-orphan"
    )


class UserSkill(Base, UUIDMixin):
    """User-declared skill capability (teaching or learning)."""

    __tablename__ = "user_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", "skill_type", name="uq_user_skill_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_type: Mapped[str] = mapped_column(
        String(10), index=True, nullable=False
    )  # "teach" or "learn"
    level: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # beginner, intermediate, advanced, expert
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    skill: Mapped["Skill"] = relationship("Skill", back_populates="user_skills")


class UserSwapProfile(Base, UUIDMixin, TimestampMixin):
    """
    Swap-specific user profile settings.
    Stores coarse coordinates (~1 km resolution) and area label.
    Precise coordinates are NEVER stored or returned via API.
    """

    __tablename__ = "user_swap_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    coarse_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    coarse_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    radius_km: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    modes: Mapped[list[str]] = mapped_column(
        JSONType, default=lambda: ["video", "in_person"], nullable=False
    )
    languages: Mapped[list[str]] = mapped_column(
        JSONType, default=lambda: ["English"], nullable=False
    )
    is_invisible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepts_newcomers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_18_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AvailabilityWindow(Base, UUIDMixin):
    """Weekly recurring availability window (stored in UTC)."""

    __tablename__ = "availability_windows"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer, index=True, nullable=False
    )  # 0=Monday ... 6=Sunday
    start_time_utc: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    end_time_utc: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AvailabilityBlackout(Base, UUIDMixin):
    """One-off blackout period when a user is unavailable."""

    __tablename__ = "availability_blackouts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    end_datetime_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class SwapListing(Base, UUIDMixin, TimestampMixin):
    """Public swap listing / offer published by a user."""

    __tablename__ = "swap_listings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    skill_offered_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    skill_wanted_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), index=True, nullable=True
    )  # None = Open to anything / Pay it forward
    description: Mapped[str] = mapped_column(Text, nullable=False)
    modes: Mapped[list[str]] = mapped_column(
        JSONType, default=lambda: ["video"], nullable=False
    )
    area_label: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), index=True, default="active", nullable=False
    )  # draft, active, paused, closed, removed
    tags: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skill_offered: Mapped["Skill"] = relationship("Skill", foreign_keys=[skill_offered_id])
    skill_wanted: Mapped["Skill | None"] = relationship("Skill", foreign_keys=[skill_wanted_id])


class SwapRequest(Base, UUIDMixin, TimestampMixin):
    """
    Swap proposal between two users.
    Follows strict state machine: pending -> accepted | declined | countered | cancelled | expired
    """

    __tablename__ = "swap_requests"

    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("swap_listings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    offered_skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    wanted_skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    mode: Mapped[str] = mapped_column(String(20), default="video", nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_slots: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), index=True, default="pending", nullable=False
    )  # pending, accepted, declined, countered, cancelled, expired
    counter_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )


class SwapSession(Base, UUIDMixin, TimestampMixin):
    """
    Agreed swap session comprised of two 30-minute halves.
    State machine: scheduled -> active -> completed | disputed | cancelled
    """

    __tablename__ = "swap_sessions"

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("swap_requests.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), index=True, default="scheduled", nullable=False
    )  # scheduled, active, completed, disputed, cancelled
    mode: Mapped[str] = mapped_column(String(20), default="video", nullable=False)
    public_place_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    public_place_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jitsi_room_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_a_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_b_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    disputed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    halves: Mapped[list["SwapSessionHalf"]] = relationship(
        "SwapSessionHalf", back_populates="session", cascade="all, delete-orphan"
    )
    messages: Mapped[list["SwapMessage"]] = relationship(
        "SwapMessage", back_populates="session", cascade="all, delete-orphan"
    )


class SwapSessionHalf(Base, UUIDMixin):
    """One 30-minute half of a swap session."""

    __tablename__ = "swap_session_halves"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("swap_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    half_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or 2
    mentor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    start_time_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    end_time_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)
    ics_uid: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    session: Mapped["SwapSession"] = relationship("SwapSession", back_populates="halves")


class SwapMessage(Base, UUIDMixin):
    """Logistics chat message within an active or scheduled swap session."""

    __tablename__ = "swap_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("swap_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True, nullable=False
    )

    session: Mapped["SwapSession"] = relationship("SwapSession", back_populates="messages")


class SwapReview(Base, UUIDMixin):
    """
    Double-blind review revealed after both parties submit or 7 calendar days elapse.
    """

    __tablename__ = "swap_reviews"
    __table_args__ = (
        UniqueConstraint("session_id", "reviewer_id", name="uq_session_reviewer"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("swap_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    tags: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    public_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_revealed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class UserBlock(Base, UUIDMixin):
    """Bi-directional block preventing discovery, matching, and messaging."""

    __tablename__ = "user_blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )

    blocker_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class SwapReport(Base, UUIDMixin):
    """User report on listing, user, or session."""

    __tablename__ = "swap_reports"

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "listing", "user", "session"
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # payment_solicitation, off_platform_contact, inappropriate_behavior, no_show, spam, safety_concern
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), index=True, default="pending", nullable=False
    )  # pending, investigating, resolved, dismissed
    admin_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class TrustScore(Base, UUIDMixin):
    """Quantitative trust metric and accomplishments."""

    __tablename__ = "trust_scores"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)  # 0 to 100
    completed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_show_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancellation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    badges: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ReciprocityLedger(Base, UUIDMixin):
    """Tracks balance of taught vs. learned sessions."""

    __tablename__ = "reciprocity_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    minutes_taught: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minutes_learned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_balance_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grace_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # up to 60m (2 sessions)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class MatchExplanation(Base, UUIDMixin):
    """Cached Gemini 'Why you match' one-sentence explanation."""

    __tablename__ = "match_explanations"

    user_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    input_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class JobRun(Base, UUIDMixin):
    """Audit record for background cron maintenance jobs."""

    __tablename__ = "job_runs"

    job_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )  # running, success, failed
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
