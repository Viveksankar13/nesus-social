"""
Admin Service
=============
Encapsulates administrative workflows:
- KPI metrics calculation and 30-day time-series aggregations
- User management (search, pagination, suspension, role updates, deletion)
- Content management (posts & comments search, hide toggling, bulk moderation)
- Moderation queue processing (approve, hide, delete flagged items)
- Activity audit trail logging
"""

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import ActivityLog
from app.models.comment import Comment
from app.models.like import Like
from app.models.moderation import ModerationFlag
from app.models.post import Post
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.admin import (
    ActivityLogListResponse,
    ActivityLogResponse,
    AdminCommentListResponse,
    AdminCommentResponse,
    AdminPostListResponse,
    AdminPostResponse,
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserResponse,
    ChartDataResponse,
    DailyMetricPoint,
    ModerationItemResponse,
    ModerationQueueResponse,
)


class AdminService:
    """Service handling all administrative actions and reporting."""

    # ── Audit Trail ──────────────────────────────────────────────────────────

    @staticmethod
    async def log_action(
        db: AsyncSession,
        admin: User,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> ActivityLog:
        """Record an administrative action in the immutable audit log."""
        log = ActivityLog(
            id=uuid.uuid4(),
            admin_id=admin.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    # ── Analytics & KPI Statistics ───────────────────────────────────────────

    @staticmethod
    async def get_stats(db: AsyncSession) -> AdminStatsResponse:
        """Calculate platform-wide KPI metric counts."""
        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)

        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        verified_users = (
            await db.execute(select(func.count(User.id)).where(User.is_verified.is_(True)))
        ).scalar() or 0
        new_users_7d = (
            await db.execute(select(func.count(User.id)).where(User.created_at >= seven_days_ago))
        ).scalar() or 0
        total_posts = (await db.execute(select(func.count(Post.id)))).scalar() or 0
        total_comments = (await db.execute(select(func.count(Comment.id)))).scalar() or 0
        total_likes = (await db.execute(select(func.count(Like.id)))).scalar() or 0
        flagged_items = (
            await db.execute(
                select(func.count(ModerationFlag.id)).where(ModerationFlag.reviewed.is_(False))
            )
        ).scalar() or 0

        return AdminStatsResponse(
            total_users=total_users,
            verified_users=verified_users,
            new_users_7d=new_users_7d,
            total_posts=total_posts,
            total_comments=total_comments,
            total_likes=total_likes,
            flagged_items=flagged_items,
        )

    @staticmethod
    async def get_charts_data(db: AsyncSession) -> ChartDataResponse:
        """
        Generate 30-day time-series data for signups/day and posts/day.
        Dual-dialect compatible across PostgreSQL and SQLite.
        """
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=29)).date()

        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
        signups_map = {d: 0 for d in dates}
        posts_map = {d: 0 for d in dates}

        cutoff_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)

        # Query user signups
        users_stmt = select(User.created_at).where(User.created_at >= cutoff_dt)
        for created_at in (await db.execute(users_stmt)).scalars():
            key = created_at.strftime("%Y-%m-%d")
            if key in signups_map:
                signups_map[key] += 1

        # Query post creations
        posts_stmt = select(Post.created_at).where(Post.created_at >= cutoff_dt)
        for created_at in (await db.execute(posts_stmt)).scalars():
            key = created_at.strftime("%Y-%m-%d")
            if key in posts_map:
                posts_map[key] += 1

        signups_points = [DailyMetricPoint(date=d, count=signups_map[d]) for d in dates]
        posts_points = [DailyMetricPoint(date=d, count=posts_map[d]) for d in dates]

        return ChartDataResponse(signups_by_day=signups_points, posts_by_day=posts_points)

    # ── User Administration ──────────────────────────────────────────────────

    @staticmethod
    async def list_users(
        db: AsyncSession,
        search: str | None = None,
        role: str | None = None,
        is_suspended: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminUserListResponse:
        """Search and paginate platform users with content statistics."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = select(User)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.username.ilike(pattern),
                    User.email.ilike(pattern),
                    User.display_name.ilike(pattern),
                    User.usn.ilike(pattern),
                )
            )
        if role and role != "all":
            query = query.where(User.role == role)
        if is_suspended is not None:
            query = query.where(User.is_suspended == is_suspended)

        # Count total
        total_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_stmt)).scalar() or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        # Fetch page
        paginated_stmt = (
            query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        users = list((await db.execute(paginated_stmt)).scalars().all())

        if not users:
            return AdminUserListResponse(
                items=[], total=total, page=page, page_size=page_size, total_pages=total_pages
            )

        user_ids = [u.id for u in users]

        # Batch count posts
        posts_counts = dict(
            (
                await db.execute(
                    select(Post.author_id, func.count(Post.id))
                    .where(Post.author_id.in_(user_ids))
                    .group_by(Post.author_id)
                )
            ).all()
        )

        # Batch count comments
        comments_counts = dict(
            (
                await db.execute(
                    select(Comment.author_id, func.count(Comment.id))
                    .where(Comment.author_id.in_(user_ids))
                    .group_by(Comment.author_id)
                )
            ).all()
        )

        items = [
            AdminUserResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                usn=u.usn,
                display_name=u.display_name,
                role=u.role,
                is_verified=u.is_verified,
                is_suspended=u.is_suspended,
                created_at=u.created_at,
                posts_count=posts_counts.get(u.id, 0),
                comments_count=comments_counts.get(u.id, 0),
            )
            for u in users
        ]

        return AdminUserListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def update_user_suspend(
        db: AsyncSession,
        admin: User,
        user_id: uuid.UUID,
        is_suspended: bool,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> AdminUserResponse:
        """Suspend or unsuspend a user account. Admins cannot suspend themselves."""
        if user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot suspend their own account.",
            )

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        user.is_suspended = is_suspended

        # If suspending, immediately invalidate all active sessions
        if is_suspended:
            await db.execute(
                update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True)
            )

        await db.commit()
        await db.refresh(user)

        action_name = "suspend_user" if is_suspended else "unsuspend_user"
        await AdminService.log_action(
            db=db,
            admin=admin,
            action=action_name,
            resource_type="user",
            resource_id=user.id,
            details={"username": user.username, "reason": reason},
            ip_address=ip_address,
        )

        return AdminUserResponse.model_validate(user)

    @staticmethod
    async def update_user_role(
        db: AsyncSession,
        admin: User,
        user_id: uuid.UUID,
        new_role: str,
        ip_address: str | None = None,
    ) -> AdminUserResponse:
        """Change a user's role. Admins cannot modify their own role."""
        if user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot modify their own role.",
            )

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        old_role = user.role
        user.role = new_role
        await db.commit()
        await db.refresh(user)

        await AdminService.log_action(
            db=db,
            admin=admin,
            action="change_role",
            resource_type="user",
            resource_id=user.id,
            details={"username": user.username, "old_role": old_role, "new_role": new_role},
            ip_address=ip_address,
        )

        return AdminUserResponse.model_validate(user)

    @staticmethod
    async def delete_user(
        db: AsyncSession,
        admin: User,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Permanently delete a user account. Admins cannot delete themselves."""
        if user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot delete their own account.",
            )

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        deleted_username = user.username
        await db.delete(user)
        await db.commit()

        await AdminService.log_action(
            db=db,
            admin=admin,
            action="delete_user",
            resource_type="user",
            resource_id=user_id,
            details={"username": deleted_username},
            ip_address=ip_address,
        )

    # ── Content Management: Posts ────────────────────────────────────────────

    @staticmethod
    async def list_posts(
        db: AsyncSession,
        search: str | None = None,
        is_hidden: bool | None = None,
        author_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminPostListResponse:
        """List and search all posts, including hidden items."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = select(Post).options(selectinload(Post.author))
        if search and search.strip():
            query = query.where(Post.content.ilike(f"%{search.strip()}%"))
        if is_hidden is not None:
            query = query.where(Post.is_hidden == is_hidden)
        if author_id:
            query = query.where(Post.author_id == author_id)

        total_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_stmt)).scalar() or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        paginated_stmt = (
            query.order_by(Post.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        posts = list((await db.execute(paginated_stmt)).scalars().all())

        if not posts:
            return AdminPostListResponse(
                items=[], total=total, page=page, page_size=page_size, total_pages=total_pages
            )

        post_ids = [p.id for p in posts]
        likes_map = dict(
            (
                await db.execute(
                    select(Like.post_id, func.count(Like.id))
                    .where(Like.post_id.in_(post_ids))
                    .group_by(Like.post_id)
                )
            ).all()
        )
        comments_map = dict(
            (
                await db.execute(
                    select(Comment.post_id, func.count(Comment.id))
                    .where(Comment.post_id.in_(post_ids))
                    .group_by(Comment.post_id)
                )
            ).all()
        )

        items = [
            AdminPostResponse(
                id=p.id,
                author_id=p.author_id,
                author_username=p.author.username if p.author else "[deleted]",
                content=p.content,
                image_url=p.image_url,
                is_hidden=p.is_hidden,
                is_edited=p.is_edited,
                created_at=p.created_at,
                likes_count=likes_map.get(p.id, 0),
                comments_count=comments_map.get(p.id, 0),
            )
            for p in posts
        ]

        return AdminPostListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def toggle_hide_post(
        db: AsyncSession,
        admin: User,
        post_id: uuid.UUID,
        is_hidden: bool,
        ip_address: str | None = None,
    ) -> AdminPostResponse:
        """Hide or restore a post."""
        post = (
            await db.execute(
                select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
            )
        ).scalar_one_or_none()

        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        post.is_hidden = is_hidden
        await db.commit()
        await db.refresh(post)

        action = "hide_post" if is_hidden else "restore_post"
        await AdminService.log_action(
            db=db,
            admin=admin,
            action=action,
            resource_type="post",
            resource_id=post.id,
            details={"is_hidden": is_hidden},
            ip_address=ip_address,
        )

        return AdminPostResponse(
            id=post.id,
            author_id=post.author_id,
            author_username=post.author.username if post.author else "[deleted]",
            content=post.content,
            image_url=post.image_url,
            is_hidden=post.is_hidden,
            is_edited=post.is_edited,
            created_at=post.created_at,
        )

    @staticmethod
    async def delete_post(
        db: AsyncSession,
        admin: User,
        post_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Permanently delete a post as administrator."""
        post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

        await db.delete(post)
        await db.commit()

        await AdminService.log_action(
            db=db,
            admin=admin,
            action="delete_post",
            resource_type="post",
            resource_id=post_id,
            ip_address=ip_address,
        )

    @staticmethod
    async def bulk_posts_action(
        db: AsyncSession,
        admin: User,
        ids: list[uuid.UUID],
        action: str,
        ip_address: str | None = None,
    ) -> int:
        """Perform bulk moderation action on multiple posts."""
        if action == "hide":
            stmt = update(Post).where(Post.id.in_(ids)).values(is_hidden=True)
            res = await db.execute(stmt)
            count = res.rowcount  # type: ignore[no-any-return]
        elif action == "restore":
            stmt = update(Post).where(Post.id.in_(ids)).values(is_hidden=False)
            res = await db.execute(stmt)
            count = res.rowcount  # type: ignore[no-any-return]
        elif action == "delete":
            posts = list((await db.execute(select(Post).where(Post.id.in_(ids)))).scalars().all())
            count = len(posts)
            for p in posts:
                await db.delete(p)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported bulk action '{action}'.",
            )

        await db.commit()

        await AdminService.log_action(
            db=db,
            admin=admin,
            action=f"bulk_{action}_posts",
            resource_type="post",
            details={"count": count, "ids": [str(i) for i in ids]},
            ip_address=ip_address,
        )
        return count

    # ── Content Management: Comments ─────────────────────────────────────────

    @staticmethod
    async def list_comments(
        db: AsyncSession,
        search: str | None = None,
        is_hidden: bool | None = None,
        post_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminCommentListResponse:
        """List and search all comments, including hidden items."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = select(Comment).options(selectinload(Comment.author))
        if search and search.strip():
            query = query.where(Comment.content.ilike(f"%{search.strip()}%"))
        if is_hidden is not None:
            query = query.where(Comment.is_hidden == is_hidden)
        if post_id:
            query = query.where(Comment.post_id == post_id)

        total_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_stmt)).scalar() or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        paginated_stmt = (
            query.order_by(Comment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        comments = list((await db.execute(paginated_stmt)).scalars().all())

        items = [
            AdminCommentResponse(
                id=c.id,
                post_id=c.post_id,
                author_id=c.author_id,
                author_username=c.author.username if c.author else "[deleted]",
                content=c.content,
                parent_id=c.parent_id,
                is_hidden=c.is_hidden,
                created_at=c.created_at,
            )
            for c in comments
        ]

        return AdminCommentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def toggle_hide_comment(
        db: AsyncSession,
        admin: User,
        comment_id: uuid.UUID,
        is_hidden: bool,
        ip_address: str | None = None,
    ) -> AdminCommentResponse:
        """Hide or restore a comment."""
        comment = (
            await db.execute(
                select(Comment)
                .options(selectinload(Comment.author))
                .where(Comment.id == comment_id)
            )
        ).scalar_one_or_none()

        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        comment.is_hidden = is_hidden
        await db.commit()
        await db.refresh(comment)

        action = "hide_comment" if is_hidden else "restore_comment"
        await AdminService.log_action(
            db=db,
            admin=admin,
            action=action,
            resource_type="comment",
            resource_id=comment.id,
            details={"is_hidden": is_hidden},
            ip_address=ip_address,
        )

        return AdminCommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_username=comment.author.username if comment.author else "[deleted]",
            content=comment.content,
            parent_id=comment.parent_id,
            is_hidden=comment.is_hidden,
            created_at=comment.created_at,
        )

    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        admin: User,
        comment_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Permanently delete a comment as administrator."""
        comment = (
            await db.execute(select(Comment).where(Comment.id == comment_id))
        ).scalar_one_or_none()
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

        await db.delete(comment)
        await db.commit()

        await AdminService.log_action(
            db=db,
            admin=admin,
            action="delete_comment",
            resource_type="comment",
            resource_id=comment_id,
            ip_address=ip_address,
        )

    @staticmethod
    async def bulk_comments_action(
        db: AsyncSession,
        admin: User,
        ids: list[uuid.UUID],
        action: str,
        ip_address: str | None = None,
    ) -> int:
        """Perform bulk moderation action on multiple comments."""
        if action == "hide":
            stmt = update(Comment).where(Comment.id.in_(ids)).values(is_hidden=True)
            res = await db.execute(stmt)
            count = res.rowcount  # type: ignore[no-any-return]
        elif action == "restore":
            stmt = update(Comment).where(Comment.id.in_(ids)).values(is_hidden=False)
            res = await db.execute(stmt)
            count = res.rowcount  # type: ignore[no-any-return]
        elif action == "delete":
            comments = list(
                (await db.execute(select(Comment).where(Comment.id.in_(ids)))).scalars().all()
            )
            count = len(comments)
            for c in comments:
                await db.delete(c)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported bulk action '{action}'.",
            )

        await db.commit()

        await AdminService.log_action(
            db=db,
            admin=admin,
            action=f"bulk_{action}_comments",
            resource_type="comment",
            details={"count": count, "ids": [str(i) for i in ids]},
            ip_address=ip_address,
        )
        return count

    # ── Moderation Queue ─────────────────────────────────────────────────────

    @staticmethod
    async def list_moderation_queue(
        db: AsyncSession,
        category: str | None = None,
        severity: str | None = None,
        reviewed: bool | None = False,
        page: int = 1,
        page_size: int = 20,
    ) -> ModerationQueueResponse:
        """List flagged items pending review with content snippet preview."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = select(ModerationFlag)
        if category and category != "all":
            query = query.where(ModerationFlag.category == category)
        if severity and severity != "all":
            query = query.where(ModerationFlag.severity == severity)
        if reviewed is not None:
            query = query.where(ModerationFlag.reviewed == reviewed)

        total_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_stmt)).scalar() or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        paginated_stmt = (
            query.order_by(ModerationFlag.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        flags = list((await db.execute(paginated_stmt)).scalars().all())

        items: list[ModerationItemResponse] = []
        for f in flags:
            snippet = None
            if f.content_type == "post":
                p = (
                    await db.execute(select(Post.content).where(Post.id == f.content_id))
                ).scalar_one_or_none()
                snippet = p[:100] if p else None
            elif f.content_type == "comment":
                c = (
                    await db.execute(select(Comment.content).where(Comment.id == f.content_id))
                ).scalar_one_or_none()
                snippet = c[:100] if c else None

            items.append(
                ModerationItemResponse(
                    id=f.id,
                    content_type=f.content_type,
                    content_id=f.content_id,
                    category=f.category,
                    severity=f.severity,
                    score=f.score,
                    action=f.action,
                    reason=f.reason,
                    reviewed=f.reviewed,
                    created_at=f.created_at,
                    content_snippet=snippet,
                )
            )

        return ModerationQueueResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def action_moderation_item(
        db: AsyncSession,
        admin: User,
        flag_id: uuid.UUID,
        action: str,
        notes: str | None = None,
        ip_address: str | None = None,
    ) -> ModerationItemResponse:
        """Resolve a moderation item: approve, hide, or delete target content."""
        flag = (
            await db.execute(select(ModerationFlag).where(ModerationFlag.id == flag_id))
        ).scalar_one_or_none()
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Moderation flag not found."
            )

        flag.reviewed = True

        if action == "hide":
            if flag.content_type == "post":
                await db.execute(
                    update(Post).where(Post.id == flag.content_id).values(is_hidden=True)
                )
            elif flag.content_type == "comment":
                await db.execute(
                    update(Comment).where(Comment.id == flag.content_id).values(is_hidden=True)
                )
        elif action == "approve":
            if flag.content_type == "post":
                await db.execute(
                    update(Post).where(Post.id == flag.content_id).values(is_hidden=False)
                )
            elif flag.content_type == "comment":
                await db.execute(
                    update(Comment).where(Comment.id == flag.content_id).values(is_hidden=False)
                )
        elif action == "delete":
            if flag.content_type == "post":
                post = (
                    await db.execute(select(Post).where(Post.id == flag.content_id))
                ).scalar_one_or_none()
                if post:
                    await db.delete(post)
            elif flag.content_type == "comment":
                comment = (
                    await db.execute(select(Comment).where(Comment.id == flag.content_id))
                ).scalar_one_or_none()
                if comment:
                    await db.delete(comment)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action '{action}'."
            )

        await db.commit()
        await db.refresh(flag)

        await AdminService.log_action(
            db=db,
            admin=admin,
            action=f"moderation_{action}",
            resource_type="moderation_flag",
            resource_id=flag.id,
            details={
                "content_type": flag.content_type,
                "content_id": str(flag.content_id),
                "notes": notes,
            },
            ip_address=ip_address,
        )

        return ModerationItemResponse.model_validate(flag)

    # ── Activity Audit Logs ──────────────────────────────────────────────────

    @staticmethod
    async def list_activity_logs(
        db: AsyncSession,
        action: str | None = None,
        resource_type: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ActivityLogListResponse:
        """List administrative audit trail logs."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = select(ActivityLog).options(selectinload(ActivityLog.admin))
        if action and action != "all":
            query = query.where(ActivityLog.action == action)
        if resource_type and resource_type != "all":
            query = query.where(ActivityLog.resource_type == resource_type)

        total_stmt = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_stmt)).scalar() or 0
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        paginated_stmt = (
            query.order_by(ActivityLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = list((await db.execute(paginated_stmt)).scalars().all())

        items = [
            ActivityLogResponse(
                id=log_entry.id,
                admin_id=log_entry.admin_id,
                admin_username=log_entry.admin.username if log_entry.admin else "[deleted]",
                action=log_entry.action,
                resource_type=log_entry.resource_type,
                resource_id=log_entry.resource_id,
                details=log_entry.details,
                ip_address=log_entry.ip_address,
                created_at=log_entry.created_at,
            )
            for log_entry in logs
        ]

        return ActivityLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


admin_service = AdminService()
