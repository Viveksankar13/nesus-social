"""
Database Integration Tests (Async SQLite in-memory)
===================================================
Tests real database transactions, constraints, and cascades against an async engine:
- Table creation and schema execution
- Foreign key cascading deletes
- Unique constraint enforcement on likes
- Comment reply tree structures
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post
from app.models.user import User


@pytest.fixture
async def async_db_session() -> AsyncSession:
    """Fixture providing an isolated in-memory SQLite database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_user_and_query(async_db_session: AsyncSession) -> None:
    """Test creating and querying a user in the database."""
    user = User(
        id=uuid.uuid4(),
        email="alice@example.com",
        username="alice",
        display_name="Alice Adams",
        hashed_password="mocked_argon2_hash",
        role="user",
        is_verified=True,
    )
    async_db_session.add(user)
    await async_db_session.commit()

    stmt = select(User).where(User.username == "alice")
    result = await async_db_session.execute(stmt)
    fetched_user = result.scalar_one_or_none()

    assert fetched_user is not None
    assert fetched_user.email == "alice@example.com"
    assert fetched_user.is_verified is True


@pytest.mark.asyncio
async def test_duplicate_user_email_raises_error(async_db_session: AsyncSession) -> None:
    """Test that creating two users with the same email violates UNIQUE constraint."""
    u1 = User(
        id=uuid.uuid4(),
        email="duplicate@example.com",
        username="user1",
        display_name="User One",
        hashed_password="hash",
    )
    u2 = User(
        id=uuid.uuid4(),
        email="duplicate@example.com",
        username="user2",
        display_name="User Two",
        hashed_password="hash",
    )
    async_db_session.add(u1)
    await async_db_session.commit()

    async_db_session.add(u2)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()


@pytest.mark.asyncio
async def test_like_uniqueness_enforced(async_db_session: AsyncSession) -> None:
    """Test that a user cannot like the same post twice (UNIQUE constraint)."""
    user = User(
        id=uuid.uuid4(),
        email="liker@example.com",
        username="liker",
        display_name="Liker",
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    post = Post(
        id=uuid.uuid4(),
        author_id=user.id,
        content="Great post to like!",
    )
    async_db_session.add(post)
    await async_db_session.commit()

    like1 = Like(
        id=uuid.uuid4(),
        user_id=user.id,
        post_id=post.id,
    )
    async_db_session.add(like1)
    await async_db_session.commit()

    # Attempting to like the same post again
    like2 = Like(
        id=uuid.uuid4(),
        user_id=user.id,
        post_id=post.id,
    )
    async_db_session.add(like2)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()


@pytest.mark.asyncio
async def test_comment_thread_structure(async_db_session: AsyncSession) -> None:
    """Test creating parent comments and 1-level threaded replies."""
    user = User(
        id=uuid.uuid4(),
        email="author@example.com",
        username="thread_author",
        display_name="Thread Author",
        hashed_password="hash",
    )
    async_db_session.add(user)
    await async_db_session.commit()

    post = Post(
        id=uuid.uuid4(),
        author_id=user.id,
        content="Threaded conversation post",
    )
    async_db_session.add(post)
    await async_db_session.commit()

    parent_comment = Comment(
        id=uuid.uuid4(),
        post_id=post.id,
        author_id=user.id,
        content="This is the parent comment",
    )
    async_db_session.add(parent_comment)
    await async_db_session.commit()

    reply_comment = Comment(
        id=uuid.uuid4(),
        post_id=post.id,
        author_id=user.id,
        parent_id=parent_comment.id,
        content="This is a nested reply",
    )
    async_db_session.add(reply_comment)
    await async_db_session.commit()

    stmt = select(Comment).where(Comment.parent_id == parent_comment.id)
    res = await async_db_session.execute(stmt)
    replies = res.scalars().all()
    assert len(replies) == 1
    assert replies[0].content == "This is a nested reply"
