"""
Diagnostic script to test SMTP / Brevo email delivery.
Run via: python scripts/test_email.py <recipient_email>
"""

import asyncio
import sys

from app.core.config import settings
from app.services.email_service import email_service


async def main() -> None:
    recipient = sys.argv[1] if len(sys.argv) > 1 else settings.SMTP_FROM_EMAIL
    print("=" * 60)
    print("NEXUS SOCIAL — SMTP / BREVO DIAGNOSTIC CHECK")
    print("=" * 60)
    print(f"SMTP Host:       {settings.SMTP_HOST}")
    print(f"SMTP Port:       {settings.SMTP_PORT}")
    print(f"SMTP Username:   {settings.SMTP_USERNAME or '(NOT SET - MISSING)'}")
    print(f"SMTP Password:   {'*' * 8 if settings.SMTP_PASSWORD else '(NOT SET - MISSING)'}")
    print(f"SMTP From Email: {settings.SMTP_FROM_EMAIL}")
    print(f"SMTP From Name:  {settings.SMTP_FROM_NAME}")
    print(f"SMTP Use TLS:    {settings.SMTP_USE_TLS}")
    print(f"Frontend URL:    {settings.FRONTEND_URL}")
    print(f"Test Recipient:  {recipient}")
    print("-" * 60)

    if settings.SMTP_HOST in ("localhost", "127.0.0.1") and settings.ENVIRONMENT == "production":
        print("⚠️  WARNING: SMTP_HOST is still set to 'localhost'!")
        print("   On Render, set SMTP_HOST=smtp-relay.brevo.com in your Environment tab.")
        print("-" * 60)

    if not settings.SMTP_PASSWORD:
        print("⚠️  WARNING: SMTP_PASSWORD is not set!")
        print("   In Brevo, go to SMTP & API -> SMTP tab -> generate an SMTP Key.")
        print("-" * 60)

    print("Attempting to send test password reset email...")
    success = await email_service.send_password_reset_email(
        to_email=recipient,
        username="testuser",
        token="diagnostic-test-token-12345",
    )

    if success:
        print("✅ SUCCESS! The email was accepted by Brevo and dispatched.")
        print(f"   Check the inbox (and spam/junk folder) for {recipient}.")
    else:
        print("❌ FAILED! Brevo / SMTP server rejected the connection or email.")
        print("   Check Render service logs for the exact SMTP error code.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
