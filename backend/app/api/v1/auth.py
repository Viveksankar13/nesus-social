"""
Authentication Router
=====================
Endpoints for registration, login, token refresh, logout, verification, and password resets.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/"
USER_ROLE_COOKIE_NAME = "user_role"


def set_refresh_cookie(response: Response, raw_token: str, role: str = "user") -> None:
    """Helper to attach rotating httpOnly refresh token cookie
    and companion role cookie to HTTP response."""
    max_age = settings.REFRESH_TOKEN_DAYS * 24 * 3600
    is_secure = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        expires=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=is_secure,
        samesite="lax",
    )
    # Companion cookie for edge route guards & client layout
    response.set_cookie(
        key=USER_ROLE_COOKIE_NAME,
        value=role,
        max_age=max_age,
        expires=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=False,
        secure=is_secure,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    req: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Register account and dispatch email verification link."""
    await auth_service.register(db, req)
    return MessageResponse(
        message="Registration successful. Please check your email to verify your account."
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address with token",
)
async def verify_email(
    req: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Activate account using token received via email."""
    result = await auth_service.verify_email(db, req.token)
    return MessageResponse(message=result["message"])


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend email verification link",
)
@limiter.limit(
    settings.RATE_LIMIT_RESend_VERIFICATION
    if hasattr(settings, "RATE_LIMIT_RESend_VERIFICATION")
    else settings.RATE_LIMIT_RESEND_VERIFICATION
)
async def resend_verification(
    request: Request,
    req: ResendVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Request a fresh activation token link (rate limited)."""
    result = await auth_service.resend_verification(db, req.email)
    return MessageResponse(message=result["message"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access token",
)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    req: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    """
    Log in with email/username and password.
    Returns 15-min JWT access token in JSON body; sets rotating refresh token in httpOnly cookie.
    """
    client_ip = request.client.host if request.client else None
    access_token, raw_refresh, user = await auth_service.login(
        db, req, user_agent=user_agent, ip_address=client_ip
    )
    set_refresh_cookie(response, raw_refresh, role=user.role)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
        user=user,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get fresh access token",
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
    user_agent: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    """
    Silent token refresh: reads httpOnly cookie, rotates token family, returns new access token.
    Detects reuse and revokes entire family if previously rotated token is replayed.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing.",
        )
    client_ip = request.client.host if request.client else None
    new_access, new_refresh, user = await auth_service.refresh(
        db, refresh_token, user_agent=user_agent, ip_address=client_ip
    )
    set_refresh_cookie(response, new_refresh, role=user.role)
    return TokenResponse(
        access_token=new_access,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
        user=user,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and invalidate current refresh token",
)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> MessageResponse:
    """Revoke session refresh token and delete httpOnly cookie."""
    await auth_service.logout(db, refresh_token)
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
    response.delete_cookie(
        key=USER_ROLE_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
    return MessageResponse(message="Successfully logged out.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset link",
)
@limiter.limit(settings.RATE_LIMIT_FORGOT_PASSWORD)
async def forgot_password(
    request: Request,
    req: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Send single-use password reset link. Returns generic message to prevent enumeration."""
    result = await auth_service.forgot_password(db, req.email)
    return MessageResponse(message=result["message"])


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(
    req: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Reset password and invalidate all active user sessions."""
    result = await auth_service.reset_password(db, req.token, req.new_password)
    return MessageResponse(message=result["message"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: Annotated[User, Depends(require_user)],
) -> User:
    """Return profile data of the currently logged-in verified user."""
    return current_user
