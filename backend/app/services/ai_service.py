"""
AI Service Orchestrator
=======================
Coordinates high-level AI operations, daily quota checks,
telemetry logging into ai_usage_logs, session persistence, and error handling.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.ai import AIChatMessage, AIChatSession, AIUsageLog
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.schemas.ai import (
    AIQuotaStatus,
    PostGenerateRequest,
    PostGenerateResponse,
    PostSummarizeResponse,
    SmartRepliesResponse,
)
from app.services.ai import get_ai_service

logger = logging.getLogger("nexus.ai.service")


class AIServiceOrchestrator:
    """High-level AI operations orchestrator."""

    async def get_quota_status(self, db: AsyncSession, user_id: uuid.UUID) -> AIQuotaStatus:
        """Calculate user's AI quota consumption in the last 24 hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        stmt = select(func.count(AIUsageLog.id)).where(
            AIUsageLog.user_id == user_id,
            AIUsageLog.created_at >= cutoff,
            AIUsageLog.status == "success",
        )
        result = await db.execute(stmt)
        used_today = result.scalar_one() or 0
        remaining = max(0, settings.AI_DAILY_QUOTA - used_today)
        return AIQuotaStatus(
            used_today=used_today,
            daily_quota=settings.AI_DAILY_QUOTA,
            remaining_today=remaining,
        )

    async def check_daily_quota(self, db: AsyncSession, user_id: uuid.UUID) -> tuple[int, int]:
        """Check user daily quota and raise 429 if exceeded."""
        status_info = await self.get_quota_status(db=db, user_id=user_id)
        if status_info.used_today >= status_info.daily_quota:
            msg = (
                f"Daily AI quota exceeded ({status_info.daily_quota} requests/day). "
                "Resets in 24 hours."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=msg,
            )
        return status_info.used_today, status_info.remaining_today

    async def record_usage(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        feature: str,
        latency_ms: int,
        tokens_used: int,
        status_val: str,
        error: str | None = None,
    ) -> AIUsageLog:
        """Record an entry in the AI usage audit log."""
        log = AIUsageLog(
            user_id=user_id,
            feature=feature,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            status=status_val,
            error=error,
        )
        db.add(log)
        await db.commit()
        return log

    # ── Feature 1: Post Generation ───────────────────────────────────

    async def generate_post(
        self,
        db: AsyncSession,
        user: User,
        data: PostGenerateRequest,
    ) -> PostGenerateResponse:
        """Generate 3 post variants based on user prompt or draft."""
        await self.check_daily_quota(db=db, user_id=user.id)
        start_time = time.perf_counter()
        ai_service = get_ai_service()

        try:
            variants, tokens = await ai_service.generate_post(
                topic=data.topic,
                draft=data.draft,
                tone=data.tone,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="post_generate",
                latency_ms=elapsed_ms,
                tokens_used=tokens,
                status_val="success",
            )
            return PostGenerateResponse(variants=variants)

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="post_generate",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status_val="error",
                error=str(e),
            )
            logger.error("AI post generation failed for user %s: %s", user.id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI post generation service encountered an unexpected error. Please retry.",
            ) from e

    # ── Feature 2: Post Summarization ────────────────────────────────

    async def summarize_post(
        self,
        db: AsyncSession,
        user: User,
        post_id: uuid.UUID,
    ) -> PostSummarizeResponse:
        """Summarize a post and its comments thread (minimum 3 comments required)."""
        await self.check_daily_quota(db=db, user_id=user.id)

        # 1. Fetch post
        post_stmt = select(Post).where(Post.id == post_id, Post.is_hidden.is_(False))
        post_res = await db.execute(post_stmt)
        post = post_res.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        # 2. Fetch comments
        comments_res = await db.execute(
            select(Comment.content)
            .where(Comment.post_id == post_id, Comment.is_hidden.is_(False))
            .order_by(Comment.created_at.asc())
        )
        comments = list(comments_res.scalars().all())

        # Strict requirement: minimum 3 comments
        if len(comments) < 3:
            msg = (
                f"Post must have at least 3 comments to generate an AI summary "
                f"(currently has {len(comments)})."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

        start_time = time.perf_counter()
        ai_service = get_ai_service()

        try:
            summary_dict, tokens = await ai_service.summarize_post(
                post_content=post.content,
                comments=comments,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="summarize",
                latency_ms=elapsed_ms,
                tokens_used=tokens,
                status_val="success",
            )

            return PostSummarizeResponse(
                summary=summary_dict.get("summary", ""),
                key_points=summary_dict.get("key_points", []),
                sentiment=summary_dict.get("sentiment", "neutral"),
            )

        except HTTPException:
            raise
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="summarize",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status_val="error",
                error=str(e),
            )
            logger.error("AI post summarization failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI summarization service encountered an error.",
            ) from e

    # ── Feature 3: Smart Replies ─────────────────────────────────────

    async def get_smart_replies(
        self,
        db: AsyncSession,
        user: User,
        post_id: uuid.UUID,
        comment_id: uuid.UUID | None = None,
    ) -> SmartRepliesResponse:
        """Generate 3 contextual quick-reply options."""
        await self.check_daily_quota(db=db, user_id=user.id)

        # 1. Fetch post
        post_stmt = select(Post).where(Post.id == post_id, Post.is_hidden.is_(False))
        post_res = await db.execute(post_stmt)
        post = post_res.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        parent_comment_text: str | None = None
        if comment_id:
            comm_res = await db.execute(
                select(Comment).where(
                    Comment.id == comment_id,
                    Comment.post_id == post_id,
                    Comment.is_hidden.is_(False),
                )
            )
            comment = comm_res.scalar_one_or_none()
            if not comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found on this post",
                )
            parent_comment_text = comment.content

        start_time = time.perf_counter()
        ai_service = get_ai_service()

        try:
            replies, tokens = await ai_service.smart_replies(
                post_content=post.content,
                parent_comment=parent_comment_text,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="smart_replies",
                latency_ms=elapsed_ms,
                tokens_used=tokens,
                status_val="success",
            )
            return SmartRepliesResponse(replies=replies)

        except HTTPException:
            raise
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="smart_replies",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status_val="error",
                error=str(e),
            )
            logger.error("AI smart replies failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI smart replies service encountered an error.",
            ) from e

    # ── Feature 4: Conversational Assistant (Sessions & Messages) ────

    async def create_chat_session(
        self,
        db: AsyncSession,
        user: User,
        title: str | None = None,
    ) -> AIChatSession:
        """Create a new conversational AI chat session."""
        session_title = title.strip() if title and title.strip() else "New Conversation"
        chat_session = AIChatSession(
            user_id=user.id,
            title=session_title,
        )
        db.add(chat_session)
        await db.commit()
        await db.refresh(chat_session)
        return chat_session

    async def list_chat_sessions(
        self,
        db: AsyncSession,
        user: User,
    ) -> list[AIChatSession]:
        """List all chat sessions for the authenticated user."""
        stmt = (
            select(AIChatSession)
            .where(AIChatSession.user_id == user.id)
            .order_by(AIChatSession.updated_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_chat_session(
        self,
        db: AsyncSession,
        user: User,
        session_id: uuid.UUID,
    ) -> AIChatSession:
        """Retrieve a specific chat session with historical messages."""
        stmt = (
            select(AIChatSession)
            .options(selectinload(AIChatSession.messages))
            .where(AIChatSession.id == session_id, AIChatSession.user_id == user.id)
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )
        return session

    async def delete_chat_session(
        self,
        db: AsyncSession,
        user: User,
        session_id: uuid.UUID,
    ) -> None:
        """Delete an AI chat session and cascade messages."""
        session = await self.get_chat_session(db=db, user=user, session_id=session_id)
        await db.delete(session)
        await db.commit()

    async def send_chat_message(
        self,
        db: AsyncSession,
        user: User,
        session_id: uuid.UUID,
        message_text: str,
    ) -> AIChatMessage:
        """Send a message to the AI assistant in non-streaming mode."""
        await self.check_daily_quota(db=db, user_id=user.id)
        chat_session = await self.get_chat_session(db=db, user=user, session_id=session_id)

        # Build context history
        history = [{"role": m.role, "content": m.content} for m in chat_session.messages[-20:]]
        history.append({"role": "user", "content": message_text})

        # Save user message
        user_msg = AIChatMessage(
            session_id=chat_session.id,
            role="user",
            content=message_text,
        )
        db.add(user_msg)

        start_time = time.perf_counter()
        ai_service = get_ai_service()

        try:
            reply_text, tokens = await ai_service.chat(messages=history)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Save model message
            model_msg = AIChatMessage(
                session_id=chat_session.id,
                role="model",
                content=reply_text,
            )
            db.add(model_msg)

            # Auto-title session if it has default title
            if chat_session.title == "New Conversation":
                chat_session.title = message_text[:40] + ("..." if len(message_text) > 40 else "")

            chat_session.updated_at = datetime.now(UTC)

            # Log usage
            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="chat",
                latency_ms=elapsed_ms,
                tokens_used=tokens,
                status_val="success",
            )

            await db.commit()
            await db.refresh(model_msg)
            return model_msg

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            await self.record_usage(
                db=db,
                user_id=user.id,
                feature="chat",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status_val="error",
                error=str(e),
            )
            logger.error("AI chat message failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI chat assistant encountered an error.",
            ) from e

    async def stream_chat_message(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        message_text: str,
    ) -> AsyncIterator[str]:
        """
        Stream conversational assistant reply chunks via Server-Sent Events.
        Persists message history upon completion.
        """
        # 1. Fetch user & session
        stmt = (
            select(AIChatSession)
            .options(selectinload(AIChatSession.messages))
            .where(AIChatSession.id == session_id, AIChatSession.user_id == user_id)
        )
        res = await db.execute(stmt)
        chat_session = res.scalar_one_or_none()
        if not chat_session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # Quota check
        status_info = await self.get_quota_status(db=db, user_id=user_id)
        if status_info.used_today >= status_info.daily_quota:
            yield f"data: {json.dumps({'error': 'Daily quota exceeded'})}\n\n"
            return

        # Add user message
        user_msg = AIChatMessage(
            session_id=chat_session.id,
            role="user",
            content=message_text,
        )
        db.add(user_msg)
        await db.commit()

        history = [{"role": m.role, "content": m.content} for m in chat_session.messages[-20:]]
        history.append({"role": "user", "content": message_text})

        # 2. Stream generation
        ai_service = get_ai_service()
        start_time = time.perf_counter()
        accumulated_chunks: list[str] = []

        try:
            async for chunk in ai_service.chat_stream(messages=history):
                accumulated_chunks.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            full_reply = "".join(accumulated_chunks)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # 3. Persist model message and telemetry
            model_msg = AIChatMessage(
                session_id=session_id,
                role="model",
                content=full_reply,
            )
            db.add(model_msg)

            # Re-fetch session to update title/timestamp
            sess_res = await db.execute(select(AIChatSession).where(AIChatSession.id == session_id))
            live_sess = sess_res.scalar_one_or_none()
            if live_sess:
                if live_sess.title == "New Conversation":
                    live_sess.title = message_text[:40] + ("..." if len(message_text) > 40 else "")
                live_sess.updated_at = datetime.now(UTC)

            # Log usage
            usage = AIUsageLog(
                user_id=user_id,
                feature="chat",
                latency_ms=elapsed_ms,
                tokens_used=len(full_reply) // 4,
                status="success",
                error=None,
            )
            db.add(usage)
            await db.commit()

            yield "data: [DONE]\n\n"

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Chat streaming failed: %s", e)
            usage = AIUsageLog(
                user_id=user_id,
                feature="chat",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status="error",
                error=str(e),
            )
            db.add(usage)
            await db.commit()

            yield f"data: {json.dumps({'error': str(e)})}\n\n"


# Singleton instance
ai_orchestrator = AIServiceOrchestrator()
