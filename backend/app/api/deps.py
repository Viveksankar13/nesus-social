"""
API Dependencies and Role-Based Access Control (RBAC)
======================================================
Provides dependencies for:
- Database session injection (`get_db`)
- JWT extraction and user resolution (`get_current_user`)
- Enforcing verified user access (`require_user`)
- Enforcing administrator access (`require_admin`)
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import decode_token
from app.db.session import get_db
from app.models.user import User

# Optional=True so public routes can inspect current user if token is present
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Extract and validate the JWT Bearer token from the Authorization header.
    Returns the authenticated User entity.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(auth.credentials, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Token missing subject claim")
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact support.",
        )

    return user


async def get_optional_current_user(
    auth: Annotated[HTTPAuthorizationCredentials | None, Security(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Return authenticated User if valid Bearer token is supplied, otherwise None."""
    if not auth or not auth.credentials:
        return None
    try:
        payload = decode_token(auth.credentials, expected_type="access")
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user and not user.is_suspended:
            return user
        return None
    except Exception:
        return None


async def require_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the user is verified and not suspended."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to access this feature.",
        )
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(require_user)],
) -> User:
    """Ensure the user has the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user
