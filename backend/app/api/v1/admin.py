"""
Admin Router
============
Endpoints for administrative dashboard, user management, content moderation,
moderation queue processing, and audit logs.
Protected by require_admin dependency across all routes.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.schemas.admin import (
    ActivityLogListResponse,
    AdminCommentListResponse,
    AdminCommentResponse,
    AdminPostListResponse,
    AdminPostResponse,
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    BulkActionRequest,
    ChartDataResponse,
    ModerationActionRequest,
    ModerationItemResponse,
    ModerationQueueResponse,
    ToggleHideRequest,
    UserRoleUpdate,
    UserSuspendUpdate,
)
from app.schemas.auth import MessageResponse
from app.services.admin_service import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_client_ip(request: Request) -> str | None:
    """Extract client IP address from headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Dashboard & Analytics ────────────────────────────────────────────────────


@router.get("/stats", response_model=AdminStatsResponse)
async def get_dashboard_stats(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminStatsResponse:
    """Retrieve platform-wide KPI counts for stat cards."""
    return await admin_service.get_stats(db=db)


@router.get("/charts", response_model=ChartDataResponse)
async def get_dashboard_charts(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChartDataResponse:
    """Retrieve 30-day analytics time-series points for signups and posts."""
    return await admin_service.get_charts_data(db=db)


# ── User Administration ──────────────────────────────────────────────────────


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Annotated[str | None, Query(description="Search username/email/name")] = None,
    role: Annotated[str | None, Query(description="Filter by role")] = None,
    is_suspended: Annotated[bool | None, Query(description="Filter by suspension status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> AdminUserListResponse:
    """Search and paginate platform users."""
    return await admin_service.list_users(
        db=db,
        search=search,
        role=role,
        is_suspended=is_suspended,
        page=page,
        page_size=page_size,
    )


@router.patch("/users/{user_id}/suspend", response_model=AdminUserResponse)
async def update_user_suspension(
    user_id: uuid.UUID,
    data: UserSuspendUpdate,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    """Suspend or unsuspend a user account. Revokes active sessions on suspension."""
    ip = get_client_ip(request)
    return await admin_service.update_user_suspend(
        db=db,
        admin=current_admin,
        user_id=user_id,
        is_suspended=data.is_suspended,
        reason=data.reason,
        ip_address=ip,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    """Promote or demote a user account role ('user' or 'admin')."""
    ip = get_client_ip(request)
    return await admin_service.update_user_role(
        db=db,
        admin=current_admin,
        user_id=user_id,
        new_role=data.role,
        ip_address=ip,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Permanently delete a user account and cascade associated data."""
    ip = get_client_ip(request)
    await admin_service.delete_user(db=db, admin=current_admin, user_id=user_id, ip_address=ip)


# ── Content Management: Posts ────────────────────────────────────────────────


@router.get("/posts", response_model=AdminPostListResponse)
async def list_posts(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Annotated[str | None, Query(description="Search content")] = None,
    is_hidden: Annotated[bool | None, Query(description="Filter by hidden state")] = None,
    author_id: Annotated[uuid.UUID | None, Query(description="Filter by author")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> AdminPostListResponse:
    """List and search all platform posts, including soft-hidden content."""
    return await admin_service.list_posts(
        db=db,
        search=search,
        is_hidden=is_hidden,
        author_id=author_id,
        page=page,
        page_size=page_size,
    )


@router.patch("/posts/{post_id}/hide", response_model=AdminPostResponse)
async def toggle_hide_post(
    post_id: uuid.UUID,
    data: ToggleHideRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminPostResponse:
    """Hide or restore a post from public feeds."""
    ip = get_client_ip(request)
    return await admin_service.toggle_hide_post(
        db=db,
        admin=current_admin,
        post_id=post_id,
        is_hidden=data.is_hidden,
        ip_address=ip,
    )


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: uuid.UUID,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Permanently delete a post and associated comments and likes."""
    ip = get_client_ip(request)
    await admin_service.delete_post(db=db, admin=current_admin, post_id=post_id, ip_address=ip)


@router.post("/posts/bulk", response_model=MessageResponse)
async def bulk_action_posts(
    data: BulkActionRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Execute bulk moderation action (hide, restore, delete) across posts."""
    ip = get_client_ip(request)
    count = await admin_service.bulk_posts_action(
        db=db,
        admin=current_admin,
        ids=data.ids,
        action=data.action,
        ip_address=ip,
    )
    return MessageResponse(message=f"Successfully performed '{data.action}' on {count} posts.")


# ── Content Management: Comments ─────────────────────────────────────────────


@router.get("/comments", response_model=AdminCommentListResponse)
async def list_comments(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: Annotated[str | None, Query(description="Search comment text")] = None,
    is_hidden: Annotated[bool | None, Query(description="Filter by hidden state")] = None,
    post_id: Annotated[uuid.UUID | None, Query(description="Filter by post")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> AdminCommentListResponse:
    """List and search all platform comments, including hidden items."""
    return await admin_service.list_comments(
        db=db,
        search=search,
        is_hidden=is_hidden,
        post_id=post_id,
        page=page,
        page_size=page_size,
    )


@router.patch("/comments/{comment_id}/hide", response_model=AdminCommentResponse)
async def toggle_hide_comment(
    comment_id: uuid.UUID,
    data: ToggleHideRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCommentResponse:
    """Hide or restore a comment."""
    ip = get_client_ip(request)
    return await admin_service.toggle_hide_comment(
        db=db,
        admin=current_admin,
        comment_id=comment_id,
        is_hidden=data.is_hidden,
        ip_address=ip,
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Permanently delete a comment and its replies."""
    ip = get_client_ip(request)
    await admin_service.delete_comment(
        db=db, admin=current_admin, comment_id=comment_id, ip_address=ip
    )


@router.post("/comments/bulk", response_model=MessageResponse)
async def bulk_action_comments(
    data: BulkActionRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Execute bulk moderation action (hide, restore, delete) across comments."""
    ip = get_client_ip(request)
    count = await admin_service.bulk_comments_action(
        db=db,
        admin=current_admin,
        ids=data.ids,
        action=data.action,
        ip_address=ip,
    )
    return MessageResponse(message=f"Successfully performed '{data.action}' on {count} comments.")


# ── Moderation Queue ─────────────────────────────────────────────────────────


@router.get("/moderation", response_model=ModerationQueueResponse)
async def list_moderation_queue(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[str | None, Query(description="Filter category")] = None,
    severity: Annotated[str | None, Query(description="Filter severity")] = None,
    reviewed: Annotated[bool | None, Query(description="Filter reviewed status")] = False,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> ModerationQueueResponse:
    """Retrieve moderation queue items flagged by automated AI or user reports."""
    return await admin_service.list_moderation_queue(
        db=db,
        category=category,
        severity=severity,
        reviewed=reviewed,
        page=page,
        page_size=page_size,
    )


@router.post("/moderation/{flag_id}/action", response_model=ModerationItemResponse)
async def action_moderation_item(
    flag_id: uuid.UUID,
    data: ModerationActionRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationItemResponse:
    """Resolve a flagged item (approve, hide, delete target content)."""
    ip = get_client_ip(request)
    return await admin_service.action_moderation_item(
        db=db,
        admin=current_admin,
        flag_id=flag_id,
        action=data.action,
        notes=data.notes,
        ip_address=ip,
    )


# ── Activity Audit Logs ──────────────────────────────────────────────────────


@router.get("/activity-logs", response_model=ActivityLogListResponse)
async def list_activity_logs(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    action: Annotated[str | None, Query(description="Filter by action name")] = None,
    resource_type: Annotated[str | None, Query(description="Filter by resource")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 25,
) -> ActivityLogListResponse:
    """Retrieve immutable administrative audit logs."""
    return await admin_service.list_activity_logs(
        db=db,
        action=action,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )
