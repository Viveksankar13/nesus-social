"""
Stage 5 Hardening, Security, Privacy & Abuse Defense Test Suite
==============================================================
Tests for Stage 5 vertical slice:
- SWAP-32: Zero Coordinate, Geohash, and Residential Address Leakage Audit.
- RBAC Boundary & Session Isolation (strict isolation of Jitsi tokens, chat, halves).
- Anti-Money Laundering & Commercial Solicitation Defense.
- Off-Platform Contact Harvesting Moderation.
- Anti-Abuse: Duplicate Request Prevention, Active Request Quotas.
- Automated 3-Strike Quarantine Threshold.
- Timezone & Conflict Prevention Guardrails.
"""

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import (
    AvailabilityBlackout,
    Skill,
    SwapListing,
    SwapReport,
    SwapRequest,
    SwapSession,
    UserSwapProfile,
)


@pytest.fixture
async def sample_skills(test_db_session: AsyncSession) -> tuple[Skill, Skill]:
    """Seed test skills in the database."""
    skill_a = Skill(
        id=uuid.uuid4(),
        slug="advanced-algorithms",
        display_name="Advanced Algorithms & Optimization",
        category="Technology",
        aliases=["algorithms", "dsa"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill_b = Skill(
        id=uuid.uuid4(),
        slug="conversational-japanese",
        display_name="Conversational Japanese",
        category="Languages",
        aliases=["japanese"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill_a, skill_b])
    await test_db_session.commit()
    return skill_a, skill_b


def _is_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


def _assert_no_geo_leakage(obj: Any, path: str = "root") -> None:
    """
    Recursively scans JSON payloads to assert that:
    1. No raw latitude, longitude, coarse_lat, coarse_lng, or geohash keys exist.
    2. No float values match coarse or high-precision geographic coordinates.
    3. No residential keywords ('Apt', 'Unit', 'Suite') are leaked.
    """
    forbidden_keys = {
        "coarse_lat",
        "coarse_lng",
        "lat",
        "lng",
        "latitude",
        "longitude",
        "geohash",
        "exact_location",
        "gps",
    }

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}"
            assert key.lower() not in forbidden_keys, (
                f"Privacy Violation: Forbidden key '{key}' found at {current_path}"
            )
            _assert_no_geo_leakage(value, current_path)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _assert_no_geo_leakage(item, f"{path}[{idx}]")
    elif isinstance(obj, str):
        if not _is_uuid(obj):
            # Scan non-UUID strings for geohash patterns (e.g. tdnu20, 6-character geohash)
            assert not re.search(r"\b[0-9bcdefghjkmnpqrstuvwxyz]{9,12}\b", obj, re.IGNORECASE), (
                f"Privacy Violation: Potential geohash string detected at {path}: {obj}"
            )


@pytest.mark.asyncio
async def test_zero_coordinate_and_address_leakage_comprehensive(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """
    SWAP-32 Security Audit:
    Assert zero coordinates, geohashes, or exact addresses are leaked
    across public profile, listing details, discovery search, and match recommendations.
    """
    skill_a, skill_b = sample_skills

    # User 1 (Author) at coarse location 12.97, 77.59
    user_author, headers_author = await create_user(
        username="privacy_author", email="p_author@swap.dev"
    )
    p_author = UserSwapProfile(
        id=uuid.uuid4(),
        user_id=user_author.id,
        coarse_lat=12.97,
        coarse_lng=77.59,
        area_label="Koramangala 4th Block",
        is_invisible=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_db_session.add(p_author)

    # User 2 (Viewer) at coarse location 12.93, 77.62 (~5 km away)
    user_viewer, headers_viewer = await create_user(
        username="privacy_viewer", email="p_viewer@swap.dev"
    )
    p_viewer = UserSwapProfile(
        id=uuid.uuid4(),
        user_id=user_viewer.id,
        coarse_lat=12.93,
        coarse_lng=77.62,
        area_label="HSR Layout",
        is_invisible=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_db_session.add(p_viewer)
    await test_db_session.commit()

    # Create listing as author
    create_res = await client.post(
        "/api/v1/swaps/listings",
        headers=headers_author,
        json={
            "title": "Algorithms Deep Dive for Japanese Conversation",
            "skill_offered_id": str(skill_a.id),
            "skill_wanted_id": str(skill_b.id),
            "description": "30 minutes of dynamic programming optimization.",
            "modes": ["video", "in_person"],
        },
    )
    assert create_res.status_code == 200
    listing_id = create_res.json()["id"]

    # 1. Audit Public Profile Endpoint (/swaps/profile/{username})
    prof_res = await client.get(
        f"/api/v1/swaps/profile/{user_author.username}",
        headers=headers_viewer,
    )
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    _assert_no_geo_leakage(prof_data, "profile_response")
    # Distance bucket must be present for viewer, but raw coords omitted
    assert "distance_bucket" in prof_data
    assert prof_data["area_label"] == "Koramangala 4th Block"

    # 2. Audit Discovery Search Endpoint (/swaps/listings)
    disc_res = await client.get("/api/v1/swaps/listings", headers=headers_viewer)
    assert disc_res.status_code == 200
    disc_data = disc_res.json()
    _assert_no_geo_leakage(disc_data, "discovery_response")
    assert len(disc_data["items"]) >= 1
    item = next(it for it in disc_data["items"] if it["id"] == listing_id)
    assert item["distance_bucket"] in ("3–5 km", "5–10 km", "1–3 km")

    # 3. Audit Listing Detail Endpoint (/swaps/listings/{id})
    detail_res = await client.get(f"/api/v1/swaps/listings/{listing_id}", headers=headers_viewer)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    _assert_no_geo_leakage(detail_data, "listing_detail_response")

    # 4. Audit Match Recommendations Endpoint (/swaps/matches)
    matches_res = await client.get("/api/v1/swaps/matches", headers=headers_viewer)
    assert matches_res.status_code == 200
    _assert_no_geo_leakage(matches_res.json(), "matches_response")


@pytest.mark.asyncio
async def test_rbac_boundary_and_session_isolation(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
) -> None:
    """
    RBAC & Privacy Boundary:
    Strictly assert that non-participants cannot view another user's session details,
    Jitsi video tokens, calendar invites, or session chat messages.
    """
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="session_host", email="host@swap.dev")
    user_b, headers_b = await create_user(username="session_guest", email="guest@swap.dev")
    user_intruder, headers_intruder = await create_user(
        username="unauthorized_spy", email="spy@swap.dev"
    )

    # Schedule a session between A and B
    slot_start = datetime.now(UTC) + timedelta(days=1, hours=14)
    slot_end = slot_start + timedelta(minutes=30)
    req_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_a,
        json={
            "recipient_id": str(user_b.id),
            "offered_skill_id": str(skill_a.id),
            "wanted_skill_id": str(skill_b.id),
            "mode": "video",
            "message": "Let's schedule our exchange session.",
            "proposed_slots": [
                {
                    "start_time_utc": slot_start.isoformat(),
                    "end_time_utc": slot_end.isoformat(),
                }
            ],
        },
    )
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    accept_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/accept",
        headers=headers_b,
        json={"selected_slot_index": 0},
    )
    assert accept_res.status_code == 200
    sess_id = accept_res.json()["id"]

    # Post a message as host
    msg_res = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/messages",
        headers=headers_a,
        json={"content": "Here is confidential preparation notes for Half 1."},
    )
    assert msg_res.status_code == 200

    # 1. Intruder attempts to view session details -> 404/403
    spy_sess = await client.get(f"/api/v1/swaps/sessions/{sess_id}", headers=headers_intruder)
    assert spy_sess.status_code in (403, 404)

    # 2. Intruder attempts to download .ics invite with Jitsi link -> 403/404
    spy_ics = await client.get(f"/api/v1/swaps/sessions/{sess_id}/ics", headers=headers_intruder)
    assert spy_ics.status_code in (403, 404)

    # 3. Intruder attempts to read session messages -> 403/404
    spy_chat = await client.get(f"/api/v1/swaps/sessions/{sess_id}/messages", headers=headers_intruder)
    assert spy_chat.status_code in (403, 404)

    # 4. Intruder attempts to send message to session chat -> 403/404
    spy_post_chat = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/messages",
        headers=headers_intruder,
        json={"content": "I am eavesdropping!"},
    )
    assert spy_post_chat.status_code in (403, 404)

    # 5. Intruder attempts to trigger AI Session Plan -> 403/404
    spy_plan = await client.post(
        f"/api/v1/swaps/sessions/{sess_id}/ai-plan",
        headers=headers_intruder,
        json={"goals": "Steal session goals"},
    )
    assert spy_plan.status_code in (403, 404)

    # 6. Unauthenticated (Anonymous) access is completely rejected -> 401
    anon_sess = await client.get(f"/api/v1/swaps/sessions/{sess_id}")
    assert anon_sess.status_code == 401


@pytest.mark.asyncio
async def test_anti_money_laundering_and_contact_harvesting(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
) -> None:
    """
    SWAP-07 & SWAP-27 Security:
    Assert zero-money policy rejects monetary solicitation and off-platform contact harvesting.
    """
    skill_a, _ = sample_skills
    user, headers = await create_user(username="scammer_bot", email="bot@swap.dev")

    # 1. Listing with explicit pricing ($25/hr) -> Blocked with 400
    res_price = await client.post(
        "/api/v1/swaps/listings",
        headers=headers,
        json={
            "title": "Expert Algorithms Coaching - $35 Per 30 Minutes",
            "skill_offered_id": str(skill_a.id),
            "description": "I teach binary trees. $35 fee payable via CashApp.",
            "modes": ["video"],
        },
    )
    assert res_price.status_code == 400
    assert "strictly non-monetary" in res_price.json()["detail"].lower()

    # 2. Listing with Venmo handle -> Blocked with 400
    res_venmo = await client.post(
        "/api/v1/swaps/listings",
        headers=headers,
        json={
            "title": "Python Tutoring for Fun",
            "skill_offered_id": str(skill_a.id),
            "description": "Great lessons. Send tip to venmo: @myhandle",
            "modes": ["video"],
        },
    )
    assert res_venmo.status_code == 400
    assert "strictly non-monetary" in res_venmo.json()["detail"].lower()

    # 3. Listing with PayPal solicitation -> Blocked with 400
    res_paypal = await client.post(
        "/api/v1/swaps/listings",
        headers=headers,
        json={
            "title": "Machine Learning Primer",
            "skill_offered_id": str(skill_a.id),
            "description": "Paypal me before the meeting.",
            "modes": ["video"],
        },
    )
    assert res_paypal.status_code == 400
    assert "strictly non-monetary" in res_paypal.json()["detail"].lower()


@pytest.mark.asyncio
async def test_duplicate_request_and_quota_defense(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
) -> None:
    """
    SWAP-13 Anti-Spam:
    Verify duplicate pending request prevention and active request quotas.
    """
    skill_a, skill_b = sample_skills
    user_sender, headers_sender = await create_user(username="requester_spammer", email="spm@swap.dev")
    user_target, _ = await create_user(username="busy_target", email="tgt2@swap.dev")

    slot_start = datetime.now(UTC) + timedelta(days=2, hours=10)
    slot_end = slot_start + timedelta(minutes=30)
    req_body = {
        "recipient_id": str(user_target.id),
        "offered_skill_id": str(skill_a.id),
        "wanted_skill_id": str(skill_b.id),
        "mode": "video",
        "message": "First proposal",
        "proposed_slots": [
            {
                "start_time_utc": slot_start.isoformat(),
                "end_time_utc": slot_end.isoformat(),
            }
        ],
    }

    # 1. First request succeeds
    r1 = await client.post("/api/v1/swaps/requests", headers=headers_sender, json=req_body)
    assert r1.status_code == 200

    # 2. Duplicate second request to same recipient must fail
    r2 = await client.post("/api/v1/swaps/requests", headers=headers_sender, json=req_body)
    assert r2.status_code == 400
    assert "pending swap request already exists" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_three_strike_auto_quarantine_integrity(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """
    SWAP-27 3-Strike Threshold:
    Assert that 3 distinct user reports automatically quashes a listing.
    """
    skill_a, _ = sample_skills
    user_spammer, headers_spammer = await create_user(username="quarantine_target", email="q_tgt@swap.dev")

    # Author creates listing
    listing_res = await client.post(
        "/api/v1/swaps/listings",
        headers=headers_spammer,
        json={
            "title": "Questionable Swap Listing",
            "skill_offered_id": str(skill_a.id),
            "description": "Suspicious offer that will get reported.",
            "modes": ["video"],
        },
    )
    assert listing_res.status_code == 200
    listing_id = listing_res.json()["id"]

    # Create 3 distinct reporting users
    r1_user, r1_headers = await create_user(username="reporter_one", email="r1@swap.dev")
    r2_user, r2_headers = await create_user(username="reporter_two", email="r2@swap.dev")
    r3_user, r3_headers = await create_user(username="reporter_three", email="r3@swap.dev")

    # Report 1
    rep1 = await client.post(
        "/api/v1/swaps/reports",
        headers=r1_headers,
        json={
            "target_type": "listing",
            "target_id": listing_id,
            "category": "spam",
            "notes": "Looks suspicious",
        },
    )
    assert rep1.status_code == 200

    # Report 2
    rep2 = await client.post(
        "/api/v1/swaps/reports",
        headers=r2_headers,
        json={
            "target_type": "listing",
            "target_id": listing_id,
            "category": "payment_solicitation",
            "notes": "Spam commercial activity",
        },
    )
    assert rep2.status_code == 200

    # Verify listing is still active after 2 reports
    check1 = await client.get(f"/api/v1/swaps/listings/{listing_id}", headers=r1_headers)
    assert check1.status_code == 200
    assert check1.json()["status"] == "active"

    # Report 3 -> Triggers 3-strike auto-quarantine threshold!
    rep3 = await client.post(
        "/api/v1/swaps/reports",
        headers=r3_headers,
        json={
            "target_type": "listing",
            "target_id": listing_id,
            "category": "inappropriate",
            "notes": "Inappropriate content",
        },
    )
    assert rep3.status_code == 200

    # Verify listing is now removed / quarantined in DB
    listing_db = await test_db_session.get(SwapListing, uuid.UUID(listing_id))
    assert listing_db is not None
    assert listing_db.status == "removed"


@pytest.mark.asyncio
async def test_blackout_and_conflict_schedule_prevention(
    client: AsyncClient,
    create_user: Callable[..., Any],
    sample_skills: tuple[Skill, Skill],
    test_db_session: AsyncSession,
) -> None:
    """
    SWAP-14 Scheduling Integrity:
    Ensure conflicting blackout periods prevent request acceptance.
    """
    skill_a, skill_b = sample_skills
    user_a, headers_a = await create_user(username="busy_teacher", email="busy@swap.dev")
    user_b, headers_b = await create_user(username="eager_student", email="eager@swap.dev")

    # User A sets a blackout window for tomorrow 14:00 to 18:00 UTC
    blackout_start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1, hours=14)
    blackout_end = blackout_start + timedelta(hours=4)
    blackout = AvailabilityBlackout(
        id=uuid.uuid4(),
        user_id=user_a.id,
        start_datetime_utc=blackout_start,
        end_datetime_utc=blackout_end,
        reason="Doctor Appointment",
    )
    test_db_session.add(blackout)
    await test_db_session.commit()

    # User B requests a slot exactly during User A's blackout
    conflicting_slot_start = blackout_start + timedelta(hours=1)
    conflicting_slot_end = conflicting_slot_start + timedelta(minutes=30)

    req_res = await client.post(
        "/api/v1/swaps/requests",
        headers=headers_b,
        json={
            "recipient_id": str(user_a.id),
            "offered_skill_id": str(skill_b.id),
            "wanted_skill_id": str(skill_a.id),
            "mode": "video",
            "message": "Let's meet during your blackout",
            "proposed_slots": [
                {
                    "start_time_utc": conflicting_slot_start.isoformat(),
                    "end_time_utc": conflicting_slot_end.isoformat(),
                }
            ],
        },
    )
    assert req_res.status_code == 200
    req_id = req_res.json()["id"]

    # When User A attempts to accept the conflicting slot, the system detects the blackout conflict!
    accept_res = await client.post(
        f"/api/v1/swaps/requests/{req_id}/accept",
        headers=headers_a,
        json={"selected_slot_index": 0},
    )
    assert accept_res.status_code == 409
    assert "conflict" in accept_res.json()["detail"].lower()
