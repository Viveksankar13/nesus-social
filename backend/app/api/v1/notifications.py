"""
Notifications and Real-Time SSE Stream Router
=============================================
Endpoints for:
- Listing persistent notifications with unread counts and keyset pagination
- Marking notifications as read (single and batch)
- Generating 60-second single-purpose stream tokens
- Serving real-time Server-Sent Events (SSE) with heartbeat keep-alives
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.tokens import create_stream_token, decode_token
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    StreamTokenResponse,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service
from app.services.pubsub import pubsub

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: Annotated[bool, Query(description="Filter to unread only")] = False,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    cursor: Annotated[str | None, Query(description="Keyset cursor")] = None,
) -> NotificationListResponse:
    """Retrieve paginated notifications and total unread count for the authenticated user."""
    return await notification_service.list_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        cursor=cursor,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnreadCountResponse:
    """Retrieve total count of unread notifications for badge rendering."""
    count = await notification_service.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationResponse:
    """Mark a specific notification as read."""
    return await notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )


@router.patch("/read-all", response_model=MessageResponse)
async def mark_all_as_read(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Mark all unread notifications for the authenticated user as read."""
    count = await notification_service.mark_all_as_read(db=db, user_id=current_user.id)
    return MessageResponse(message=f"Marked {count} notifications as read.")


@router.post("/token", response_model=StreamTokenResponse)
async def get_stream_token(
    current_user: Annotated[User, Depends(require_user)],
) -> StreamTokenResponse:
    """
    Issue a short-lived (60s) single-purpose JWT for Server-Sent Events authorization.
    Used in EventSource query params since the browser EventSource API cannot set headers.
    """
    token = create_stream_token(user_id=current_user.id, expires_seconds=60)
    return StreamTokenResponse(token=token, expires_in=60)


async def sse_event_generator(
    user: User,
    request: Request,
) -> AsyncGenerator[str, None]:
    """
    Yields Server-Sent Events for the authenticated user.
    Includes initial connection event, periodic heartbeat pings,
    and real-time event distribution.
    """
    channels = [f"user:{user.id}"]
    if user.role == "admin":
        channels.append("admin")

    # Initial connection confirmation
    initial_event = json.dumps({"status": "connected", "user_id": str(user.id)})
    yield f"event: connected\ndata: {initial_event}\n\n"

    subscriber = pubsub.subscribe(channels)
    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                # Wait for event or heartbeat timeout (20s)
                msg = await asyncio.wait_for(subscriber.__anext__(), timeout=20.0)
                event_type = msg.get("event", "notification")
                event_data = json.dumps(msg.get("data", {}))
                yield f"event: {event_type}\ndata: {event_data}\n\n"
            except TimeoutError:
                # Heartbeat comment to keep intermediate proxies from closing the connection
                now_str = datetime.now(UTC).isoformat()
                yield f": heartbeat {now_str}\n\n"
            except StopAsyncIteration:
                break
    except asyncio.CancelledError:
        pass
    finally:
        await subscriber.aclose()


@router.get("/stream")
async def notification_stream(
    token: Annotated[str, Query(description="Short-lived 60s stream token")],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """
    Server-Sent Events endpoint streaming real-time notifications.
    Authenticated via 60-second single-purpose stream token query parameter.
    """
    try:
        payload = decode_token(token, expected_type="stream")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Token missing subject")
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired stream token: {e}",
        ) from e

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or user.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or invalid.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account email is not verified.",
        )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        sse_event_generator(user=user, request=request),
        media_type="text/event-stream",
        headers=headers,
    )
