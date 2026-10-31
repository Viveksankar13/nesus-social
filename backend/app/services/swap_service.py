"""
Skill Swap Core Service
=======================
Handles swap profile lifecycle, skill competencies, weekly availability windows,
blackout dates, and privacy-preserving public profile serialization.
"""

import re
import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.post import Post
from app.models.swap import (
    AvailabilityBlackout,
    AvailabilityWindow,
    ReciprocityLedger,
    Skill,
    SwapListing,
    TrustScore,
    UserBlock,
    UserSkill,
    UserSwapProfile,
)
from app.models.user import User
from app.schemas.swap import (
    AvailabilityBlackoutResponse,
    AvailabilityWindowResponse,
    PublicUserMinimal,
    SkillResponse,
    SwapListingCreate,
    SwapListingListResponse,
    SwapListingResponse,
    SwapListingShareResponse,
    SwapListingUpdate,
    UserSkillResponse,
    UserSwapProfilePrivateResponse,
    UserSwapProfilePublicResponse,
    UserSwapProfileUpdate,
)
from app.services.ai.moderation import moderate_content_task
from app.services.swap_geocoding import (
    calculate_haversine_km as haversine_km,
)
from app.services.swap_geocoding import (
    coarsen_coord,
    get_distance_bucket,
)
from app.services.swap_taxonomy import SwapTaxonomyService

MONEY_PATTERNS = [
    r"\$\d+",
    r"\b\d+\s*(?:dollars?|usd|eur|gbp|inr|bucks)\b",
    r"\b(?:paypal|venmo|cashapp|zelle|crypto|bitcoin|eth)\b",
    r"\b(?:hourly rate|per hour|fixed price|pricing|consulting fee|cash only|wire transfer)\b",
]


def assert_no_money_policy(text: str) -> None:
    """Enforce strict non-monetary policy on listings and requests."""
    for pattern in MONEY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Nexus Swaps are strictly non-monetary peer exchanges. "
                    "Payment solicitation, fees, or monetary references are prohibited."
                ),
            )



class SwapService:
    """Core domain service for skill swap profiles, availability, and privacy."""

    @staticmethod
    async def get_or_create_profile(
        db: AsyncSession, user_id: uuid.UUID
    ) -> UserSwapProfile:
        """Fetch existing swap profile or initialize default settings."""
        stmt = select(UserSwapProfile).where(UserSwapProfile.user_id == user_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            profile = UserSwapProfile(
                id=uuid.uuid4(),
                user_id=user_id,
                bio=None,
                coarse_lat=None,
                coarse_lng=None,
                area_label=None,
                radius_km=10,
                modes=["video", "in_person"],
                languages=["English"],
                is_invisible=False,
                accepts_newcomers=True,
                is_18_confirmed=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(profile)

            # Also ensure TrustScore and ReciprocityLedger exist
            ts = await db.execute(select(TrustScore).where(TrustScore.user_id == user_id))
            if not ts.scalar_one_or_none():
                db.add(
                    TrustScore(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        score=100,
                        completed_count=0,
                        no_show_count=0,
                        cancellation_count=0,
                        avg_rating=5.0,
                        badges=[],
                        updated_at=datetime.now(UTC),
                    )
                )

            rl = await db.execute(
                select(ReciprocityLedger).where(ReciprocityLedger.user_id == user_id)
            )
            if not rl.scalar_one_or_none():
                db.add(
                    ReciprocityLedger(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        minutes_taught=0,
                        minutes_learned=0,
                        net_balance_minutes=0,
                        grace_used=0,
                        updated_at=datetime.now(UTC),
                    )
                )

            await db.commit()
            await db.refresh(profile)

        return profile

    @staticmethod
    async def get_private_profile(
        db: AsyncSession, user_id: uuid.UUID
    ) -> UserSwapProfilePrivateResponse:
        """Get full profile details for the authenticated user (viewer is owner)."""
        profile = await SwapService.get_or_create_profile(db, user_id)

        # User skills
        us_stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .options(selectinload(UserSkill.skill))
        )
        us_res = await db.execute(us_stmt)
        user_skills = list(us_res.scalars().all())

        teach_skills = [
            UserSkillResponse(
                id=us.id,
                skill=SkillResponse.model_validate(us.skill),
                skill_type="teach",
                level=us.level,
                years_experience=us.years_experience,
                notes=us.notes,
            )
            for us in user_skills
            if us.skill_type == "teach"
        ]

        learn_skills = [
            UserSkillResponse(
                id=us.id,
                skill=SkillResponse.model_validate(us.skill),
                skill_type="learn",
                level=us.level,
                years_experience=us.years_experience,
                notes=us.notes,
            )
            for us in user_skills
            if us.skill_type == "learn"
        ]

        # Availability windows
        aw_stmt = (
            select(AvailabilityWindow)
            .where(AvailabilityWindow.user_id == user_id)
            .order_by(AvailabilityWindow.day_of_week, AvailabilityWindow.start_time_utc)
        )
        aw_res = await db.execute(aw_stmt)
        windows = [
            AvailabilityWindowResponse.model_validate(w)
            for w in aw_res.scalars().all()
        ]

        # Blackout dates
        ab_stmt = (
            select(AvailabilityBlackout)
            .where(AvailabilityBlackout.user_id == user_id)
            .order_by(AvailabilityBlackout.start_datetime_utc)
        )
        ab_res = await db.execute(ab_stmt)
        blackouts = [
            AvailabilityBlackoutResponse.model_validate(b)
            for b in ab_res.scalars().all()
        ]

        # Trust score & ledger
        ts_stmt = select(TrustScore).where(TrustScore.user_id == user_id)
        ts_res = await db.execute(ts_stmt)
        ts = ts_res.scalar_one_or_none()

        rl_stmt = select(ReciprocityLedger).where(ReciprocityLedger.user_id == user_id)
        rl_res = await db.execute(rl_stmt)
        rl = rl_res.scalar_one_or_none()

        return UserSwapProfilePrivateResponse(
            user_id=profile.user_id,
            bio=profile.bio,
            coarse_lat=profile.coarse_lat,
            coarse_lng=profile.coarse_lng,
            area_label=profile.area_label,
            radius_km=profile.radius_km,
            modes=profile.modes,
            languages=profile.languages,
            is_invisible=profile.is_invisible,
            accepts_newcomers=profile.accepts_newcomers,
            is_18_confirmed=profile.is_18_confirmed,
            teach_skills=teach_skills,
            learn_skills=learn_skills,
            availability_windows=windows,
            blackout_dates=blackouts,
            trust_score=ts.score if ts else 100,
            avg_rating=ts.avg_rating if ts else 5.0,
            completed_swaps=ts.completed_count if ts else 0,
            badges=ts.badges if ts else [],
            reciprocity_balance_minutes=rl.net_balance_minutes if rl else 0,
        )

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: uuid.UUID, data: UserSwapProfileUpdate
    ) -> UserSwapProfilePrivateResponse:
        """Update profile settings, skills, and availability."""
        profile = await SwapService.get_or_create_profile(db, user_id)

        # Update scalar fields
        profile.bio = data.bio
        profile.coarse_lat = coarsen_coord(data.coarse_lat)
        profile.coarse_lng = coarsen_coord(data.coarse_lng)
        profile.area_label = data.area_label
        profile.radius_km = data.radius_km
        profile.modes = data.modes
        profile.languages = data.languages
        profile.is_invisible = data.is_invisible
        profile.accepts_newcomers = data.accepts_newcomers
        profile.is_18_confirmed = data.is_18_confirmed
        profile.updated_at = datetime.now(UTC)

        # Update skills (replace existing)
        await db.execute(delete(UserSkill).where(UserSkill.user_id == user_id))

        for item in data.teach_skills:
            skill = await SwapTaxonomyService.find_by_slug(db, item.skill_slug)
            if not skill:
                skill = await SwapTaxonomyService.suggest_skill(db, item.skill_slug, "General")
            db.add(
                UserSkill(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    skill_id=skill.id,
                    skill_type="teach",
                    level=item.level,
                    years_experience=item.years_experience,
                    notes=item.notes,
                    created_at=datetime.now(UTC),
                )
            )

        for item in data.learn_skills:
            skill = await SwapTaxonomyService.find_by_slug(db, item.skill_slug)
            if not skill:
                skill = await SwapTaxonomyService.suggest_skill(db, item.skill_slug, "General")
            db.add(
                UserSkill(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    skill_id=skill.id,
                    skill_type="learn",
                    level=item.level,
                    years_experience=item.years_experience,
                    notes=item.notes,
                    created_at=datetime.now(UTC),
                )
            )

        # Update availability windows
        await db.execute(
            delete(AvailabilityWindow).where(AvailabilityWindow.user_id == user_id)
        )
        for w in data.availability_windows:
            db.add(
                AvailabilityWindow(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    day_of_week=w.day_of_week,
                    start_time_utc=w.start_time_utc,
                    end_time_utc=w.end_time_utc,
                    created_at=datetime.now(UTC),
                )
            )

        # Update blackout dates
        await db.execute(
            delete(AvailabilityBlackout).where(AvailabilityBlackout.user_id == user_id)
        )
        for b in data.blackout_dates:
            db.add(
                AvailabilityBlackout(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    start_datetime_utc=b.start_datetime_utc,
                    end_datetime_utc=b.end_datetime_utc,
                    reason=b.reason,
                    created_at=datetime.now(UTC),
                )
            )

        await db.commit()
        return await SwapService.get_private_profile(db, user_id)

    @staticmethod
    async def get_public_profile(
        db: AsyncSession, viewer_id: uuid.UUID | None, target_username: str
    ) -> UserSwapProfilePublicResponse:
        """
        Fetch public swap profile.
        PRIVACY GUARANTEE: Never exposes coordinates. Strictly exposes distance bucket.
        Excludes invisible profiles and blocked relationships.
        """
        # Find target user
        u_stmt = select(User).where(User.username == target_username)
        u_res = await db.execute(u_stmt)
        target = u_res.scalar_one_or_none()
        if not target or target.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or account unavailable.",
            )

        # Block check
        if viewer_id:
            block_stmt = select(UserBlock).where(
                ((UserBlock.blocker_id == viewer_id) & (UserBlock.blocked_id == target.id))
                | ((UserBlock.blocker_id == target.id) & (UserBlock.blocked_id == viewer_id))
            )
            if (await db.execute(block_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )

        target_profile = await SwapService.get_or_create_profile(db, target.id)
        if target_profile.is_invisible and (viewer_id != target.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This user has set their swap profile to invisible.",
            )

        # Compute distance bucket
        distance_bucket = "remote"
        if viewer_id:
            viewer_prof = await SwapService.get_or_create_profile(db, viewer_id)
            distance_bucket = get_distance_bucket(
                viewer_prof.coarse_lat,
                viewer_prof.coarse_lng,
                target_profile.coarse_lat,
                target_profile.coarse_lng,
            )

        # Fetch skills
        us_stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == target.id)
            .options(selectinload(UserSkill.skill))
        )
        us_res = await db.execute(us_stmt)
        user_skills = list(us_res.scalars().all())

        teach_skills = [
            UserSkillResponse(
                id=us.id,
                skill=SkillResponse.model_validate(us.skill),
                skill_type="teach",
                level=us.level,
                years_experience=us.years_experience,
                notes=us.notes,
            )
            for us in user_skills
            if us.skill_type == "teach"
        ]

        learn_skills = [
            UserSkillResponse(
                id=us.id,
                skill=SkillResponse.model_validate(us.skill),
                skill_type="learn",
                level=us.level,
                years_experience=us.years_experience,
                notes=us.notes,
            )
            for us in user_skills
            if us.skill_type == "learn"
        ]

        # Trust score
        ts_res = await db.execute(select(TrustScore).where(TrustScore.user_id == target.id))
        ts = ts_res.scalar_one_or_none()

        return UserSwapProfilePublicResponse(
            user=PublicUserMinimal(
                id=target.id,
                username=target.username,
                display_name=target.display_name,
                avatar_url=target.avatar_url,
                usn=target.usn,
            ),
            bio=target_profile.bio,
            area_label=target_profile.area_label,
            distance_bucket=distance_bucket,
            modes=target_profile.modes,
            languages=target_profile.languages,
            accepts_newcomers=target_profile.accepts_newcomers,
            teach_skills=teach_skills,
            learn_skills=learn_skills,
            trust_score=ts.score if ts else 100,
            avg_rating=ts.avg_rating if ts else 5.0,
            completed_swaps=ts.completed_count if ts else 0,
            badges=ts.badges if ts else [],
        )

    # ── Swap Listing Domain Logic ────────────────────────────────────
    @staticmethod
    async def create_listing(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: SwapListingCreate,
        background_tasks: BackgroundTasks | None = None,
    ) -> SwapListingResponse:
        """Create a new swap listing, enforcing maximum active listings and no-money policy."""
        # Enforce max active listings limit
        count_stmt = select(func.count(SwapListing.id)).where(
            SwapListing.user_id == user_id,
            SwapListing.status == "active",
        )
        active_count = (await db.execute(count_stmt)).scalar_one() or 0
        if active_count >= settings.SWAP_MAX_ACTIVE_LISTINGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Maximum active swap listings limit reached "
                    f"({settings.SWAP_MAX_ACTIVE_LISTINGS})."
                ),
            )

        # Enforce non-monetary policy
        assert_no_money_policy(f"{data.title} {data.description} {' '.join(data.tags)}")

        # Validate offered skill
        offered = await db.get(Skill, data.skill_offered_id)
        if not offered or offered.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offered skill not found or not active.",
            )

        # Validate wanted skill if provided
        if data.skill_wanted_id:
            wanted = await db.get(Skill, data.skill_wanted_id)
            if not wanted or wanted.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Wanted skill not found or not active.",
                )

        # Fall back to user swap profile's area_label if not specified
        profile = await SwapService.get_or_create_profile(db, user_id)
        area_label = data.area_label or profile.area_label

        listing = SwapListing(
            id=uuid.uuid4(),
            user_id=user_id,
            title=data.title.strip(),
            skill_offered_id=data.skill_offered_id,
            skill_wanted_id=data.skill_wanted_id,
            description=data.description.strip(),
            modes=data.modes,
            area_label=area_label,
            status="active",
            tags=data.tags,
            expires_at=data.expires_at,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(listing)
        await db.commit()

        # Queue background AI moderation task
        if background_tasks:
            background_tasks.add_task(
                moderate_content_task,
                content_type="swap_listing",
                content_id=listing.id,
                text=f"{listing.title}\n{listing.description}",
                user_id=user_id,
            )

        return await SwapService.get_listing_by_id(db, listing.id, viewer_id=user_id)

    @staticmethod
    async def get_listing_by_id(
        db: AsyncSession,
        listing_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
    ) -> SwapListingResponse:
        """Fetch listing details with dynamic distance bucket for the viewer."""
        stmt = (
            select(SwapListing)
            .where(SwapListing.id == listing_id)
            .options(
                selectinload(SwapListing.skill_offered),
                selectinload(SwapListing.skill_wanted),
                selectinload(SwapListing.user),
            )
        )
        res = await db.execute(stmt)
        listing = res.scalar_one_or_none()
        if not listing or listing.status == "removed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap listing not found.",
            )

        # Inactive listings only visible to owner
        if listing.status != "active" and (not viewer_id or viewer_id != listing.user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap listing not found.",
            )

        # Block check
        if viewer_id and viewer_id != listing.user_id:
            block_stmt = select(UserBlock).where(
                ((UserBlock.blocker_id == viewer_id) & (UserBlock.blocked_id == listing.user_id))
                | ((UserBlock.blocker_id == listing.user_id) & (UserBlock.blocked_id == viewer_id))
            )
            if (await db.execute(block_stmt)).scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Swap listing not found.",
                )

        distance_bucket = "remote"
        if viewer_id:
            viewer_prof = await SwapService.get_or_create_profile(db, viewer_id)
            owner_prof = await SwapService.get_or_create_profile(db, listing.user_id)
            distance_bucket = get_distance_bucket(
                viewer_prof.coarse_lat,
                viewer_prof.coarse_lng,
                owner_prof.coarse_lat,
                owner_prof.coarse_lng,
            )

        return SwapListingResponse(
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
            distance_bucket=distance_bucket,
            expires_at=listing.expires_at,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )

    @staticmethod
    async def get_user_listings(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[SwapListingResponse]:
        """Fetch all listings owned by the user, excluding removed."""
        stmt = (
            select(SwapListing)
            .where(
                SwapListing.user_id == user_id,
                SwapListing.status != "removed",
            )
            .order_by(SwapListing.created_at.desc())
            .options(
                selectinload(SwapListing.skill_offered),
                selectinload(SwapListing.skill_wanted),
                selectinload(SwapListing.user),
            )
        )
        res = await db.execute(stmt)
        listings = res.scalars().all()
        return [
            SwapListingResponse(
                id=item.id,
                user_id=item.user_id,
                user=PublicUserMinimal(
                    id=item.user.id,
                    username=item.user.username,
                    display_name=item.user.display_name,
                    avatar_url=item.user.avatar_url,
                    usn=item.user.usn,
                ),
                title=item.title,
                skill_offered=SkillResponse.model_validate(item.skill_offered),
                skill_wanted=(
                    SkillResponse.model_validate(item.skill_wanted)
                    if item.skill_wanted
                    else None
                ),
                description=item.description,
                modes=item.modes,
                area_label=item.area_label,
                status=item.status,
                tags=item.tags,
                distance_bucket="remote",
                expires_at=item.expires_at,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in listings
        ]

    @staticmethod
    async def update_listing(
        db: AsyncSession,
        listing_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SwapListingUpdate,
        background_tasks: BackgroundTasks | None = None,
    ) -> SwapListingResponse:
        """Update a swap listing owned by the authenticated user."""
        stmt = select(SwapListing).where(SwapListing.id == listing_id)
        res = await db.execute(stmt)
        listing = res.scalar_one_or_none()
        if not listing or listing.status == "removed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap listing not found.",
            )

        if listing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this listing.",
            )

        if data.status == "active" and listing.status != "active":
            count_stmt = select(func.count(SwapListing.id)).where(
                SwapListing.user_id == user_id,
                SwapListing.status == "active",
            )
            active_count = (await db.execute(count_stmt)).scalar_one() or 0
            if active_count >= settings.SWAP_MAX_ACTIVE_LISTINGS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Maximum active swap listings limit reached "
                        f"({settings.SWAP_MAX_ACTIVE_LISTINGS})."
                    ),
                )

        if data.title is not None:
            assert_no_money_policy(data.title)
            listing.title = data.title.strip()

        if data.description is not None:
            assert_no_money_policy(data.description)
            listing.description = data.description.strip()

        if data.skill_offered_id is not None:
            offered = await db.get(Skill, data.skill_offered_id)
            if not offered or offered.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Offered skill not found or not active.",
                )
            listing.skill_offered_id = data.skill_offered_id

        if data.skill_wanted_id is not None:
            wanted = await db.get(Skill, data.skill_wanted_id)
            if not wanted or wanted.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Wanted skill not found or not active.",
                )
            listing.skill_wanted_id = data.skill_wanted_id

        if data.modes is not None:
            listing.modes = data.modes
        if data.area_label is not None:
            listing.area_label = data.area_label
        if data.tags is not None:
            listing.tags = data.tags
        if data.status is not None:
            listing.status = data.status
        if data.expires_at is not None:
            listing.expires_at = data.expires_at

        listing.updated_at = datetime.now(UTC)
        await db.commit()

        if background_tasks and (data.title or data.description):
            background_tasks.add_task(
                moderate_content_task,
                content_type="swap_listing",
                content_id=listing.id,
                text=f"{listing.title}\n{listing.description}",
                user_id=user_id,
            )

        return await SwapService.get_listing_by_id(db, listing.id, viewer_id=user_id)

    @staticmethod
    async def share_listing_to_feed(
        db: AsyncSession,
        listing_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapListingShareResponse:
        """Create a social feed post showcasing an active swap listing with direct CTA."""
        listing = await db.get(SwapListing, listing_id)
        if not listing or listing.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active swap listing not found.",
            )

        if listing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only share your own active swap listings.",
            )

        offered = await db.get(Skill, listing.skill_offered_id)
        wanted = (
            await db.get(Skill, listing.skill_wanted_id)
            if listing.skill_wanted_id
            else None
        )
        wanted_label = wanted.display_name if wanted else "Open to anything / Pay it forward"

        post_content = (
            f"🔄 Skill Swap Offer: {listing.title}\n\n"
            f"I can teach: {offered.display_name if offered else 'Various'}\n"
            f"Looking for: {wanted_label}\n\n"
            f"{listing.description}\n\n"
            f"Check listing: /swaps/{listing.id}"
        )

        post = Post(
            id=uuid.uuid4(),
            author_id=user_id,
            content=post_content,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)

        return SwapListingShareResponse(
            listing_id=listing.id,
            post_id=post.id,
            message="Listing shared to feed successfully.",
        )

    # ── Swap Discovery Query Engine ──────────────────────────────────
    @staticmethod
    async def search_listings(
        db: AsyncSession,
        viewer_id: uuid.UUID | None = None,
        query_text: str | None = None,
        category: str | None = None,
        mode: str | None = None,
        distance_filter: str | None = None,
        sort: str = "newest",
        limit: int = 20,
        cursor: int = 0,
    ) -> SwapListingListResponse:
        """
        Search active swap listings with spatial and category filters.
        PRIVACY GUARANTEE: Never exposes coordinates. Strictly exposes distance bucket.
        """
        # Block filter
        blocked_user_ids: set[uuid.UUID] = set()
        viewer_profile: UserSwapProfile | None = None
        if viewer_id:
            viewer_profile = await SwapService.get_or_create_profile(db, viewer_id)
            block_stmt = select(UserBlock).where(
                (UserBlock.blocker_id == viewer_id) | (UserBlock.blocked_id == viewer_id)
            )
            block_res = await db.execute(block_stmt)
            for b in block_res.scalars().all():
                if b.blocker_id == viewer_id:
                    blocked_user_ids.add(b.blocked_id)
                else:
                    blocked_user_ids.add(b.blocker_id)

        now = datetime.now(UTC)
        stmt = (
            select(SwapListing)
            .join(SwapListing.user)
            .join(SwapListing.skill_offered)
            .join(UserSwapProfile, UserSwapProfile.user_id == SwapListing.user_id)
            .where(
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

        if blocked_user_ids:
            stmt = stmt.where(SwapListing.user_id.not_in(blocked_user_ids))

        if category:
            stmt = stmt.where(Skill.category == category)

        if query_text:
            stmt = stmt.where(
                or_(
                    SwapListing.title.ilike(f"%{query_text}%"),
                    SwapListing.description.ilike(f"%{query_text}%"),
                    Skill.display_name.ilike(f"%{query_text}%"),
                )
            )

        res = await db.execute(stmt)
        all_listings = list(res.scalars().all())

        # In-memory filter for modes if specified (cross-dialect safe)
        if mode:
            all_listings = [
                entry for entry in all_listings
                if mode in (entry.modes or []) or "any" in (entry.modes or [])
            ]

        # Fetch owner profiles and trust scores for distance/trust sorting
        owner_ids = [entry.user_id for entry in all_listings]
        owner_profiles: dict[uuid.UUID, UserSwapProfile] = {}
        trust_scores: dict[uuid.UUID, int] = {}
        if owner_ids:
            prof_res = await db.execute(
                select(UserSwapProfile).where(UserSwapProfile.user_id.in_(owner_ids))
            )
            owner_profiles = {p.user_id: p for p in prof_res.scalars().all()}

            ts_res = await db.execute(
                select(TrustScore).where(TrustScore.user_id.in_(owner_ids))
            )
            trust_scores = {ts.user_id: ts.score for ts in ts_res.scalars().all()}

        # Compute distance bucket and km for each listing
        decorated_listings = []
        for entry in all_listings:
            owner_p = owner_profiles.get(entry.user_id)
            dist_km: float | None = None
            bucket = "remote"
            if viewer_profile and owner_p:
                dist_km = haversine_km(
                    viewer_profile.coarse_lat,
                    viewer_profile.coarse_lng,
                    owner_p.coarse_lat,
                    owner_p.coarse_lng,
                )
                bucket = get_distance_bucket(
                    viewer_profile.coarse_lat,
                    viewer_profile.coarse_lng,
                    owner_p.coarse_lat,
                    owner_p.coarse_lng,
                )

            # Apply distance filter if requested
            if distance_filter and bucket != distance_filter:
                continue

            decorated_listings.append({
                "listing": entry,
                "distance_bucket": bucket,
                "distance_km": dist_km if dist_km is not None else 99999.0,
                "trust_score": trust_scores.get(entry.user_id, 100),
            })

        # Sort
        if sort == "nearest":
            decorated_listings.sort(key=lambda x: x["distance_km"])
        elif sort == "trust":
            decorated_listings.sort(key=lambda x: x["trust_score"], reverse=True)
        else:  # newest
            decorated_listings.sort(key=lambda x: x["listing"].created_at, reverse=True)

        total = len(decorated_listings)
        paged = decorated_listings[cursor : cursor + limit]
        next_cursor = str(cursor + limit) if (cursor + limit) < total else None

        items = [
            SwapListingResponse(
                id=d["listing"].id,
                user_id=d["listing"].user_id,
                user=PublicUserMinimal(
                    id=d["listing"].user.id,
                    username=d["listing"].user.username,
                    display_name=d["listing"].user.display_name,
                    avatar_url=d["listing"].user.avatar_url,
                    usn=d["listing"].user.usn,
                ),
                title=d["listing"].title,
                skill_offered=SkillResponse.model_validate(d["listing"].skill_offered),
                skill_wanted=(
                    SkillResponse.model_validate(d["listing"].skill_wanted)
                    if d["listing"].skill_wanted
                    else None
                ),
                description=d["listing"].description,
                modes=d["listing"].modes,
                area_label=d["listing"].area_label,
                status=d["listing"].status,
                tags=d["listing"].tags,
                distance_bucket=d["distance_bucket"],
                expires_at=d["listing"].expires_at,
                created_at=d["listing"].created_at,
                updated_at=d["listing"].updated_at,
            )
            for d in paged
        ]

        return SwapListingListResponse(
            items=items,
            total=total,
            next_cursor=next_cursor,
        )

