"""
Skill Swap Profiles & Taxonomy Test Suite
=========================================
Tests for Stage 1 (Taxonomy, User Skills, Availability, and Privacy):
- SWAP-01: Canonical taxonomy retrieval, category grouping, and fuzzy skill matching
- SWAP-02: User skill competency declaration (teach & learn) and level validation
- SWAP-03: Recurring weekly availability windows and blackout intervals
- SWAP-04: Strict location privacy: Coarse coordinates (~1 km), distance bucketing,
           and zero latitude/longitude exposure in public profile JSON.
- SWAP-05: 18+ confirmation and profile invisible toggle.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import Skill, UserSwapProfile
from app.services.swap_geocoding import calculate_haversine_km, get_distance_bucket
from app.services.swap_taxonomy import SwapTaxonomyService


@pytest.mark.asyncio
async def test_taxonomy_retrieval_and_suggestion(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test retrieving active taxonomy and suggesting a new skill."""
    user, headers = await create_user(username="swap_tester1", email="tester1@swap.dev")

    # Seed a couple of canonical skills
    skill1 = Skill(
        id=uuid.uuid4(),
        slug="python-core",
        display_name="Python Core",
        category="Technology",
        aliases=["python", "py"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill2 = Skill(
        id=uuid.uuid4(),
        slug="spanish-convo",
        display_name="Conversational Spanish",
        category="Languages",
        aliases=["spanish", "espanol"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill1, skill2])
    await test_db_session.commit()

    # 1. Fetch taxonomy
    resp = await client.get("/api/v1/swaps/taxonomy")
    assert resp.status_code == 200
    groups = resp.json()
    assert len(groups) >= 2
    categories = [g["category"] for g in groups]
    assert "Technology" in categories
    assert "Languages" in categories

    # 2. Suggest new skill
    suggest_resp = await client.post(
        "/api/v1/swaps/taxonomy/suggest",
        json={"name": "Docker & Containers", "category": "DevOps"},
        headers=headers,
    )
    assert suggest_resp.status_code == 200
    s_data = suggest_resp.json()
    assert s_data["slug"] == "docker-containers"
    assert s_data["status"] == "active"


@pytest.mark.asyncio
async def test_taxonomy_fuzzy_matching(test_db_session: AsyncSession) -> None:
    """Test fuzzy skill normalization across exact, alias, and typo variants."""
    s = Skill(
        id=uuid.uuid4(),
        slug="guitar-acoustic",
        display_name="Acoustic Guitar Basics",
        category="Music",
        aliases=["guitar", "acoustic guitar", "fingerpicking"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(s)
    await test_db_session.commit()

    # Exact slug
    m1 = await SwapTaxonomyService.fuzzy_match_skill(test_db_session, "guitar-acoustic")
    assert m1 is not None and m1.id == s.id

    # Alias match
    m2 = await SwapTaxonomyService.fuzzy_match_skill(test_db_session, "fingerpicking")
    assert m2 is not None and m2.id == s.id

    # Substring in display name
    m3 = await SwapTaxonomyService.fuzzy_match_skill(test_db_session, "guitar")
    assert m3 is not None and m3.id == s.id

    # Typo match via difflib
    m4 = await SwapTaxonomyService.fuzzy_match_skill(test_db_session, "acustic guitar")
    assert m4 is not None and m4.id == s.id


@pytest.mark.asyncio
async def test_profile_lifecycle_and_privacy_guarantee(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """
    Test setting up a swap profile with skills, availability, and coarse coordinates,
    then verifying that public viewing exposes ONLY distance buckets, with ZERO coordinate leakage.
    """
    user_alice, headers_alice = await create_user(username="alice_mentor", email="alice@nexus.dev")
    user_bob, headers_bob = await create_user(username="bob_learner", email="bob@nexus.dev")

    # Add skill
    skill = Skill(
        id=uuid.uuid4(),
        slug="react-fundamentals",
        display_name="React Fundamentals",
        category="Technology",
        aliases=["react"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add(skill)
    await test_db_session.commit()

    # Alice sets her profile in Mission District, SF (~37.77, -122.42)
    alice_update = {
        "bio": "Frontend specialist eager to swap React tutoring for Spanish practice.",
        "coarse_lat": 37.774929,  # High-precision input
        "coarse_lng": -122.419416,  # High-precision input
        "area_label": "Mission District, San Francisco, CA",
        "radius_km": 10,
        "modes": ["video", "in_person"],
        "languages": ["English"],
        "is_invisible": False,
        "accepts_newcomers": True,
        "is_18_confirmed": True,
        "teach_skills": [
            {
                "skill_slug": "react-fundamentals",
                "level": "expert",
                "years_experience": 4,
                "notes": "Component design, hooks, state management.",
            }
        ],
        "learn_skills": [],
        "availability_windows": [
            {"day_of_week": 0, "start_time_utc": "10:00", "end_time_utc": "16:00"},
            {"day_of_week": 2, "start_time_utc": "12:00", "end_time_utc": "18:00"},
        ],
        "blackout_dates": [],
    }

    put_resp = await client.put(
        "/api/v1/swaps/profile/me", json=alice_update, headers=headers_alice
    )
    assert put_resp.status_code == 200
    alice_data = put_resp.json()

    # Private view should coarsen coords to 2 decimal places
    assert alice_data["coarse_lat"] == 37.77
    assert alice_data["coarse_lng"] == -122.42
    assert alice_data["area_label"] == "Mission District, San Francisco, CA"
    assert alice_data["is_18_confirmed"] is True
    assert len(alice_data["teach_skills"]) == 1
    assert len(alice_data["availability_windows"]) == 2

    # Bob sets his profile nearby in SoMa, SF (~37.78, -122.40) -> ~2.1 km away
    bob_update = {
        "bio": "Learning web dev.",
        "coarse_lat": 37.78,
        "coarse_lng": -122.40,
        "area_label": "SoMa, San Francisco, CA",
        "radius_km": 5,
        "modes": ["video", "in_person"],
        "languages": ["English"],
        "is_invisible": False,
        "accepts_newcomers": True,
        "is_18_confirmed": True,
        "teach_skills": [],
        "learn_skills": [],
        "availability_windows": [],
        "blackout_dates": [],
    }
    await client.put("/api/v1/swaps/profile/me", json=bob_update, headers=headers_bob)

    # Bob views Alice's public profile
    pub_resp = await client.get("/api/v1/swaps/profile/alice_mentor", headers=headers_bob)
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()

    # ── PRIVACY ASSERTIONS ───────────────────────────────────────────
    # 1. Ensure latitude/longitude keys are NOT present in public response
    assert "coarse_lat" not in pub_data
    assert "coarse_lng" not in pub_data
    assert "latitude" not in pub_data
    assert "longitude" not in pub_data
    assert "geohash" not in pub_data

    # 2. Distance bucket should be correctly calculated (~2.1 km -> '1–3 km')
    assert pub_data["distance_bucket"] == "1–3 km"
    assert pub_data["area_label"] == "Mission District, San Francisco, CA"
    assert pub_data["user"]["username"] == "alice_mentor"
    assert len(pub_data["teach_skills"]) == 1
    assert pub_data["teach_skills"][0]["skill"]["slug"] == "react-fundamentals"


@pytest.mark.asyncio
async def test_invisible_profile_hidden_from_others(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test that setting a profile to invisible prevents other users from viewing it."""
    alice, headers_alice = await create_user(username="alice_ghost", email="ghost@nexus.dev")
    bob, headers_bob = await create_user(username="bob_seeker", email="seeker@nexus.dev")

    # Alice sets invisible = True
    await client.put(
        "/api/v1/swaps/profile/me",
        json={
            "bio": "Private profile test",
            "is_invisible": True,
            "teach_skills": [],
            "learn_skills": [],
            "availability_windows": [],
            "blackout_dates": [],
        },
        headers=headers_alice,
    )

    # Bob tries to view Alice's profile -> 404
    resp = await client.get("/api/v1/swaps/profile/alice_ghost", headers=headers_bob)
    assert resp.status_code == 404

    # Alice can still view her own private profile
    own_resp = await client.get("/api/v1/swaps/profile/me", headers=headers_alice)
    assert own_resp.status_code == 200
    assert own_resp.json()["is_invisible"] is True


@pytest.mark.asyncio
async def test_distance_bucketing_calculations() -> None:
    """Verify distance bucketing logic with known coordinates."""
    # Co-located (< 1km)
    assert get_distance_bucket(37.77, -122.42, 37.772, -122.421) == "under 1 km"

    # Mission to SoMa (~2.1 km)
    assert get_distance_bucket(37.77, -122.42, 37.78, -122.40) == "1–3 km"

    # Mission to Presidio (~4.2 km)
    assert get_distance_bucket(37.77, -122.42, 37.80, -122.45) == "3–5 km"

    # SF to Oakland (~12 km)
    assert get_distance_bucket(37.77, -122.42, 37.80, -122.27) == "10–25 km"

    # SF to San Jose (~65 km -> remote)
    assert get_distance_bucket(37.77, -122.42, 37.33, -121.89) == "remote"

    # Missing coordinates -> remote
    assert get_distance_bucket(None, None, 37.77, -122.42) == "remote"
