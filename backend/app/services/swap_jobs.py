"""
Swap Background Jobs & Secret Cron Runner
=========================================
Idempotent scheduled maintenance tasks for the Skill Swap Economy:
1. auto-expire-requests: Expire pending/countered proposals past 72h.
2. auto-complete-sessions: Mark sessions completed if 2h past scheduled end without dispute.
3. reveal-swap-reviews: Unmask double-blind reviews after 7 calendar days.
4. send-session-reminders: Dispatch 24h and 15m notification & email alerts.

Every execution is audited and logged in the `job_runs` table.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.models.swap import (
    JobRun,
    ReciprocityLedger,
    SwapRequest,
    SwapReview,
    SwapSession,
    TrustScore,
)
from app.services.email_service import EmailService
from app.services.notification_service import notification_service
from app.services.swap_service import parse_utc_datetime

logger = get_logger(__name__)
email_service = EmailService()


class SwapJobsService:
    """Idempotent scheduled maintenance tasks."""

    @staticmethod
    async def run_job(db: AsyncSession, job_name: str) -> dict[str, Any]:
        """Execute a named background job and record its audit trail in `job_runs`."""
        now = datetime.now(UTC)
        job_run = JobRun(
            id=uuid.uuid4(),
            job_name=job_name,
            status="running",
            records_processed=0,
            details={},
            started_at=now,
        )
        db.add(job_run)
        await db.commit()

        try:
            if job_name == "auto-expire-requests":
                res = await SwapJobsService.auto_expire_requests(db)
            elif job_name == "auto-complete-sessions":
                res = await SwapJobsService.auto_complete_sessions(db)
            elif job_name == "reveal-swap-reviews":
                res = await SwapJobsService.reveal_swap_reviews(db)
            elif job_name == "send-session-reminders":
                res = await SwapJobsService.send_session_reminders(db)
            else:
                raise ValueError(f"Unknown job name: {job_name}")

            job_run.status = "success"
            job_run.records_processed = res.get("records_processed", 0)
            job_run.details = res
            job_run.completed_at = datetime.now(UTC)
            await db.commit()
            return res
        except Exception as e:
            logger.error(f"Job {job_name} failed: {e}", exc_info=True)
            job_run.status = "failed"
            job_run.details = {"error": str(e)}
            job_run.completed_at = datetime.now(UTC)
            await db.commit()
            raise

    @staticmethod
    async def auto_expire_requests(db: AsyncSession) -> dict[str, Any]:
        """Expire pending and countered proposals that have exceeded their 72h window."""
        now = datetime.now(UTC)
        stmt = select(SwapRequest).where(
            SwapRequest.status.in_(["pending", "countered"]),
            SwapRequest.expires_at <= now,
        )
        requests = (await db.execute(stmt)).scalars().all()
        count = 0
        for req in requests:
            req.status = "expired"
            req.updated_at = now
            count += 1

        await db.commit()
        return {"job": "auto-expire-requests", "records_processed": count}

    @staticmethod
    async def auto_complete_sessions(db: AsyncSession) -> dict[str, Any]:
        """
        Auto-complete sessions where end time + 2 hours has elapsed with no dispute filed.
        Credits both participants with +30 minutes taught and +30 minutes learned.
        """
        now = datetime.now(UTC)
        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.halves),
            )
            .where(
                SwapSession.status.in_(["scheduled", "active"]),
                SwapSession.dispute_reason.is_(None),
            )
        )
        sessions = (await db.execute(stmt)).scalars().all()
        count = 0

        for sess in sessions:
            if not sess.halves:
                continue

            max_end = max(parse_utc_datetime(h.end_time_utc) for h in sess.halves)
            if max_end + timedelta(hours=2) <= now:
                sess.status = "completed"
                sess.updated_at = now
                for h in sess.halves:
                    h.status = "completed"

                for uid in (sess.user_a_id, sess.user_b_id):
                    # Reciprocity ledger
                    rl = (
                        await db.execute(
                            select(ReciprocityLedger).where(ReciprocityLedger.user_id == uid)
                        )
                    ).scalar_one_or_none()
                    if not rl:
                        rl = ReciprocityLedger(
                            id=uuid.uuid4(),
                            user_id=uid,
                            minutes_taught=0,
                            minutes_learned=0,
                            net_balance_minutes=0,
                            grace_used=0,
                            updated_at=now,
                        )
                        db.add(rl)
                    rl.minutes_taught += settings.SWAP_SESSION_MINUTES
                    rl.minutes_learned += settings.SWAP_SESSION_MINUTES
                    rl.net_balance_minutes = rl.minutes_taught - rl.minutes_learned
                    rl.updated_at = now

                    # Trust score
                    ts = (
                        await db.execute(select(TrustScore).where(TrustScore.user_id == uid))
                    ).scalar_one_or_none()
                    if not ts:
                        ts = TrustScore(
                            id=uuid.uuid4(),
                            user_id=uid,
                            score=100,
                            completed_count=0,
                            no_show_count=0,
                            cancellation_count=0,
                            avg_rating=5.0,
                            badges=[],
                            updated_at=now,
                        )
                        db.add(ts)
                    ts.completed_count += 1
                    ts.updated_at = now

                count += 1

        await db.commit()
        return {"job": "auto-complete-sessions", "records_processed": count}

    @staticmethod
    async def reveal_swap_reviews(db: AsyncSession) -> dict[str, Any]:
        """
        Automatically reveal isolated double-blind reviews after 7 calendar days have passed.
        """
        now = datetime.now(UTC)
        threshold = now - timedelta(days=7)
        stmt = select(SwapReview).where(
            SwapReview.is_revealed.is_(False),
            SwapReview.created_at <= threshold,
        )
        reviews = (await db.execute(stmt)).scalars().all()
        count = 0
        affected_users = set()

        for r in reviews:
            r.is_revealed = True
            r.revealed_at = now
            affected_users.add(r.reviewee_id)
            count += 1

        # Recalculate ratings
        for uid in affected_users:
            avg_val = (
                await db.execute(
                    select(func.avg(SwapReview.rating)).where(
                        SwapReview.reviewee_id == uid,
                        SwapReview.is_revealed.is_(True),
                    )
                )
            ).scalar()
            if avg_val is not None:
                ts = (
                    await db.execute(select(TrustScore).where(TrustScore.user_id == uid))
                ).scalar_one_or_none()
                if ts:
                    ts.avg_rating = round(float(avg_val), 2)
                    ts.updated_at = now

        await db.commit()
        return {"job": "reveal-swap-reviews", "records_processed": count}

    @staticmethod
    async def send_session_reminders(db: AsyncSession) -> dict[str, Any]:
        """
        Send 24-hour and 15-minute reminders for upcoming scheduled sessions.
        """
        now = datetime.now(UTC)
        # 24h window: 23h45m to 24h15m
        w24_start = now + timedelta(hours=23, minutes=45)
        w24_end = now + timedelta(hours=24, minutes=15)

        # 15m window: 10m to 20m
        w15_start = now + timedelta(minutes=10)
        w15_end = now + timedelta(minutes=20)

        stmt = (
            select(SwapSession)
            .options(
                selectinload(SwapSession.user_a),
                selectinload(SwapSession.user_b),
                selectinload(SwapSession.halves),
            )
            .where(SwapSession.status == "scheduled")
        )
        sessions = (await db.execute(stmt)).scalars().all()
        count = 0

        for sess in sessions:
            if not sess.halves:
                continue

            first_half = min(sess.halves, key=lambda h: h.half_number)
            start_time = parse_utc_datetime(first_half.start_time_utc)

            # Check 24-hour trigger
            if w24_start <= start_time <= w24_end:
                for u in (sess.user_a, sess.user_b):
                    await notification_service.create_and_push_notification(
                        db,
                        user_id=u.id,
                        type="session_reminder_24h",
                        payload={
                            "session_id": str(sess.id),
                            "start_time_utc": start_time.isoformat(),
                            "message": f"Reminder: You have a skill swap session scheduled tomorrow at {start_time.strftime('%H:%M UTC')}.",
                        },
                    )
                count += 2

            # Check 15-minute trigger
            elif w15_start <= start_time <= w15_end:
                for u in (sess.user_a, sess.user_b):
                    await notification_service.create_and_push_notification(
                        db,
                        user_id=u.id,
                        type="session_reminder_15m",
                        payload={
                            "session_id": str(sess.id),
                            "start_time_utc": start_time.isoformat(),
                            "message": "Your skill swap session starts in 15 minutes! Please prepare to join.",
                        },
                    )
                count += 2

        return {"job": "send-session-reminders", "records_processed": count}
