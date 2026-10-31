"""Add friendships, conversations, and direct_messages tables

Revision ID: 0003_add_friends_and_messages
Revises: 0002_add_student_usn
Create Date: 2026-10-31 07:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_friends_and_messages"
down_revision: str | None = "0002_add_student_usn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── friendships ────────────────────────────────────────────────────────
    op.create_table(
        "friendships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("receiver_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sender_id", "receiver_id", name="uq_friendships_sender_receiver"),
    )
    op.create_index("ix_friendships_receiver_id", "friendships", ["receiver_id"])
    op.create_index("ix_friendships_sender_id", "friendships", ["sender_id"])
    op.create_index("ix_friendships_status", "friendships", ["status"])
    op.create_index("ix_friendships_status_receiver", "friendships", ["status", "receiver_id"])
    op.create_index("ix_friendships_status_sender", "friendships", ["status", "sender_id"])

    # ── conversations ──────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user1_id", sa.Uuid(), nullable=False),
        sa.Column("user2_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user1_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user2_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user1_id", "user2_id", name="uq_conversations_user1_user2"),
    )
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_index("ix_conversations_user1_id", "conversations", ["user1_id"])
    op.create_index("ix_conversations_user2_id", "conversations", ["user2_id"])
    op.create_index("ix_conversations_users", "conversations", ["user1_id", "user2_id"])

    # ── direct_messages ────────────────────────────────────────────────────
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_direct_messages_conversation_id", "direct_messages", ["conversation_id"])
    op.create_index("ix_direct_messages_created_at", "direct_messages", ["created_at"])
    op.create_index("ix_direct_messages_is_read", "direct_messages", ["is_read"])
    op.create_index("ix_direct_messages_sender_id", "direct_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_table("direct_messages")
    op.drop_table("conversations")
    op.drop_table("friendships")

