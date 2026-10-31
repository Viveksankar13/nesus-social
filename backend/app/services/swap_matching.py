"""
Skill Swap Matching Engine
==========================
Transparent weighted recommendation engine:
- Mutual skill match (canonical match + category overlap) (35%)
- Spatial proximity & remote mode compatibility (25%)
- 14-day recurring availability overlap (20%)
- Peer trust score (15%)
- Listing freshness and active engagement (5%)

Includes Gemini-powered 'Why you match' explanation generation with SHA-256 caching.
"""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.swap import (
    AvailabilityWindow,
    MatchExplanation,
    SwapListing,
    TrustScore,
    UserBlock,
    UserSkill,
    UserSwapProfile,
)
from app.models.user import User
from app.schemas.swap import (
    ListingAIDraftRequest,
    ListingAIDraftResponse,
    PublicUserMinimal,
    SkillResponse,
    SwapListingResponse,
    SwapMatchResponse,
)
from app.services.ai import get_ai_service
from app.services.ai.prompts import (
    SWAP_LISTING_DRAFT_SYSTEM_PROMPT,
    SWAP_MATCH_EXPLANATION_SYSTEM_PROMPT,
    build_listing_draft_prompt,
    build_match_explanation_prompt,
)
from app.services.swap_geocoding import calculate_haversine_km, get_distance_bucket

logger = logging.getLogger("nexus.swap.matching")


class SwapMatchingService:
    """Core domain matching engine with cached AI explanations."""

    @staticmethod
    def calculate_match_score(
        viewer_profile: UserSwapProfile | None,
        viewer_teach_slugs: set[str],
        viewer_learn_slugs: set[str],
        viewer_learn_categories: set[str],
        viewer_windows: list[AvailabilityWindow],
        listing: SwapListing,
        owner_profile: UserSwapProfile | None,
        owner_windows: list[AvailabilityWindow],
        owner_trust_score: int,
    ) -> tuple[float, dict[str, float]]:
        """
        Compute transparent weighted score S in [0.0, 1.0].
        Weights configured via MATCH_WEIGHT_* settings.
        """
        # 1. Skill Match (Weight: settings.MATCH_WEIGHT_SKILL, default 0.35)
        # Does listing offer what viewer wants to learn?
        skill_score = 0.0
        offered_slug = listing.skill_offered.slug if listing.skill_offered else ""
        offered_cat = listing.skill_offered.category if listing.skill_offered else ""

        if offered_slug in viewer_learn_slugs:
            skill_score += 0.6  # Exact match for learning
        elif offered_cat in viewer_learn_categories:
            skill_score += 0.35  # Category match for learning
        else:
            skill_score += 0.1  # Discovery discovery baseline

        # Does viewer teach what listing wants to learn?
        if not listing.skill_wanted_id:
            skill_score += 0.4  # Listing is open to anything / pay it forward
        else:
            wanted_slug = listing.skill_wanted.slug if listing.skill_wanted else ""
            wanted_cat = listing.skill_wanted.category if listing.skill_wanted else ""
            if wanted_slug in viewer_teach_slugs:
                skill_score += 0.4
            elif wanted_cat in viewer_learn_categories:
                skill_score += 0.2
            else:
                skill_score += 0.1
        skill_score = min(1.0, skill_score)

        # 2. Proximity & Mode Compatibility (Weight: settings.MATCH_WEIGHT_PROXIMITY, default 0.25)
        prox_score = 0.5  # baseline
        listing_modes = set(listing.modes or ["video"])
        viewer_modes = set(viewer_profile.modes if viewer_profile else ["video"])

        # If remote/video is shared
        has_video_overlap = bool(
            {"video", "remote", "chat-only", "chat_only"} & listing_modes & viewer_modes
        )
        has_inperson_overlap = "in_person" in listing_modes and "in_person" in viewer_modes

        if viewer_profile and owner_profile and has_inperson_overlap:
            dist = calculate_haversine_km(
                viewer_profile.coarse_lat,
                viewer_profile.coarse_lng,
                owner_profile.coarse_lat,
                owner_profile.coarse_lng,
            )
            if dist < 3.0:
                prox_score = 1.0
            elif dist < 10.0:
                prox_score = 0.8
            elif dist <= 25.0:
                prox_score = 0.6
            elif has_video_overlap:
                prox_score = 0.75
            else:
                prox_score = 0.3
        elif has_video_overlap:
            prox_score = 0.85
        else:
            prox_score = 0.4

        # 3. Availability Overlap (Weight: settings.MATCH_WEIGHT_AVAILABILITY, default 0.20)
        avail_score = 0.5  # default baseline if either has not filled windows
        if viewer_windows and owner_windows:
            overlap_days = 0
            for vw in viewer_windows:
                for ow in owner_windows:
                    if vw.day_of_week == ow.day_of_week:
                        # Overlap check
                        if (
                            vw.start_time_utc < ow.end_time_utc
                            and vw.end_time_utc > ow.start_time_utc
                        ):
                            overlap_days += 1
                            break
            if overlap_days >= 2:
                avail_score = 1.0
            elif overlap_days == 1:
                avail_score = 0.75
            else:
                avail_score = 0.35

        # 4. Trust Score (Weight: settings.MATCH_WEIGHT_TRUST, default 0.15)
        trust_normalized = max(0.0, min(1.0, owner_trust_score / 100.0))

        # 5. Freshness / Activity (Weight: settings.MATCH_WEIGHT_FRESHNESS, default 0.05)
        now = datetime.now(UTC)
        created_at = listing.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        age_days = (now - created_at).total_seconds() / 86400.0
        freshness_score = max(0.0, 1.0 - (age_days / 30.0))

        total_score = (
            (skill_score * settings.MATCH_WEIGHT_SKILL)
            + (prox_score * settings.MATCH_WEIGHT_PROXIMITY)
            + (avail_score * settings.MATCH_WEIGHT_AVAILABILITY)
            + (trust_normalized * settings.MATCH_WEIGHT_TRUST)
            + (freshness_score * settings.MATCH_WEIGHT_FRESHNESS)
        )
        total_score = round(min(1.0, max(0.0, total_score)), 3)

        breakdown = {
            "skill_match": round(skill_score, 2),
            "proximity": round(prox_score, 2),
            "availability": round(avail_score, 2),
            "trust": round(trust_normalized, 2),
            "freshness": round(freshness_score, 2),
        }
        return total_score, breakdown

    @staticmethod
    async def get_or_create_match_explanation(
        db: AsyncSession,
        viewer: User,
        viewer_learn_skills: list[str],
        viewer_teach_skills: list[str],
        listing: SwapListing,
        distance_bucket: str,
    ) -> str:
        """
        Retrieve cached match explanation or generate one via Gemini with SHA-256 caching.
        """
        # SHA-256 hash of input context
        input_str = (
            f"{viewer.id}:{listing.id}:{listing.skill_offered.slug}:"
            f"{listing.skill_wanted.slug if listing.skill_wanted else 'open'}"
        )
        input_hash = hashlib.sha256(input_str.encode("utf-8")).hexdigest()

        now = datetime.now(UTC)
        # Check cache in DB
        cache_stmt = select(MatchExplanation).where(
            MatchExplanation.input_hash == input_hash,
            MatchExplanation.expires_at > now,
        )
        cache_res = await db.execute(cache_stmt)
        cached = cache_res.scalar_one_or_none()
        if cached:
            return cached.explanation

        # Generate explanation
        explanation = (
            f"Great match! {listing.user.display_name} teaches "
            f"{listing.skill_offered.display_name}, aligning with your learning goals."
        )

        try:
            ai_service = get_ai_service()
            if ai_service.enabled and ai_service.client:
                prompt = build_match_explanation_prompt(
                    viewer_learning=viewer_learn_skills,
                    viewer_teaching=viewer_teach_skills,
                    listing_title=listing.title,
                    skill_offered=listing.skill_offered.display_name,
                    skill_wanted=(
                        listing.skill_wanted.display_name if listing.skill_wanted else None
                    ),
                    distance_bucket=distance_bucket,
                )
                response = await ai_service.client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "system_instruction": SWAP_MATCH_EXPLANATION_SYSTEM_PROMPT,
                        "temperature": 0.4,
                        "max_output_tokens": 100,
                    },
                )
                if response and response.text:
                    cleaned = response.text.strip().replace("\n", " ")
                    if cleaned:
                        explanation = cleaned
        except Exception as e:
            logger.warning("Gemini match explanation generation error: %s; using fallback.", e)

        # Store in cache
        cache_entry = MatchExplanation(
            id=uuid.uuid4(),
            user_a_id=viewer.id,
            user_b_id=listing.user_id,
            input_hash=input_hash,
            explanation=explanation,
            expires_at=now + timedelta(days=7),
            created_at=now,
        )
        db.add(cache_entry)
        await db.commit()

        return explanation

    @staticmethod
    async def generate_listing_draft(
        req: ListingAIDraftRequest,
    ) -> ListingAIDraftResponse:
        """AI helper to draft an engaging listing title, description, and tags."""
        default_title = f"{req.skill_offered_name} Peer Help & Mentorship"
        default_desc = (
            f"Offering a focused 30-minute swap session on {req.skill_offered_name}. "
            f"{req.notes or 'Happy to explain core principles, review code, or share tips!'}"
        )
        default_tags = [
            req.skill_offered_name.lower()[:20],
            "peer-swap",
            "mentorship",
        ]

        try:
            ai_service = get_ai_service()
            if ai_service.enabled and ai_service.client:
                prompt = build_listing_draft_prompt(
                    skill_offered=req.skill_offered_name,
                    skill_wanted=req.skill_wanted_name,
                    notes=req.notes,
                )
                response = await ai_service.client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "system_instruction": SWAP_LISTING_DRAFT_SYSTEM_PROMPT,
                        "temperature": 0.5,
                        "response_mime_type": "application/json",
                    },
                )
                if response and response.text:
                    data = json.loads(response.text)
                    return ListingAIDraftResponse(
                        title=data.get("title", default_title),
                        description=data.get("description", default_desc),
                        suggested_tags=data.get("suggested_tags", default_tags),
                    )
        except Exception as e:
            logger.warning("Listing draft AI generation error: %s; using template fallback.", e)

        return ListingAIDraftResponse(
            title=default_title,
            description=default_desc,
            suggested_tags=default_tags,
        )

    @staticmethod
    async def get_top_matches(
        db: AsyncSession,
        viewer: User,
        limit: int = 10,
    ) -> list[SwapMatchResponse]:
        """Find the highest-scoring peer swap opportunities for the viewer."""
        # 1. Fetch viewer profile, skills, windows
        p_res = await db.execute(
            select(UserSwapProfile).where(UserSwapProfile.user_id == viewer.id)
        )
        viewer_profile = p_res.scalar_one_or_none()

        us_res = await db.execute(
            select(UserSkill)
            .where(UserSkill.user_id == viewer.id)
            .options(selectinload(UserSkill.skill))
        )
        viewer_user_skills = list(us_res.scalars().all())
        viewer_teach_slugs = {
            us.skill.slug for us in viewer_user_skills if us.skill_type == "teach"
        }
        viewer_teach_names = [
            us.skill.display_name for us in viewer_user_skills if us.skill_type == "teach"
        ]
        viewer_learn_slugs = {
            us.skill.slug for us in viewer_user_skills if us.skill_type == "learn"
        }
        viewer_learn_names = [
            us.skill.display_name for us in viewer_user_skills if us.skill_type == "learn"
        ]
        viewer_learn_categories = {
            us.skill.category for us in viewer_user_skills if us.skill_type == "learn"
        }

        w_res = await db.execute(
            select(AvailabilityWindow).where(AvailabilityWindow.user_id == viewer.id)
        )
        viewer_windows = list(w_res.scalars().all())

        # Blocked users check
        block_stmt = select(UserBlock).where(
            (UserBlock.blocker_id == viewer.id) | (UserBlock.blocked_id == viewer.id)
        )
        block_res = await db.execute(block_stmt)
        blocked_ids = {
            b.blocked_id if b.blocker_id == viewer.id else b.blocker_id
            for b in block_res.scalars().all()
        }

        # 2. Fetch candidate listings
        now = datetime.now(UTC)
        stmt = (
            select(SwapListing)
            .join(SwapListing.user)
            .join(UserSwapProfile, UserSwapProfile.user_id == SwapListing.user_id)
            .where(
                SwapListing.user_id != viewer.id,
                SwapListing.status == "active",
                UserSwapProfile.is_invisible.is_(False),
                or_(SwapListing.expires_at.is_(None), SwapListing.expires_at > now),
            )
            .options(
                selectinload(SwapListing.skill_offered),
                selectinload(SwapListing.skill_wanted),
                selectinload(SwapListing.user),
            )
        )
        if blocked_ids:
            stmt = stmt.where(SwapListing.user_id.not_in(blocked_ids))

        res = await db.execute(stmt)
        candidates = list(res.scalars().all())

        if not candidates:
            return []

        # 3. Batch load owner profiles, windows, and trust scores
        owner_ids = list({c.user_id for c in candidates})
        prof_res = await db.execute(
            select(UserSwapProfile).where(UserSwapProfile.user_id.in_(owner_ids))
        )
        owner_profiles = {p.user_id: p for p in prof_res.scalars().all()}

        win_res = await db.execute(
            select(AvailabilityWindow).where(AvailabilityWindow.user_id.in_(owner_ids))
        )
        owner_windows_map: dict[uuid.UUID, list[AvailabilityWindow]] = {
            uid: [] for uid in owner_ids
        }
        for w in win_res.scalars().all():
            owner_windows_map[w.user_id].append(w)

        ts_res = await db.execute(select(TrustScore).where(TrustScore.user_id.in_(owner_ids)))
        trust_map = {ts.user_id: ts.score for ts in ts_res.scalars().all()}

        # 4. Score all candidates
        scored_candidates = []
        for c in candidates:
            op = owner_profiles.get(c.user_id)
            ow = owner_windows_map.get(c.user_id, [])
            ots = trust_map.get(c.user_id, 100)

            score, breakdown = SwapMatchingService.calculate_match_score(
                viewer_profile=viewer_profile,
                viewer_teach_slugs=viewer_teach_slugs,
                viewer_learn_slugs=viewer_learn_slugs,
                viewer_learn_categories=viewer_learn_categories,
                viewer_windows=viewer_windows,
                listing=c,
                owner_profile=op,
                owner_windows=ow,
                owner_trust_score=ots,
            )

            dist_bucket = "remote"
            if viewer_profile and op:
                dist_bucket = get_distance_bucket(
                    viewer_profile.coarse_lat,
                    viewer_profile.coarse_lng,
                    op.coarse_lat,
                    op.coarse_lng,
                )

            scored_candidates.append({
                "listing": c,
                "score": score,
                "breakdown": breakdown,
                "distance_bucket": dist_bucket,
            })

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = scored_candidates[:limit]

        # 5. Build responses with explanations
        results = []
        for tc in top_candidates:
            listing = tc["listing"]
            explanation = await SwapMatchingService.get_or_create_match_explanation(
                db=db,
                viewer=viewer,
                viewer_learn_skills=viewer_learn_names,
                viewer_teach_skills=viewer_teach_names,
                listing=listing,
                distance_bucket=tc["distance_bucket"],
            )

            listing_resp = SwapListingResponse(
                id=listing.id,
                user_id=listing.user_id,
                user=PublicUserMinimal(
                    id=listing.user.id,
                    username=listing.user.username,
                    display_name=listing.user.display_name,
                    avatar_url=listing.user.avatar_url,
                    usn=listing.user.usn,
                ),
                title=listing.title,
                skill_offered=SkillResponse.model_validate(listing.skill_offered),
                skill_wanted=(
                    SkillResponse.model_validate(listing.skill_wanted)
                    if listing.skill_wanted
                    else None
                ),
                description=listing.description,
                modes=listing.modes,
                area_label=listing.area_label,
                status=listing.status,
                tags=listing.tags,
                distance_bucket=tc["distance_bucket"],
                expires_at=listing.expires_at,
                created_at=listing.created_at,
                updated_at=listing.updated_at,
            )

            results.append(
                SwapMatchResponse(
                    listing=listing_resp,
                    match_score=tc["score"],
                    explanation=explanation,
                    score_breakdown=tc["breakdown"],
                )
            )

        return results
