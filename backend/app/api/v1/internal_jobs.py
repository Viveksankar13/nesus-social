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
    Browser-accessible diagnostic endpoint to test Brevo delivery without requiring Render Shell.
    Supports both Brevo HTTPS REST API (Port 443, recommended for Render Free) and SMTP.
    Usage: GET /api/v1/internal/jobs/test-email?secret=<CRON_SECRET>&to=<your_email>
    """
    if secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret parameter. Must match CRON_SECRET configured in Render.",
        )

    brevo_api_key = settings.BREVO_API_KEY or (
        settings.SMTP_PASSWORD if settings.SMTP_PASSWORD.startswith("xkeysib-") else ""
    )

    diagnostic = {
        "delivery_mode": "Brevo REST API (HTTPS port 443)" if brevo_api_key else "SMTP (port 587)",
        "brevo_api_key_configured": bool(brevo_api_key),
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "smtp_username": settings.SMTP_USERNAME,
        "smtp_from_email": settings.SMTP_FROM_EMAIL,
        "smtp_from_name": settings.SMTP_FROM_NAME,
        "test_recipient": to,
    }

    # If Brevo API key is available, use HTTPS (Port 443) which Render Free NEVER blocks
    if brevo_api_key:
        import httpx

        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": settings.SMTP_FROM_NAME, "email": settings.SMTP_FROM_EMAIL},
            "to": [{"email": to}],
            "subject": "Nexus Social — Brevo HTTPS Success!",
            "htmlContent": f"""
            <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h2 style="color: #2563eb;">Nexus Social — Email Delivered via Brevo API!</h2>
                <p>Your FastAPI backend on Render successfully delivered this email via HTTPS REST API (Port 443).</p>
                <p>This bypasses Render Free Tier's outbound SMTP port 587 blocking!</p>
                <p><strong>Recipient:</strong> {to}</p>
                <p><strong>Sender:</strong> {settings.SMTP_FROM_EMAIL}</p>
            </div>
            """,
        }
        headers = {
            "accept": "application/json",
            "api-key": brevo_api_key,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    return {
                        "status": "success",
                        "delivery_method": "Brevo REST API (HTTPS Port 443)",
                        "message": f"Test email successfully dispatched to {to}! Check your inbox.",
                        "diagnostic": diagnostic,
                    }
                else:
                    return {
                        "status": "error",
                        "error_type": "BrevoAPIError",
                        "error_details": f"HTTP {resp.status_code}: {resp.text}",
                        "troubleshooting_hint": "Check if your BREVO_API_KEY is active and your SMTP_FROM_EMAIL is a verified sender in Brevo.",
                        "diagnostic": diagnostic,
                    }
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "troubleshooting_hint": "Network error reaching api.brevo.com",
                "diagnostic": diagnostic,
            }

    # Fallback to SMTP
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    import aiosmtplib

    message = MIMEMultipart("alternative")
    message["Subject"] = "Nexus Social — Diagnostic Test Email"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2563eb;">Nexus Social — Brevo SMTP Success!</h2>
        <p>Recipient: {to}</p>
        <p>Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}</p>
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
            "delivery_method": "SMTP",
            "message": f"Test email successfully dispatched to {to}!",
            "diagnostic": diagnostic,
        }
    except Exception as e:
        error_msg = str(e)
        hint = "Render Free blocks outbound SMTP ports 25, 465, and 587. To fix: in Brevo go to SMTP & API -> API Keys -> copy your API Key (xkeysib-...) and set BREVO_API_KEY in Render."
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
