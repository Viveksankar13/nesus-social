"""
Skill Taxonomy & Fuzzy Matching Service
=======================================
Manages the canonical skills taxonomy, category grouping, fuzzy matching,
and automated suggestion ingestion.
"""

import difflib
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import Skill
from app.schemas.swap import SkillCategoryGroup, SkillResponse


def slugify_skill(name: str) -> str:
    """Generate clean URL-safe slug from skill name."""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


class SwapTaxonomyService:
    """Service handling skill taxonomy lookups and fuzzy normalization."""

    @staticmethod
    async def list_active_skills(db: AsyncSession) -> list[Skill]:
        """Fetch all active canonical skills sorted by category and display name."""
        stmt = (
            select(Skill)
            .where(Skill.status == "active")
            .order_by(Skill.category, Skill.display_name)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_grouped_categories(db: AsyncSession) -> list[SkillCategoryGroup]:
        """Return active skills grouped by category."""
        skills = await SwapTaxonomyService.list_active_skills(db)
        groups: dict[str, list[SkillResponse]] = {}
        for s in skills:
            if s.category not in groups:
                groups[s.category] = []
            groups[s.category].append(SkillResponse.model_validate(s))

        return [SkillCategoryGroup(category=cat, skills=items) for cat, items in groups.items()]

    @staticmethod
    async def find_by_slug(db: AsyncSession, slug: str) -> Skill | None:
        """Find skill by exact slug."""
        stmt = select(Skill).where(Skill.slug == slug)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def fuzzy_match_skill(db: AsyncSession, query: str) -> Skill | None:
        """
        Fuzzy match user query against canonical names, slugs, and aliases.
        Returns the best matching Skill or None if no confident match exists.
        """
        clean_q = query.strip().lower()
        if not clean_q:
            return None

        skills = await SwapTaxonomyService.list_active_skills(db)

        # 1. Exact slug match
        for s in skills:
            if s.slug == clean_q or s.display_name.lower() == clean_q:
                return s

        # 2. Exact alias match
        for s in skills:
            for alias in s.aliases:
                if alias.lower() == clean_q:
                    return s

        # 3. Partial substring match in display_name
        for s in skills:
            if clean_q in s.display_name.lower() or clean_q in s.slug:
                return s

        # 4. Difflib close matches against display names & aliases
        candidates_map: dict[str, Skill] = {}
        for s in skills:
            candidates_map[s.display_name.lower()] = s
            candidates_map[s.slug] = s
            for a in s.aliases:
                candidates_map[a.lower()] = s

        matches = difflib.get_close_matches(clean_q, list(candidates_map.keys()), n=1, cutoff=0.7)
        if matches:
            return candidates_map[matches[0]]

        return None

    @staticmethod
    async def suggest_skill(db: AsyncSession, name: str, category: str) -> Skill:
        """
        Suggest a new skill.
        Auto-approves if valid and doesn't conflict with existing skills.
        """
        clean_name = name.strip()
        slug = slugify_skill(clean_name)
        existing = await SwapTaxonomyService.find_by_slug(db, slug)
        if existing:
            return existing

        # Basic hygiene check: ensure no spam / money words
        forbidden = ["money", "cash", "dollar", "pay", "venmo", "escrow", "crypto"]
        lower = clean_name.lower()
        is_suspicious = any(w in lower for w in forbidden)

        status = "pending" if is_suspicious else "active"

        skill = Skill(
            id=uuid.uuid4(),
            slug=slug,
            display_name=clean_name,
            category=category.strip(),
            aliases=[clean_name.lower()],
            status=status,
            created_at=datetime.now(UTC),
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return skill
