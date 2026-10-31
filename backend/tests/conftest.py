"""
Pytest Configuration and Shared Fixtures
=========================================
Provides shared fixtures for all backend tests:
- Isolated in-memory async SQLite database session (`test_db_session`)
- Async HTTP test client with database override (`client`)
- Helper fixture to create authenticated test users with JWT headers (`create_user`)
"""

import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.security import hash_password
from app.core.tokens import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Isolated in-memory database session fixture."""
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


@pytest.fixture
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with database dependency override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(
    test_db_session: AsyncSession,
) -> Callable[..., Any]:
    """Factory fixture to insert a user and return (User, auth_headers)."""

    async def _create_user(
        username: str = "testuser",
        email: str = "testuser@example.com",
        display_name: str = "Test User",
        password: str = "StrongPass123!",
        role: str = "user",
        is_verified: bool = True,
        is_suspended: bool = False,
    ) -> tuple[User, dict[str, str]]:
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            display_name=display_name,
            hashed_password=hash_password(password),
            role=role,
            is_verified=is_verified,
            is_suspended=is_suspended,
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)

        token = create_access_token(
            user_id=user.id,
            role=user.role,
        )
        headers = {"Authorization": f"Bearer {token}"}
        return user, headers

    return _create_user
