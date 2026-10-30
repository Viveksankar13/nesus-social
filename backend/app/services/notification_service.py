"""
Notification Service
====================
Handles persistent notification lifecycle and real-time push distribution:
- Always persists to PostgreSQL before publishing to pub/sub (guarantees delivery).
- Dispatches user-scoped and admin-wide real-time events.
- Provides unread tracking, cursor-paginated retrieval, and mark-as-read operations.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import decode_cursor, encode_cursor
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
)
from app.services.pubsub import pubsub


class NotificationService:
    """Service encapsulating notification persistence and real-time push."""

    @staticmethod
    async def create_and_push_notification(
        db: AsyncSession,
        user_id: uuid.UUID,
        type: str,
        payload: dict[str, Any],
    ) -> Notification:
        """
        Persist a notification to the database, then broadcast to real-time pub/sub.
        Always persists first so missed events are recoverable via REST polling.
        """
        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type=type,
            payload=payload,
            is_read=False,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)

        event_dict = NotificationResponse.model_validate(notif).model_dump(mode="json")

        # Push to targeted user channel
        await pubsub.publish(
            f"user:{user_id}",
            {"event": "notification", "data": event_dict},
        )

        # Broadcast admin-relevant events to the shared admin channel
        if type in ("admin_login", "moderation", "flagged"):
            await pubsub.publish(
                "admin",
                {"event": "admin_alert", "data": event_dict},
            )

        return notif

    @staticmethod
    async def list_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
        cursor: str | None = None,
    ) -> NotificationListResponse:
        """Retrieve paginated notifications and total unread count."""
        limit = max(1, min(limit, 100))

        # Total unread count
        unread_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        unread_count = (await db.execute(unread_query)).scalar() or 0

        # Notifications query
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))

        if cursor:
            decoded = decode_cursor(cursor)
            if decoded:
                cursor_dt, cursor_id = decoded
                query = query.where(
                    (Notification.created_at < cursor_dt)
                    | ((Notification.created_at == cursor_dt) & (Notification.id < cursor_id))
                )

        query = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(
            limit + 1
        )
        result = await db.execute(query)
        items = list(result.scalars().all())

        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        responses = [NotificationResponse.model_validate(n) for n in items]

        return NotificationListResponse(
            items=responses,
            unread_count=unread_count,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Get the count of unread notifications for a user."""
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        return (await db.execute(query)).scalar() or 0

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> NotificationResponse:
        """Mark a single notification as read."""
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await db.execute(query)
        notif = result.scalar_one_or_none()

        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )

        notif.is_read = True
        await db.commit()
        await db.refresh(notif)

        return NotificationResponse.model_validate(notif)

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Mark all unread notifications for a user as read."""
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount  # type: ignore[no-any-return]

    @staticmethod
    async def notify_admins_of_login(
        db: AsyncSession,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Record a persistent login alert for administrators and broadcast in real time.
        Debounces repeated logins within 60s for the same user.
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=60)

        # Query all active admin IDs
        admins_stmt = select(User.id).where(User.role == "admin", User.is_suspended.is_(False))
        admin_ids = list((await db.execute(admins_stmt)).scalars().all())
        if not admin_ids:
            return

        # Dual-dialect safe check: check recent admin_login notifications
        recent_query = select(Notification).where(
            Notification.type == "admin_login",
            Notification.created_at >= cutoff,
        )
        res = await db.execute(recent_query)
        for n in res.scalars():
            if n.payload.get("login_user_id") == str(user.id):
                return  # Debounced within 60s

        payload = {
            "login_user_id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "ip": ip_address,
            "user_agent": user_agent,
            "time": now.isoformat(),
        }

        for admin_id in admin_ids:
            await NotificationService.create_and_push_notification(
                db=db,
                user_id=admin_id,
                type="admin_login",
                payload=payload,
            )


notification_service = NotificationService()
