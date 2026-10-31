"""Add skill swap economy tables

Revision ID: 0004_add_skill_swap_economy
Revises: 0003_add_friends_and_messages
Create Date: 2026-10-31 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_add_skill_swap_economy"
down_revision: str | None = "0003_add_friends_and_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. skills ──────────────────────────────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "aliases",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_skills_slug", "skills", ["slug"], unique=True)
    op.create_index("ix_skills_category", "skills", ["category"])
    op.create_index("ix_skills_status", "skills", ["status"])

    # ── 2. user_skills ─────────────────────────────────────────────────────
    op.create_table(
        "user_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("skill_type", sa.String(length=10), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_id", "skill_type", name="uq_user_skill_type"),
    )
    op.create_index("ix_user_skills_user_id", "user_skills", ["user_id"])
    op.create_index("ix_user_skills_skill_id", "user_skills", ["skill_id"])
    op.create_index("ix_user_skills_skill_type", "user_skills", ["skill_type"])

    # ── 3. user_swap_profiles ──────────────────────────────────────────────
    op.create_table(
        "user_swap_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("coarse_lat", sa.Float(), nullable=True),
        sa.Column("coarse_lng", sa.Float(), nullable=True),
        sa.Column("area_label", sa.String(length=150), nullable=True),
        sa.Column("radius_km", sa.Integer(), server_default="10", nullable=False),
        sa.Column(
            "modes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "languages",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("is_invisible", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "accepts_newcomers", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("is_18_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_swap_profiles_user_id"),
    )
    op.create_index("ix_user_swap_profiles_user_id", "user_swap_profiles", ["user_id"])
    op.create_index(
        "ix_swap_profiles_coarse_lat_lng",
        "user_swap_profiles",
        ["coarse_lat", "coarse_lng"],
    )

    # ── 4. availability_windows ────────────────────────────────────────────
    op.create_table(
        "availability_windows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time_utc", sa.String(length=5), nullable=False),
        sa.Column("end_time_utc", sa.String(length=5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_availability_windows_user_id", "availability_windows", ["user_id"])
    op.create_index("ix_availability_windows_day_of_week", "availability_windows", ["day_of_week"])

    # ── 5. availability_blackouts ──────────────────────────────────────────
    op.create_table(
        "availability_blackouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("start_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_availability_blackouts_user_id", "availability_blackouts", ["user_id"])
    op.create_index(
        "ix_availability_blackouts_time",
        "availability_blackouts",
        ["start_datetime_utc", "end_datetime_utc"],
    )

    # ── 6. swap_listings ───────────────────────────────────────────────────
    op.create_table(
        "swap_listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("skill_offered_id", sa.Uuid(), nullable=False),
        sa.Column("skill_wanted_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "modes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("area_label", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column(
            "tags",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["skill_offered_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["skill_wanted_id"], ["skills.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swap_listings_user_id", "swap_listings", ["user_id"])
    op.create_index("ix_swap_listings_status", "swap_listings", ["status"])
    op.create_index("ix_swap_listings_skill_offered_id", "swap_listings", ["skill_offered_id"])
    op.create_index("ix_swap_listings_skill_wanted_id", "swap_listings", ["skill_wanted_id"])
    op.create_index("ix_swap_listings_created_at", "swap_listings", ["created_at"])

    # ── 7. swap_requests ───────────────────────────────────────────────────
    op.create_table(
        "swap_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("offered_skill_id", sa.Uuid(), nullable=False),
        sa.Column("wanted_skill_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=20), server_default="video", nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column(
            "proposed_slots",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("counter_note", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["swap_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offered_skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wanted_skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swap_requests_requester_id", "swap_requests", ["requester_id"])
    op.create_index("ix_swap_requests_recipient_id", "swap_requests", ["recipient_id"])
    op.create_index("ix_swap_requests_status", "swap_requests", ["status"])
    op.create_index("ix_swap_requests_expires_at", "swap_requests", ["expires_at"])

    # ── 8. swap_sessions ───────────────────────────────────────────────────
    op.create_table(
        "swap_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("user_a_id", sa.Uuid(), nullable=False),
        sa.Column("user_b_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("mode", sa.String(length=20), server_default="video", nullable=False),
        sa.Column("public_place_name", sa.String(length=150), nullable=True),
        sa.Column("public_place_address", sa.String(length=255), nullable=True),
        sa.Column("jitsi_room_token", sa.String(length=100), nullable=True),
        sa.Column(
            "user_a_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "user_b_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("dispute_reason", sa.Text(), nullable=True),
        sa.Column("disputed_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["disputed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["swap_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_swap_sessions_request_id"),
    )
    op.create_index("ix_swap_sessions_user_a_id", "swap_sessions", ["user_a_id"])
    op.create_index("ix_swap_sessions_user_b_id", "swap_sessions", ["user_b_id"])
    op.create_index("ix_swap_sessions_status", "swap_sessions", ["status"])

    # ── 9. swap_session_halves ─────────────────────────────────────────────
    op.create_table(
        "swap_session_halves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("half_number", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("ics_uid", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["swap_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swap_session_halves_session_id", "swap_session_halves", ["session_id"])
    op.create_index("ix_swap_session_halves_mentor_id", "swap_session_halves", ["mentor_id"])
    op.create_index("ix_swap_session_halves_learner_id", "swap_session_halves", ["learner_id"])
    op.create_index(
        "ix_swap_session_halves_time", "swap_session_halves", ["start_time_utc", "end_time_utc"]
    )

    # ── 10. swap_messages ──────────────────────────────────────────────────
    op.create_table(
        "swap_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["swap_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swap_messages_session_id", "swap_messages", ["session_id"])
    op.create_index("ix_swap_messages_sender_id", "swap_messages", ["sender_id"])
    op.create_index("ix_swap_messages_created_at", "swap_messages", ["created_at"])

    # ── 11. swap_reviews ───────────────────────────────────────────────────
    op.create_table(
        "swap_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("reviewee_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "tags",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("public_comment", sa.Text(), nullable=True),
        sa.Column("private_feedback", sa.Text(), nullable=True),
        sa.Column("is_revealed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["swap_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "reviewer_id", name="uq_session_reviewer"),
    )
    op.create_index("ix_swap_reviews_session_id", "swap_reviews", ["session_id"])
    op.create_index("ix_swap_reviews_reviewer_id", "swap_reviews", ["reviewer_id"])
    op.create_index("ix_swap_reviews_reviewee_id", "swap_reviews", ["reviewee_id"])
    op.create_index("ix_swap_reviews_is_revealed", "swap_reviews", ["is_revealed"])

    # ── 12. user_blocks ────────────────────────────────────────────────────
    op.create_table(
        "user_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocker_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    op.create_index("ix_user_blocks_blocker_id", "user_blocks", ["blocker_id"])
    op.create_index("ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"])

    # ── 13. swap_reports ───────────────────────────────────────────────────
    op.create_table(
        "swap_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("admin_resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swap_reports_reporter_id", "swap_reports", ["reporter_id"])
    op.create_index("ix_swap_reports_target_id", "swap_reports", ["target_id"])
    op.create_index("ix_swap_reports_status", "swap_reports", ["status"])

    # ── 14. trust_scores ───────────────────────────────────────────────────
    op.create_table(
        "trust_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="100", nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("no_show_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cancellation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avg_rating", sa.Float(), server_default="5.0", nullable=False),
        sa.Column(
            "badges",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_trust_scores_user_id"),
    )
    op.create_index("ix_trust_scores_user_id", "trust_scores", ["user_id"])

    # ── 15. reciprocity_ledger ─────────────────────────────────────────────
    op.create_table(
        "reciprocity_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("minutes_taught", sa.Integer(), server_default="0", nullable=False),
        sa.Column("minutes_learned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("net_balance_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("grace_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_reciprocity_ledger_user_id"),
    )
    op.create_index("ix_reciprocity_ledger_user_id", "reciprocity_ledger", ["user_id"])

    # ── 16. match_explanations ─────────────────────────────────────────────
    op.create_table(
        "match_explanations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_a_id", sa.Uuid(), nullable=False),
        sa.Column("user_b_id", sa.Uuid(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_explanations_input_hash", "match_explanations", ["input_hash"])
    op.create_index("ix_match_explanations_users", "match_explanations", ["user_a_id", "user_b_id"])

    # ── 17. job_runs ───────────────────────────────────────────────────────
    op.create_table(
        "job_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
        sa.Column("records_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])


def downgrade() -> None:
    op.drop_table("job_runs")
    op.drop_table("match_explanations")
    op.drop_table("reciprocity_ledger")
    op.drop_table("trust_scores")
    op.drop_table("swap_reports")
    op.drop_table("user_blocks")
    op.drop_table("swap_reviews")
    op.drop_table("swap_messages")
    op.drop_table("swap_session_halves")
    op.drop_table("swap_sessions")
    op.drop_table("swap_requests")
    op.drop_table("swap_listings")
    op.drop_table("availability_blackouts")
    op.drop_table("availability_windows")
    op.drop_table("user_swap_profiles")
    op.drop_table("user_skills")
    op.drop_table("skills")
