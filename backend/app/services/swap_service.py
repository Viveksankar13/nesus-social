"""
Skill Swap Core Service
=======================
Handles swap profile lifecycle, skill competencies, weekly availability windows,
blackout dates, and privacy-preserving public profile serialization.
"""

import json
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
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
    SwapMessage,
    SwapReport,
    SwapRequest,
    SwapReview,
    SwapSession,
    SwapSessionHalf,
    TrustScore,
    UserBlock,
    UserSkill,
    UserSwapProfile,
)
from app.models.user import User
from app.schemas.swap import (
    AgendaItem,
    AvailabilityBlackoutResponse,
    AvailabilityWindowResponse,
    ICSExportResponse,
    InPersonSafetyCheck,
    PublicUserMinimal,
    SkillResponse,
    SwapAdminStatsResponse,
    SwapDisputeAdminResponse,
    SwapDisputeCreate,
    SwapDisputeResolveRequest,
    SwapFairnessAdviceResponse,
    SwapListingAdminResponse,
    SwapListingCreate,
    SwapListingListResponse,
    SwapListingResponse,
    SwapListingShareResponse,
    SwapListingUpdate,
    SwapMessageCreate,
    SwapMessageResponse,
    SwapReportCreate,
    SwapReportResponse,
    SwapRequestAccept,
    SwapRequestCounter,
    SwapRequestCreate,
    SwapRequestListResponse,
    SwapRequestResponse,
    SwapReviewCreate,
    SwapReviewResponse,
    SwapSessionHalfResponse,
    SwapSessionPlanRequest,
    SwapSessionPlanResponse,
    SwapSessionRecapRequest,
    SwapSessionRecapResponse,
    SwapSessionResponse,
    UserBlockResponse,
    UserSkillResponse,
    UserSwapProfilePrivateResponse,
    UserSwapProfilePublicResponse,
    UserSwapProfileUpdate,
)
from app.services.ai import get_ai_service
from app.services.ai.moderation import moderate_content_task
from app.services.ai.prompts import (
    SWAP_FAIRNESS_ADVISOR_SYSTEM_PROMPT,
    SWAP_SESSION_PLAN_SYSTEM_PROMPT,
    SWAP_SESSION_RECAP_SYSTEM_PROMPT,
    build_fairness_advisor_prompt,
    build_session_plan_prompt,
    build_session_recap_prompt,
)
from app.services.notification_service import notification_service
from app.services.pubsub import pubsub
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

RESIDENTIAL_PATTERNS = [
    r"\bapt\b",
    r"\bapartment\b",
    r"\bunit\b\s*#?\d+",
    r"\bsuite\b\s*#?\d+",
    r"\bflat\b\s*#?\d+",
    r"\broom\b\s*#?\d+",
    r"\bfloor\b\s*#?\d+",
    r"\bresidence\b",
    r"\bhome address\b",
    r"\bmy house\b",
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


def assert_public_place(place_name: str | None, place_address: str | None) -> None:
    """Validate that in-person swaps occur in a named public venue, rejecting residential patterns."""
    if not place_name or len(place_name.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="In-person swaps require a named public place (e.g. 'Campus Main Library', 'Starbucks Downtown').",
        )
    combined = f"{place_name} {place_address or ''}".lower()
    for pat in RESIDENTIAL_PATTERNS:
        if re.search(pat, combined):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "For safety and privacy, in-person meetups must occur in a verified public venue. "
                    "Residential addresses, apartment units, and private residences are prohibited."
                ),
            )


def parse_utc_datetime(dt_val: Any) -> datetime:
    """Ensure datetime has UTC timezone."""
    if isinstance(dt_val, str):
        dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
    else:
        dt = dt_val
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def build_user_minimal(u: User) -> PublicUserMinimal:
    return PublicUserMinimal(
        id=u.id,
        username=u.username,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        usn=u.usn,
    )


class SwapService:
    """Core domain service for skill swap profiles, availability, and privacy."""

    @staticmethod
    async def get_or_create_profile(db: AsyncSession, user_id: uuid.UUID) -> UserSwapProfile:
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
    async def get_or_create_ledger(db: AsyncSession, user_id: uuid.UUID) -> ReciprocityLedger:
        """Ensure reciprocity ledger exists for a user and return it."""
        stmt = select(ReciprocityLedger).where(ReciprocityLedger.user_id == user_id)
        rl = (await db.execute(stmt)).scalar_one_or_none()
        if not rl:
            rl = ReciprocityLedger(
                id=uuid.uuid4(),
                user_id=user_id,
                minutes_taught=0,
                minutes_learned=0,
                net_balance_minutes=0,
                grace_used=0,
                updated_at=datetime.now(UTC),
            )
            db.add(rl)
            await db.commit()
            await db.refresh(rl)
        return rl

    @staticmethod
    async def get_or_create_trust_score(db: AsyncSession, user_id: uuid.UUID) -> TrustScore:
        """Ensure trust score exists for a user and return it."""
        stmt = select(TrustScore).where(TrustScore.user_id == user_id)
        ts = (await db.execute(stmt)).scalar_one_or_none()
        if not ts:
            ts = TrustScore(
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
            db.add(ts)
            await db.commit()
            await db.refresh(ts)
        return ts

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
        windows = [AvailabilityWindowResponse.model_validate(w) for w in aw_res.scalars().all()]

        # Blackout dates
        ab_stmt = (
            select(AvailabilityBlackout)
            .where(AvailabilityBlackout.user_id == user_id)
            .order_by(AvailabilityBlackout.start_datetime_utc)
        )
        ab_res = await db.execute(ab_stmt)
        blackouts = [AvailabilityBlackoutResponse.model_validate(b) for b in ab_res.scalars().all()]

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
        await db.execute(delete(AvailabilityWindow).where(AvailabilityWindow.user_id == user_id))
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
                SkillResponse.model_validate(listing.skill_wanted) if listing.skill_wanted else None
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
                    SkillResponse.model_validate(item.skill_wanted) if item.skill_wanted else None
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
        wanted = await db.get(Skill, listing.skill_wanted_id) if listing.skill_wanted_id else None
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
                entry
                for entry in all_listings
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

            ts_res = await db.execute(select(TrustScore).where(TrustScore.user_id.in_(owner_ids)))
            trust_scores = {ts.user_id: ts.score for ts in ts_res.scalars().all()}

        # Compute distance bucket and km for each listing
        decorated_listings = []
        for entry in all_listings:
            owner_p = owner_profiles.get(entry.user_id)
            dist_km: float | None = None
            bucket = "remote"
            if (
                viewer_profile
                and owner_p
                and viewer_profile.coarse_lat is not None
                and viewer_profile.coarse_lng is not None
                and owner_p.coarse_lat is not None
                and owner_p.coarse_lng is not None
            ):
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

            decorated_listings.append(
                {
                    "listing": entry,
                    "distance_bucket": bucket,
                    "distance_km": dist_km if dist_km is not None else 99999.0,
                    "trust_score": trust_scores.get(entry.user_id, 100),
                }
            )

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

    # ── Stage 3: Request State Machine & Counter-Offers ─────────────────
    @staticmethod
    async def create_request(
        db: AsyncSession,
        requester_id: uuid.UUID,
        data: SwapRequestCreate,
    ) -> SwapRequestResponse:
        """Create a new swap proposal with up to 3 proposed 30-minute slots."""
        if requester_id == data.recipient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot propose a swap to yourself.",
            )

        # Non-monetary check
        assert_no_money_policy(data.message)

        # Public place check for in-person swaps
        if data.mode == "in_person":
            assert_public_place(data.public_place_name, data.public_place_address)

        # Block check
        block_stmt = select(UserBlock).where(
            or_(
                and_(
                    UserBlock.blocker_id == requester_id, UserBlock.blocked_id == data.recipient_id
                ),
                and_(
                    UserBlock.blocker_id == data.recipient_id, UserBlock.blocked_id == requester_id
                ),
            )
        )
        if (await db.execute(block_stmt)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot propose a swap with this user due to privacy/blocking settings.",
            )

        # Quota check: max pending requests
        pending_count = (
            await db.execute(
                select(func.count(SwapRequest.id)).where(
                    SwapRequest.requester_id == requester_id,
                    SwapRequest.status == "pending",
                )
            )
        ).scalar() or 0
        if pending_count >= settings.SWAP_MAX_PENDING_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You have reached the maximum limit of {settings.SWAP_MAX_PENDING_REQUESTS} active pending requests.",
            )

        # Reciprocity balance check: allow down to -60 min
        rl = (
            await db.execute(
                select(ReciprocityLedger).where(ReciprocityLedger.user_id == requester_id)
            )
        ).scalar_one_or_none()
        if rl and rl.net_balance_minutes <= -60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Reciprocity grace limit reached (-60m net balance). "
                    "Please teach a swap session to replenish your balance before requesting more peer learning."
                ),
            )

        # Verify skills exist
        offered = (
            await db.execute(select(Skill).where(Skill.id == data.offered_skill_id))
        ).scalar_one_or_none()
        wanted = (
            await db.execute(select(Skill).where(Skill.id == data.wanted_skill_id))
        ).scalar_one_or_none()
        if not offered or not wanted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both selected skills do not exist in the canonical taxonomy.",
            )

        now = datetime.now(UTC)
        # Validate proposed slots are in the future
        for slot in data.proposed_slots:
            slot_start = parse_utc_datetime(slot.start_time_utc)
            if slot_start <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All proposed swap slots must be in the future.",
                )

        req_id = uuid.uuid4()
        swap_req = SwapRequest(
            id=req_id,
            listing_id=data.listing_id,
            requester_id=requester_id,
            recipient_id=data.recipient_id,
            offered_skill_id=data.offered_skill_id,
            wanted_skill_id=data.wanted_skill_id,
            mode=data.mode,
            message=data.message,
            proposed_slots=[s.model_dump(mode="json") for s in data.proposed_slots],
            status="pending",
            counter_note=None,
            expires_at=now + timedelta(hours=72),
            created_at=now,
            updated_at=now,
        )
        db.add(swap_req)
        await db.commit()

        # Re-fetch with relationships
        full_req = (
            await db.execute(
                select(SwapRequest)
                .options(
                    selectinload(SwapRequest.requester),
                    selectinload(SwapRequest.recipient),
                    selectinload(SwapRequest.offered_skill),
                    selectinload(SwapRequest.wanted_skill),
                )
                .where(SwapRequest.id == req_id)
            )
        ).scalar_one()

        # Push notification to recipient
        await notification_service.create_and_push_notification(
            db,
            user_id=data.recipient_id,
            type="swap_request_received",
            payload={
                "request_id": str(req_id),
                "requester_id": str(requester_id),
                "requester_username": full_req.requester.username,
                "offered_skill": full_req.offered_skill.display_name,
                "wanted_skill": full_req.wanted_skill.display_name,
                "message": f"New skill swap request from @{full_req.requester.username}: '{data.message[:60]}...'",
            },
        )

        return SwapService._build_swap_request_response(full_req)

    @staticmethod
    async def get_user_requests(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> SwapRequestListResponse:
        """Retrieve all incoming and outgoing swap proposals for a user."""
        stmt_opts = (
            selectinload(SwapRequest.requester),
            selectinload(SwapRequest.recipient),
            selectinload(SwapRequest.offered_skill),
            selectinload(SwapRequest.wanted_skill),
        )

        incoming_stmt = (
            select(SwapRequest)
            .options(*stmt_opts)
            .where(SwapRequest.recipient_id == user_id)
            .order_by(SwapRequest.created_at.desc())
        )
        outgoing_stmt = (
            select(SwapRequest)
            .options(*stmt_opts)
            .where(SwapRequest.requester_id == user_id)
            .order_by(SwapRequest.created_at.desc())
        )

        incoming_res = (await db.execute(incoming_stmt)).scalars().all()
        outgoing_res = (await db.execute(outgoing_stmt)).scalars().all()

        return SwapRequestListResponse(
            incoming=[SwapService._build_swap_request_response(r) for r in incoming_res],
            outgoing=[SwapService._build_swap_request_response(r) for r in outgoing_res],
        )

    @staticmethod
    async def get_request_by_id(
        db: AsyncSession,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapRequestResponse:
        """Fetch a specific swap proposal (participants only)."""
        stmt = (
            select(SwapRequest)
            .options(
                selectinload(SwapRequest.requester),
                selectinload(SwapRequest.recipient),
                selectinload(SwapRequest.offered_skill),
                selectinload(SwapRequest.wanted_skill),
            )
            .where(SwapRequest.id == request_id)
        )
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap proposal not found"
            )

        if user_id not in (req.requester_id, req.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this proposal"
            )

        return SwapService._build_swap_request_response(req)

    @staticmethod
    async def counter_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SwapRequestCounter,
    ) -> SwapRequestResponse:
        """Counter-propose alternative time slots or mode on a pending proposal."""
        assert_no_money_policy(data.message)
        if data.mode == "in_person":
            assert_public_place(data.public_place_name, data.public_place_address)

        stmt = (
            select(SwapRequest)
            .options(
                selectinload(SwapRequest.requester),
                selectinload(SwapRequest.recipient),
                selectinload(SwapRequest.offered_skill),
                selectinload(SwapRequest.wanted_skill),
            )
            .where(SwapRequest.id == request_id)
        )
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap proposal not found"
            )

        if user_id not in (req.requester_id, req.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to counter this proposal",
            )

        if req.status not in ("pending", "countered"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot counter a request in status '{req.status}'.",
            )

        now = datetime.now(UTC)
        for slot in data.proposed_slots:
            if parse_utc_datetime(slot.start_time_utc) <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All counter-proposed slots must be in the future.",
                )

        req.status = "countered"
        req.counter_note = data.message
        req.proposed_slots = [s.model_dump(mode="json") for s in data.proposed_slots]
        if data.mode:
            req.mode = data.mode
        req.expires_at = now + timedelta(hours=72)
        req.updated_at = now

        await db.commit()
        await db.refresh(req)

        partner_id = req.requester_id if user_id == req.recipient_id else req.recipient_id
        await notification_service.create_and_push_notification(
            db,
            user_id=partner_id,
            type="swap_countered",
            payload={
                "request_id": str(req.id),
                "message": f"Counter-proposal received: '{data.message[:60]}...'",
            },
        )

        return SwapService._build_swap_request_response(req)

    @staticmethod
    async def decline_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapRequestResponse:
        """Decline a pending or countered proposal."""
        stmt = (
            select(SwapRequest)
            .options(
                selectinload(SwapRequest.requester),
                selectinload(SwapRequest.recipient),
                selectinload(SwapRequest.offered_skill),
                selectinload(SwapRequest.wanted_skill),
            )
            .where(SwapRequest.id == request_id)
        )
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap proposal not found"
            )

        if user_id not in (req.requester_id, req.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to decline this proposal",
            )

        if req.status not in ("pending", "countered"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot decline request in status '{req.status}'.",
            )

        req.status = "declined"
        req.updated_at = datetime.now(UTC)
        await db.commit()

        partner_id = req.requester_id if user_id == req.recipient_id else req.recipient_id
        await notification_service.create_and_push_notification(
            db,
            user_id=partner_id,
            type="swap_declined",
            payload={
                "request_id": str(req.id),
                "message": "Your swap proposal was politely declined.",
            },
        )

        return SwapService._build_swap_request_response(req)

    @staticmethod
    async def cancel_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapRequestResponse:
        """Cancel an outgoing proposal before it is accepted."""
        stmt = (
            select(SwapRequest)
            .options(
                selectinload(SwapRequest.requester),
                selectinload(SwapRequest.recipient),
                selectinload(SwapRequest.offered_skill),
                selectinload(SwapRequest.wanted_skill),
            )
            .where(SwapRequest.id == request_id)
        )
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap proposal not found"
            )

        if user_id not in (req.requester_id, req.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this proposal",
            )

        if req.status not in ("pending", "countered"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel proposal in status '{req.status}'.",
            )

        req.status = "cancelled"
        req.updated_at = datetime.now(UTC)
        await db.commit()

        return SwapService._build_swap_request_response(req)

    # ── Stage 3: Sessions, Halves, and Conflict Checking ───────────────
    @staticmethod
    async def check_schedule_conflicts(
        db: AsyncSession,
        user_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        """Validate that a user has no overlapping active session halves or blackout dates."""
        # 1. Existing session halves
        overlap_stmt = select(SwapSessionHalf).where(
            or_(
                SwapSessionHalf.mentor_id == user_id,
                SwapSessionHalf.learner_id == user_id,
            ),
            SwapSessionHalf.status.in_(["scheduled", "active"]),
            SwapSessionHalf.start_time_utc < end_time,
            SwapSessionHalf.end_time_utc > start_time,
        )
        if (await db.execute(overlap_stmt)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Schedule conflict: One of the participants has an overlapping swap session at that time.",
            )

        # 2. Blackout dates
        blackout_stmt = select(AvailabilityBlackout).where(
            AvailabilityBlackout.user_id == user_id,
            AvailabilityBlackout.start_datetime_utc < end_time,
            AvailabilityBlackout.end_datetime_utc > start_time,
        )
        if (await db.execute(blackout_stmt)).scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Schedule conflict: A participant has declared a blackout interval during this time slot.",
            )

    @staticmethod
    async def accept_request(
        db: AsyncSession,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        accept_data: SwapRequestAccept,
    ) -> SwapSessionResponse:
        """
        Accept a swap proposal, creating an agreed SwapSession and two 30-minute halves.
        Enforces schedule conflict guards, Jitsi token generation, and public venue validation.
        """
        stmt = (
            select(SwapRequest)
            .options(
                selectinload(SwapRequest.requester),
                selectinload(SwapRequest.recipient),
                selectinload(SwapRequest.offered_skill),
                selectinload(SwapRequest.wanted_skill),
            )
            .where(SwapRequest.id == request_id)
        )
        req = (await db.execute(stmt)).scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap proposal not found"
            )

        if user_id not in (req.requester_id, req.recipient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to accept this proposal",
            )

        if req.status not in ("pending", "countered"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept proposal in status '{req.status}'.",
            )

        if not req.proposed_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No proposed slots found on proposal",
            )

        slot_idx = accept_data.selected_slot_index
        if slot_idx < 0 or slot_idx >= len(req.proposed_slots):
            slot_idx = 0
        slot = req.proposed_slots[slot_idx]

        start_time_1 = parse_utc_datetime(slot["start_time_utc"])
        end_time_1 = parse_utc_datetime(slot["end_time_utc"])
        start_time_2 = end_time_1
        end_time_2 = start_time_2 + timedelta(minutes=settings.SWAP_SESSION_MINUTES)

        now = datetime.now(UTC)
        if start_time_1 <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The chosen time slot has already passed. Please counter with a future slot.",
            )

        # Conflict guards for both participants
        await SwapService.check_schedule_conflicts(db, req.requester_id, start_time_1, end_time_2)
        await SwapService.check_schedule_conflicts(db, req.recipient_id, start_time_1, end_time_2)

        if req.mode == "in_person":
            place_name = accept_data.public_place_name or "Campus Main Library"
            place_addr = accept_data.public_place_address
            assert_public_place(place_name, place_addr)
        else:
            place_name = None
            place_addr = None

        # Update proposal status
        req.status = "accepted"
        req.updated_at = now

        # Create SwapSession
        session_id = uuid.uuid4()
        room_token = secrets.token_urlsafe(16) if req.mode == "video" else None
        session = SwapSession(
            id=session_id,
            request_id=req.id,
            user_a_id=req.requester_id,
            user_b_id=req.recipient_id,
            status="scheduled",
            mode=req.mode,
            public_place_name=place_name,
            public_place_address=place_addr,
            jitsi_room_token=room_token,
            user_a_confirmed=False,
            user_b_confirmed=False,
            created_at=now,
            updated_at=now,
        )
        db.add(session)

        # Half 1: Requester mentors Recipient (Offered Skill) for 30m
        half_1 = SwapSessionHalf(
            id=uuid.uuid4(),
            session_id=session_id,
            half_number=1,
            mentor_id=req.requester_id,
            learner_id=req.recipient_id,
            skill_id=req.offered_skill_id,
            start_time_utc=start_time_1,
            end_time_utc=end_time_1,
            status="scheduled",
            ics_uid=f"swap-h1-{uuid.uuid4()}@nexussocial.dev",
            created_at=now,
        )
        # Half 2: Recipient mentors Requester (Wanted Skill) for 30m
        half_2 = SwapSessionHalf(
            id=uuid.uuid4(),
            session_id=session_id,
            half_number=2,
            mentor_id=req.recipient_id,
            learner_id=req.requester_id,
            skill_id=req.wanted_skill_id,
            start_time_utc=start_time_2,
            end_time_utc=end_time_2,
            status="scheduled",
            ics_uid=f"swap-h2-{uuid.uuid4()}@nexussocial.dev",
            created_at=now,
        )
        db.add(half_1)
        db.add(half_2)

        await db.commit()

        # Push notification to the other participant
        partner_id = req.requester_id if user_id == req.recipient_id else req.recipient_id
        await notification_service.create_and_push_notification(
            db,
            user_id=partner_id,
            type="swap_accepted",
            payload={
                "session_id": str(session_id),
                "request_id": str(req.id),
                "start_time_utc": start_time_1.isoformat(),
                "mode": req.mode,
                "message": f"Swap confirmed! Session scheduled for {start_time_1.strftime('%b %d at %H:%M UTC')}.",
            },
        )

        return await SwapService.get_session_by_id(db, session_id, user_id)

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[SwapSessionResponse]:
        """Retrieve all scheduled, active, and completed swap sessions for a user."""
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.mentor),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.learner),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            )
            .where(or_(SwapSession.user_a_id == user_id, SwapSession.user_b_id == user_id))
            .order_by(SwapSession.created_at.desc())
        )
        sessions = (await db.execute(stmt)).scalars().all()
        return [SwapService._build_swap_session_response(s) for s in sessions]

    @staticmethod
    async def get_session_by_id(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapSessionResponse:
        """Fetch session details, halves, and secure video room access."""
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.mentor),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.learner),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            )
            .where(SwapSession.id == session_id)
        )
        sess = (await db.execute(stmt)).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if user_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this session"
            )

        return SwapService._build_swap_session_response(sess)

    # ── Stage 3: Completion, Reviews, Trust Engine & Chat ───────────────
    @staticmethod
    async def confirm_session_completion(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SwapSessionResponse:
        """Confirm completion of both halves by a participant. Marks completed when both agree."""
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.mentor),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.learner),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            )
            .where(SwapSession.id == session_id)
        )
        sess = (await db.execute(stmt)).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if user_id == sess.user_a_id:
            sess.user_a_confirmed = True
        elif user_id == sess.user_b_id:
            sess.user_b_confirmed = True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        now = datetime.now(UTC)
        # If both confirmed, complete session and update reciprocity & trust
        if sess.user_a_confirmed and sess.user_b_confirmed:
            sess.status = "completed"
            sess.updated_at = now
            for h in sess.halves:
                h.status = "completed"

            # Update reciprocity ledgers (+30m taught, +30m learned for each)
            for uid in (sess.user_a_id, sess.user_b_id):
                rl = (
                    await db.execute(
                        select(ReciprocityLedger).where(ReciprocityLedger.user_id == uid)
                    )
                ).scalar_one_or_none()
                if not rl:
                    rl = ReciprocityLedger(
                        id=uuid.uuid4(),
                        user_id=uid,
                        minutes_taught=0,
                        minutes_learned=0,
                        net_balance_minutes=0,
                        grace_used=0,
                        updated_at=now,
                    )
                    db.add(rl)
                rl.minutes_taught += settings.SWAP_SESSION_MINUTES
                rl.minutes_learned += settings.SWAP_SESSION_MINUTES
                rl.net_balance_minutes = rl.minutes_taught - rl.minutes_learned
                rl.updated_at = now

                # Trust Score update
                ts = (
                    await db.execute(select(TrustScore).where(TrustScore.user_id == uid))
                ).scalar_one_or_none()
                if not ts:
                    ts = TrustScore(
                        id=uuid.uuid4(),
                        user_id=uid,
                        score=100,
                        completed_count=0,
                        no_show_count=0,
                        cancellation_count=0,
                        avg_rating=5.0,
                        badges=[],
                        updated_at=now,
                    )
                    db.add(ts)
                ts.completed_count += 1
                # Badges
                if ts.completed_count >= 1 and "First Swap" not in ts.badges:
                    ts.badges = list(ts.badges) + ["First Swap"]
                if ts.completed_count >= 5 and "Swap Veteran" not in ts.badges:
                    ts.badges = list(ts.badges) + ["Swap Veteran"]
                if ts.completed_count >= 10 and "Skill Master" not in ts.badges:
                    ts.badges = list(ts.badges) + ["Skill Master"]
                ts.updated_at = now

            # Broadcast completion to session and user notifications
            await pubsub.publish(
                f"session:{session_id}",
                {"event": "session_completed", "data": {"session_id": str(session_id)}},
            )
            for uid in (sess.user_a_id, sess.user_b_id):
                await notification_service.create_and_push_notification(
                    db,
                    user_id=uid,
                    type="swap_completed",
                    payload={
                        "session_id": str(session_id),
                        "message": "Swap completed! Please leave your double-blind review to reveal peer feedback.",
                    },
                )

        await db.commit()
        return SwapService._build_swap_session_response(sess)

    @staticmethod
    async def create_session_review(
        db: AsyncSession,
        session_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        data: SwapReviewCreate,
    ) -> SwapReviewResponse:
        """
        Submit a double-blind review.
        Reviews remain hidden until both participants submit or 7 calendar days elapse.
        """
        sess = (
            await db.execute(select(SwapSession).where(SwapSession.id == session_id))
        ).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if reviewer_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        reviewee_id = sess.user_b_id if reviewer_id == sess.user_a_id else sess.user_a_id

        # Existing review check
        existing = (
            await db.execute(
                select(SwapReview).where(
                    SwapReview.session_id == session_id,
                    SwapReview.reviewer_id == reviewer_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this session",
            )

        # Check if peer review exists
        peer_review = (
            await db.execute(
                select(SwapReview).where(
                    SwapReview.session_id == session_id,
                    SwapReview.reviewer_id == reviewee_id,
                )
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        both_revealed = peer_review is not None

        new_review = SwapReview(
            id=uuid.uuid4(),
            session_id=session_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=data.rating,
            tags=data.tags,
            public_comment=data.public_comment,
            private_feedback=data.private_feedback,
            is_revealed=both_revealed,
            revealed_at=now if both_revealed else None,
            created_at=now,
        )
        db.add(new_review)

        if both_revealed and peer_review:
            peer_review.is_revealed = True
            peer_review.revealed_at = now

            # Recalculate average ratings for both users
            for uid in (reviewer_id, reviewee_id):
                avg_res = (
                    await db.execute(
                        select(func.avg(SwapReview.rating)).where(
                            SwapReview.reviewee_id == uid,
                            SwapReview.is_revealed.is_(True),
                        )
                    )
                ).scalar()
                if avg_res is not None:
                    ts = (
                        await db.execute(select(TrustScore).where(TrustScore.user_id == uid))
                    ).scalar_one_or_none()
                    if ts:
                        ts.avg_rating = round(float(avg_res), 2)
                        ts.updated_at = now

            # Notifications to both
            for uid in (reviewer_id, reviewee_id):
                await notification_service.create_and_push_notification(
                    db,
                    user_id=uid,
                    type="review_revealed",
                    payload={
                        "session_id": str(session_id),
                        "message": "Both reviews submitted! Peer feedback and ratings are now revealed.",
                    },
                )
        else:
            # Notify peer that partner has submitted their review
            await notification_service.create_and_push_notification(
                db,
                user_id=reviewee_id,
                type="review_pending",
                payload={
                    "session_id": str(session_id),
                    "message": "Your swap partner has submitted a review! Submit yours to reveal mutual ratings.",
                },
            )

        await db.commit()

        # Eager load reviewer & reviewee
        review_full = (
            await db.execute(
                select(SwapReview)
                .options(
                    selectinload(SwapReview.reviewer),
                    selectinload(SwapReview.reviewee),
                )
                .where(SwapReview.id == new_review.id)
            )
        ).scalar_one()

        return SwapService._build_swap_review_response(review_full, viewer_id=reviewer_id)

    @staticmethod
    async def get_session_reviews(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SwapReviewResponse]:
        """Fetch reviews for a session respecting double-blind isolation."""
        stmt = (
            select(SwapReview)
            .options(
                selectinload(SwapReview.reviewer),
                selectinload(SwapReview.reviewee),
            )
            .where(SwapReview.session_id == session_id)
        )
        reviews = (await db.execute(stmt)).scalars().all()
        # If not revealed, only return user's own review
        result: list[SwapReviewResponse] = []
        for r in reviews:
            if r.is_revealed or r.reviewer_id == user_id:
                result.append(SwapService._build_swap_review_response(r, viewer_id=user_id))
        return result

    @staticmethod
    async def report_session_dispute(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: SwapDisputeCreate,
    ) -> SwapSessionResponse:
        """Report a no-show, violation, or dispute on a session."""
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.mentor),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.learner),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            )
            .where(SwapSession.id == session_id)
        )
        sess = (await db.execute(stmt)).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if user_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        now = datetime.now(UTC)
        sess.status = "disputed"
        sess.dispute_reason = data.reason
        sess.disputed_by_id = user_id
        sess.updated_at = now

        # Create audit report
        report = SwapReport(
            id=uuid.uuid4(),
            reporter_id=user_id,
            target_type="session",
            target_id=session_id,
            category="dispute",
            notes=data.reason,
            status="pending",
            created_at=now,
        )
        db.add(report)

        # Notify admin channel
        await pubsub.publish(
            "admin",
            {
                "event": "admin_alert",
                "data": {
                    "type": "swap_dispute",
                    "session_id": str(session_id),
                    "disputed_by": str(user_id),
                    "reason": data.reason,
                },
            },
        )

        await db.commit()
        return SwapService._build_swap_session_response(sess)

    @staticmethod
    async def post_session_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        sender_id: uuid.UUID,
        data: SwapMessageCreate,
    ) -> SwapMessageResponse:
        """Post a logistics chat message within an active or scheduled session."""
        sess = (
            await db.execute(select(SwapSession).where(SwapSession.id == session_id))
        ).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if sender_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        now = datetime.now(UTC)
        msg_id = uuid.uuid4()
        msg = SwapMessage(
            id=msg_id,
            session_id=session_id,
            sender_id=sender_id,
            content=data.content,
            created_at=now,
        )
        db.add(msg)
        await db.commit()

        msg_full = (
            await db.execute(
                select(SwapMessage)
                .options(selectinload(SwapMessage.sender))
                .where(SwapMessage.id == msg_id)
            )
        ).scalar_one()

        resp = SwapMessageResponse(
            id=msg_full.id,
            session_id=msg_full.session_id,
            sender=build_user_minimal(msg_full.sender),
            content=msg_full.content,
            created_at=msg_full.created_at,
        )

        # Broadcast via pub/sub to session channel
        await pubsub.publish(
            f"session:{session_id}",
            {"event": "chat_message", "data": resp.model_dump(mode="json")},
        )

        return resp

    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[SwapMessageResponse]:
        """Fetch logistics chat messages for a session."""
        sess = (
            await db.execute(select(SwapSession).where(SwapSession.id == session_id))
        ).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if user_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        stmt = (
            select(SwapMessage)
            .options(selectinload(SwapMessage.sender))
            .where(SwapMessage.session_id == session_id)
            .order_by(SwapMessage.created_at.asc())
        )
        msgs = (await db.execute(stmt)).scalars().all()
        return [
            SwapMessageResponse(
                id=m.id,
                session_id=m.session_id,
                sender=build_user_minimal(m.sender),
                content=m.content,
                created_at=m.created_at,
            )
            for m in msgs
        ]

    @staticmethod
    async def generate_session_ics(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ICSExportResponse:
        """Generate standard RFC 5545 iCalendar (.ics) file for both halves."""
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.mentor),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.learner),
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            )
            .where(SwapSession.id == session_id)
        )
        sess = (await db.execute(stmt)).scalar_one_or_none()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Swap session not found"
            )

        if user_id not in (sess.user_a_id, sess.user_b_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant of this session"
            )

        now_fmt = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Nexus Social//Skill Swap Economy//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for h in sess.halves:
            start_fmt = h.start_time_utc.strftime("%Y%m%dT%H%M%SZ")
            end_fmt = h.end_time_utc.strftime("%Y%m%dT%H%M%SZ")
            loc = (
                sess.public_place_name
                if sess.mode == "in_person"
                else f"{settings.JITSI_BASE_URL}/nexus-swap-{sess.id}-{sess.jitsi_room_token}"
            )
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{h.ics_uid}",
                    f"DTSTAMP:{now_fmt}",
                    f"DTSTART:{start_fmt}",
                    f"DTEND:{end_fmt}",
                    f"SUMMARY:Skill Swap Half {h.half_number}: {h.skill.display_name} ({h.mentor.display_name} -> {h.learner.display_name})",
                    "DESCRIPTION:Reciprocal 30-minute peer skill mentorship on Nexus Social.",
                    f"LOCATION:{loc or 'Remote Video'}",
                    "STATUS:CONFIRMED",
                    "END:VEVENT",
                ]
            )

        lines.append("END:VCALENDAR")
        return ICSExportResponse(
            filename=f"nexus-swap-{sess.id}.ics",
            content="\r\n".join(lines),
        )

    # ── Internal Response Builders ─────────────────────────────────────
    @staticmethod
    def _build_swap_request_response(req: SwapRequest) -> SwapRequestResponse:
        return SwapRequestResponse(
            id=req.id,
            listing_id=req.listing_id,
            requester=build_user_minimal(req.requester),
            recipient=build_user_minimal(req.recipient),
            offered_skill=SkillResponse.model_validate(req.offered_skill),
            wanted_skill=SkillResponse.model_validate(req.wanted_skill),
            mode=req.mode,
            message=req.message,
            proposed_slots=req.proposed_slots,
            status=req.status,
            counter_note=req.counter_note,
            expires_at=req.expires_at,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )

    @staticmethod
    def _build_swap_session_response(sess: SwapSession) -> SwapSessionResponse:
        halves = [
            SwapSessionHalfResponse(
                id=h.id,
                session_id=h.session_id,
                half_number=h.half_number,
                mentor=build_user_minimal(h.mentor),
                learner=build_user_minimal(h.learner),
                skill=SkillResponse.model_validate(h.skill),
                start_time_utc=h.start_time_utc,
                end_time_utc=h.end_time_utc,
                status=h.status,
                ics_uid=h.ics_uid,
            )
            for h in sess.halves
        ]
        halves.sort(key=lambda x: x.half_number)

        jitsi_url = (
            f"{settings.JITSI_BASE_URL}/nexus-swap-{sess.id}-{sess.jitsi_room_token}"
            if (sess.mode == "video" and sess.jitsi_room_token)
            else None
        )

        return SwapSessionResponse(
            id=sess.id,
            request_id=sess.request_id,
            user_a=build_user_minimal(sess.user_a),
            user_b=build_user_minimal(sess.user_b),
            status=sess.status,
            mode=sess.mode,
            public_place_name=sess.public_place_name,
            public_place_address=sess.public_place_address,
            jitsi_room_token=sess.jitsi_room_token,
            jitsi_room_url=jitsi_url,
            user_a_confirmed=sess.user_a_confirmed,
            user_b_confirmed=sess.user_b_confirmed,
            dispute_reason=sess.dispute_reason,
            halves=halves,
            created_at=sess.created_at,
            updated_at=sess.updated_at,
        )

    @staticmethod
    def _build_swap_review_response(
        r: SwapReview, viewer_id: uuid.UUID | None = None
    ) -> SwapReviewResponse:
        # If not revealed and viewer is the reviewee, mask rating & comment
        is_owner = viewer_id == r.reviewer_id
        is_revealed = r.is_revealed

        rating = r.rating if (is_revealed or is_owner) else None
        comment = r.public_comment if (is_revealed or is_owner) else None

        return SwapReviewResponse(
            id=r.id,
            session_id=r.session_id,
            reviewer=build_user_minimal(r.reviewer),
            reviewee=build_user_minimal(r.reviewee),
            rating=rating,
            tags=r.tags if (is_revealed or is_owner) else [],
            public_comment=comment,
            is_revealed=r.is_revealed,
            revealed_at=r.revealed_at,
            created_at=r.created_at,
        )

    # ── Stage 4: AI Assistants ───────────────────────────────────────
    @staticmethod
    async def generate_session_plan(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        req: SwapSessionPlanRequest,
    ) -> SwapSessionPlanResponse:
        """Generate structured 30-minute agenda with time allocations and milestones."""
        sess = await db.get(
            SwapSession,
            session_id,
            options=[
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            ],
        )
        if not sess or (sess.user_a_id != user_id and sess.user_b_id != user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        # Identify skill to mentor/learn
        skill_name = "Peer Skill"
        if sess.halves:
            skill_name = sess.halves[0].skill.display_name

        ai = get_ai_service()
        prompt = build_session_plan_prompt(
            skill_name=skill_name,
            mentor_notes=req.mentor_notes,
            learner_level="Intermediate",
            session_goals=req.goals,
        )

        try:
            raw_text, _ = await ai.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction=SWAP_SESSION_PLAN_SYSTEM_PROMPT,
            )
            # Clean markdown codeblocks
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            parsed = json.loads(clean_text.strip())
            return SwapSessionPlanResponse(
                objective=parsed.get("objective", f"Master core concepts of {skill_name} in 30 minutes"),
                agenda_items=[AgendaItem(**item) for item in parsed.get("agenda_items", [])],
                suggested_questions=parsed.get("suggested_questions", []),
                mentor_tips=parsed.get("mentor_tips", "Keep explanations practical and encourage questions."),
            )
        except Exception:
            # Fallback deterministic 30m plan
            return SwapSessionPlanResponse(
                objective=f"Master key practical fundamentals of {skill_name} in 30 focused minutes",
                agenda_items=[
                    AgendaItem(minute="0-5", title="Warm-up & Goal Alignment", description="Introductions, assessing current knowledge, and agreeing on key targets."),
                    AgendaItem(minute="5-20", title="Core Demonstration & Coaching", description=f"Hands-on walkthrough of {skill_name} concepts and live examples."),
                    AgendaItem(minute="20-27", title="Interactive Practice & Guidance", description="Learner attempts exercises with real-time mentor feedback."),
                    AgendaItem(minute="27-30", title="Key Takeaways & Next Steps", description="Reviewing accomplishments and identifying follow-up practice materials."),
                ],
                suggested_questions=[
                    f"What is the most challenging aspect of {skill_name} you've faced?",
                    "Can we walk through a real-world scenario together?",
                    "What resources would help reinforce what we covered today?",
                ],
                mentor_tips="Focus on high-leverage concepts and pause regularly for questions.",
            )

    @staticmethod
    async def generate_session_recap(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        req: SwapSessionRecapRequest,
    ) -> SwapSessionRecapResponse:
        """Convert rough session notes into structured takeaways and action items."""
        sess = await db.get(
            SwapSession,
            session_id,
            options=[
                selectinload(SwapSession.halves).selectinload(SwapSessionHalf.skill),
            ],
        )
        if not sess or (sess.user_a_id != user_id and sess.user_b_id != user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        skill_name = sess.halves[0].skill.display_name if sess.halves else "Skill"
        ai = get_ai_service()
        prompt = build_session_recap_prompt(skill_name=skill_name, rough_notes=req.rough_notes)

        try:
            raw_text, _ = await ai.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction=SWAP_SESSION_RECAP_SYSTEM_PROMPT,
            )
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            parsed = json.loads(clean_text.strip())
            return SwapSessionRecapResponse(
                summary=parsed.get("summary", "Session completed with key milestones achieved."),
                key_takeaways=parsed.get("key_takeaways", []),
                action_items=parsed.get("action_items", []),
                recommended_followup=parsed.get("recommended_followup", "Continue practicing daily."),
            )
        except Exception:
            return SwapSessionRecapResponse(
                summary=f"Productive 30-minute peer swap on {skill_name}. Covered practical concepts with active mentoring.",
                key_takeaways=[
                    f"Established core theoretical foundations for {skill_name}.",
                    "Identified practical troubleshooting strategies.",
                    "Practiced hands-on implementation steps.",
                ],
                action_items=[
                    "Review code and exercises covered during the session.",
                    "Complete one independent practice exercise before the next meetup.",
                ],
                recommended_followup=f"Build a small mini-project applying today's {skill_name} takeaways.",
            )

    @staticmethod
    async def generate_fairness_advice(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> SwapFairnessAdviceResponse:
        """Analyze user reciprocity ledger and generate helpful guidance."""
        ledger = await SwapService.get_or_create_ledger(db, user_id)
        us_stmt = (
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .options(selectinload(UserSkill.skill))
        )
        skills = (await db.execute(us_stmt)).scalars().all()
        taught = [s.skill.display_name for s in skills if s.skill_type == "teach"]
        wanted = [s.skill.display_name for s in skills if s.skill_type == "learn"]

        net = ledger.net_balance_minutes
        if net < -30:
            status_val = "learning_deficit"
            headline = "You've received great mentorship! Time to pay it forward."
            action_tips = [
                "Create a new swap listing offering your strongest skills.",
                "Accept incoming swap requests from community newcomers.",
            ]
        elif net > 30:
            status_val = "teaching_deficit"
            headline = "You're a star contributor! Treat yourself to new learning."
            action_tips = [
                "Browse the Discovery Hub and propose swaps for skills you want to learn.",
                "Connect with recommended peers in the AI Matches section.",
            ]
        else:
            status_val = "balanced"
            headline = "Your skill exchange balance is in perfect equilibrium!"
            action_tips = [
                "Keep offering and receiving 30-minute peer sessions.",
                "Share your active listings to the main feed to meet new partners.",
            ]

        ai = get_ai_service()
        prompt = build_fairness_advisor_prompt(
            minutes_taught=ledger.minutes_taught,
            minutes_learned=ledger.minutes_learned,
            net_balance_minutes=ledger.net_balance_minutes,
            grace_used=ledger.grace_used,
            user_skills_taught=taught,
            user_skills_wanted=wanted,
        )

        try:
            raw_text, _ = await ai.chat(
                messages=[{"role": "user", "content": prompt}],
                system_instruction=SWAP_FAIRNESS_ADVISOR_SYSTEM_PROMPT,
            )
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            parsed = json.loads(clean_text.strip())
            return SwapFairnessAdviceResponse(
                balance_status=parsed.get("balance_status", status_val),
                headline=parsed.get("headline", headline),
                insights=parsed.get("insights", f"You have completed {ledger.minutes_taught}m teaching and {ledger.minutes_learned}m learning."),
                recommended_actions=parsed.get("recommended_actions", action_tips),
                recommended_skills_to_offer=parsed.get("recommended_skills_to_offer", taught[:2]),
            )
        except Exception:
            return SwapFairnessAdviceResponse(
                balance_status=status_val,
                headline=headline,
                insights=f"You have taught {ledger.minutes_taught} minutes and learned for {ledger.minutes_learned} minutes (Net balance: {net}m, Grace used: {ledger.grace_used}m).",
                recommended_actions=action_tips,
                recommended_skills_to_offer=taught[:2] or ["General Mentorship"],
            )

    # ── Safety & Moderation (Stage 4) ─────────────────────────────────
    @staticmethod
    def detect_swap_safety_violations(text: str) -> list[str]:
        """Detect monetary requests, off-platform contact harvesting, and unsafe meetup locations."""
        violations: list[str] = []
        lower = text.lower()
        for p in MONEY_PATTERNS:
            if re.search(p, lower):
                violations.append("Monetary payment or fee solicitation detected.")
                break

        contact_harvesting_patterns = [
            r"\b(?:telegram|whatsapp|wa\.me|snapchat|snap|discord|wechat)\s*[:@/]?\s*[\w\.\+]+",
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            r"\b(?:dm me on ig|hit my insta|reach me on whatsapp|message my tg)\b",
        ]
        for p in contact_harvesting_patterns:
            if re.search(p, lower):
                violations.append("External contact harvesting or off-platform communication handle detected.")
                break

        unsafe_venue_patterns = [
            r"\b(?:my house|my place|my apartment|come over to my room|hotel room|motel)\b",
        ]
        for p in unsafe_venue_patterns:
            if re.search(p, lower):
                violations.append("Unsafe private residence or unverified private venue requested.")
                break

        return violations

    @staticmethod
    async def block_user(
        db: AsyncSession,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> UserBlockResponse:
        """Block a peer to prevent all mutual discovery, proposals, and chats."""
        if blocker_id == blocked_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot block yourself.")

        # Check existing block
        existing = (
            await db.execute(
                select(UserBlock).where(
                    UserBlock.blocker_id == blocker_id,
                    UserBlock.blocked_id == blocked_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            blocked_user = await db.get(User, blocked_id)
            return UserBlockResponse(
                id=existing.id,
                blocker_id=existing.blocker_id,
                blocked_id=existing.blocked_id,
                blocked_user=build_user_minimal(blocked_user) if blocked_user else None,
                created_at=existing.created_at,
            )

        block = UserBlock(
            id=uuid.uuid4(),
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            created_at=datetime.now(UTC),
        )
        db.add(block)
        await db.commit()
        await db.refresh(block)

        blocked_user = await db.get(User, blocked_id)
        return UserBlockResponse(
            id=block.id,
            blocker_id=block.blocker_id,
            blocked_id=block.blocked_id,
            blocked_user=build_user_minimal(blocked_user) if blocked_user else None,
            created_at=block.created_at,
        )

    @staticmethod
    async def unblock_user(
        db: AsyncSession,
        blocker_id: uuid.UUID,
        blocked_id: uuid.UUID,
    ) -> None:
        """Remove a block pair."""
        await db.execute(
            delete(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        await db.commit()

    @staticmethod
    async def list_blocked_users(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[UserBlockResponse]:
        """List all users blocked by the authenticated user."""
        stmt = (
            select(UserBlock)
            .where(UserBlock.blocker_id == user_id)
            .options(selectinload(UserBlock.blocked_user))
            .order_by(UserBlock.created_at.desc())
        )
        res = await db.execute(stmt)
        return [
            UserBlockResponse(
                id=b.id,
                blocker_id=b.blocker_id,
                blocked_id=b.blocked_id,
                blocked_user=build_user_minimal(b.blocked_user) if b.blocked_user else None,
                created_at=b.created_at,
            )
            for b in res.scalars().all()
        ]

    @staticmethod
    async def report_target(
        db: AsyncSession,
        reporter_id: uuid.UUID,
        req: SwapReportCreate,
    ) -> SwapReportResponse:
        """
        Submit a safety report against a listing, user, or session.
        AUTOMATIC 3-STRIKE THRESHOLD:
        If 3 distinct users report the target within 24 hours, the system automatically:
        - Unpublishes/removes the listing (if listing)
        - Hides user profile (is_invisible=True) and pauses listings (if user)
        """
        # Save report
        report = SwapReport(
            id=uuid.uuid4(),
            reporter_id=reporter_id,
            target_type=req.target_type,
            target_id=req.target_id,
            category=req.category,
            notes=req.notes,
            status="pending",
            created_at=datetime.now(UTC),
        )
        db.add(report)
        await db.commit()

        # Check 3-strike threshold in the last 24h
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        count_stmt = select(func.count(func.distinct(SwapReport.reporter_id))).where(
            SwapReport.target_type == req.target_type,
            SwapReport.target_id == req.target_id,
            SwapReport.created_at >= cutoff,
        )
        distinct_reporters = (await db.execute(count_stmt)).scalar_one() or 0

        if distinct_reporters >= 3:
            if req.target_type == "listing":
                listing = await db.get(SwapListing, req.target_id)
                if listing and listing.status == "active":
                    listing.status = "removed"
                    await db.commit()
            elif req.target_type == "user":
                prof_stmt = select(UserSwapProfile).where(UserSwapProfile.user_id == req.target_id)
                prof = (await db.execute(prof_stmt)).scalar_one_or_none()
                if prof:
                    prof.is_invisible = True
                    # Pause all active listings
                    active_listings_res = await db.execute(
                        select(SwapListing).where(
                            SwapListing.user_id == prof.user_id,
                            SwapListing.status == "active",
                        )
                    )
                    for lst_item in active_listings_res.scalars().all():
                        lst_item.status = "paused"
                    await db.commit()

        reporter = await db.get(User, reporter_id)
        return SwapReportResponse(
            id=report.id,
            reporter_id=report.reporter_id,
            reporter=build_user_minimal(reporter) if reporter else None,
            target_type=report.target_type,
            target_id=report.target_id,
            category=report.category,
            notes=report.notes,
            status=report.status,
            admin_resolution=report.admin_resolution,
            created_at=report.created_at,
        )

    @staticmethod
    def check_in_person_safety(
        place_name: str,
        address: str,
    ) -> InPersonSafetyCheck:
        """Verify public venue safety and provide guidance."""
        try:
            assert_public_place(place_name, address)
            return InPersonSafetyCheck(
                public_place_name=place_name,
                public_place_address=address,
                is_safe_public_venue=True,
                warning=None,
                safety_tips=[
                    "Meet in well-lit, public areas with people around (e.g. library, cafe, campus center).",
                    "Keep your phone charged and inform a friend about your meetup location and schedule.",
                    "Never accept rides from strangers or move to private locations.",
                    "If you ever feel uncomfortable, you may leave immediately without penalty.",
                ],
            )
        except HTTPException as e:
            return InPersonSafetyCheck(
                public_place_name=place_name,
                public_place_address=address,
                is_safe_public_venue=False,
                warning=str(e.detail),
                safety_tips=[
                    "Residential addresses and private units are strictly prohibited.",
                    "Please choose a public library, coffee shop, or university commons.",
                ],
            )

    # ── Admin Swaps Console Operations (Stage 4) ──────────────────────
    @staticmethod
    async def get_swap_admin_stats(db: AsyncSession) -> SwapAdminStatsResponse:
        """Aggregate platform KPIs for Admin Swaps console."""
        active_listings = (
            await db.execute(select(func.count(SwapListing.id)).where(SwapListing.status == "active"))
        ).scalar_one() or 0

        week_ago = datetime.now(UTC) - timedelta(days=7)
        swaps_this_week = (
            await db.execute(
                select(func.count(SwapSession.id)).where(SwapSession.created_at >= week_ago)
            )
        ).scalar_one() or 0

        completed = (
            await db.execute(
                select(func.count(SwapSession.id)).where(SwapSession.status == "completed")
            )
        ).scalar_one() or 0

        disputes = (
            await db.execute(select(func.count(SwapReport.id)))
        ).scalar_one() or 0

        total_sessions = (
            await db.execute(select(func.count(SwapSession.id)))
        ).scalar_one() or 0

        completion_rate = (completed / total_sessions * 100.0) if total_sessions > 0 else 100.0
        dispute_rate = (disputes / total_sessions * 100.0) if total_sessions > 0 else 0.0

        # Top skills
        top_skills_query = (
            select(Skill.display_name, func.count(UserSkill.id).label("count"))
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .group_by(Skill.display_name)
            .order_by(func.count(UserSkill.id).desc())
            .limit(5)
        )
        top_skills_res = await db.execute(top_skills_query)
        top_skills = [
            {"skill": row[0], "count": row[1]}
            for row in top_skills_res.all()
        ]

        return SwapAdminStatsResponse(
            total_active_listings=active_listings,
            swaps_this_week=swaps_this_week,
            total_scheduled_sessions=total_sessions,
            total_completed_sessions=completed,
            total_disputes=disputes,
            completion_rate=round(completion_rate, 1),
            dispute_rate=round(dispute_rate, 1),
            top_skills=top_skills,
        )

    @staticmethod
    async def list_admin_listings(
        db: AsyncSession,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> list[SwapListingAdminResponse]:
        """Admin listing view with report counts."""
        stmt = (
            select(SwapListing)
            .options(
                selectinload(SwapListing.user),
                selectinload(SwapListing.skill_offered),
                selectinload(SwapListing.skill_wanted),
            )
            .order_by(SwapListing.created_at.desc())
            .limit(limit)
        )
        if status_filter:
            stmt = stmt.where(SwapListing.status == status_filter)

        res = await db.execute(stmt)
        listings = res.scalars().all()

        output = []
        for listing_obj in listings:
            reports_count = (
                await db.execute(
                    select(func.count(SwapReport.id)).where(
                        SwapReport.target_type == "listing",
                        SwapReport.target_id == listing_obj.id,
                    )
                )
            ).scalar_one() or 0

            output.append(
                SwapListingAdminResponse(
                    id=listing_obj.id,
                    title=listing_obj.title,
                    user=build_user_minimal(listing_obj.user),
                    skill_offered=SkillResponse.model_validate(listing_obj.skill_offered),
                    skill_wanted=SkillResponse.model_validate(listing_obj.skill_wanted) if listing_obj.skill_wanted else None,
                    status=listing_obj.status,
                    modes=listing_obj.modes,
                    reports_count=reports_count,
                    created_at=listing_obj.created_at,
                )
            )
        return output

    @staticmethod
    async def update_admin_listing_status(
        db: AsyncSession,
        listing_id: uuid.UUID,
        new_status: str,
    ) -> SwapListing:
        """Suspend, pause, or reinstate a swap listing."""
        listing = await db.get(SwapListing, listing_id)
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
        listing.status = new_status
        await db.commit()
        await db.refresh(listing)
        return listing

    @staticmethod
    async def list_admin_disputes(
        db: AsyncSession,
        status_filter: str | None = None,
    ) -> list[SwapDisputeAdminResponse]:
        """Retrieve disputes and reports for admin triage."""
        stmt = (
            select(SwapReport)
            .options(selectinload(SwapReport.reporter))
            .order_by(SwapReport.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(SwapReport.status == status_filter)

        res = await db.execute(stmt)
        reports = res.scalars().all()
        return [
            SwapDisputeAdminResponse(
                id=r.id,
                session_id=r.target_id,
                reporter=build_user_minimal(r.reporter),
                target_type=r.target_type,
                category=r.category,
                notes=r.notes,
                status=r.status,
                created_at=r.created_at,
            )
            for r in reports
        ]

    @staticmethod
    async def resolve_admin_dispute(
        db: AsyncSession,
        report_id: uuid.UUID,
        req: SwapDisputeResolveRequest,
    ) -> SwapReportResponse:
        """Resolve a dispute report and apply trust score penalties if warranted."""
        report = await db.get(SwapReport, report_id, options=[selectinload(SwapReport.reporter)])
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

        report.status = req.status
        report.admin_resolution = req.admin_resolution

        # If penalty specified and target was user/session
        if req.trust_score_penalty > 0 and report.target_type == "user":
            trust = await SwapService.get_or_create_trust_score(db, report.target_id)
            trust.score = max(0, trust.score - req.trust_score_penalty)
            trust.no_show_count += 1
            trust.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(report)

        return SwapReportResponse(
            id=report.id,
            reporter_id=report.reporter_id,
            reporter=build_user_minimal(report.reporter) if report.reporter else None,
            target_type=report.target_type,
            target_id=report.target_id,
            category=report.category,
            notes=report.notes,
            status=report.status,
            admin_resolution=report.admin_resolution,
            created_at=report.created_at,
        )

    @staticmethod
    async def approve_taxonomy_skill(
        db: AsyncSession,
        skill_id: uuid.UUID,
        display_name: str | None = None,
        category: str | None = None,
    ) -> SkillResponse:
        """Approve a pending user-suggested skill."""
        skill = await db.get(Skill, skill_id)
        if not skill:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")
        skill.status = "active"
        if display_name:
            skill.display_name = display_name
        if category:
            skill.category = category
        await db.commit()
        await db.refresh(skill)
        return SkillResponse.model_validate(skill)

    @staticmethod
    async def merge_taxonomy_skills(
        db: AsyncSession,
        source_skill_id: uuid.UUID,
        target_skill_id: uuid.UUID,
    ) -> SkillResponse:
        """Merge a redundant/synonym skill into a canonical target skill."""
        source = await db.get(Skill, source_skill_id)
        target = await db.get(Skill, target_skill_id)
        if not source or not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

        # Re-link user_skills pointing to source
        user_skills_res = await db.execute(
            select(UserSkill).where(UserSkill.skill_id == source_skill_id)
        )
        for us in user_skills_res.scalars().all():
            us.skill_id = target_skill_id

        # Re-link swap_listings pointing to source
        listings_offered = await db.execute(
            select(SwapListing).where(SwapListing.skill_offered_id == source_skill_id)
        )
        for off_item in listings_offered.scalars().all():
            off_item.skill_offered_id = target_skill_id

        listings_wanted = await db.execute(
            select(SwapListing).where(SwapListing.skill_wanted_id == source_skill_id)
        )
        for want_item in listings_wanted.scalars().all():
            want_item.skill_wanted_id = target_skill_id

        # Add source display_name / slug to target aliases
        aliases = list(target.aliases) if target.aliases else []
        if source.slug not in aliases:
            aliases.append(source.slug)
        if source.display_name.lower() not in aliases:
            aliases.append(source.display_name.lower())
        target.aliases = aliases

        # Mark source as rejected/merged
        source.status = "rejected"

        await db.commit()
        await db.refresh(target)
        return SkillResponse.model_validate(target)
