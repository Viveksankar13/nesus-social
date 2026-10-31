"""
Friends Router
==============
Endpoints for sending, accepting, rejecting, listing friends, and checking status.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.models.friendship import Friendship
from app.models.message import Conversation
from app.models.notification import Notification
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.friendship import (
    FriendRequestResponse,
    FriendshipStatusResponse,
    FriendUserResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.get("/status/{target_user_id}", response_model=FriendshipStatusResponse)
async def get_friendship_status(
    target_user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FriendshipStatusResponse:
    """Check friendship relationship between current user and target user."""
    if target_user_id == current_user.id:
        return FriendshipStatusResponse(
            target_user_id=target_user_id,
            status="none",
        )

    stmt = select(Friendship).where(
        or_(
            (Friendship.sender_id == current_user.id) & (Friendship.receiver_id == target_user_id),
            (Friendship.sender_id == target_user_id) & (Friendship.receiver_id == current_user.id),
        )
    )
    res = await db.execute(stmt)
    rel = res.scalar_one_or_none()

    if not rel:
        return FriendshipStatusResponse(target_user_id=target_user_id, status="none")

    if rel.status == "accepted":
        return FriendshipStatusResponse(
            target_user_id=target_user_id,
            status="friends",
            friendship_id=rel.id,
        )

    if rel.status == "pending":
        if rel.sender_id == current_user.id:
            return FriendshipStatusResponse(
                target_user_id=target_user_id,
                status="pending_sent",
                friendship_id=rel.id,
            )
        else:
            return FriendshipStatusResponse(
                target_user_id=target_user_id,
                status="pending_received",
                friendship_id=rel.id,
            )

    return FriendshipStatusResponse(target_user_id=target_user_id, status="none")


@router.post("/request/{target_user_id}", response_model=MessageResponse)
async def send_friend_request(
    target_user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Send a friend request to another user."""
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot send a friend request to yourself.",
        )

    # Check target exists
    target = await db.get(User, target_user_id)
    if not target or target.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    # Check existing relationship
    stmt = select(Friendship).where(
        or_(
            (Friendship.sender_id == current_user.id) & (Friendship.receiver_id == target_user_id),
            (Friendship.sender_id == target_user_id) & (Friendship.receiver_id == current_user.id),
        )
    )
    res = await db.execute(stmt)
    rel = res.scalar_one_or_none()

    if rel:
        if rel.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already friends with this user.",
            )
        if rel.status == "pending":
            if rel.sender_id == current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Friend request is already pending.",
                )
            else:
                # If they sent you one, accept it!
                rel.status = "accepted"
                await db.commit()
                return MessageResponse(message="Friend request accepted automatically!")
        if rel.status == "rejected":
            rel.sender_id = current_user.id
            rel.receiver_id = target_user_id
            rel.status = "pending"
    else:
        rel = Friendship(
            id=uuid.uuid4(),
            sender_id=current_user.id,
            receiver_id=target_user_id,
            status="pending",
        )
        db.add(rel)

    # Send Notification to target
    notif = Notification(
        id=uuid.uuid4(),
        user_id=target_user_id,
        type="friend_request",
        payload={
            "sender_id": str(current_user.id),
            "sender_name": current_user.display_name,
            "sender_username": current_user.username,
            "sender_avatar": current_user.avatar_url,
            "message": f"{current_user.display_name} sent you a friend request.",
        },
    )
    db.add(notif)
    await db.commit()

    return MessageResponse(message="Friend request sent successfully.")


@router.post("/accept/{request_id}", response_model=MessageResponse)
async def accept_friend_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Accept an incoming friend request."""
    rel = await db.get(Friendship, request_id)
    if not rel or rel.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found.",
        )

    if rel.status == "accepted":
        return MessageResponse(message="Already friends.")

    rel.status = "accepted"

    # Pre-create or find conversation so direct messaging is ready
    u1, u2 = sorted([str(rel.sender_id), str(rel.receiver_id)])
    conv_stmt = select(Conversation).where(
        (Conversation.user1_id == uuid.UUID(u1)) & (Conversation.user2_id == uuid.UUID(u2))
    )
    conv_res = await db.execute(conv_stmt)
    if not conv_res.scalar_one_or_none():
        conv = Conversation(
            id=uuid.uuid4(),
            user1_id=uuid.UUID(u1),
            user2_id=uuid.UUID(u2),
        )
        db.add(conv)

    # Notification to sender
    notif = Notification(
        id=uuid.uuid4(),
        user_id=rel.sender_id,
        type="friend_accepted",
        payload={
            "user_id": str(current_user.id),
            "user_name": current_user.display_name,
            "user_username": current_user.username,
            "user_avatar": current_user.avatar_url,
            "message": f"{current_user.display_name} accepted your friend request!",
        },
    )
    db.add(notif)
    await db.commit()

    return MessageResponse(message="Friend request accepted.")


@router.post("/reject/{request_id}", response_model=MessageResponse)
async def reject_friend_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Decline an incoming friend request."""
    rel = await db.get(Friendship, request_id)
    if not rel or rel.receiver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found.",
        )

    rel.status = "rejected"
    await db.commit()
    return MessageResponse(message="Friend request rejected.")


@router.delete("/{target_user_id}", response_model=MessageResponse)
async def remove_friend(
    target_user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Unfriend or cancel a friend request."""
    stmt = select(Friendship).where(
        or_(
            (Friendship.sender_id == current_user.id) & (Friendship.receiver_id == target_user_id),
            (Friendship.sender_id == target_user_id) & (Friendship.receiver_id == current_user.id),
        )
    )
    res = await db.execute(stmt)
    rel = res.scalar_one_or_none()

    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No friendship relationship found.",
        )

    await db.delete(rel)
    await db.commit()
    return MessageResponse(message="Friend removed successfully.")


@router.get("", response_model=list[FriendUserResponse])
@router.get("/", include_in_schema=False, response_model=list[FriendUserResponse])
async def list_friends(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FriendUserResponse]:
    """List all accepted friends of the authenticated user."""
    stmt = (
        select(Friendship)
        .where(
            (Friendship.status == "accepted")
            & (
                (Friendship.sender_id == current_user.id)
                | (Friendship.receiver_id == current_user.id)
            )
        )
        .order_by(Friendship.updated_at.desc())
    )
    res = await db.execute(stmt)
    friendships = res.scalars().all()

    results = []
    for f in friendships:
        friend_user = f.receiver if f.sender_id == current_user.id else f.sender
        results.append(
            FriendUserResponse(
                friendship_id=f.id,
                friend=UserResponse.model_validate(friend_user),
                since=f.updated_at,
            )
        )
    return results


@router.get("/requests", response_model=dict[str, list[FriendRequestResponse]])
async def list_friend_requests(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, list[FriendRequestResponse]]:
    """List pending incoming and outgoing friend requests."""
    incoming_stmt = (
        select(Friendship)
        .where((Friendship.receiver_id == current_user.id) & (Friendship.status == "pending"))
        .order_by(Friendship.created_at.desc())
    )
    inc_res = await db.execute(incoming_stmt)
    incoming = inc_res.scalars().all()

    outgoing_stmt = (
        select(Friendship)
        .where((Friendship.sender_id == current_user.id) & (Friendship.status == "pending"))
        .order_by(Friendship.created_at.desc())
    )
    out_res = await db.execute(outgoing_stmt)
    outgoing = out_res.scalars().all()

    return {
        "incoming": [FriendRequestResponse.model_validate(i) for i in incoming],
        "outgoing": [FriendRequestResponse.model_validate(o) for o in outgoing],
    }
