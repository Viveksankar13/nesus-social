"""
Comment Service
===============
Handles creation, listing, updating, and deletion of threaded comments
with strict 1-level reply enforcement.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.user import AuthorSummary


class CommentService:
    """Service encapsulating comment operations and 1-level reply enforcement."""

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        post_id: uuid.UUID,
        author: User,
        data: CommentCreate,
    ) -> CommentResponse:
        """
        Create a top-level comment or a 1-level reply to an existing comment.
        Rejects nested replies beyond 1 level.
        Dispatches persistent notifications to post author and parent comment author.
        """
        # Validate target post exists and is not hidden
        post_query = select(Post).where(Post.id == post_id)
        post = (await db.execute(post_query)).scalar_one_or_none()
        if not post or post.is_hidden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        parent_comment: Comment | None = None
        if data.parent_id:
            parent_query = (
                select(Comment)
                .options(selectinload(Comment.author))
                .where(Comment.id == data.parent_id, Comment.post_id == post_id)
            )
            parent_comment = (await db.execute(parent_query)).scalar_one_or_none()

            if not parent_comment or parent_comment.is_hidden:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found.",
                )

            # Strict 1-level nesting check: replies cannot have replies
            if parent_comment.parent_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nested replies beyond 1 level are not allowed.",
                )

        # Create comment
        comment = Comment(
            post_id=post_id,
            author_id=author.id,
            parent_id=data.parent_id,
            content=data.content,
        )
        db.add(comment)
        await db.flush()  # assign UUID

        # Notification for post author
        if post.author_id != author.id:
            notif = Notification(
                user_id=post.author_id,
                type="comment",
                payload={
                    "post_id": str(post.id),
                    "comment_id": str(comment.id),
                    "author_id": str(author.id),
                    "author_username": author.username,
                    "author_name": author.display_name,
                },
            )
            db.add(notif)

        # Notification for parent comment author if reply
        if (
            parent_comment
            and parent_comment.author_id
            and parent_comment.author_id != author.id
            and parent_comment.author_id != post.author_id
        ):
            notif = Notification(
                user_id=parent_comment.author_id,
                type="reply",
                payload={
                    "post_id": str(post.id),
                    "comment_id": str(comment.id),
                    "parent_id": str(parent_comment.id),
                    "author_id": str(author.id),
                    "author_username": author.username,
                    "author_name": author.display_name,
                },
            )
            db.add(notif)

        await db.commit()
        await db.refresh(comment)

        author_summary = AuthorSummary(
            id=author.id,
            username=author.username,
            display_name=author.display_name,
            avatar_url=author.avatar_url,
        )

        return CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_id=author.id,
            author=author_summary,
            parent_id=comment.parent_id,
            content=comment.content,
            is_hidden=comment.is_hidden,
            is_edited=comment.is_edited,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[],
        )

    @staticmethod
    async def get_post_comments(db: AsyncSession, post_id: uuid.UUID) -> list[CommentResponse]:
        """
        Fetch all active comments for a post and organize them into
        top-level comments with nested 1-level replies.
        """
        query = (
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.post_id == post_id, Comment.is_hidden.is_(False))
            .order_by(Comment.created_at.asc())
        )
        result = await db.execute(query)
        all_comments = list(result.scalars().all())

        # Map comments into top-level and replies
        top_level: list[CommentResponse] = []
        replies_by_parent: dict[uuid.UUID, list[CommentResponse]] = {}

        for c in all_comments:
            author_summary = None
            if c.author:
                author_summary = AuthorSummary(
                    id=c.author.id,
                    username=c.author.username,
                    display_name=c.author.display_name,
                    avatar_url=c.author.avatar_url,
                )

            item = CommentResponse(
                id=c.id,
                post_id=c.post_id,
                author_id=c.author_id,
                author=author_summary,
                parent_id=c.parent_id,
                content=c.content,
                is_hidden=c.is_hidden,
                is_edited=c.is_edited,
                created_at=c.created_at,
                updated_at=c.updated_at,
                replies=[],
            )

            if c.parent_id is None:
                top_level.append(item)
            else:
                replies_by_parent.setdefault(c.parent_id, []).append(item)

        # Attach replies to parents
        for top in top_level:
            top.replies = replies_by_parent.get(top.id, [])

        return top_level

    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: uuid.UUID,
        user: User,
        data: CommentUpdate,
    ) -> CommentResponse:
        """Edit a comment. Only the author or an admin may edit."""
        query = (
            select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment_id)
        )
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment or (comment.is_hidden and user.role != "admin"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found.",
            )

        if comment.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this comment.",
            )

        comment.content = data.content
        comment.is_edited = True

        await db.commit()
        await db.refresh(comment)

        author_summary = None
        if comment.author:
            author_summary = AuthorSummary(
                id=comment.author.id,
                username=comment.author.username,
                display_name=comment.author.display_name,
                avatar_url=comment.author.avatar_url,
            )

        return CommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author=author_summary,
            parent_id=comment.parent_id,
            content=comment.content,
            is_hidden=comment.is_hidden,
            is_edited=comment.is_edited,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[],
        )

    @staticmethod
    async def delete_comment(db: AsyncSession, comment_id: uuid.UUID, user: User) -> None:
        """Delete a comment. Cascades to replies. Only author or admin allowed."""
        query = select(Comment).where(Comment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found.",
            )

        if comment.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this comment.",
            )

        await db.delete(comment)
        await db.commit()


comment_service = CommentService()
