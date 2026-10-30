"""
Posts and Interactions Router
==============================
Endpoints for creating, reading, editing, and deleting posts,
toggling likes, and adding comments.
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user, require_user
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse
from app.schemas.post import FeedResponse, LikeResponse, PostCreate, PostResponse, PostUpdate
from app.services.comment_service import comment_service
from app.services.post_service import post_service

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("", response_model=FeedResponse)
async def list_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    cursor: Annotated[str | None, Query(description="Keyset cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Items per page")] = 20,
    feed_type: Annotated[Literal["all", "mine"], Query(description="Feed category")] = "all",
) -> FeedResponse:
    """
    Retrieve keyset cursor-paginated post feed.
    - 'all': platform-wide public posts
    - 'mine': posts authored by the authenticated user
    """
    return await post_service.get_feed(
        db=db,
        current_user=current_user,
        cursor=cursor,
        limit=limit,
        feed_type=feed_type,
    )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostCreate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """Create a new post (max 1000 characters with optional image URL)."""
    return await post_service.create_post(db=db, author=current_user, data=data)


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
) -> PostResponse:
    """Retrieve a single post by UUID."""
    return await post_service.get_post_by_id(db=db, post_id=post_id, current_user=current_user)


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    data: PostUpdate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostResponse:
    """Edit an existing post. Only the author or an admin may perform edits."""
    return await post_service.update_post(db=db, post_id=post_id, user=current_user, data=data)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a post. Cascades to all associated likes and comments."""
    await post_service.delete_post(db=db, post_id=post_id, user=current_user)


@router.post("/{post_id}/like", response_model=LikeResponse)
async def toggle_like(
    post_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LikeResponse:
    """Toggle like on a post. Returns whether liked and updated like count."""
    liked, total_likes = await post_service.toggle_like(db=db, post_id=post_id, user=current_user)
    return LikeResponse(liked=liked, likes_count=total_likes, post_id=post_id)


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    post_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CommentResponse]:
    """Retrieve threaded comments for a post with 1-level nested replies."""
    return await comment_service.get_post_comments(db=db, post_id=post_id)


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: uuid.UUID,
    data: CommentCreate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    """Add a top-level comment or reply to an existing comment (1-level maximum)."""
    return await comment_service.create_comment(
        db=db,
        post_id=post_id,
        author=current_user,
        data=data,
    )
