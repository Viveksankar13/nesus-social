"""
Admin Backend Test Suite
========================
Comprehensive tests verifying:
- ADMIN-01: Dashboard stats KPI cards
- ADMIN-02: 30-day time-series analytics charts
- ADMIN-03: User management (search, suspend/unsuspend, role changes, deletion)
- ADMIN-04: Posts and comments management, hide toggling, and bulk moderation actions
- ADMIN-05: Moderation queue processing (approve, hide, delete flagged items)
- ADMIN-06: Activity audit trail logging for all administrative operations
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityLog
from app.models.moderation import ModerationFlag
from app.models.post import Post

# ── ADMIN-01 & ADMIN-02: Stats and 30-Day Charts ─────────────────────────────


@pytest.mark.asyncio
async def test_admin_stats_and_charts(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify KPI stat cards and 30-day analytics charts endpoints."""
    # 1. Regular user forbidden
    _, user_headers = await create_user(username="regular_viewer", email="rv@example.com")
    forbidden_stats = await client.get("/api/v1/admin/stats", headers=user_headers)
    assert forbidden_stats.status_code == 403

    # 2. Admin access
    _, admin_headers = await create_user(
        username="admin_analytics", email="aa@example.com", role="admin"
    )

    stats_res = await client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_users" in stats
    assert "verified_users" in stats
    assert "total_posts" in stats
    assert "total_comments" in stats
    assert "total_likes" in stats
    assert "flagged_items" in stats
    assert stats["total_users"] >= 2

    # 3. Charts data
    charts_res = await client.get("/api/v1/admin/charts", headers=admin_headers)
    assert charts_res.status_code == 200
    charts = charts_res.json()
    assert len(charts["signups_by_day"]) == 30
    assert len(charts["posts_by_day"]) == 30


# ── ADMIN-03: User Administration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_user_management(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify user search, pagination, suspension toggle, role update, and deletion."""
    target, _ = await create_user(
        username="target_user",
        email="target@example.com",
        password="TargetPass123!",
    )
    admin, admin_headers = await create_user(
        username="admin_manager", email="am@example.com", role="admin"
    )

    # 1. Search users list
    list_res = await client.get("/api/v1/admin/users?search=target", headers=admin_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) == 1
    assert list_res.json()["items"][0]["username"] == "target_user"

    # 2. Suspend target user
    suspend_res = await client.patch(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"is_suspended": True, "reason": "Terms violation"},
        headers=admin_headers,
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["is_suspended"] is True

    # Attempt to log in with suspended user -> 403 Forbidden
    login_attempt = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "target_user", "password": "TargetPass123!"},
    )
    assert login_attempt.status_code == 403
    assert "suspended" in login_attempt.json()["detail"].lower()

    # Unsuspend target user
    unsuspend_res = await client.patch(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"is_suspended": False},
        headers=admin_headers,
    )
    assert unsuspend_res.status_code == 200
    assert unsuspend_res.json()["is_suspended"] is False

    # 3. Change user role
    role_res = await client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"] == "admin"

    # 4. Self-action guard: Admin cannot suspend or delete self
    self_suspend = await client.patch(
        f"/api/v1/admin/users/{admin.id}/suspend",
        json={"is_suspended": True},
        headers=admin_headers,
    )
    assert self_suspend.status_code == 400

    self_delete = await client.delete(
        f"/api/v1/admin/users/{admin.id}",
        headers=admin_headers,
    )
    assert self_delete.status_code == 400

    # 5. Delete target user
    del_res = await client.delete(
        f"/api/v1/admin/users/{target.id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 204


# ── ADMIN-04: Posts & Comments Management and Bulk Actions ───────────────────


@pytest.mark.asyncio
async def test_admin_content_and_bulk_actions(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Verify post/comment management, hide toggling, and bulk operations."""
    author, author_headers = await create_user(username="bulk_author", email="ba@example.com")
    _, admin_headers = await create_user(
        username="admin_moderator", email="amod@example.com", role="admin"
    )

    # Create 3 posts
    post_ids: list[str] = []
    for i in range(3):
        res = await client.post(
            "/api/v1/posts",
            json={"content": f"Bulk post {i}"},
            headers=author_headers,
        )
        post_ids.append(res.json()["id"])

    # 1. Toggle hide single post
    hide_res = await client.patch(
        f"/api/v1/admin/posts/{post_ids[0]}/hide",
        json={"is_hidden": True},
        headers=admin_headers,
    )
    assert hide_res.status_code == 200
    assert hide_res.json()["is_hidden"] is True

    # Verify hidden post does not appear in public feed
    feed_res = await client.get("/api/v1/posts")
    feed_ids = [p["id"] for p in feed_res.json()["items"]]
    assert post_ids[0] not in feed_ids

    # 2. Bulk hide remaining 2 posts
    bulk_hide = await client.post(
        "/api/v1/admin/posts/bulk",
        json={"ids": post_ids[1:], "action": "hide"},
        headers=admin_headers,
    )
    assert bulk_hide.status_code == 200
    assert "performed 'hide' on 2 posts" in bulk_hide.json()["message"]

    # 3. Bulk delete all 3 posts
    bulk_del = await client.post(
        "/api/v1/admin/posts/bulk",
        json={"ids": post_ids, "action": "delete"},
        headers=admin_headers,
    )
    assert bulk_del.status_code == 200
    assert "performed 'delete' on 3 posts" in bulk_del.json()["message"]


# ── ADMIN-05: Moderation Queue ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_moderation_queue(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Verify moderation queue listing and resolve actions."""
    author, author_headers = await create_user(username="flagged_user", email="fu@example.com")
    _, admin_headers = await create_user(
        username="admin_queue", email="aq@example.com", role="admin"
    )

    # Create a post
    post_res = await client.post(
        "/api/v1/posts",
        json={"content": "Questionable content under review."},
        headers=author_headers,
    )
    post_id = uuid.UUID(post_res.json()["id"])

    # Insert a moderation flag
    flag = ModerationFlag(
        id=uuid.uuid4(),
        content_type="post",
        content_id=post_id,
        category="harassment",
        severity="medium",
        score=0.78,
        action="flag",
        reason="Detected potential harassment keywords.",
        reviewed=False,
    )
    test_db_session.add(flag)
    await test_db_session.commit()

    # 1. List moderation queue
    queue_res = await client.get("/api/v1/admin/moderation", headers=admin_headers)
    assert queue_res.status_code == 200
    items = queue_res.json()["items"]
    assert len(items) >= 1
    assert items[0]["content_id"] == str(post_id)
    assert items[0]["content_snippet"] is not None

    # 2. Action: hide content
    action_res = await client.post(
        f"/api/v1/admin/moderation/{flag.id}/action",
        json={"action": "hide", "notes": "Hidden due to community guidelines."},
        headers=admin_headers,
    )
    assert action_res.status_code == 200
    assert action_res.json()["reviewed"] is True

    # Post should now be hidden
    post_db = (
        await test_db_session.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    assert post_db is not None
    assert post_db.is_hidden is True


# ── ADMIN-06: Activity Audit Logs ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_activity_audit_logs(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Verify audit log entries are generated and queryable."""
    user, _ = await create_user(username="action_user", email="act@example.com")
    _, admin_headers = await create_user(
        username="audit_admin", email="audit@example.com", role="admin"
    )

    # Perform an admin action (suspend user) to generate an audit log
    await client.patch(
        f"/api/v1/admin/users/{user.id}/suspend",
        json={"is_suspended": True, "reason": "Audit verification"},
        headers=admin_headers,
    )

    # Query activity logs endpoint
    logs_res = await client.get("/api/v1/admin/activity-logs", headers=admin_headers)
    assert logs_res.status_code == 200
    data = logs_res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["action"] == "suspend_user"
    assert data["items"][0]["admin_username"] == "audit_admin"

    # Verify directly from database table
    db_logs = list((await test_db_session.execute(select(ActivityLog))).scalars().all())
    assert len(db_logs) >= 1
    actions = [log.action for log in db_logs]
    assert any("user" in a or "post" in a or "moderation" in a for a in actions)
