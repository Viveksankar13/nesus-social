"""
Skill Swap API Router
=====================
REST endpoints for:
- Canonical taxonomy and suggestions
- Coarse geocoding search
- User swap profiles (private management vs. public privacy-preserving view)
- Swap listings lifecycle and feed integration
- Hyper-local swap discovery query engine
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user, require_user
from app.models.user import User
from app.schemas.swap import (
    GeocodeSearchResult,
    ListingAIDraftRequest,
    ListingAIDraftResponse,
    SkillCategoryGroup,
    SkillResponse,
    SkillSuggestRequest,
    SwapListingCreate,
    SwapListingListResponse,
    SwapListingResponse,
    SwapListingShareResponse,
    SwapListingUpdate,
    SwapMatchResponse,
    UserSwapProfilePrivateResponse,
    UserSwapProfilePublicResponse,
    UserSwapProfileUpdate,
)
from app.services.swap_geocoding import search_coarse_locations
from app.services.swap_matching import SwapMatchingService
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


# ── 4. Listings Endpoints ────────────────────────────────────────────
@router.post("/listings", response_model=SwapListingResponse)
async def create_swap_listing(
    data: SwapListingCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapListingResponse:
    """Create a new swap listing (max 5 active per user, non-monetary policy enforced)."""
    return await SwapService.create_listing(db, current_user.id, data, background_tasks)


@router.get("/listings", response_model=SwapListingListResponse)
async def search_swap_listings(
    db: Annotated[AsyncSession, Depends(get_db)],
    viewer: Annotated[User | None, Depends(get_optional_current_user)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=50)] = None,
    mode: Annotated[str | None, Query(max_length=20)] = None,
    distance_bucket: Annotated[str | None, Query(max_length=30)] = None,
    sort: Annotated[Literal["newest", "nearest", "trust"], Query()] = "newest",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[int, Query(ge=0)] = 0,
) -> SwapListingListResponse:
    """
    Search swap listings with hyper-local spatial filtering and privacy protections.
    PRIVACY GUARANTEE: Never exposes coordinates or geohashes.
    """
    viewer_id = viewer.id if viewer else None
    return await SwapService.search_listings(
        db=db,
        viewer_id=viewer_id,
        query_text=q,
        category=category,
        mode=mode,
        distance_filter=distance_bucket,
        sort=sort,
        limit=limit,
        cursor=cursor,
    )


@router.get("/listings/me", response_model=list[SwapListingResponse])
async def get_my_swap_listings(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SwapListingResponse]:
    """Retrieve all swap listings created by the authenticated user."""
    return await SwapService.get_user_listings(db, current_user.id)


@router.post("/listings/ai-draft", response_model=ListingAIDraftResponse)
async def generate_listing_ai_draft(
    req: ListingAIDraftRequest,
    current_user: Annotated[User, Depends(require_user)],
) -> ListingAIDraftResponse:
    """Use Gemini AI to draft an engaging swap listing title, description, and tags."""
    return await SwapMatchingService.generate_listing_draft(req)


@router.get("/matches", response_model=list[SwapMatchResponse])
async def get_swap_matches(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[SwapMatchResponse]:
    """
    Get top personalized peer swap recommendations with cached Gemini 'Why you match' explanations.
    """
    return await SwapMatchingService.get_top_matches(db, current_user, limit=limit)


@router.get("/listings/{listing_id}", response_model=SwapListingResponse)
async def get_swap_listing_by_id(
    listing_id: uuid.UUID,
    viewer: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapListingResponse:
    """Fetch single swap listing details with privacy-safe distance bucket."""
    viewer_id = viewer.id if viewer else None
    return await SwapService.get_listing_by_id(db, listing_id, viewer_id)


@router.put("/listings/{listing_id}", response_model=SwapListingResponse)
async def update_swap_listing(
    listing_id: uuid.UUID,
    data: SwapListingUpdate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapListingResponse:
    """Update title, description, modes, or status of an owned swap listing."""
    return await SwapService.update_listing(
        db, listing_id, current_user.id, data, background_tasks
    )


@router.post("/listings/{listing_id}/share", response_model=SwapListingShareResponse)
async def share_swap_listing_to_feed(
    listing_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapListingShareResponse:
    """Share an active swap listing into the social feed as an interactive Swap Offer post."""
    return await SwapService.share_listing_to_feed(db, listing_id, current_user.id)

