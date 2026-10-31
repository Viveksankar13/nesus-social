"""
Skill Swap API Router
=====================
REST endpoints for:
- Canonical taxonomy and suggestions
- Coarse geocoding search
- User swap profiles (private management vs. public privacy-preserving view)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user, require_user
from app.models.user import User
from app.schemas.swap import (
    GeocodeSearchResult,
    SkillCategoryGroup,
    SkillResponse,
    SkillSuggestRequest,
    UserSwapProfilePrivateResponse,
    UserSwapProfilePublicResponse,
    UserSwapProfileUpdate,
)
from app.services.swap_geocoding import search_coarse_locations
from app.services.swap_service import SwapService
from app.services.swap_taxonomy import SwapTaxonomyService

router = APIRouter(prefix="/swaps", tags=["Skill Swaps"])


# ── 1. Taxonomy Endpoints ────────────────────────────────────────────
@router.get("/taxonomy", response_model=list[SkillCategoryGroup])
async def get_skill_taxonomy(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SkillCategoryGroup]:
    """Retrieve active canonical skills grouped by category."""
    return await SwapTaxonomyService.get_grouped_categories(db)


@router.post("/taxonomy/suggest", response_model=SkillResponse)
async def suggest_skill(
    req: SkillSuggestRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillResponse:
    """Suggest a new skill into the taxonomy. Auto-approves clean submissions."""
    skill = await SwapTaxonomyService.suggest_skill(db, req.name, req.category)
    return SkillResponse.model_validate(skill)


# ── 2. Coarse Geocoding ──────────────────────────────────────────────
@router.get("/geocode", response_model=list[GeocodeSearchResult])
async def geocode_coarse_location(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    current_user: Annotated[User, Depends(require_user)],
) -> list[GeocodeSearchResult]:
    """Search for locations via Open-Meteo. Returns ~1 km coarse coordinates."""
    return await search_coarse_locations(q, count=5)


# ── 3. Profile Endpoints ─────────────────────────────────────────────
@router.get("/profile/me", response_model=UserSwapProfilePrivateResponse)
async def get_my_swap_profile(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSwapProfilePrivateResponse:
    """Retrieve the authenticated user's private swap profile and preferences."""
    return await SwapService.get_private_profile(db, current_user.id)


@router.put("/profile/me", response_model=UserSwapProfilePrivateResponse)
async def update_my_swap_profile(
    data: UserSwapProfileUpdate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSwapProfilePrivateResponse:
    """Update own swap profile, teaching/learning competencies, and availability."""
    return await SwapService.update_profile(db, current_user.id, data)


@router.get("/profile/{username}", response_model=UserSwapProfilePublicResponse)
async def get_public_swap_profile(
    username: str,
    viewer: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserSwapProfilePublicResponse:
    """
    Retrieve public swap profile for a user.
    PRIVACY GUARANTEE: Never exposes coordinates or geohashes.
    Serializes location as a safe distance bucket (e.g. 'under 1 km', '1–3 km', 'remote').
    """
    viewer_id = viewer.id if viewer else None
    return await SwapService.get_public_profile(db, viewer_id, username)
