"""
Export current database users and seed data into a clean SQL script
that can be pasted directly into Supabase SQL Editor.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_session_factory
from app.models.user import User
from sqlalchemy import select


async def main() -> None:
    async with async_session_factory() as session:
        users = (await session.execute(select(User))).scalars().all()
        lines = [
            "-- =========================================================================",
            "-- Nexus Social — Supabase Database Seed Script",
            "-- Paste this directly into Supabase SQL Editor and click RUN",
            "-- =========================================================================",
            "BEGIN;",
            "",
        ]

        for u in users:
            bio_val = f"'{u.bio.replace("'", "''")}'" if u.bio else "NULL"
            loc_val = f"'{u.location.replace("'", "''")}'" if u.location else "NULL"
            web_val = f"'{u.website.replace("'", "''")}'" if u.website else "NULL"
            ava_val = f"'{u.avatar_url.replace("'", "''")}'" if u.avatar_url else "NULL"
            usn_val = f"'{u.usn}'" if u.usn else "NULL"

            lines.append(
                f"INSERT INTO users (id, email, username, usn, display_name, hashed_password, role, is_verified, is_suspended, bio, location, website, avatar_url, created_at, updated_at) "
                f"VALUES ('{u.id}', '{u.email}', '{u.username}', {usn_val}, '{u.display_name.replace("'", "''")}', '{u.hashed_password}', '{u.role}', {str(u.is_verified).lower()}, {str(u.is_suspended).lower()}, {bio_val}, {loc_val}, {web_val}, {ava_val}, NOW(), NOW()) "
                f"ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password, role = EXCLUDED.role, is_verified = true;"
            )

        lines.append("")
        lines.append("COMMIT;")

        with open("../supabase_seed.sql", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        print(f"Successfully generated supabase_seed.sql with {len(users)} users.")


if __name__ == "__main__":
    asyncio.run(main())
