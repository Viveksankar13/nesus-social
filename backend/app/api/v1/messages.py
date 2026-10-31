"""
Direct Messages Router
======================
Endpoints for 1-on-1 private messaging between users and friends.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.models.friendship import Friendship
from app.models.message import Conversation, DirectMessage
from app.models.notification import Notification
from app.models.user import User
from app.schemas.message import (
    ConversationResponse,
    DirectMessageResponse,
    SendMessageRequest,
    UnreadMessageCountResponse,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/messages", tags=["Direct Messages"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConversationResponse]:
    """List all private direct message conversations for the current user."""
    stmt = (
        select(Conversation)
        .where(
            or_(
                Conversation.user1_id == current_user.id,
                Conversation.user2_id == current_user.id,
            )
        )
        .order_by(Conversation.updated_at.desc())
    )
    res = await db.execute(stmt)
    conversations = res.scalars().all()

    results = []
    for conv in conversations:
        other_user = conv.user2 if conv.user1_id == current_user.id else conv.user1

        # Query latest message
        msg_stmt = (
            select(DirectMessage)
            .where(DirectMessage.conversation_id == conv.id)
            .order_by(DirectMessage.created_at.desc())
            .limit(1)
        )
        msg_res = await db.execute(msg_stmt)
        last_msg = msg_res.scalar_one_or_none()

        # Query unread count for current user
        unread_stmt = select(func.count(DirectMessage.id)).where(
            DirectMessage.conversation_id == conv.id,
            DirectMessage.sender_id != current_user.id,
            DirectMessage.is_read.is_(False),
        )
        unread_res = await db.execute(unread_stmt)
        unread_count = unread_res.scalar_one() or 0

        results.append(
            ConversationResponse(
                id=conv.id,
                other_user=UserResponse.model_validate(other_user),
                last_message=DirectMessageResponse.model_validate(last_msg) if last_msg else None,
                unread_count=unread_count,
                updated_at=conv.updated_at,
            )
        )

    return results


@router.get("/unread-count", response_model=UnreadMessageCountResponse)
async def get_total_unread_messages(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnreadMessageCountResponse:
    """Get the total count of unread incoming messages across all conversations."""
    conv_stmt = select(Conversation.id).where(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id,
        )
    )
    conv_res = await db.execute(conv_stmt)
    conv_ids = conv_res.scalars().all()

    if not conv_ids:
        return UnreadMessageCountResponse(unread_count=0)

    stmt = select(func.count(DirectMessage.id)).where(
        DirectMessage.conversation_id.in_(conv_ids),
        DirectMessage.sender_id != current_user.id,
        DirectMessage.is_read.is_(False),
    )
    res = await db.execute(stmt)
    total = res.scalar_one() or 0
    return UnreadMessageCountResponse(unread_count=total)


@router.get("/{conversation_id}", response_model=list[DirectMessageResponse])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DirectMessageResponse]:
    """Retrieve full message history for a conversation and mark incoming messages as read."""
    conv = await db.get(Conversation, conversation_id)
    if not conv or (conv.user1_id != current_user.id and conv.user2_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )

    # Mark incoming messages as read
    await db.execute(
        update(DirectMessage)
        .where(
            DirectMessage.conversation_id == conversation_id,
            DirectMessage.sender_id != current_user.id,
            DirectMessage.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()

    # Fetch messages
    stmt = (
        select(DirectMessage)
        .where(DirectMessage.conversation_id == conversation_id)
        .order_by(DirectMessage.created_at.asc())
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()

    return [DirectMessageResponse.model_validate(m) for m in messages]


@router.post("/send", response_model=DirectMessageResponse)
async def send_direct_message(
    req: SendMessageRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DirectMessageResponse:
    """Send a private direct message to a user or friend."""
    if req.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send messages to yourself.",
        )

    receiver = await db.get(User, req.receiver_id)
    if not receiver or receiver.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found or unavailable.",
        )

    # Check friendship status
    friend_stmt = select(Friendship).where(
        (Friendship.status == "accepted")
        & (
            (Friendship.sender_id == current_user.id) & (Friendship.receiver_id == req.receiver_id)
            | (Friendship.sender_id == req.receiver_id)
            & (Friendship.receiver_id == current_user.id)
        )
    )
    friend_res = await db.execute(friend_stmt)
    is_friend = friend_res.scalar_one_or_none() is not None

    if not is_friend:
        # Non-friends: check if target is an admin or allow messaging
        if current_user.role != "admin" and receiver.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be friends with this user to send direct messages.",
            )

    # Find or create conversation
    u1, u2 = sorted([str(current_user.id), str(req.receiver_id)])
    conv_stmt = select(Conversation).where(
        (Conversation.user1_id == uuid.UUID(u1)) & (Conversation.user2_id == uuid.UUID(u2))
    )
    conv_res = await db.execute(conv_stmt)
    conv = conv_res.scalar_one_or_none()

    now = datetime.now(UTC)
    if not conv:
        conv = Conversation(
            id=uuid.uuid4(),
            user1_id=uuid.UUID(u1),
            user2_id=uuid.UUID(u2),
            updated_at=now,
        )
        db.add(conv)
        await db.flush()
    else:
        conv.updated_at = now

    # Create message
    msg = DirectMessage(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        sender_id=current_user.id,
        content=req.content.strip(),
        is_read=False,
        created_at=now,
    )
    db.add(msg)

    # Dispatch notification to recipient
    notif = Notification(
        id=uuid.uuid4(),
        user_id=req.receiver_id,
        type="direct_message",
        payload={
            "sender_id": str(current_user.id),
            "sender_name": current_user.display_name,
            "sender_username": current_user.username,
            "sender_avatar": current_user.avatar_url,
            "conversation_id": str(conv.id),
            "preview": req.content[:80],
        },
    )
    db.add(notif)
    await db.commit()
    await db.refresh(msg)

    return DirectMessageResponse.model_validate(msg)
