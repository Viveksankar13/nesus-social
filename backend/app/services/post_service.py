"""
Post Service
============
Handles post creation, retrieval, updates, deletions, keyset-paginated feeds,
and like toggling.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import decode_cursor, encode_cursor
from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post
from app.models.user import User
from app.schemas.post import FeedResponse, PostCreate, PostResponse, PostUpdate
from app.schemas.user import AuthorSummary
from app.services.notification_service import notification_service


class PostService:
    """Service encapsulating post and feed operations."""

    @staticmethod
    async def create_post(db: AsyncSession, author: User, data: PostCreate) -> PostResponse:
        """Create a new post authored by the authenticated user."""
        post = Post(
            author_id=author.id,
            content=data.content,
            image_url=data.image_url,
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)

        author_summary = AuthorSummary(
            id=author.id,
            username=author.username,
            display_name=author.display_name,
            avatar_url=author.avatar_url,
        )

        return PostResponse(
            id=post.id,
            author_id=author.id,
            author=author_summary,
            content=post.content,
            image_url=post.image_url,
            is_hidden=post.is_hidden,
            is_edited=post.is_edited,
            created_at=post.created_at,
            updated_at=post.updated_at,
            likes_count=0,
            comments_count=0,
            has_liked=False,
        )

    @staticmethod
    async def get_post_by_id(
        db: AsyncSession,
        post_id: uuid.UUID,
        current_user: User | None = None,
    ) -> PostResponse:
        """Fetch a single post by ID with author details, counts, and reaction status."""
        query = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
        result = await db.execute(query)
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        if post.is_hidden and (not current_user or current_user.role != "admin"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        # Count likes
        likes_query = select(func.count(Like.id)).where(Like.post_id == post.id)
        likes_count = (await db.execute(likes_query)).scalar() or 0

        # Count active comments
        comments_query = select(func.count(Comment.id)).where(
            Comment.post_id == post.id,
            Comment.is_hidden.is_(False),
        )
        comments_count = (await db.execute(comments_query)).scalar() or 0

        # Check if viewer liked
        has_liked = False
        if current_user:
            has_liked_query = select(func.count(Like.id)).where(
                Like.post_id == post.id,
                Like.user_id == current_user.id,
            )
            has_liked = bool((await db.execute(has_liked_query)).scalar())

        return PostResponse(
            id=post.id,
            author_id=post.author_id,
            author=AuthorSummary(
                id=post.author.id,
                username=post.author.username,
                display_name=post.author.display_name,
                avatar_url=post.author.avatar_url,
            ),
            content=post.content,
            image_url=post.image_url,
            is_hidden=post.is_hidden,
            is_edited=post.is_edited,
            created_at=post.created_at,
            updated_at=post.updated_at,
            likes_count=likes_count,
            comments_count=comments_count,
            has_liked=has_liked,
        )

    @staticmethod
    async def update_post(
        db: AsyncSession,
        post_id: uuid.UUID,
        user: User,
        data: PostUpdate,
    ) -> PostResponse:
        """Edit post content/image. Only the author or an admin may edit."""
        query = select(Post).options(selectinload(Post.author)).where(Post.id == post_id)
        result = await db.execute(query)
        post = result.scalar_one_or_none()

        if not post or (post.is_hidden and user.role != "admin"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        if post.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this post.",
            )

        post.content = data.content
        post.image_url = data.image_url
        post.is_edited = True

        await db.commit()
        await db.refresh(post)

        return await PostService.get_post_by_id(db, post.id, current_user=user)

    @staticmethod
    async def delete_post(db: AsyncSession, post_id: uuid.UUID, user: User) -> None:
        """Delete a post. Cascades to comments and likes. Only author or admin allowed."""
        query = select(Post).where(Post.id == post_id)
        result = await db.execute(query)
        post = result.scalar_one_or_none()

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        if post.author_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this post.",
            )

        await db.delete(post)
        await db.commit()

    @staticmethod
    async def get_feed(
        db: AsyncSession,
        current_user: User | None = None,
        cursor: str | None = None,
        limit: int = 20,
        feed_type: str = "all",
        author_id: uuid.UUID | None = None,
    ) -> FeedResponse:
        """
        Fetch keyset-paginated posts feed.
        Uses compound (created_at DESC, id DESC) for stable cursor pagination.
        Executes constant-count batch queries to avoid N+1 count and like lookups.
        """
        # Clamp limit
        limit = max(1, min(limit, 50))

        query = select(Post).options(selectinload(Post.author)).where(Post.is_hidden.is_(False))

        if feed_type == "mine" and current_user:
            query = query.where(Post.author_id == current_user.id)
        elif author_id is not None:
            query = query.where(Post.author_id == author_id)

        # Apply cursor filter if valid cursor supplied
        if cursor:
            decoded = decode_cursor(cursor)
            if decoded:
                cursor_dt, cursor_id = decoded
                query = query.where(
                    (Post.created_at < cursor_dt)
                    | ((Post.created_at == cursor_dt) & (Post.id < cursor_id))
                )

        query = query.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit + 1)
        result = await db.execute(query)
        posts = list(result.scalars().all())

        has_more = len(posts) > limit
        if has_more:
            posts = posts[:limit]

        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = encode_cursor(last_post.created_at, last_post.id)

        if not posts:
            return FeedResponse(items=[], next_cursor=None, has_more=False)

        post_ids = [p.id for p in posts]

        # Batch count likes
        likes_counts_query = (
            select(Like.post_id, func.count(Like.id))
            .where(Like.post_id.in_(post_ids))
            .group_by(Like.post_id)
        )
        likes_counts_res = await db.execute(likes_counts_query)
        likes_map = dict(likes_counts_res.all())

        # Batch count comments
        comments_counts_query = (
            select(Comment.post_id, func.count(Comment.id))
            .where(Comment.post_id.in_(post_ids), Comment.is_hidden.is_(False))
            .group_by(Comment.post_id)
        )
        comments_counts_res = await db.execute(comments_counts_query)
        comments_map = dict(comments_counts_res.all())

        # Batch check viewer liked
        user_liked_set: set[uuid.UUID] = set()
        if current_user:
            user_liked_query = select(Like.post_id).where(
                Like.post_id.in_(post_ids),
                Like.user_id == current_user.id,
            )
            user_liked_res = await db.execute(user_liked_query)
            user_liked_set = set(user_liked_res.scalars().all())

        # Build responses
        items: list[PostResponse] = []
        for post in posts:
            author_summary = AuthorSummary(
                id=post.author.id,
                username=post.author.username,
                display_name=post.author.display_name,
                avatar_url=post.author.avatar_url,
            )
            items.append(
                PostResponse(
                    id=post.id,
                    author_id=post.author_id,
                    author=author_summary,
                    content=post.content,
                    image_url=post.image_url,
                    is_hidden=post.is_hidden,
                    is_edited=post.is_edited,
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                    likes_count=likes_map.get(post.id, 0),
                    comments_count=comments_map.get(post.id, 0),
                    has_liked=post.id in user_liked_set,
                )
            )

        return FeedResponse(items=items, next_cursor=next_cursor, has_more=has_more)

    @staticmethod
    async def toggle_like(
        db: AsyncSession,
        post_id: uuid.UUID,
        user: User,
    ) -> tuple[bool, int]:
        """
        Toggle like on a post.
        Creates a persistent notification for post author if liked and author != user.
        Returns (liked, current_total_likes).
        """
        # Fetch post
        post_query = select(Post).where(Post.id == post_id)
        result = await db.execute(post_query)
        post = result.scalar_one_or_none()

        if not post or post.is_hidden:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found.",
            )

        # Check existing like
        like_query = select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
        existing_like = (await db.execute(like_query)).scalar_one_or_none()

        if existing_like:
            await db.delete(existing_like)
            liked = False
        else:
            new_like = Like(user_id=user.id, post_id=post_id)
            db.add(new_like)
            await db.commit()
            liked = True

            # Trigger notification if liker is not the author
            if post.author_id != user.id:
                await notification_service.create_and_push_notification(
                    db=db,
                    user_id=post.author_id,
                    type="like",
                    payload={
                        "post_id": str(post.id),
                        "liker_id": str(user.id),
                        "liker_username": user.username,
                        "liker_name": user.display_name,
                    },
                )

        await db.commit()

        # Count new likes
        count_query = select(func.count(Like.id)).where(Like.post_id == post_id)
        total_likes = (await db.execute(count_query)).scalar() or 0

        return liked, total_likes


post_service = PostService()
