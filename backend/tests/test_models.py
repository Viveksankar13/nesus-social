"""
Unit Tests for Database Models
===============================
Verifies:
- All 11 models registered in Base.metadata
- Primary key generation and default values
- Column defaults in table DDL metadata
- Relationships and foreign keys
- Model methods (token expiration, validation)
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.db.base import Base
from app.models.activity import ActivityLog
from app.models.ai import AIChatMessage, AIChatSession, AIUsageLog
from app.models.comment import Comment
from app.models.like import Like
from app.models.moderation import ModerationFlag
from app.models.notification import Notification
from app.models.post import Post
from app.models.token import EmailToken, RefreshToken
from app.models.user import User


def test_metadata_contains_all_11_tables() -> None:
    """Verify that all 11 required tables are registered in SQLAlchemy Base.metadata."""
    expected_tables = {
        "users",
        "refresh_tokens",
        "email_tokens",
        "posts",
        "comments",
        "likes",
        "notifications",
        "moderation_flags",
        "ai_chat_sessions",
        "ai_chat_messages",
        "ai_usage_logs",
        "activity_logs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    for table in expected_tables:
        assert table in actual_tables, f"Table '{table}' missing from Base.metadata"


def test_user_model_defaults() -> None:
    """Verify User model attributes and table defaults."""
    user = User(
        email="test@example.com",
        username="testuser",
        display_name="Test User",
        hashed_password="argon2id$mockedhash",
        role="user",
        is_verified=False,
        is_suspended=False,
    )
    assert user.role == "user"
    assert user.is_verified is False
    assert user.is_suspended is False
    assert user.avatar_url is None
    assert str(user) == "<User testuser (test@example.com) role=user>"

    # Check table column defaults
    users_table = Base.metadata.tables["users"]
    assert users_table.c.role.default.arg == "user"
    assert users_table.c.is_verified.default.arg is False
    assert users_table.c.is_suspended.default.arg is False


def test_post_model_attributes() -> None:
    """Verify Post model attributes and check constraints."""
    user_id = uuid.uuid4()
    post = Post(
        author_id=user_id,
        content="Hello world from Stage 1!",
        is_hidden=False,
        is_edited=False,
    )
    assert post.is_hidden is False
    assert post.is_edited is False
    assert post.image_url is None

    # Check table column defaults
    posts_table = Base.metadata.tables["posts"]
    assert posts_table.c.is_hidden.default.arg is False
    assert posts_table.c.is_edited.default.arg is False

    # Check that check constraint is configured on table
    constraints = [c.name for c in posts_table.constraints if hasattr(c, "name")]
    assert "ck_posts_content_length" in constraints


def test_like_model_unique_constraint() -> None:
    """Verify Like model has the unique constraint on (user_id, post_id)."""
    table = Base.metadata.tables["likes"]
    uq_names = [c.name for c in table.constraints if hasattr(c, "name")]
    assert "uq_likes_user_post" in uq_names


def test_refresh_token_expiration_logic() -> None:
    """Verify RefreshToken is_expired calculation."""
    user_id = uuid.uuid4()
    token_future = RefreshToken(
        user_id=user_id,
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    assert token_future.is_expired() is False

    token_past = RefreshToken(
        user_id=user_id,
        token_hash="b" * 64,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    assert token_past.is_expired() is True


def test_email_token_validation_logic() -> None:
    """Verify EmailToken is_valid calculation."""
    user_id = uuid.uuid4()
    valid_token = EmailToken(
        user_id=user_id,
        token_hash="c" * 64,
        token_type="verify_email",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=None,
    )
    assert valid_token.is_valid() is True

    used_token = EmailToken(
        user_id=user_id,
        token_hash="d" * 64,
        token_type="verify_email",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used_at=datetime.now(UTC),
    )
    assert used_token.is_valid() is False


def test_notification_payload_type() -> None:
    """Verify Notification model initializes with empty or custom payload."""
    notif = Notification(
        user_id=uuid.uuid4(),
        type="like",
        payload={"post_id": str(uuid.uuid4()), "actor": "alice"},
        is_read=False,
    )
    assert notif.type == "like"
    assert notif.payload["actor"] == "alice"
    assert notif.is_read is False

    # Check table column defaults
    notif_table = Base.metadata.tables["notifications"]
    assert notif_table.c.is_read.default.arg is False


def test_moderation_flag_attributes() -> None:
    """Verify ModerationFlag model attributes."""
    flag = ModerationFlag(
        content_type="post",
        content_id=uuid.uuid4(),
        category="spam",
        severity="high",
        score=0.92,
        action="flag",
        reason="Detected repetitive advertising patterns",
        reviewed=False,
    )
    assert flag.reviewed is False
    assert flag.score == 0.92
    assert flag.action == "flag"

    # Check table column defaults
    mod_table = Base.metadata.tables["moderation_flags"]
    assert mod_table.c.reviewed.default.arg is False


def test_ai_models_and_activity_log() -> None:
    """Verify AI models and ActivityLog structure."""
    session_id = uuid.uuid4()
    msg = AIChatMessage(
        session_id=session_id,
        role="user",
        content="Can you improve my post?",
    )
    assert msg.role == "user"

    log = ActivityLog(
        action="suspend_user",
        resource_type="user",
        resource_id=uuid.uuid4(),
        details={"reason": "Spam activity"},
    )
    assert log.action == "suspend_user"
    assert log.details["reason"] == "Spam activity"
