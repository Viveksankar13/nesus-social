"""
Email Delivery Service
======================
Renders Jinja2 HTML templates and dispatches emails via SMTP (aiosmtplib).
Fully supports local testing via Mailpit and production SMTP providers such as
Brevo (smtp-relay.brevo.com), Gmail, and Resend.
Includes support for Student USN (University Seat Number / College ID Number)
in verification, password reset, and welcome notifications.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Set up Jinja2 template environment
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


class EmailService:
    """Asynchronous SMTP email dispatch service with Brevo and Mailpit support."""

    def __init__(self) -> None:
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    async def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send a single HTML email message via SMTP.
        Configured to handle Brevo (port 587 STARTTLS or port 465 SSL) seamlessly.
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email

        part = MIMEText(html_content, "html")
        message.attach(part)

        # Port-aware TLS negotiation (Brevo recommends port 587 with STARTTLS)
        is_direct_ssl = self.use_tls and self.port == 465
        is_starttls = self.use_tls and self.port != 465

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                use_tls=is_direct_ssl,
                start_tls=is_starttls,
                timeout=15,
            )
            logger.info(
                "Email sent successfully",
                extra={
                    "recipient": to_email,
                    "subject": subject,
                    "smtp_host": self.host,
                    "smtp_port": self.port,
                },
            )
            return True
        except Exception as e:
            # In dev/test, log warning instead of crashing flow if SMTP server is down
            logger.warning(
                "Failed to send email via SMTP (logged for development / diagnostics)",
                extra={"recipient": to_email, "subject": subject, "error": str(e)},
            )
            return False

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        token: str,
        usn: str | None = None,
    ) -> bool:
        """Send account activation email with verification token link and optional Student USN."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        template = jinja_env.get_template("verification.html")
        html_content = template.render(
            username=username,
            usn=usn,
            verification_url=verification_url,
        )
        return await self._send_email(
            to_email=to_email,
            subject="Verify your Nexus Social account",
            html_content=html_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        token: str,
        usn: str | None = None,
    ) -> bool:
        """Send password reset link with single-use token and optional Student USN confirmation."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        template = jinja_env.get_template("reset_password.html")
        html_content = template.render(
            username=username,
            usn=usn,
            reset_url=reset_url,
        )
        return await self._send_email(
            to_email=to_email,
            subject="Reset your Nexus Social password",
            html_content=html_content,
        )

    async def send_welcome_email(
        self,
        to_email: str,
        username: str,
        usn: str | None = None,
    ) -> bool:
        """Send confirmation email once account is verified."""
        feed_url = f"{settings.FRONTEND_URL}/feed"
        template = jinja_env.get_template("welcome.html")
        html_content = template.render(
            username=username,
            usn=usn,
            feed_url=feed_url,
        )
        return await self._send_email(
            to_email=to_email,
            subject="Welcome to Nexus Social!",
            html_content=html_content,
        )


email_service = EmailService()
