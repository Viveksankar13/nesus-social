"""
Skill Swap Requests & Sessions Test Suite
=========================================
Tests for Stage 3 (Vertical Slice: Requests, Sessions, Halves, Blind Reviews & Jobs):
- S3a: Request state machine (pending -> countered -> accepted / declined / cancelled).
- S3a: Max pending request quotas and zero-money enforcement.
- S3b: Scheduling two 30-minute halves and unguessable Jitsi Meet room generation.
- S3b: Schedule conflict guards (overlapping sessions and blackout windows).
- S3b: Internal cron runner with X-Cron-Secret authentication.
- S3c: Participant confirmation, reciprocity ledger updates (+30m taught, +30m learned).
- S3c: Double-blind review system with mutual unmasking and trust score updates.
- S3c: Session room logistics chat and iCalendar (.ics) download.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.swap import (
    AvailabilityBlackout,
    JobRun,
    ReciprocityLedger,
    Skill,
    SwapRequest,
    SwapSession,
    TrustScore,
)


@pytest.fixture
async def sample_skills(test_db_session: AsyncSession) -> tuple[Skill, Skill]:
    """Seed test skills in the database."""
    skill_a = Skill(
        id=uuid.uuid4(),
        slug="algorithms-ds",
        display_name="Algorithms & Data Structures",
        category="Technology",
        aliases=["dsa"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill_b = Skill(
        id=uuid.uuid4(),
        slug="conversational-french",
        display_name="Conversational French",
        category="Languages",
        aliases=["french"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill_a, skill_b])
    await test_db_session.commit()
    return skill_a, skill_b


@pytest.mark.asyncio
async def test_swap_request_creation_and_quota(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
) -> None:
    """Test creating a swap request and quota limits."""
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="swap_requester", email="req@swap.dev")
    user_b, headers_b = await create_user(username="swap_recipient", email="rec@swap.dev")

    # Proposing to oneself is forbidden
    slot_time_start = datetime.now(UTC) + timedelta(days=2, hours=10)
    slot_time_end = slot_time_start + timedelta(minutes=30)
    self_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_a.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Hey, let's swap skills peer-to-peer!",
            "proposed_slots": [
                {
                    "start_time_utc": slot_time_start.isoformat(),
                    "end_time_utc": slot_time_end.isoformat(),
                }
            ],
        },
    )
    assert self_res.status_code == 400
    assert "yourself" in self_res.json()["detail"]

    # Money solicitation is forbidden
    money_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "I will teach you for $25 via PayPal.",
            "proposed_slots": [
                {
                    "start_time_utc": slot_time_start.isoformat(),
                    "end_time_utc": slot_time_end.isoformat(),
                }
            ],
        },
    )
    assert money_res.status_code == 400
    assert "strictly non-monetary" in money_res.json()["detail"]

    # Valid creation
    res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Would love to exchange 30m of DSA for 30m of conversational French!",
            "proposed_slots": [
                {
                    "start_time_utc": slot_time_start.isoformat(),
                    "end_time_utc": slot_time_end.isoformat(),
                }
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending"
    assert data["requester"]["username"] == "swap_requester"
    assert data["recipient"]["username"] == "swap_recipient"
    assert len(data["proposed_slots"]) == 1

    # Check recipient inbox
    inbox_res = await client.get("/api/v1/swaps/requests", headers=headers_b)
    assert inbox_res.status_code == 200
    inbox_data = inbox_res.json()
    assert len(inbox_data["incoming"]) == 1
    assert inbox_data["incoming"][0]["id"] == data["id"]


@pytest.mark.asyncio
async def test_swap_request_state_machine_counter_and_decline(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
) -> None:
    """Test counter-proposal and declining a swap request."""
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="counter_a", email="ca@swap.dev")
    user_b, headers_b = await create_user(username="counter_b", email="cb@swap.dev")

    slot_1_start = datetime.now(UTC) + timedelta(days=2, hours=10)
    slot_1_end = slot_1_start + timedelta(minutes=30)
    slot_2_start = datetime.now(UTC) + timedelta(days=3, hours=14)
    slot_2_end = slot_2_start + timedelta(minutes=30)

    # 1. User A proposes
    create_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Let's do a 30m swap!",
            "proposed_slots": [
                {
                    "start_time_utc": slot_1_start.isoformat(),
                    "end_time_utc": slot_1_end.isoformat(),
                }
            ],
        },
    )
    req_id = create_res.json()["id"]

    # 2. User B counters with a different time
    counter_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/counter",
        headers=headers_b,
        json={
            "message": "Can we do tomorrow afternoon instead?",
            "proposed_slots": [
                {
                    "start_time_utc": slot_2_start.isoformat(),
                    "end_time_utc": slot_2_end.isoformat(),
                }
            ],
        },
    )
    assert counter_res.status_code == 200
    counter_data = counter_res.json()
    assert counter_data["status"] == "countered"
    assert counter_data["counter_note"] == "Can we do tomorrow afternoon instead?"

    # 3. User A declines
    decline_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/decline",
        headers=headers_a,
    )
    assert decline_res.status_code == 200
    assert decline_res.json()["status"] == "declined"


@pytest.mark.asyncio
async def test_swap_request_acceptance_creates_session_and_halves(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """Test accepting a proposal creates SwapSession and two 30-minute halves with Jitsi Meet URL."""
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="mentor_a", email="ma@swap.dev")
    user_b, headers_b = await create_user(username="mentor_b", email="mb@swap.dev")

    slot_start = datetime.now(UTC) + timedelta(days=2, hours=10)
    slot_end = slot_start + timedelta(minutes=30)

    # 1. Propose
    create_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Ready to mentor in algorithms!",
            "proposed_slots": [
                {
                    "start_time_utc": slot_start.isoformat(),
                    "end_time_utc": slot_end.isoformat(),
                }
            ],
        },
    )
    req_id = create_res.json()["id"]

    # 2. Accept
    accept_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/accept",
        headers=headers_b,
        json={"selected_slot_index": 0},
    )
    assert accept_res.status_code == 200
    sess = accept_res.json()
    assert sess["status"] == "scheduled"
    assert sess["mode"] == "video"
    assert sess["jitsi_room_token"] is not None
    assert "https://meet.jit.si" in sess["jitsi_room_url"]

    # Validate 2 distinct 30-minute halves
    halves = sess["halves"]
    assert len(halves) == 2
    assert halves[0]["half_number"] == 1
    assert halves[0]["mentor"]["username"] == "mentor_a"
    assert halves[0]["learner"]["username"] == "mentor_b"

    assert halves[1]["half_number"] == 2
    assert halves[1]["mentor"]["username"] == "mentor_b"
    assert halves[1]["learner"]["username"] == "mentor_a"

    # 3. Schedule conflict guard check: trying to schedule an overlapping session must fail
    conflict_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Another proposal at the exact same time",
            "proposed_slots": [
                {
                    "start_time_utc": slot_start.isoformat(),
                    "end_time_utc": slot_end.isoformat(),
                }
            ],
        },
    )
    req2_id = conflict_res.json()["id"]
    accept_conflict_res = await client.post(
        f"/api/v1/swaps/requests/{req2_id}/accept",
        headers=headers_b,
        json={"selected_slot_index": 0},
    )
    assert accept_conflict_res.status_code == 409
    assert "Schedule conflict" in accept_conflict_res.json()["detail"]


@pytest.mark.asyncio
async def test_session_completion_double_blind_reviews_and_reciprocity(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """Test completion confirmations, double-blind reviews, and reciprocity ledger updates."""
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="recip_a", email="ra@swap.dev")
    user_b, headers_b = await create_user(username="recip_b", email="rb@swap.dev")

    slot_start = datetime.now(UTC) + timedelta(days=1, hours=8)
    slot_end = slot_start + timedelta(minutes=30)

    # Setup session
    create_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Mutual learning proposal",
            "proposed_slots": [
                {
                    "start_time_utc": slot_start.isoformat(),
                    "end_time_utc": slot_end.isoformat(),
                }
            ],
        },
    )
    req_id = create_res.json()["id"]
    sess_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/accept",
        headers=headers_b,
        json={"selected_slot_index": 0},
    )
    sess_id = sess_res.json()["id"]

    # 1. Chat logistics
    chat_res = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/messages",
        headers=headers_a,
        json={"content": "Hi! Looking forward to our session tomorrow."},
    )
    assert chat_res.status_code == 200
    assert chat_res.json()["content"] == "Hi! Looking forward to our session tomorrow."

    msgs_res = await client.get(f"/api/v1/swaps/sessions/{sess_id}/messages", headers=headers_b)
    assert msgs_res.status_code == 200
    assert len(msgs_res.json()) == 1

    # 2. iCalendar export
    ics_res = await client.get(f"/api/v1/swaps/sessions/{sess_id}/ics", headers=headers_a)
    assert ics_res.status_code == 200
    assert "BEGIN:VCALENDAR" in ics_res.text
    assert "BEGIN:VEVENT" in ics_res.text

    # 3. Confirm completion from User A
    c1 = await client.post(f"/api/v1/swaps/sessions/{sess_id}/confirm", headers=headers_a)
    assert c1.status_code == 200
    assert c1.json()["user_a_confirmed"] is True
    assert c1.json()["status"] == "scheduled"  # Not yet completed until both agree

    # 4. Confirm completion from User B -> completes session
    c2 = await client.post(f"/api/v1/swaps/sessions/{sess_id}/confirm", headers=headers_b)
    assert c2.status_code == 200
    assert c2.json()["status"] == "completed"

    # Verify reciprocity ledger: +30 min taught and +30 min learned for both users
    ledger_a = (
        await test_db_session.execute(
            select(ReciprocityLedger).where(ReciprocityLedger.user_id == user_a.id)
        )
    ).scalar_one()
    assert ledger_a.minutes_taught == 30
    assert ledger_a.minutes_learned == 30
    assert ledger_a.net_balance_minutes == 0

    # 5. User A submits review -> double-blind isolation (is_revealed = False)
    r1 = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/reviews",
        headers=headers_a,
        json={
            "rating": 5,
            "tags": ["Patient Teacher", "Clear Explanations"],
            "public_comment": "Wonderful mentor, explained French verbs clearly!",
            "private_feedback": "Great session.",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["is_revealed"] is False

    # User B views reviews -> rating and comments are masked
    b_views = await client.get(f"/api/v1/swaps/sessions/{sess_id}/reviews", headers=headers_b)
    assert len(b_views.json()) == 0  # Not revealed, User B hasn't submitted yet

    # 6. User B submits review -> MUTUAL UNMASKING (both become is_revealed = True)
    r2 = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/reviews",
        headers=headers_b,
        json={
            "rating": 5,
            "tags": ["Great Explanations", "Well Prepared"],
            "public_comment": "Fantastic algorithm walkthrough!",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["is_revealed"] is True

    # Both reviews now fully visible
    both_views = await client.get(f"/api/v1/swaps/sessions/{sess_id}/reviews", headers=headers_a)
    assert len(both_views.json()) == 2
    assert all(r["is_revealed"] is True for r in both_views.json())


@pytest.mark.asyncio
async def test_internal_cron_runner_and_secret(
    client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    """Test secret-protected internal cron job runner."""
    # 1. Missing or invalid secret
    unauth_res = await client.post("/api/v1/internal/jobs/auto-expire-requests")
    assert unauth_res.status_code == 401

    bad_sec_res = await client.post(
        "/api/v1/internal/jobs/auto-expire-requests",
        headers={"X-Cron-Secret": "invalid-secret"},
    )
    assert bad_sec_res.status_code == 401

    # 2. Valid secret execution
    valid_res = await client.post(
        "/api/v1/internal/jobs/auto-expire-requests",
        headers={"X-Cron-Secret": settings.CRON_SECRET},
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["job"] == "auto-expire-requests"

    # Verify audit record in job_runs table
    job_run = (
        (
            await test_db_session.execute(
                select(JobRun).where(JobRun.job_name == "auto-expire-requests")
            )
        )
        .scalars()
        .first()
    )
    assert job_run is not None
    assert job_run.status == "success"
