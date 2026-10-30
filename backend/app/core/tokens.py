"""
JWT and Token Management
========================
Provides encoding and decoding for:
- 15-minute JWT access tokens (held in frontend memory only)
- 60-second single-purpose stream tokens for SSE connections
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate a signed JWT access token for authentication.
    Default lifetime: settings.ACCESS_TOKEN_MINUTES (15 min).
    """
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_stream_token(user_id: uuid.UUID, expires_seconds: int = 60) -> str:
    """
    Generate a short-lived (60s) single-purpose JWT for SSE authorization.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=expires_seconds)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "stream",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises ValueError with a human-readable message on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_type = payload.get("type")
        if token_type != expected_type:
            raise ValueError(f"Invalid token type: expected {expected_type}, got {token_type}")
        return payload
    except ExpiredSignatureError as e:
        raise ValueError("Token has expired") from e
    except InvalidTokenError as e:
        raise ValueError("Invalid authentication token") from e
