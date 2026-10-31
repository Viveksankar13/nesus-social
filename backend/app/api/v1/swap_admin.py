"""
Admin Swaps Router
==================
Endpoints for administrative management of the Hyper-Local Skill Swap Economy:
- Platform KPIs and activity stats
- Listing moderation and status override (suspend / reinstate)
- Dispute triage and trust score adjustments
- Skill taxonomy curation (approve pending skills, merge synonyms)
- Manual background cron maintenance trigger

All routes are strictly protected by the require_admin dependency.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.swap import Skill
from app.models.user import User
from app.schemas.swap import (
    SkillResponse,
    SwapAdminStatsResponse,
    SwapDisputeAdminResponse,
    SwapDisputeResolveRequest,
    SwapListingAdminResponse,
    SwapListingStatusUpdate,
    SwapReportResponse,
    SwapTaxonomyApproveRequest,
    SwapTaxonomyMergeRequest,
)
from app.services.swap_jobs import SwapJobsService
from app.services.swap_service import SwapService

router = APIRouter(prefix="/admin/swaps", tags=["Admin Swaps"])


@router.get("/stats", response_model=SwapAdminStatsResponse)
async def get_swap_admin_stats(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapAdminStatsResponse:
    """Retrieve aggregate KPIs and metrics for the Skill Swap Economy."""
    return await SwapService.get_swap_admin_stats(db)


@router.get("/listings", response_model=list[SwapListingAdminResponse])
async def list_admin_swap_listings(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[SwapListingAdminResponse]:
    """List swap listings with report counts for administrative moderation."""
    return await SwapService.list_admin_listings(db, status_filter=status, limit=limit)


@router.put("/listings/{listing_id}/status", response_model=dict[str, str])
async def update_admin_listing_status(
    listing_id: uuid.UUID,
    req: SwapListingStatusUpdate,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Suspend, pause, or reinstate a swap listing."""
    await SwapService.update_admin_listing_status(db, listing_id, req.status)
    return {"message": f"Listing status updated to {req.status}."}


@router.get("/disputes", response_model=list[SwapDisputeAdminResponse])
async def list_admin_disputes(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
) -> list[SwapDisputeAdminResponse]:
    """Retrieve active reports and disputes for administrative review."""
    return await SwapService.list_admin_disputes(db, status_filter=status)


@router.post("/disputes/{report_id}/resolve", response_model=SwapReportResponse)
async def resolve_admin_dispute(
    report_id: uuid.UUID,
    req: SwapDisputeResolveRequest,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SwapReportResponse:
    """Resolve an open dispute or safety report and apply trust penalties if needed."""
    return await SwapService.resolve_admin_dispute(db, report_id, req)


@router.get("/taxonomy", response_model=list[SkillResponse])
async def list_admin_taxonomy(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
) -> list[SkillResponse]:
    """List all skills in the taxonomy across active, pending, and rejected statuses."""
    stmt = select(Skill).order_by(Skill.category, Skill.display_name)
    if status:
        stmt = stmt.where(Skill.status == status)
    res = await db.execute(stmt)
    return [SkillResponse.model_validate(s) for s in res.scalars().all()]


@router.post("/taxonomy/approve", response_model=SkillResponse)
async def approve_taxonomy_skill(
    req: SwapTaxonomyApproveRequest,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillResponse:
    """Approve a user-suggested pending skill."""
    return await SwapService.approve_taxonomy_skill(
        db, req.skill_id, display_name=req.display_name, category=req.category
    )


@router.post("/taxonomy/merge", response_model=SkillResponse)
async def merge_taxonomy_skills(
    req: SwapTaxonomyMergeRequest,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillResponse:
    """Merge a duplicate skill into a canonical target skill."""
    return await SwapService.merge_taxonomy_skills(db, req.source_skill_id, req.target_skill_id)


@router.post("/jobs/{job_name}/run", response_model=dict[str, str | int])
async def trigger_admin_swap_job(
    job_name: str,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | int]:
    """Manually trigger background cron maintenance jobs from the admin console."""
    try:
        res = await SwapJobsService.run_job(db, job_name)
        return {"job": job_name, "status": "success", "records_processed": res.get("records_processed", 0)}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown background job: {job_name}",
        ) from None
