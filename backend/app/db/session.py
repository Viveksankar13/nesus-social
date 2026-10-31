"""
Database Engine and Session Factory
====================================
Configures the async SQLAlchemy 2.0 engine and provides the `get_db`
dependency for FastAPI routes.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Engine pool settings suitable for both production and local dev
engine_kwargs: dict[str, object] = {
    "echo": settings.ENVIRONMENT == "development",
    "future": True,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
    )
    # Supabase / PgBouncer transaction pooler (port 6543) requires disabling statement cache in asyncpg
    if ":6543" in settings.DATABASE_URL:
        engine_kwargs["connect_args"] = {"statement_cache_size": 0}

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an active async database session.
    Automatically commits on success or rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
