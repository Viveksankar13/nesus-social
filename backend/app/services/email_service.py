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

    @property
    def host(self) -> str:
        return settings.SMTP_HOST

    @property
    def port(self) -> int:
        return settings.SMTP_PORT

    @property
    def username(self) -> str:
        return settings.SMTP_USERNAME

    @property
    def password(self) -> str:
        return settings.SMTP_PASSWORD

    @property
    def use_tls(self) -> bool:
        return settings.SMTP_USE_TLS

    @property
    def from_email(self) -> str:
        return settings.SMTP_FROM_EMAIL

    @property
    def from_name(self) -> str:
        return settings.SMTP_FROM_NAME

    async def _send_via_brevo_api(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        api_key: str,
    ) -> bool:
        """
        Send transactional email via Brevo REST API over HTTPS (Port 443).
        Bypasses Render Free Tier's firewall blocking outbound SMTP ports 587/465.
        """
        import httpx

        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {"name": self.from_name, "email": self.from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
        }
        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    logger.info(
                        f"Email sent successfully via Brevo REST API (HTTPS port 443) to {to_email}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Failed to send email via Brevo REST API to {to_email}: {resp.status_code} {resp.text}"
                    )
                    return False
        except Exception as e:
            logger.warning(f"Error calling Brevo REST API for {to_email}: {e}")
            return False

    async def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send a single HTML email message.
        Automatically uses Brevo REST API over HTTPS (Port 443) if BREVO_API_KEY is configured
        (bypassing Render Free Tier's port 587 block), otherwise falls back to standard SMTP.
        """
        # If Brevo API Key is configured, use HTTPS REST API (Port 443)
        brevo_key = settings.BREVO_API_KEY or (
            self.password if self.password.startswith("xkeysib-") else ""
        )
        if brevo_key:
            return await self._send_via_brevo_api(to_email, subject, html_content, brevo_key)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email

        part = MIMEText(html_content, "html")
        message.attach(part)

        # Port-aware TLS negotiation:
        # Port 465 is direct SSL; Port 587 requires STARTTLS; otherwise honor SMTP_USE_TLS
        is_direct_ssl = self.port == 465
        is_starttls = self.port == 587 or (self.use_tls and self.port != 465)

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
                f"Email sent successfully to {to_email}",
                extra={
                    "recipient": to_email,
                    "subject": subject,
                    "smtp_host": self.host,
                    "smtp_port": self.port,
                },
            )
            return True
        except Exception as e:
            # Log exact error so administrators can troubleshoot Brevo in Render console
            logger.warning(
                f"Failed to send email via SMTP to {to_email}: {e}",
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

    async def send_swap_request_email(
        self,
        to_email: str,
        username: str,
        requester_name: str,
        offered_skill: str,
        wanted_skill: str,
        message: str,
        request_id: str,
    ) -> bool:
        """Send notification when a user receives a new peer swap proposal."""
        swap_url = f"{settings.FRONTEND_URL}/swaps/requests"
        template = jinja_env.get_template("swap_request.html")
        html_content = template.render(
            username=username,
            requester_name=requester_name,
            offered_skill=offered_skill,
            wanted_skill=wanted_skill,
            message=message,
            swap_url=swap_url,
        )
        return await self._send_email(
            to_email=to_email,
            subject=f"New skill swap proposal from @{requester_name}",
            html_content=html_content,
        )

    async def send_swap_accepted_email(
        self,
        to_email: str,
        username: str,
        peer_name: str,
        scheduled_time: str,
        mode: str,
        session_id: str,
        location: str | None = None,
    ) -> bool:
        """Send notification when a swap proposal is accepted and scheduled."""
        session_url = f"{settings.FRONTEND_URL}/swaps/sessions/{session_id}"
        template = jinja_env.get_template("swap_accepted.html")
        html_content = template.render(
            username=username,
            peer_name=peer_name,
            scheduled_time=scheduled_time,
            mode=mode,
            session_url=session_url,
            location=location,
        )
        return await self._send_email(
            to_email=to_email,
            subject=f"Skill Swap Confirmed with @{peer_name}!",
            html_content=html_content,
        )

    async def send_session_reminder_email(
        self,
        to_email: str,
        username: str,
        peer_name: str,
        scheduled_time: str,
        mode: str,
        session_id: str,
        location: str | None = None,
    ) -> bool:
        """Send reminder notification before a scheduled swap session starts."""
        session_url = f"{settings.FRONTEND_URL}/swaps/sessions/{session_id}"
        template = jinja_env.get_template("swap_reminder.html")
        html_content = template.render(
            username=username,
            peer_name=peer_name,
            scheduled_time=scheduled_time,
            mode=mode,
            session_url=session_url,
            location=location,
        )
        return await self._send_email(
            to_email=to_email,
            subject=f"Reminder: Upcoming Skill Swap with @{peer_name}",
            html_content=html_content,
        )


email_service = EmailService()
