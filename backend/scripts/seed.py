"""
Database Seed Script
====================
Populates the database with:
1. Admin user (from env vars) — always
2. Demo users, posts, comments, likes — with --demo flag

Usage:
    cd backend
    python scripts/seed.py
    python scripts/seed.py --demo

Populated in Stage 1 with actual model imports.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


async def seed_admin() -> None:
    """Create the admin user from environment variables."""
    from app.core.config import settings
    print(f"Would seed admin user: {settings.ADMIN_EMAIL} / @{settings.ADMIN_USERNAME}")
    print("(Full implementation in Stage 1 after database models are defined)")


async def seed_demo() -> None:
    """Create demo users and content."""
    print("Would seed demo data: 10 users, 50 posts, 100 comments, 200 likes")
    print("(Full implementation in Stage 1 after database models are defined)")


async def main(demo: bool = False) -> None:
    """Run the seed script."""
    print("🌱 Nexus Social — Database Seeder")
    await seed_admin()
    if demo:
        await seed_demo()
    print("✅ Seed complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Nexus Social database")
    parser.add_argument("--demo", action="store_true", help="Also seed demo data")
    args = parser.parse_args()
    asyncio.run(main(demo=args.demo))
