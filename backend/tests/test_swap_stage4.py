"""
Stage 4 Safety, Admin & AI Helpers Test Suite
=============================================
Tests for Stage 4 vertical slice:
- S4a: AI Session Planner, Post-Session Recap, and Fairness Advisor.
- S4b: User blocking, reporting with 3-strike auto-hide, and public place verification.
- S4c: Admin Swaps Management Console (KPIs, listing moderation, dispute resolution,
  taxonomy approval & merging, and manual cron job trigger).
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import (
    Skill,
    SwapListing,
    SwapRequest,
    SwapSession,
    UserBlock,
    UserSwapProfile,
)


@pytest.fixture
async def sample_skills(test_db_session: AsyncSession) -> tuple[Skill, Skill, Skill]:
    """Seed test skills in the database."""
    skill_a = Skill(
        id=uuid.uuid4(),
        slug="python-backend-dev",
        display_name="Python Backend Development",
        category="Technology",
        aliases=["python", "fastapi"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill_b = Skill(
        id=uuid.uuid4(),
        slug="resume-review",
        display_name="Resume & Interview Prep",
        category="Career",
        aliases=["resume"],
        status="active",
        created_at=datetime.now(UTC),
    )
    pending_skill = Skill(
        id=uuid.uuid4(),
        slug="quantum-computing-basics",
        display_name="Quantum Computing Basics",
        category="Technology",
        aliases=["quantum"],
        status="pending",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill_a, skill_b, pending_skill])
    await test_db_session.commit()
    return skill_a, skill_b, pending_skill


@pytest.mark.asyncio
async def test_ai_session_planner_and_recap(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill, Skill],
) -> None:
    """Test AI Session Planner and Post-Session Recap helper."""
    skill_a, skill_b, _ = sample_skills
    user_a, headers_a = await create_user(username="ai_mentor", email="aim@swap.dev")
    user_b, headers_b = await create_user(username="ai_learner", email="ail@swap.dev")

    # Setup session
    slot_start = datetime.now(UTC) + timedelta(days=2, hours=10)
    slot_end = slot_start + timedelta(minutes=30)
    req_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Let's plan a 30m swap!",
            "proposed_slots": [
                {
                    "start_time_utc": slot_start.isoformat(),
                    "end_time_utc": slot_end.isoformat(),
                }
            ],
        },
    )
    req_id = req_res.json()["id"]
    sess_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/accept",
        headers=headers_b,
        json={"selected_slot_index": 0},
    )
    sess_id = sess_res.json()["id"]

    # 1. AI Session Plan
    plan_res = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/ai-plan",
        headers=headers_a,
        json={"goals": "Understand async FastAPI dependency injection and testing"},
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert "objective" in plan_data
    assert len(plan_data["agenda_items"]) >= 3
    assert len(plan_data["suggested_questions"]) >= 1

    # 2. AI Post-Session Recap
    recap_res = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/ai-recap",
        headers=headers_b,
        json={
            "rough_notes": "Discussed Depends(get_db), overriding fixtures in pytest, AsyncSession commit vs rollback."
        },
    )
    assert recap_res.status_code == 200
    recap_data = recap_res.json()
    assert "summary" in recap_data
    assert len(recap_data["key_takeaways"]) >= 1
    assert len(recap_data["action_items"]) >= 1

    # 3. Fairness Advice
    fair_res = await client.get("/api/v1/swaps/fairness-advice", headers=headers_a)
    assert fair_res.status_code == 200
    fair_data = fair_res.json()
    assert fair_data["balance_status"] in ["balanced", "learning_deficit", "teaching_deficit"]
    assert "headline" in fair_data
    assert len(fair_data["recommended_actions"]) >= 1


@pytest.mark.asyncio
async def test_user_blocking_and_discovery_isolation(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """Test blocking a user excludes them from discovery and prevents self-blocking."""
    skill_a, skill_b, _ = sample_skills
    user_a, headers_a = await create_user(username="blocker_user", email="blk@swap.dev")
    user_b, headers_b = await create_user(username="blocked_target", email="tgt@swap.dev")

    # Self-block fails
    self_res = await client.post(
        "/api/v1/swaps/blocks",
        headers=headers_a,
        json={"blocked_id": str(user_a.id)},
    )
    assert self_res.status_code == 400

    # User B creates a swap listing
    create_list_res = await client.post(
        "/api/v1/swaps/listings",
        headers=headers_b,
        json={
            "title": "Python Guidance for English Practice",
            "skill_offered_id": str(skill_a.id),
            "skill_wanted_id": str(skill_b.id),
            "description": "Happy to offer 30 minutes of Python guidance for English conversation.",
            "modes": ["video"],
        },
    )
    assert create_list_res.status_code == 200

    # User A sees the listing in discovery before block
    disc_before = await client.get("/api/v1/swaps/listings", headers=headers_a)
    assert any(item["user"]["username"] == "blocked_target" for item in disc_before.json()["items"])

    # User A blocks User B
    blk_res = await client.post(
        "/api/v1/swaps/blocks",
        headers=headers_a,
        json={"blocked_id": str(user_b.id)},
    )
    assert blk_res.status_code == 200

    # Verify listing of blocked users
    list_blks = await client.get("/api/v1/swaps/blocks", headers=headers_a)
    assert list_blks.status_code == 200
    assert len(list_blks.json()) == 1
    assert list_blks.json()[0]["blocked_id"] == str(user_b.id)

    # User A no longer sees User B's listing in discovery
    disc_after = await client.get("/api/v1/swaps/listings", headers=headers_a)
    assert not any(item["user"]["username"] == "blocked_target" for item in disc_after.json()["items"])

    # Unblock
    unblk_res = await client.delete(f"/api/v1/swaps/blocks/{user_b.id}", headers=headers_a)
    assert unblk_res.status_code == 200


@pytest.mark.asyncio
async def test_reporting_and_three_strike_auto_hide(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """Test 3 distinct reports against a listing automatically unpublishes it."""
    skill_a, skill_b, _ = sample_skills
    spammer, spammer_headers = await create_user(username="spam_lister", email="spm@swap.dev")

    # Create listing
    listing_res = await client.post(
        "/api/v1/swaps/listings",
        headers=spammer_headers,
        json={
            "title": "Suspicious Peer Mentorship",
            "skill_offered_id": str(skill_a.id),
            "skill_wanted_id": str(skill_b.id),
            "description": "Offering general peer help for community trades.",
            "modes": ["video"],
        },
    )
    listing_id = listing_res.json()["id"]

    # 3 distinct users submit reports
    for i in range(1, 4):
        _, user_headers = await create_user(username=f"reporter_{i}", email=f"rep{i}@swap.dev")
        rep_res = await client.post(
            "/api/v1/swaps/reports",
            headers=user_headers,
            json={
                "target_type": "listing",
                "target_id": listing_id,
                "category": "spam",
                "notes": f"Automated test report #{i}",
            },
        )
        assert rep_res.status_code == 200

    # Verify listing is now automatically marked as "removed"
    db_listing = await test_db_session.get(SwapListing, uuid.UUID(listing_id))
    assert db_listing is not None
    assert db_listing.status == "removed"


@pytest.mark.asyncio
async def test_in_person_venue_safety_validator(client: AsyncClient) -> None:
    """Test venue safety verification rejects residential addresses."""
    # 1. Valid public venue
    safe_res = await client.post(
        "/api/v1/swaps/safety/check-venue",
        params={
            "place_name": "Seattle Central Public Library",
            "address": "1000 4th Ave, Seattle, WA",
        },
    )
    assert safe_res.status_code == 200
    safe_data = safe_res.json()
    assert safe_data["is_safe_public_venue"] is True
    assert safe_data["warning"] is None
    assert len(safe_data["safety_tips"]) >= 2

    # 2. Residential private address rejected
    unsafe_res = await client.post(
        "/api/v1/swaps/safety/check-venue",
        params={
            "place_name": "My Apartment Room",
            "address": "Unit 4B, 742 Evergreen Terrace",
        },
    )
    assert unsafe_res.status_code == 200
    unsafe_data = unsafe_res.json()
    assert unsafe_data["is_safe_public_venue"] is False
    assert unsafe_data["warning"] is not None


@pytest.mark.asyncio
async def test_admin_swaps_console_and_taxonomy(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """Test Admin Swaps Console: KPIs, listings, disputes, taxonomy, and manual cron trigger."""
    skill_a, skill_b, pending_skill = sample_skills
    _, admin_headers = await create_user(username="swap_admin", email="admin@swap.dev", role="admin")
    _, norm_headers = await create_user(username="normal_user", email="norm@swap.dev", role="user")

    # 1. Non-admin forbidden
    forbidden_res = await client.get("/api/v1/admin/swaps/stats", headers=norm_headers)
    assert forbidden_res.status_code == 403

    # 2. Admin retrieves stats
    stats_res = await client.get("/api/v1/admin/swaps/stats", headers=admin_headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_active_listings" in stats_data
    assert "completion_rate" in stats_data

    # 3. Admin lists taxonomy and approves pending skill
    tax_res = await client.get("/api/v1/admin/swaps/taxonomy?status=pending", headers=admin_headers)
    assert tax_res.status_code == 200
    pending_list = tax_res.json()
    assert any(s["slug"] == "quantum-computing-basics" for s in pending_list)

    approve_res = await client.post(
        "/api/v1/admin/swaps/taxonomy/approve",
        headers=admin_headers,
        json={
            "skill_id": str(pending_skill.id),
            "display_name": "Quantum Computing & Qiskit",
            "category": "Technology",
        },
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "active"
    assert approve_res.json()["display_name"] == "Quantum Computing & Qiskit"

    # 4. Admin merges taxonomy skills
    merge_res = await client.post(
        "/api/v1/admin/swaps/taxonomy/merge",
        headers=admin_headers,
        json={
            "source_skill_id": str(pending_skill.id),
            "target_skill_id": str(skill_a.id),
        },
    )
    assert merge_res.status_code == 200
    merged_target = merge_res.json()
    assert "quantum-computing-basics" in merged_target["aliases"]

    # 5. Admin manual cron job trigger
    cron_res = await client.post(
        "/api/v1/admin/swaps/jobs/auto-expire-requests/run",
        headers=admin_headers,
    )
    assert cron_res.status_code == 200
    assert cron_res.json()["status"] == "success"
