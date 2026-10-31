"""
Media API Router
================
Endpoints for uploading feed images and user profile pictures.
Protected by require_user dependency.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.media_service import media_service

router = APIRouter(prefix="/media", tags=["Media"])


class ImageUploadResponse(BaseModel):
    """Details of an uploaded image."""

    url: str
    filename: str
    width: int
    height: int
    content_type: str


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for feed posts or chat",
)
async def upload_image(
    _: Annotated[User, Depends(require_user)],
    file: Annotated[UploadFile, File(description="Image file to upload (JPEG, PNG, WebP, GIF)")],
    folder: Annotated[str, Form(description="Target folder ('posts' or 'avatars')")] = "posts",
) -> ImageUploadResponse:
    """Upload and sanitize an image file, stripping EXIF and optimizing size."""
    safe_folder = "avatars" if folder == "avatars" else "posts"
    result = await media_service.save_image(file=file, folder=safe_folder)
    return ImageUploadResponse(**result)


@router.post(
    "/avatar",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and set current user avatar",
)
async def upload_avatar(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Avatar image file to upload")],
) -> UserResponse:
    """Upload new avatar image, optimize, and update user's profile."""
    result = await media_service.save_image(file=file, folder="avatars", max_dimension=800)
    current_user.avatar_url = str(result["url"])
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
