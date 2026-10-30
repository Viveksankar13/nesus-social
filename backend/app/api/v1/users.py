"""
User Profile Router
===================
Endpoints for retrieving and editing profiles, changing passwords,
and fetching user post feeds.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_optional_current_user, require_user
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, MessageResponse
from app.schemas.post import FeedResponse
from app.schemas.user import UserProfileResponse, UserResponse, UserUpdate
from app.services.post_service import post_service
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(require_user)],
) -> User:
    """Retrieve full account and profile details for the authenticated user."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Update profile bio, location, website, avatar URL, or display name."""
    return await user_service.update_profile(db=db, user=current_user, data=data)


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Change account password. Revokes all active refresh tokens on completion."""
    await user_service.change_password(
        db=db,
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    return MessageResponse(
        message="Password changed successfully. Please log in with your new password."
    )


@router.get("/{identifier}", response_model=UserProfileResponse)
async def get_user_profile(
    identifier: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """
    Retrieve public profile by username or user UUID.
    Includes active post counts and total likes received.
    """
    return await user_service.get_user_profile(db=db, identifier=identifier)


@router.get("/{username}/posts", response_model=FeedResponse)
async def get_user_posts(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    cursor: Annotated[str | None, Query(description="Keyset cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Items per page")] = 20,
) -> FeedResponse:
    """Retrieve paginated posts authored by a specific user."""
    profile = await user_service.get_user_profile(db=db, identifier=username)
    return await post_service.get_feed(
        db=db,
        current_user=current_user,
        cursor=cursor,
        limit=limit,
        author_id=profile.id,
    )
