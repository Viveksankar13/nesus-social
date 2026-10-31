"""
Authentication Service
======================
Implements core authentication business logic:
- Registration & email verification
- Login with password verification & account state validation
- Refresh token rotation & family-based reuse detection
- Password reset workflows with token revocation
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    generate_random_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.tokens import create_access_token
from app.models.token import EmailToken, RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_service import email_service
from app.services.notification_service import notification_service

logger = get_logger(__name__)


class AuthService:
    """Authentication and session management provider."""

    async def register(
        self,
        session: AsyncSession,
        req: RegisterRequest,
    ) -> User:
        """Register a new user account and dispatch verification email."""
        clean_email = req.email.strip().lower()
        clean_username = req.username.strip().lower()
        clean_usn = req.usn.strip().upper() if req.usn else None

        # Check uniqueness of email, username, or Student USN
        conditions = [User.email == clean_email, User.username == clean_username]
        if clean_usn:
            conditions.append(User.usn == clean_usn)
        stmt = select(User).where(or_(*conditions))
        res = await session.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, username, or Student USN already in use.",
            )

        user = User(
            id=uuid.uuid4(),
            email=clean_email,
            username=clean_username,
            usn=clean_usn,
            display_name=req.display_name.strip(),
            hashed_password=hash_password(req.password),
            role="user",
            is_verified=False,
            is_suspended=False,
        )
        session.add(user)
        await session.flush()

        # Issue 24-hour email verification token
        raw_token, token_hash = generate_random_token(32)
        email_token = EmailToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            token_type="verify_email",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        session.add(email_token)
        await session.commit()

        # Send activation email in background
        await email_service.send_verification_email(
            to_email=user.email,
            username=user.username,
            token=raw_token,
            usn=user.usn,
        )
        logger.info(
            "User registered successfully", extra={"user_id": str(user.id), "email": user.email}
        )
        return user

    async def verify_email(self, session: AsyncSession, token: str) -> dict[str, str]:
        """Validate an email verification token and activate the account."""
        token_hash = hash_token(token)
        stmt = select(EmailToken).where(
            (EmailToken.token_hash == token_hash) & (EmailToken.token_type == "verify_email")
        )
        res = await session.execute(stmt)
        email_token = res.scalar_one_or_none()

        if not email_token or not email_token.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token.",
            )

        # Mark token consumed
        email_token.used_at = datetime.now(UTC)

        # Mark user verified
        user_stmt = select(User).where(User.id == email_token.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user:
            user.is_verified = True
            await session.commit()
            await email_service.send_welcome_email(user.email, user.username, usn=user.usn)
            logger.info("Email verified successfully", extra={"user_id": str(user.id)})

        return {"message": "Email successfully verified. You may now log in."}

    async def resend_verification(self, session: AsyncSession, email: str) -> dict[str, str]:
        """Resend email verification link if account is unverified (rate limited)."""
        clean_id = email.strip()
        conditions = [
            User.email == clean_id.lower(),
            User.username == clean_id.lower(),
            User.usn == clean_id.upper(),
        ]
        stmt = select(User).where(or_(*conditions))
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        # Return identical response to prevent email enumeration
        generic_msg = (
            "If an unverified account exists with that identifier, "
            "a verification link has been sent."
        )

        if not user or user.is_verified:
            return {"message": generic_msg}

        # Invalidate any pending verify tokens
        now = datetime.now(UTC)
        await session.execute(
            update(EmailToken)
            .where((EmailToken.user_id == user.id) & (EmailToken.token_type == "verify_email"))
            .values(used_at=now)
        )

        # Issue fresh token
        raw_token, token_hash = generate_random_token(32)
        new_token = EmailToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            token_type="verify_email",
            expires_at=now + timedelta(hours=24),
        )
        session.add(new_token)
        await session.commit()

        await email_service.send_verification_email(
            user.email, user.username, raw_token, usn=user.usn
        )
        return {"message": generic_msg}

    async def login(
        self,
        session: AsyncSession,
        req: LoginRequest,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """
        Authenticate user credentials by email, username, or Student USN.
        Returns:
            (access_token, raw_refresh_token, user)
        """
        identifier = req.email_or_username.strip()
        conditions = [
            User.email == identifier.lower(),
            User.username == identifier.lower(),
            User.usn == identifier.upper(),
        ]
        stmt = select(User).where(or_(*conditions))
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Email not verified. Please check your inbox or request a new "
                    "verification email."
                ),
            )

        if user.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been suspended. Please contact support.",
            )

        # Generate 15-minute access token
        access_token = create_access_token(user.id, user.role)

        # Generate rotating 7-day refresh token
        raw_refresh, token_hash = generate_random_token(32)
        family_id = uuid.uuid4()
        now = datetime.now(UTC)
        refresh_token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            family_id=family_id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
            revoked=False,
        )
        session.add(refresh_token)
        await session.commit()

        # Notify administrators of login in real time (debounced 60s)
        try:
            await notification_service.notify_admins_of_login(
                db=session,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning("Failed to dispatch admin login notification", extra={"error": str(e)})

        logger.info(
            "User logged in successfully",
            extra={"user_id": str(user.id), "ip": ip_address, "user_agent": user_agent},
        )
        return access_token, raw_refresh, user

    async def refresh(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, User]:
        """
        Rotate a refresh token and issue a fresh 15-minute access token.
        Detects reuse attacks: revokes the entire family if an already-revoked token is used!
        """
        token_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        res = await session.execute(stmt)
        token = res.scalar_one_or_none()

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        # ── REUSE DETECTION ───────────────────────────────────────────
        if token.revoked:
            logger.warning(
                "Refresh token reuse detected! Revoking family.",
                extra={"family_id": str(token.family_id), "user_id": str(token.user_id)},
            )
            # Revoke entire token family
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token.family_id)
                .values(revoked=True)
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected. All sessions in this chain have been terminated.",
            )

        # Check expiration
        if token.is_expired():
            token.revoked = True
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
            )

        # Verify user still active
        user_stmt = select(User).where(User.id == token.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user or user.is_suspended:
            token.revoked = True
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended or invalid.",
            )

        # ── ROTATE TOKEN ──────────────────────────────────────────────
        token.revoked = True  # Consume old token

        now = datetime.now(UTC)
        new_raw_refresh, new_hash = generate_random_token(32)
        new_refresh = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=new_hash,
            family_id=token.family_id,  # Preserve family lineage
            user_agent=user_agent or token.user_agent,
            ip_address=ip_address or token.ip_address,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
            revoked=False,
        )
        session.add(new_refresh)

        # Issue new access token
        new_access_token = create_access_token(user.id, user.role)
        await session.commit()

        return new_access_token, new_raw_refresh, user

    async def logout(self, session: AsyncSession, raw_refresh_token: str | None) -> None:
        """Revoke the current refresh token upon user logout."""
        if not raw_refresh_token:
            return
        token_hash = hash_token(raw_refresh_token)
        await session.execute(
            update(RefreshToken).where(RefreshToken.token_hash == token_hash).values(revoked=True)
        )
        await session.commit()

    async def forgot_password(self, session: AsyncSession, identifier: str) -> dict[str, str]:
        """
        Initiate password reset flow using registered email address, username, or Student USN.
        Sends single-use reset token link via Brevo/SMTP to the user's verified email.
        """
        clean_id = identifier.strip()
        conditions = [
            User.email == clean_id.lower(),
            User.username == clean_id.lower(),
            User.usn == clean_id.upper(),
        ]
        stmt = select(User).where(or_(*conditions))
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        generic_response = {
            "message": (
                "If an account matching that identifier exists, "
                "a password reset link has been sent."
            )
        }

        if not user or user.is_suspended:
            return generic_response

        # Invalidate prior reset tokens
        now = datetime.now(UTC)
        await session.execute(
            update(EmailToken)
            .where((EmailToken.user_id == user.id) & (EmailToken.token_type == "reset_password"))
            .values(used_at=now)
        )

        # Create 1-hour reset token
        raw_token, token_hash = generate_random_token(32)
        reset_token = EmailToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            token_type="reset_password",
            expires_at=now + timedelta(hours=1),
        )
        session.add(reset_token)
        await session.commit()

        await email_service.send_password_reset_email(
            user.email, user.username, raw_token, usn=user.usn
        )
        return generic_response

    async def reset_password(
        self,
        session: AsyncSession,
        token: str,
        new_password: str,
    ) -> dict[str, str]:
        """Validate reset token, update password, and revoke all active refresh tokens."""
        token_hash = hash_token(token)
        stmt = select(EmailToken).where(
            (EmailToken.token_hash == token_hash) & (EmailToken.token_type == "reset_password")
        )
        res = await session.execute(stmt)
        email_token = res.scalar_one_or_none()

        if not email_token or not email_token.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token.",
            )

        # Mark token consumed
        now = datetime.now(UTC)
        email_token.used_at = now

        # Update password
        user_stmt = select(User).where(User.id == email_token.user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user or user.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is invalid or suspended.",
            )

        user.hashed_password = hash_password(new_password)

        # Revoke all refresh tokens for this user (force re-login everywhere)
        await session.execute(
            update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
        )
        await session.commit()
        logger.info("Password reset successfully", extra={"user_id": str(user.id)})

        return {"message": "Password successfully reset. Please log in with your new password."}


auth_service = AuthService()
