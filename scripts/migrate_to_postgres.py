"""
Database Migration Script: SQLite -> PostgreSQL (Docker)
=========================================================
Migrates all platform entities, users, skills, posts, and swap data
from local SQLite (nexus_dev.db) into PostgreSQL running in Docker.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import app.models  # ensure all models are imported
from app.db.base import Base

SQLITE_URL = "sqlite+aiosqlite:///backend/nexus_dev.db"
POSTGRES_URL = "postgresql+asyncpg://socialmedia:devpassword@localhost:5432/socialmedia"

# Tables in dependency order
TABLE_MODELS = [
    app.models.User,
    app.models.RefreshToken,
    app.models.EmailToken,
    app.models.ActivityLog,
    app.models.AIUsageLog,
    app.models.Post,
    app.models.Comment,
    app.models.Like,
    app.models.Friendship,
    app.models.Conversation,
    app.models.DirectMessage,
    app.models.Notification,
    app.models.AIChatSession,
    app.models.AIChatMessage,
    app.models.ModerationFlag,
    app.models.Skill,
    app.models.UserSkill,
    app.models.UserSwapProfile,
    app.models.AvailabilityWindow,
    app.models.AvailabilityBlackout,
    app.models.SwapListing,
    app.models.SwapRequest,
    app.models.SwapSession,
    app.models.SwapSessionHalf,
    app.models.SwapMessage,
    app.models.SwapReview,
    app.models.UserBlock,
    app.models.SwapReport,
    app.models.TrustScore,
    app.models.ReciprocityLedger,
    app.models.MatchExplanation,
    app.models.JobRun,
]

async def migrate():
    sqlite_engine = create_async_engine(SQLITE_URL, echo=False)
    pg_engine = create_async_engine(POSTGRES_URL, echo=False)

    sqlite_session = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    pg_session = async_sessionmaker(pg_engine, expire_on_commit=False)

    print("Beginning migration from SQLite to PostgreSQL (Docker)...")

    async with sqlite_session() as s_db, pg_session() as pg_db:
        for model in TABLE_MODELS:
            table_name = model.__tablename__
            try:
                # Read from SQLite
                stmt = select(model)
                results = (await s_db.execute(stmt)).scalars().all()
                if not results:
                    continue

                if model == app.models.Comment:
                    existing_post_ids = set((await pg_db.execute(select(app.models.Post.id))).scalars().all())
                    results = [item for item in results if item.post_id in existing_post_ids]

                if model == app.models.Like:
                    existing_post_ids = set((await pg_db.execute(select(app.models.Post.id))).scalars().all())
                    results = [item for item in results if item.post_id in existing_post_ids]

                # Insert into PostgreSQL
                for item in results:
                    # Merge item into postgres session
                    data = {c.name: getattr(item, c.name) for c in model.__table__.columns}
                    new_item = model(**data)
                    await pg_db.merge(new_item)

                await pg_db.commit()
                print(f"  [OK] Migrated {len(results)} rows for table '{table_name}'")
            except Exception as e:
                await pg_db.rollback()
                print(f"  [SKIP/ERROR] Table '{table_name}': {e}")

    await sqlite_engine.dispose()
    await pg_engine.dispose()
    print("Migration finished!")

if __name__ == "__main__":
    asyncio.run(migrate())
