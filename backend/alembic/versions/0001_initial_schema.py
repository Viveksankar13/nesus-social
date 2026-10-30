"""Initial database schema: 11 tables

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_suspended", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # ── 2. refresh_tokens ────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False
    )
    op.create_index(
        "ix_refresh_tokens_family_revoked", "refresh_tokens", ["family_id", "revoked"], unique=False
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(
        op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    # ── 3. email_tokens ──────────────────────────────────────────────────────
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_email_tokens_token_hash")),
    )
    op.create_index(op.f("ix_email_tokens_id"), "email_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_email_tokens_token_hash"), "email_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_email_tokens_user_id"), "email_tokens", ["user_id"], unique=False)

    # ── 4. posts ─────────────────────────────────────────────────────────────
    op.create_table(
        "posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(content) <= 1000", name="ck_posts_content_length"),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_posts_author_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
    )
    op.create_index(op.f("ix_posts_author_id"), "posts", ["author_id"], unique=False)
    op.create_index(
        "ix_posts_author_created_at", "posts", ["author_id", "created_at"], unique=False
    )
    op.create_index("ix_posts_feed_created_at", "posts", ["created_at"], unique=False)
    op.create_index(op.f("ix_posts_id"), "posts", ["id"], unique=False)
    op.create_index(op.f("ix_posts_is_hidden"), "posts", ["is_hidden"], unique=False)

    # ── 5. comments ──────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(content) <= 500", name="ck_comments_content_length"),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_comments_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["comments.id"],
            name=op.f("fk_comments_parent_id_comments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], name=op.f("fk_comments_post_id_posts"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(op.f("ix_comments_author_id"), "comments", ["author_id"], unique=False)
    op.create_index(op.f("ix_comments_id"), "comments", ["id"], unique=False)
    op.create_index(op.f("ix_comments_is_hidden"), "comments", ["is_hidden"], unique=False)
    op.create_index(op.f("ix_comments_parent_id"), "comments", ["parent_id"], unique=False)
    op.create_index("ix_comments_post_created", "comments", ["post_id", "created_at"], unique=False)
    op.create_index(op.f("ix_comments_post_id"), "comments", ["post_id"], unique=False)

    # ── 6. likes ─────────────────────────────────────────────────────────────
    op.create_table(
        "likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], name=op.f("fk_likes_post_id_posts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_likes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_likes")),
        sa.UniqueConstraint("user_id", "post_id", name="uq_likes_user_post"),
    )
    op.create_index(op.f("ix_likes_id"), "likes", ["id"], unique=False)
    op.create_index(op.f("ix_likes_post_id"), "likes", ["post_id"], unique=False)
    op.create_index(op.f("ix_likes_user_id"), "likes", ["user_id"], unique=False)

    # ── 7. notifications ─────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_notifications_user_read", "notifications", ["user_id", "is_read"], unique=False
    )

    # ── 8. moderation_flags ──────────────────────────────────────────────────
    op.create_table(
        "moderation_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_flags")),
    )
    op.create_index(
        "ix_moderation_content", "moderation_flags", ["content_type", "content_id"], unique=False
    )
    op.create_index(
        op.f("ix_moderation_flags_content_id"), "moderation_flags", ["content_id"], unique=False
    )
    op.create_index(op.f("ix_moderation_flags_id"), "moderation_flags", ["id"], unique=False)
    op.create_index(
        op.f("ix_moderation_flags_reviewed"), "moderation_flags", ["reviewed"], unique=False
    )
    op.create_index("ix_moderation_queue", "moderation_flags", ["reviewed", "action"], unique=False)

    # ── 9. ai_chat_sessions ──────────────────────────────────────────────────
    op.create_table(
        "ai_chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "title", sa.String(length=150), server_default="New Conversation", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_chat_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_chat_sessions")),
    )
    op.create_index(op.f("ix_ai_chat_sessions_id"), "ai_chat_sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_ai_chat_sessions_user_id"), "ai_chat_sessions", ["user_id"], unique=False
    )

    # ── 10. ai_chat_messages ─────────────────────────────────────────────────
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_chat_sessions.id"],
            name=op.f("fk_ai_chat_messages_session_id_ai_chat_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_chat_messages")),
    )
    op.create_index(op.f("ix_ai_chat_messages_id"), "ai_chat_messages", ["id"], unique=False)
    op.create_index(
        op.f("ix_ai_chat_messages_session_id"), "ai_chat_messages", ["session_id"], unique=False
    )

    # ── 11. ai_usage_logs ────────────────────────────────────────────────────
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_usage_logs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_usage_logs")),
    )
    op.create_index(
        "ix_ai_usage_feature_status", "ai_usage_logs", ["feature", "status"], unique=False
    )
    op.create_index(
        "ix_ai_usage_user_date", "ai_usage_logs", ["user_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_ai_usage_logs_id"), "ai_usage_logs", ["id"], unique=False)
    op.create_index(op.f("ix_ai_usage_logs_user_id"), "ai_usage_logs", ["user_id"], unique=False)

    # ── 12. activity_logs ────────────────────────────────────────────────────
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name=op.f("fk_activity_logs_admin_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_logs")),
    )
    op.create_index(
        "ix_activity_admin_created", "activity_logs", ["admin_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_activity_logs_admin_id"), "activity_logs", ["admin_id"], unique=False)
    op.create_index(op.f("ix_activity_logs_id"), "activity_logs", ["id"], unique=False)
    op.create_index(
        "ix_activity_resource", "activity_logs", ["resource_type", "resource_id"], unique=False
    )


def downgrade() -> None:
    op.drop_table("activity_logs")
    op.drop_table("ai_usage_logs")
    op.drop_table("ai_chat_messages")
    op.drop_table("ai_chat_sessions")
    op.drop_table("moderation_flags")
    op.drop_table("notifications")
    op.drop_table("likes")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("email_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
