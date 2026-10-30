"""
AI Router
=========
FastAPI v1 router exposing all 5 Google Gemini AI capabilities:
1. POST /api/v1/ai/generate-post: 3 post variants + tone
2. POST /api/v1/ai/summarize: Post + comment thread summary & sentiment
3. POST /api/v1/ai/smart-replies: 3 contextual reply suggestions
4. Conversational assistant sessions & messages (standard + SSE streaming)
5. GET /api/v1/ai/quota: Daily quota consumption status
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    AIChatMessageRequest,
    AIChatMessageResponse,
    AIChatSessionCreate,
    AIChatSessionDetailResponse,
    AIChatSessionResponse,
    AIQuotaStatus,
    PostGenerateRequest,
    PostGenerateResponse,
    PostSummarizeRequest,
    PostSummarizeResponse,
    SmartRepliesRequest,
    SmartRepliesResponse,
)
from app.services.ai_service import ai_orchestrator

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/quota", response_model=AIQuotaStatus)
async def get_ai_quota(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIQuotaStatus:
    """Check current user's daily AI quota consumption and remaining allowance."""
    return await ai_orchestrator.get_quota_status(db=db, user_id=current_user.id)


@router.post("/generate-post", response_model=PostGenerateResponse)
@limiter.limit(settings.RATE_LIMIT_AI)
async def generate_post(
    request: Request,
    response: Response,
    data: PostGenerateRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostGenerateResponse:
    """Generate or refine 3 social media post variants based on topic or draft."""
    return await ai_orchestrator.generate_post(db=db, user=current_user, data=data)


@router.post("/summarize", response_model=PostSummarizeResponse)
@limiter.limit(settings.RATE_LIMIT_AI)
async def summarize_post(
    request: Request,
    response: Response,
    data: PostSummarizeRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostSummarizeResponse:
    """
    Summarize a post thread and evaluate audience sentiment.
    Strictly requires at least 3 comments.
    """
    return await ai_orchestrator.summarize_post(db=db, user=current_user, post_id=data.post_id)


@router.post("/smart-replies", response_model=SmartRepliesResponse)
@limiter.limit(settings.RATE_LIMIT_AI)
async def get_smart_replies(
    request: Request,
    response: Response,
    data: SmartRepliesRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SmartRepliesResponse:
    """Generate 3 short, contextual quick reply options for a post or comment thread."""
    return await ai_orchestrator.get_smart_replies(
        db=db,
        user=current_user,
        post_id=data.post_id,
        comment_id=data.comment_id,
    )


# ── Conversational Assistant ─────────────────────────────────────────


@router.get("/chat/sessions", response_model=list[AIChatSessionResponse])
async def list_chat_sessions(
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIChatSessionResponse]:
    """List all AI chat sessions for the authenticated user."""
    sessions = await ai_orchestrator.list_chat_sessions(db=db, user=current_user)
    return [AIChatSessionResponse.model_validate(s) for s in sessions]


@router.post(
    "/chat/sessions",
    response_model=AIChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_session(
    data: AIChatSessionCreate,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIChatSessionResponse:
    """Create a new conversational AI chat session."""
    session = await ai_orchestrator.create_chat_session(db=db, user=current_user, title=data.title)
    return AIChatSessionResponse.model_validate(session)


@router.get("/chat/sessions/{session_id}", response_model=AIChatSessionDetailResponse)
async def get_chat_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIChatSessionDetailResponse:
    """Retrieve an AI chat session and its complete message history."""
    session = await ai_orchestrator.get_chat_session(
        db=db, user=current_user, session_id=session_id
    )
    return AIChatSessionDetailResponse.model_validate(session)


@router.delete("/chat/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an AI chat session and cascade all contained messages."""
    await ai_orchestrator.delete_chat_session(db=db, user=current_user, session_id=session_id)


@router.post("/chat/message", response_model=None)
@limiter.limit(settings.RATE_LIMIT_AI)
async def send_chat_message(
    request: Request,
    response: Response,
    data: AIChatMessageRequest,
    current_user: Annotated[User, Depends(require_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse | AIChatMessageResponse:
    """
    Send a message to the AI assistant.
    If stream=True: returns text/event-stream Server-Sent Events.
    If stream=False: returns AIChatMessageResponse directly.
    """
    if data.stream:
        return StreamingResponse(
            ai_orchestrator.stream_chat_message(
                db=db,
                user_id=current_user.id,
                session_id=data.session_id,
                message_text=data.message,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    model_msg = await ai_orchestrator.send_chat_message(
        db=db,
        user=current_user,
        session_id=data.session_id,
        message_text=data.message,
    )
    return AIChatMessageResponse.model_validate(model_msg)
