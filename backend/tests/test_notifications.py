"""
Notifications and Real-Time SSE Test Suite
==========================================
Comprehensive tests verifying:
- NOTIF-01: Notification persistence, listing, filtering, marking as read, and unread badge count
- NOTIF-02: Stream token generation and SSE stream connectivity
- NOTIF-03: Real-time Pub/Sub distribution and admin login alert with 60s debouncing
"""

import asyncio
import json
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import create_stream_token
from app.models.notification import Notification
from app.services.notification_service import notification_service
from app.services.pubsub import pubsub

# ── NOTIF-01: Persistence, Listing, and Read Status ──────────────────────────


@pytest.mark.asyncio
async def test_notifications_crud_and_read_status(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test notification listing, unread count, and marking notifications as read."""
    user, headers = await create_user(username="notif_user", email="nu@example.com")

    # Manually seed 3 notifications
    for i in range(3):
        await notification_service.create_and_push_notification(
            db=test_db_session,
            user_id=user.id,
            type="like",
            payload={"post_id": f"dummy-post-{i}", "item_num": i},
        )

    # 1. Verify unread count is 3
    unread_res = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res.status_code == 200
    assert unread_res.json()["unread_count"] == 3

    # 2. List notifications
    list_res = await client.get("/api/v1/notifications", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert len(data["items"]) == 3
    assert data["unread_count"] == 3
    first_notif_id = data["items"][0]["id"]

    # 3. Mark single notification as read
    read_res = await client.patch(
        f"/api/v1/notifications/{first_notif_id}/read",
        headers=headers,
    )
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Verify unread count decremented to 2
    unread_res2 = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res2.json()["unread_count"] == 2

    # 4. Filter unread only
    unread_filter_res = await client.get(
        "/api/v1/notifications?unread_only=true",
        headers=headers,
    )
    assert unread_filter_res.status_code == 200
    assert len(unread_filter_res.json()["items"]) == 2

    # 5. Mark all as read
    mark_all_res = await client.patch(
        "/api/v1/notifications/read-all",
        headers=headers,
    )
    assert mark_all_res.status_code == 200
    assert "Marked 2 notifications as read" in mark_all_res.json()["message"]

    # Unread count now 0
    unread_res3 = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_res3.json()["unread_count"] == 0


# ── NOTIF-02: Stream Token and SSE Connectivity ──────────────────────────────


@pytest.mark.asyncio
async def test_stream_token_generation_and_stream(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test generating a 60s stream token and establishing an SSE stream connection."""
    user, headers = await create_user(username="stream_user", email="su@example.com")

    # 1. Generate stream token
    token_res = await client.post("/api/v1/notifications/token", headers=headers)
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "token" in token_data
    assert token_data["expires_in"] == 60
    stream_token = token_data["token"]

    # 2. Connect to SSE stream and read initial connection message
    # We read line by line from the streaming response
    async with client.stream(
        "GET",
        f"/api/v1/notifications/stream?token={stream_token}",
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines: list[str] = []
        async for line in response.aiter_lines():
            if line.strip():
                lines.append(line.strip())
            if len(lines) >= 2:
                break

        assert "event: connected" in lines[0]
        data_json = json.loads(lines[1].replace("data: ", ""))
        assert data_json["status"] == "connected"
        assert data_json["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_stream_invalid_token_rejected(
    client: AsyncClient,
) -> None:
    """Test that connecting to SSE with an invalid or expired token is rejected."""
    bad_res = await client.get("/api/v1/notifications/stream?token=invalid.jwt.token")
    assert bad_res.status_code == 401


# ── NOTIF-03: Real-Time Pub/Sub Distribution and Admin Login Alert ────────────


@pytest.mark.asyncio
async def test_pubsub_realtime_event_delivery() -> None:
    """Verify in-process pub/sub publish and subscribe behavior."""
    channel = "test-channel"
    sub_gen = pubsub.subscribe(channel)

    # Start listener task so generator registers subscription in pubsub
    listen_task = asyncio.create_task(sub_gen.__anext__())
    await asyncio.sleep(0.01)

    test_message = {"event": "notification", "data": {"greeting": "hello"}}
    await pubsub.publish(channel, test_message)

    received = await asyncio.wait_for(listen_task, timeout=2.0)
    assert received == test_message

    await sub_gen.aclose()


@pytest.mark.asyncio
async def test_admin_login_notification_and_debouncing(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """
    Verify successful login triggers a real-time admin notification,
    and repeated logins within 60 seconds are debounced.
    """
    # 1. Create an admin user
    admin, _ = await create_user(
        username="superadmin",
        email="admin_notif@example.com",
        role="admin",
    )

    # 2. Create a normal user
    _, _ = await create_user(
        username="regular_login",
        email="reg_login@example.com",
        password="ValidPass123!",
    )

    # 3. User logs in -> should generate admin notification
    login_res1 = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "regular_login", "password": "ValidPass123!"},
    )
    assert login_res1.status_code == 200

    # Verify notification persisted for admin
    notif_stmt = select(Notification).where(
        Notification.user_id == admin.id,
        Notification.type == "admin_login",
    )
    notifs1 = list((await test_db_session.execute(notif_stmt)).scalars().all())
    assert len(notifs1) == 1
    assert notifs1[0].payload["username"] == "regular_login"

    # 4. User logs in again immediately -> debounced, no second notification
    login_res2 = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "regular_login", "password": "ValidPass123!"},
    )
    assert login_res2.status_code == 200

    notifs2 = list((await test_db_session.execute(notif_stmt)).scalars().all())
    assert len(notifs2) == 1  # Still 1 because debounced within 60s
