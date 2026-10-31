"""
Skill Swap Core Service
=======================
Handles swap profile lifecycle, skill competencies, weekly availability windows,
blackout dates, and privacy-preserving public profile serialization.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.swap import (
    AvailabilityBlackout,
    AvailabilityWindow,
    ReciprocityLedger,
    Skill,
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
    UserSkillResponse,
    UserSwapProfilePrivateResponse,
    UserSwapProfilePublicResponse,
    UserSwapProfileUpdate,
)
from app.services.swap_geocoding import coarsen_coord, get_distance_bucket
from app.services.swap_taxonomy import SwapTaxonomyService


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
        ts_res = await db.execute(select(TrustScore).where(TrustScore.user_id == user_id))
        ts = ts_res.scalar_one_or_none()
        rl_res = await db.execute(select(ReciprocityLedger).where(ReciprocityLedger.user_id == user_id))
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
