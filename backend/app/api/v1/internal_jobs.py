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


@router.get("/test-email")
async def test_email_browser(
    to: str,
    secret: str,
) -> dict[str, Any]:
    """
    Browser-accessible diagnostic endpoint to test Brevo SMTP delivery
    without requiring a Render paid Shell.
    Usage: GET /api/v1/internal/jobs/test-email?secret=<CRON_SECRET>&to=<your_email>
    """
    if secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret parameter. Must match CRON_SECRET configured in Render.",
        )

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    import aiosmtplib

    diagnostic = {
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_username": settings.SMTP_USERNAME,
        "smtp_from_email": settings.SMTP_FROM_EMAIL,
        "smtp_from_name": settings.SMTP_FROM_NAME,
        "smtp_use_tls": settings.SMTP_USE_TLS,
        "test_recipient": to,
    }

    message = MIMEMultipart("alternative")
    message["Subject"] = "Nexus Social — Diagnostic Test Email"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2563eb;">Nexus Social — Brevo SMTP Success!</h2>
        <p>Your FastAPI backend on Render successfully connected to Brevo and delivered this message.</p>
        <p><strong>Recipient:</strong> {to}</p>
        <p><strong>SMTP Host:</strong> {settings.SMTP_HOST}:{settings.SMTP_PORT}</p>
        <p><strong>From Sender:</strong> {settings.SMTP_FROM_EMAIL}</p>
    </div>
    """
    message.attach(MIMEText(html, "html"))

    is_direct_ssl = settings.SMTP_PORT == 465
    is_starttls = settings.SMTP_PORT == 587 or (settings.SMTP_USE_TLS and settings.SMTP_PORT != 465)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=is_direct_ssl,
            start_tls=is_starttls,
            timeout=15,
        )
        return {
            "status": "success",
            "message": f"Test email successfully dispatched to {to}! Check your inbox and spam folder.",
            "diagnostic": diagnostic,
        }
    except Exception as e:
        error_msg = str(e)
        hint = "Review your Brevo credentials and sender settings"
        if "535" in error_msg:
            hint = "Authentication failed: Ensure SMTP_PASSWORD is your Brevo SMTP Master Key (starts with xsmtpsib-), NOT the REST API key."
        elif "550" in error_msg:
            hint = f"Sender rejected: {settings.SMTP_FROM_EMAIL} is not verified in Brevo. In Render, set SMTP_FROM_EMAIL to your registered Brevo account email."
        elif "Unauthorized IP" in error_msg or "blocked" in error_msg.lower():
            hint = "Brevo blocked Render IP: Go to https://app.brevo.com/security/authorised_ips and turn OFF 'Block unknown IP addresses'."

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_details": error_msg,
            "troubleshooting_hint": hint,
            "diagnostic": diagnostic,
        }


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
