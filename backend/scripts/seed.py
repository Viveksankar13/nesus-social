"""
Database Seed Script
====================
Seeds the database with:
1. Primary Administrator account (configured via environment variables)
2. Optional demo content (--demo flag): users, posts, comments, likes, notifications

Usage:
    python scripts/seed.py
    python scripts/seed.py --demo
"""

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import Base
from app.db.session import async_session_factory, engine
from app.models.comment import Comment
from app.models.like import Like
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    try:
        from argon2 import PasswordHasher

        ph = PasswordHasher()
        return ph.hash(password)
    except ImportError:
        # Fallback hash placeholder for offline/bootstrap testing if argon2-cffi binary is unavailable
        import hashlib

        salt = "nexus_social_salt"
        return f"argon2id_mock${hashlib.sha256((password + salt).encode()).hexdigest()}"


async def seed_admin(session: AsyncSession) -> User:
    """Seed the admin account if it does not already exist."""
    print(f"Checking for admin account ({settings.ADMIN_EMAIL})...")
    stmt = select(User).where(
        (User.email == settings.ADMIN_EMAIL) | (User.username == settings.ADMIN_USERNAME)
    )
    res = await session.execute(stmt)
    existing_admin = res.scalar_one_or_none()

    if existing_admin:
        print(f" Admin user @{existing_admin.username} ({existing_admin.email}) already exists.")
        return existing_admin

    admin = User(
        id=uuid.uuid4(),
        email=settings.ADMIN_EMAIL,
        username=settings.ADMIN_USERNAME,
        display_name="Nexus Administrator",
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role="admin",
        is_verified=True,
        is_suspended=False,
        bio="System Administrator and platform orchestrator for Nexus Social.",
        location="Global HQ",
        website="https://nexussocial.dev",
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop",
    )
    session.add(admin)
    await session.commit()
    print(f" Admin user @{admin.username} created successfully.")
    return admin


async def seed_demo(session: AsyncSession, admin: User) -> None:
    """Seed realistic demo users, posts, comments, likes, and notifications."""
    print("Seeding demo data...")

    demo_users_data = [
        {
            "email": "sarah.chen@example.com",
            "username": "sarah_chen",
            "usn": "1MS21CS001",
            "display_name": "Dr. Sarah Chen",
            "bio": "AI Researcher & Distributed Systems enthusiast. Building the future of neural interfaces.",
            "location": "San Francisco, CA",
            "website": "https://sarahchen.ai",
            "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop",
        },
        {
            "email": "marcus.vance@example.com",
            "username": "marcus_v",
            "usn": "1RV20EC045",
            "display_name": "Marcus Vance",
            "bio": "Full-stack engineer, open-source contributor, and coffee lover. Next.js + FastAPI advocate.",
            "location": "Austin, TX",
            "website": "https://marcusvance.dev",
            "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop",
        },
        {
            "email": "elena.rostova@example.com",
            "username": "elena_designs",
            "usn": "4NI21IS020",
            "display_name": "Elena Rostova",
            "bio": "Design Systems Lead @ FinTech. Passionate about accessibility, typography, and micro-interactions.",
            "location": "London, UK",
            "website": "https://elenarostova.design",
            "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&h=200&fit=crop",
        },
        {
            "email": "devon.miles@example.com",
            "username": "devon_codes",
            "usn": "1PE19CS088",
            "display_name": "Devon Miles",
            "bio": "Kubernetes whisperer and cloud infrastructure engineer. Always automating something.",
            "location": "Seattle, WA",
            "website": "https://devonmiles.cloud",
            "avatar_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop",
        },
        {
            "email": "aiko.tanaka@example.com",
            "username": "aiko_t",
            "usn": "1BM22AI012",
            "display_name": "Aiko Tanaka",
            "bio": "Data Scientist & generative art creator. Finding beauty in latent spaces and high-dimensional manifolds.",
            "location": "Tokyo, Japan",
            "website": "https://aikotanaka.art",
            "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop",
        },
    ]

    users: list[User] = [admin]
    for u_data in demo_users_data:
        stmt = select(User).where(User.email == u_data["email"])
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        if not existing:
            user = User(
                id=uuid.uuid4(),
                email=u_data["email"],
                username=u_data["username"],
                usn=u_data["usn"],
                display_name=u_data["display_name"],
                hashed_password=hash_password("DemoPassword123!"),
                role="user",
                is_verified=True,
                is_suspended=False,
                bio=u_data["bio"],
                location=u_data["location"],
                website=u_data["website"],
                avatar_url=u_data["avatar_url"],
            )
            session.add(user)
            users.append(user)
        else:
            users.append(existing)

    await session.commit()
    print(f" {len(users)} users ready.")

    # Demo Posts
    post_contents = [
        (
            users[1],
            "Excited to launch my thoughts on the new Gemini 2.5 Flash architecture! The reduction in time-to-first-token is genuinely impressive for real-time applications. Has anyone else benchmarked structured JSON output reliability? #AI #Gemini",
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&h=450&fit=crop",
        ),
        (
            users[2],
            "Refining our design system tokens today. When building light/dark mode with CSS variables, remember to test contrast ratios against AA and AAA guidelines for muted text. Small details compound into incredible polish! ✨",
            None,
        ),
        (
            users[3],
            "Just deployed a zero-downtime database migration strategy on PostgreSQL with Alembic. The key is separating column additions from constraint backfills. What are your favorite patterns for zero-downtime schemas?",
            None,
        ),
        (
            users[4],
            "Synthesizing high-resolution procedural textures with diffusion priors. The interplay between geometry and noise is fascinating. Here is a render from last night's experiment! 🎨",
            "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?w=800&h=450&fit=crop",
        ),
        (
            users[0],
            "Welcome to Nexus Social! 🌐 Our mission is to combine genuine human connection with helpful, transparent AI capabilities. Explore the feed, try the post composer, and let us know your thoughts!",
            None,
        ),
    ]

    posts: list[Post] = []
    base_time = datetime.now(UTC) - timedelta(days=2)
    for i, (author, content, img) in enumerate(post_contents):
        stmt = select(Post).where((Post.author_id == author.id) & (Post.content == content))
        res = await session.execute(stmt)
        existing_post = res.scalar_one_or_none()
        if not existing_post:
            post = Post(
                id=uuid.uuid4(),
                author_id=author.id,
                content=content,
                image_url=img,
                is_hidden=False,
                is_edited=False,
                created_at=base_time + timedelta(hours=i * 6),
                updated_at=base_time + timedelta(hours=i * 6),
            )
            session.add(post)
            posts.append(post)
        else:
            posts.append(existing_post)

    await session.commit()
    print(f" {len(posts)} posts ready.")

    # Demo Comments
    if posts:
        target_post = posts[0]
        comments_data = [
            (
                users[2],
                "Great analysis Sarah! We tested JSON mode with Pydantic validation and saw zero malformed responses over 500 runs.",
            ),
            (
                users[3],
                "The latency on streaming chat is what impressed me most. Sub-200ms latency makes the assistant feel instantaneous.",
            ),
            (users[4], "Did you benchmark against 1.5 Pro on complex reasoning prompts?"),
        ]
        comments: list[Comment] = []
        for i, (author, c_text) in enumerate(comments_data):
            stmt = select(Comment).where(
                (Comment.post_id == target_post.id)
                & (Comment.author_id == author.id)
                & (Comment.content == c_text)
            )
            res = await session.execute(stmt)
            existing_c = res.scalar_one_or_none()
            if not existing_c:
                c = Comment(
                    id=uuid.uuid4(),
                    post_id=target_post.id,
                    author_id=author.id,
                    content=c_text,
                    is_hidden=False,
                    is_edited=False,
                    created_at=base_time + timedelta(hours=i + 1),
                    updated_at=base_time + timedelta(hours=i + 1),
                )
                session.add(c)
                comments.append(c)
            else:
                comments.append(existing_c)

        await session.commit()

        # Threaded reply (one-level)
        if comments:
            parent_comment = comments[0]
            reply_text = "Thanks Marcus! Yes, the strict schema enforcement makes it rock-solid for backend pipelines."
            stmt = select(Comment).where(Comment.parent_id == parent_comment.id)
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                reply = Comment(
                    id=uuid.uuid4(),
                    post_id=target_post.id,
                    author_id=users[1].id,
                    parent_id=parent_comment.id,
                    content=reply_text,
                    is_hidden=False,
                    is_edited=False,
                    created_at=base_time + timedelta(hours=3),
                    updated_at=base_time + timedelta(hours=3),
                )
                session.add(reply)
                await session.commit()

        print(f" Comments and threaded replies seeded for post '{target_post.content[:30]}...'")

    # Demo Likes
    like_count = 0
    for p in posts:
        for u in users[:3]:
            stmt = select(Like).where((Like.user_id == u.id) & (Like.post_id == p.id))
            res = await session.execute(stmt)
            if not res.scalar_one_or_none():
                like = Like(
                    id=uuid.uuid4(),
                    user_id=u.id,
                    post_id=p.id,
                    created_at=datetime.now(UTC),
                )
                session.add(like)
                like_count += 1
    await session.commit()
    print(f" {like_count} likes seeded.")

    # Demo Notification
    if len(users) > 1 and posts:
        stmt = select(Notification).where(Notification.user_id == users[1].id)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            notif = Notification(
                id=uuid.uuid4(),
                user_id=users[1].id,
                type="like",
                payload={
                    "actor_id": str(users[2].id),
                    "actor_name": users[2].display_name,
                    "actor_avatar": users[2].avatar_url,
                    "post_id": str(posts[0].id),
                    "post_preview": posts[0].content[:60],
                },
                is_read=False,
                created_at=datetime.now(UTC) - timedelta(minutes=15),
            )
            session.add(notif)
            await session.commit()
            print(" Sample notification created.")


async def main(demo: bool = False) -> None:
    """Run database seeding process."""
    print("🌱 Nexus Social — Database Seeder")
    print(f"Environment: {settings.ENVIRONMENT}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_factory() as session:
        try:
            admin = await seed_admin(session)
            if demo:
                await seed_demo(session, admin)
            print("✅ Database seeding complete.")
        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Nexus Social database")
    parser.add_argument(
        "--demo", action="store_true", help="Also seed demo users, posts, comments, and likes"
    )
    args = parser.parse_args()
    asyncio.run(main(demo=args.demo))
