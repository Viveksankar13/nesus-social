"""
User Service
============
Handles profile viewing, profile editing, and password changes.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.like import Like
from app.models.post import Post
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserUpdate


class UserService:
    """Service handling user profile and account operations."""

    @staticmethod
    async def get_user_profile(db: AsyncSession, identifier: str) -> UserProfileResponse:
        """
        Fetch a user profile by UUID or by username.
        Includes activity metrics (posts count and total likes received).
        """
        user_uuid: uuid.UUID | None = None
        try:
            user_uuid = uuid.UUID(identifier)
        except ValueError:
            user_uuid = None

        if user_uuid:
            query = select(User).where(User.id == user_uuid)
        else:
            query = select(User).where(
                (func.lower(User.username) == identifier.lower())
                | (User.usn == identifier.upper())
            )

        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{identifier}' not found.",
            )

        if user.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account is suspended.",
            )

        # Count active posts
        posts_count_query = select(func.count(Post.id)).where(
            Post.author_id == user.id,
            Post.is_hidden.is_(False),
        )
        posts_count = (await db.execute(posts_count_query)).scalar() or 0

        # Count likes received across all user's active posts
        likes_count_query = (
            select(func.count(Like.id))
            .join(Post, Like.post_id == Post.id)
            .where(
                Post.author_id == user.id,
                Post.is_hidden.is_(False),
            )
        )
        likes_count = (await db.execute(likes_count_query)).scalar() or 0

        return UserProfileResponse(
            id=user.id,
            username=user.username,
            usn=user.usn,
            display_name=user.display_name,
            bio=user.bio,
            location=user.location,
            website=user.website,
            avatar_url=user.avatar_url,
            role=user.role,
            created_at=user.created_at,
            posts_count=posts_count,
            likes_received_count=likes_count,
        )

    @staticmethod
    async def update_profile(db: AsyncSession, user: User, data: UserUpdate) -> User:
        """Update profile fields for the authenticated user."""
        if data.display_name is not None:
            user.display_name = data.display_name
        if data.usn is not None:
            clean_usn = data.usn.strip().upper() if data.usn else None
            if clean_usn and clean_usn != user.usn:
                existing = await db.execute(
                    select(User).where(User.usn == clean_usn, User.id != user.id)
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Student USN is already assigned to another account.",
                    )
            user.usn = clean_usn
        if data.bio is not None:
            user.bio = data.bio
        if data.location is not None:
            user.location = data.location
        if data.website is not None:
            user.website = data.website
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change user password, verifying current password first.
        Revokes all active refresh tokens for the user upon success.
        """
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password.",
            )

        user.hashed_password = hash_password(new_password)

        # Revoke all active refresh tokens for security
        await db.execute(
            update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
        )

        await db.commit()


user_service = UserService()
