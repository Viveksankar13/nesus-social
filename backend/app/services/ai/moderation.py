"""
Background Content Moderation Worker
====================================
Evaluates posts and comments asynchronously against safety policies.
Writes flags to moderation_flags and auto-hides severe content.
Handles fail-open vs fail-closed according to settings.
"""

import logging
import time
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.ai import AIUsageLog
from app.models.comment import Comment
from app.models.moderation import ModerationFlag
from app.models.post import Post
from app.services.ai import get_ai_service

logger = logging.getLogger("nexus.ai.moderation")


async def moderate_content_task(
    content_type: str,
    content_id: uuid.UUID,
    text: str,
    user_id: uuid.UUID,
    session: AsyncSession | None = None,
) -> None:
    """
    Background worker task to check content for safety and spam.
    Runs in the provided session or spins up a fresh session from factory.
    """
    start_time = time.perf_counter()
    ai_service = get_ai_service()

    async def _execute(db: AsyncSession) -> None:
        try:
            result, tokens = await ai_service.moderate_content(content_type=content_type, text=text)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            action = result.get("action", "allow")
            severity = result.get("severity", "low")
            category = result.get("category", "other")
            score = float(result.get("score", 0.0))
            reason = result.get("reason", "Automated scan")

            # Record flag if flagged or blocked
            if action in ("flag", "block"):
                flag = ModerationFlag(
                    content_type=content_type,
                    content_id=content_id,
                    category=category,
                    severity=severity,
                    score=score,
                    action=action,
                    reason=reason,
                    reviewed=False,
                )
                db.add(flag)

                # Auto-hide content if blocked
                if action == "block":
                    if content_type == "post":
                        await db.execute(
                            update(Post).where(Post.id == content_id).values(is_hidden=True)
                        )
                    elif content_type == "comment":
                        await db.execute(
                            update(Comment).where(Comment.id == content_id).values(is_hidden=True)
                        )
                    logger.info(
                        "Auto-hid %s %s due to critical violation: %s (%s)",
                        content_type,
                        content_id,
                        category,
                        reason,
                    )

            # Record AI usage telemetry
            usage = AIUsageLog(
                user_id=user_id,
                feature="moderation",
                latency_ms=elapsed_ms,
                tokens_used=tokens,
                status="success",
                error=None,
            )
            db.add(usage)
            await db.commit()

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(
                "Content moderation task failed for %s %s: %s", content_type, content_id, e
            )

            # Check fail-mode
            if settings.MODERATION_FAIL_MODE == "closed":
                logger.warning(
                    "MODERATION_FAIL_MODE is closed. Flagging %s %s for manual review.",
                    content_type,
                    content_id,
                )
                flag = ModerationFlag(
                    content_type=content_type,
                    content_id=content_id,
                    category="other",
                    severity="medium",
                    score=0.5,
                    action="flag",
                    reason=f"Flagged due to moderation system error (fail-closed): {e}",
                    reviewed=False,
                )
                db.add(flag)

            # Record error in usage log
            usage = AIUsageLog(
                user_id=user_id,
                feature="moderation",
                latency_ms=elapsed_ms,
                tokens_used=0,
                status="error",
                error=str(e),
            )
            db.add(usage)
            try:
                await db.commit()
            except Exception as commit_err:
                logger.error("Failed to commit moderation error log: %s", commit_err)

    if session is not None:
        await _execute(session)
    else:
        async with async_session_factory() as db:
            await _execute(db)
