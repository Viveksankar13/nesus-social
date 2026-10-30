"""
Comments Router
===============
Endpoints for editing and deleting existing comments.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.models.user import User
from app.schemas.comment import CommentResponse, CommentUpdate
from app.services.comment_service import comment_service

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: uuid.UUID,
    data: CommentUpdate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentResponse:
    """Edit an existing comment. Only the author or an admin may edit."""
    return await comment_service.update_comment(
        db=db,
        comment_id=comment_id,
        user=current_user,
        data=data,
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a comment. Cascades to any child replies."""
    await comment_service.delete_comment(db=db, comment_id=comment_id, user=current_user)
