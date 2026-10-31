"""
Skill Swap Listings & Discovery Test Suite
==========================================
Tests for Stage 2 (Listings, Discovery & Spatial Privacy):
- SWAP-06: Create, update, pause, close swap listings with offered/wanted skills.
- SWAP-07: Strict enforcement of SWAP_MAX_ACTIVE_LISTINGS (default 5).
- SWAP-08: Zero-money policy enforcement (rejects $, paypal, hourly rate, etc.).
- SWAP-09: Feed sharing creates interactive Swap Offer post.
- SWAP-10: Discovery search with spatial distance bucketing, category filters,
           and zero coordinate/geohash leakage.
- SWAP-11: Blocked user isolation in discovery search.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import Skill, UserBlock, UserSwapProfile


@pytest.mark.asyncio
async def test_swap_listing_lifecycle(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test full CRUD lifecycle of a swap listing."""
    user, headers = await create_user(username="listing_author", email="author@swap.dev")

    # Seed offered and wanted skills
    skill_offered = Skill(
        id=uuid.uuid4(),
        slug="react-nextjs",
        display_name="React & Next.js",
        category="Technology",
        aliases=["react"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill_wanted = Skill(
        id=uuid.uuid4(),
        slug="resume-review",
        display_name="Resume Review",
        category="Career",
        aliases=["resume"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill_offered, skill_wanted])
    await test_db_session.commit()

    # 1. Create Listing
    payload = {
        "title": "React Architecture Mentorship for Resume Polish",
        "skill_offered_id": str(skill_offered.id),
        "skill_wanted_id": str(skill_wanted.id),
        "description": (
            "30 minutes of deep-dive Next.js App router patterns in exchange for resume feedback."
        ),
        "modes": ["video"],
        "area_label": "Downtown Tech Hub",
        "tags": ["frontend", "career", "nextjs"],
    }
    resp = await client.post("/api/v1/swaps/listings", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    listing_data = resp.json()
    assert listing_data["title"] == payload["title"]
    assert listing_data["status"] == "active"
    assert listing_data["skill_offered"]["slug"] == "react-nextjs"
    assert listing_data["skill_wanted"]["slug"] == "resume-review"
    listing_id = listing_data["id"]

    # 2. Get Listing by ID (unauthenticated public view)
    get_resp = await client.get(f"/api/v1/swaps/listings/{listing_id}")
    assert get_resp.status_code == 200
    pub_data = get_resp.json()
    assert pub_data["id"] == listing_id
    assert pub_data["distance_bucket"] == "remote"
    # PRIVACY ASSERTION: coordinates must NEVER be present in listing response
    assert "coarse_lat" not in pub_data
    assert "coarse_lng" not in pub_data
    assert "geohash" not in pub_data

    # 3. Update Listing (pause it)
    update_resp = await client.put(
        f"/api/v1/swaps/listings/{listing_id}",
        json={"status": "paused", "title": "Updated React Mentorship"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "paused"
    assert update_resp.json()["title"] == "Updated React Mentorship"

    # Reactivate
    reactivate_resp = await client.put(
        f"/api/v1/swaps/listings/{listing_id}",
        json={"status": "active"},
        headers=headers,
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_swap_listing_no_money_policy(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test that monetary terms, cash, and payment solicitation are strictly rejected."""
    user, headers = await create_user(username="greedy_user", email="greedy@swap.dev")

    skill = Skill(
        id=uuid.uuid4(),
        slug="python-algo",
        display_name="Python Algorithms",
        category="Technology",
        aliases=["algorithms"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Attempt with dollar sign
    resp1 = await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Python algorithms tutoring for $20",
            "skill_offered_id": str(skill.id),
            "description": "Offering quick tutoring session for cash.",
            "modes": ["video"],
        },
        headers=headers,
    )
    assert resp1.status_code == 400
    assert "strictly non-monetary" in resp1.json()["detail"]

    # Attempt with paypal keyword in description
    resp2 = await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Python Tutoring Exchange",
            "skill_offered_id": str(skill.id),
            "description": "Send payment via PayPal if you don't have skills to swap.",
            "modes": ["video"],
        },
        headers=headers,
    )
    assert resp2.status_code == 400
    assert "strictly non-monetary" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_swap_listing_max_limit_enforced(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test that users cannot exceed SWAP_MAX_ACTIVE_LISTINGS (5)."""
    user, headers = await create_user(username="prolific_creator", email="creator@swap.dev")

    skill = Skill(
        id=uuid.uuid4(),
        slug="creative-writing",
        display_name="Creative Writing",
        category="Arts",
        aliases=["writing"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Create 5 active listings
    for i in range(5):
        resp = await client.post(
            "/api/v1/swaps/listings",
            json={
                "title": f"Creative Writing Workshop Session #{i+1}",
                "skill_offered_id": str(skill.id),
                "description": (
                    f"Exploring short story structure and dialogue techniques part {i+1}."
                ),
                "modes": ["video"],
            },
            headers=headers,
        )
        assert resp.status_code == 200

    # 6th listing should fail
    resp6 = await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Creative Writing Session #6 Exceeds Limit",
            "skill_offered_id": str(skill.id),
            "description": "This one should be rejected by the active listings quota.",
            "modes": ["video"],
        },
        headers=headers,
    )
    assert resp6.status_code == 400
    assert "Maximum active swap listings limit reached" in resp6.json()["detail"]


@pytest.mark.asyncio
async def test_swap_listing_share_to_feed(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test sharing a swap listing into the social feed."""
    user, headers = await create_user(username="feed_sharer", email="sharer@swap.dev")

    skill = Skill(
        id=uuid.uuid4(),
        slug="guitar-basics",
        display_name="Guitar Basics",
        category="Music",
        aliases=["guitar"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Create listing
    create_resp = await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Beginner Acoustic Guitar for Conversational Japanese",
            "skill_offered_id": str(skill.id),
            "description": "Learn basic chords and fingerpicking in 30 minutes.",
            "modes": ["in_person", "video"],
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    listing_id = create_resp.json()["id"]

    # Share to feed
    share_resp = await client.post(f"/api/v1/swaps/listings/{listing_id}/share", headers=headers)
    assert share_resp.status_code == 200
    share_data = share_resp.json()
    assert share_data["listing_id"] == listing_id
    assert "post_id" in share_data

    # Verify post appears in social feed
    feed_resp = await client.get("/api/v1/posts", headers=headers)
    assert feed_resp.status_code == 200
    feed_items = feed_resp.json()["items"]
    matching_post = next((p for p in feed_items if str(listing_id) in p["content"]), None)
    assert matching_post is not None
    assert "🔄 Skill Swap Offer:" in matching_post["content"]


@pytest.mark.asyncio
async def test_swap_discovery_spatial_and_blocking(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test discovery search with spatial distance bucketing and blocked user exclusion."""
    user_viewer, viewer_headers = await create_user(username="viewer_user", email="viewer@swap.dev")
    user_neighbor, neighbor_headers = await create_user(
        username="neighbor_user", email="neighbor@swap.dev"
    )
    user_blocked, blocked_headers = await create_user(
        username="blocked_user", email="blocked@swap.dev"
    )

    # Set coarse coordinates
    # Viewer at 12.97, 77.59 (Bangalore Central)
    # Neighbor at 12.98, 77.60 (~1.5 km away)
    # Blocked user at 12.97, 77.58 (~1.1 km away)
    p_viewer = UserSwapProfile(
        id=uuid.uuid4(),
        user_id=user_viewer.id,
        coarse_lat=12.97,
        coarse_lng=77.59,
        area_label="MG Road",
        is_invisible=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    p_neighbor = UserSwapProfile(
        id=uuid.uuid4(),
        user_id=user_neighbor.id,
        coarse_lat=12.98,
        coarse_lng=77.60,
        area_label="Indiranagar",
        is_invisible=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    p_blocked = UserSwapProfile(
        id=uuid.uuid4(),
        user_id=user_blocked.id,
        coarse_lat=12.97,
        coarse_lng=77.58,
        area_label="Cubbon Park",
        is_invisible=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_db_session.add_all([p_viewer, p_neighbor, p_blocked])

    # Viewer blocks blocked_user
    block = UserBlock(
        id=uuid.uuid4(),
        blocker_id=user_viewer.id,
        blocked_id=user_blocked.id,
        created_at=datetime.now(UTC),
    )
    test_db_session.add(block)

    skill = Skill(
        id=uuid.uuid4(),
        slug="data-structures",
        display_name="Data Structures",
        category="Technology",
        aliases=["dsa"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Create listing by neighbor
    await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Binary Trees and Heaps Deep Dive",
            "skill_offered_id": str(skill.id),
            "description": "Understanding balanced binary trees and priority queues.",
            "modes": ["in_person", "video"],
        },
        headers=neighbor_headers,
    )

    # Create listing by blocked user
    await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Blocked User DSA Help",
            "skill_offered_id": str(skill.id),
            "description": "This listing should NOT appear to the viewer.",
            "modes": ["video"],
        },
        headers=blocked_headers,
    )

    # 1. Search as viewer
    search_resp = await client.get("/api/v1/swaps/listings", headers=viewer_headers)
    assert search_resp.status_code == 200
    items = search_resp.json()["items"]

    # Blocked listing must be completely filtered out
    titles = [item["title"] for item in items]
    assert "Binary Trees and Heaps Deep Dive" in titles
    assert "Blocked User DSA Help" not in titles

    # Neighbor's listing distance bucket must be computed (~1.5 km -> "1–3 km")
    neighbor_item = next(
        item for item in items if item["title"] == "Binary Trees and Heaps Deep Dive"
    )
    assert neighbor_item["distance_bucket"] in ("1–3 km", "under 1 km")

    # PRIVACY CRITICAL ASSERTION: coordinates must NEVER be leaked in search results
    for item in items:
        assert "coarse_lat" not in item
        assert "coarse_lng" not in item
        assert "lat" not in item
        assert "lng" not in item
        assert "geohash" not in item


@pytest.mark.asyncio
async def test_matching_engine_and_cached_explanation(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test weighted matching score calculation and SHA-256 match explanation caching."""
    user_learner, learner_headers = await create_user(
        username="learner_user", email="learner@swap.dev"
    )
    user_teacher, teacher_headers = await create_user(
        username="teacher_user", email="teacher@swap.dev"
    )

    # Seed skill
    skill = Skill(
        id=uuid.uuid4(),
        slug="machine-learning",
        display_name="Machine Learning",
        category="Data Science",
        aliases=["ml"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Learner declares learning skill
    await client.put(
        "/api/v1/swaps/profile/me",
        json={
            "learn_skills": [{"skill_slug": "machine-learning", "level": "beginner"}],
            "teach_skills": [],
            "availability_windows": [],
            "blackout_dates": [],
            "is_18_confirmed": True,
        },
        headers=learner_headers,
    )

    # Teacher creates listing offering Machine Learning
    listing_resp = await client.post(
        "/api/v1/swaps/listings",
        json={
            "title": "Intro to Neural Networks in PyTorch",
            "skill_offered_id": str(skill.id),
            "description": "30 minutes covering tensors, autograd, and training loops.",
            "modes": ["video"],
        },
        headers=teacher_headers,
    )
    assert listing_resp.status_code == 200

    # Learner requests matches
    matches_resp = await client.get("/api/v1/swaps/matches", headers=learner_headers)
    assert matches_resp.status_code == 200
    matches = matches_resp.json()
    assert len(matches) >= 1
    match = matches[0]
    assert match["match_score"] > 0.3
    assert "score_breakdown" in match
    assert match["score_breakdown"]["skill_match"] >= 0.6
    assert len(match["explanation"]) > 5

    # Second request must hit the SHA-256 cached explanation in match_explanations
    matches_resp_2 = await client.get("/api/v1/swaps/matches", headers=learner_headers)
    assert matches_resp_2.status_code == 200
    assert matches_resp_2.json()[0]["explanation"] == match["explanation"]


@pytest.mark.asyncio
async def test_listing_ai_draft_helper(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test AI listing drafting helper endpoint."""
    user, headers = await create_user(username="drafter_user", email="drafter@swap.dev")

    resp = await client.post(
        "/api/v1/swaps/listings/ai-draft",
        json={
            "skill_offered_name": "Docker & Containers",
            "skill_wanted_name": "System Design",
            "notes": "Help with Dockerfiles, multi-stage builds, and docker compose.",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert "description" in data
    assert len(data["suggested_tags"]) >= 1
