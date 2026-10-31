"""
Internal Jobs API Router
========================
Secret-protected internal endpoints for cron runners (e.g. Render Cron Jobs).
Requires X-Cron-Secret header matching settings.CRON_SECRET.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.services.swap_jobs import SwapJobsService

router = APIRouter(prefix="/internal/jobs", tags=["Internal Jobs"])


def verify_cron_secret(
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
) -> None:
    """Verify incoming request contains the configured CRON_SECRET."""
    if not x_cron_secret or x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Cron-Secret header.",
        )


@router.post("/{job_name}", dependencies=[Depends(verify_cron_secret)])
async def trigger_internal_job(
    job_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Trigger an idempotent background job by name. Protected by X-Cron-Secret."""
    allowed_jobs = [
        "auto-expire-requests",
        "auto-complete-sessions",
        "reveal-swap-reviews",
        "send-session-reminders",
    ]
    if job_name not in allowed_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown job '{job_name}'. Allowed jobs: {allowed_jobs}",
        )
    return await SwapJobsService.run_job(db, job_name)
