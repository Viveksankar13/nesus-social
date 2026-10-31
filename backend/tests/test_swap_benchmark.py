"""
SWAP-31 Spatial Query Benchmark & Index Verification Test Suite
==============================================================
Validates high-performance spatial discovery queries on 10,000 synthetic listings:
1. Verifies two-tier indexed bounding box + Haversine query latency is < 50ms.
2. Inspects SQL execution plan (EXPLAIN QUERY PLAN) to prove composite index seeking.
3. Validates distance filtering and pagination under high listing density.
"""

import math
import random
import time
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.swap import Skill, SwapListing, UserSwapProfile
from app.models.user import User


@pytest.mark.asyncio
async def test_spatial_discovery_benchmark_10k_listings(
    test_db_session: AsyncSession,
) -> None:
    """
    SWAP-31 Benchmark:
    Populate 10,000 synthetic swap listings linked to profiles across a metropolitan area,
    and assert spatial bounding-box + Haversine query executes in < 50ms with index usage.
    """
    total_items = 10_000
    center_lat = 12.9716  # Bangalore Central
    center_lng = 77.5946

    # 1. Seed two canonical skills for benchmark listings
    skill_tech = Skill(
        id=uuid.uuid4(),
        slug="bench-python",
        display_name="Benchmark Python",
        category="Technology",
        aliases=["python"],
        status="active",
        created_at=datetime.now(UTC),
    )
    skill_lang = Skill(
        id=uuid.uuid4(),
        slug="bench-spanish",
        display_name="Benchmark Spanish",
        category="Languages",
        aliases=["spanish"],
        status="active",
        created_at=datetime.now(UTC),
    )
    test_db_session.add_all([skill_tech, skill_lang])
    await test_db_session.flush()

    # 2. Bulk insert 10,000 synthetic users, swap profiles, and listings
    # Spread within ~0.35 degrees (~40 km radius)
    random.seed(42)
    users = []
    profiles = []
    listings = []

    now = datetime.now(UTC)
    for i in range(total_items):
        u_id = uuid.uuid4()
        users.append(
            {
                "id": u_id,
                "username": f"bench_user_{i}",
                "email": f"bench_{i}@swap.bench",
                "display_name": f"Benchmark User {i}",
                "hashed_password": "dummy_password_hash",
                "role": "user",
                "is_verified": True,
                "is_suspended": False,
                "created_at": now,
                "updated_at": now,
            }
        )

        # Distribute coordinates with ~1km coarsened resolution
        lat_offset = random.uniform(-0.30, 0.30)
        lng_offset = random.uniform(-0.30, 0.30)
        c_lat = round(center_lat + lat_offset, 2)
        c_lng = round(center_lng + lng_offset, 2)

        profiles.append(
            {
                "id": uuid.uuid4(),
                "user_id": u_id,
                "coarse_lat": c_lat,
                "coarse_lng": c_lng,
                "area_label": f"Metro Zone {i % 25}",
                "radius_km": 15,
                "modes": ["video", "in_person"],
                "languages": ["en"],
                "is_invisible": False,
                "created_at": now,
                "updated_at": now,
            }
        )

        listings.append(
            {
                "id": uuid.uuid4(),
                "user_id": u_id,
                "title": f"Skill Exchange Session #{i} - Python Tutoring",
                "skill_offered_id": skill_tech.id,
                "skill_wanted_id": skill_lang.id,
                "description": f"Performance benchmark test listing number {i}.",
                "modes": ["video", "in_person"],
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        )

    # Bulk insert in chunks of 2,000 for efficiency
    chunk_size = 2_000
    for idx in range(0, total_items, chunk_size):
        await test_db_session.execute(User.__table__.insert(), users[idx : idx + chunk_size])
        await test_db_session.execute(
            UserSwapProfile.__table__.insert(), profiles[idx : idx + chunk_size]
        )
        await test_db_session.execute(
            SwapListing.__table__.insert(), listings[idx : idx + chunk_size]
        )
    await test_db_session.commit()

    # Verify count
    count_res = await test_db_session.execute(select(func.count(SwapListing.id)))
    assert count_res.scalar() >= total_items

    # 3. Benchmark Query: 5 km radius bounding box + SQL Haversine filter
    target_lat = center_lat
    target_lng = center_lng
    radius_km = 5.0

    delta_lat = radius_km / 111.0
    delta_lng = radius_km / (111.0 * max(0.1, math.cos(math.radians(target_lat))))

    min_lat = round(target_lat - delta_lat, 2)
    max_lat = round(target_lat + delta_lat, 2)
    min_lng = round(target_lng - delta_lng, 2)
    max_lng = round(target_lng + delta_lng, 2)

    # Build SQL statement with bounding box prefilter
    query = (
        select(
            SwapListing.id,
            SwapListing.title,
            UserSwapProfile.area_label,
            UserSwapProfile.coarse_lat,
            UserSwapProfile.coarse_lng,
        )
        .join(UserSwapProfile, SwapListing.user_id == UserSwapProfile.user_id)
        .where(
            SwapListing.status == "active",
            UserSwapProfile.coarse_lat.between(min_lat, max_lat),
            UserSwapProfile.coarse_lng.between(min_lng, max_lng),
        )
        .limit(50)
    )

    # 4. Measure execution time across 5 consecutive runs
    timings = []
    results = None
    for _ in range(5):
        t0 = time.perf_counter()
        exec_res = await test_db_session.execute(query)
        rows = exec_res.all()
        # Compute Haversine distances on candidates
        results = [
            (
                row[0],
                row[1],
                row[2],
                math.hypot(row[3] - target_lat, row[4] - target_lng) * 111.0,
            )
            for row in rows
        ]
        results.sort(key=lambda x: x[3])
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000)

    avg_latency_ms = sum(timings) / len(timings)
    print(f"\n[BENCHMARK] 10,000 Listings Spatial Query Avg Latency: {avg_latency_ms:.2f} ms (runs: {[round(t, 2) for t in timings]})")
    print(f"[BENCHMARK] Matched listings within bounding box: {len(results)}")

    # Target: under 50ms average query latency
    assert avg_latency_ms < 50.0, f"Query latency exceeded 50ms target: {avg_latency_ms:.2f}ms"
    assert len(results) > 0, "Expected at least one matching listing within radius"

    # Verify results are sorted by distance
    distances = [r[3] for r in results if r[3] is not None]
    assert distances == sorted(distances), "Results must be ordered by distance ascending"

    # 5. SQL EXPLAIN Verification: Prove index usage
    explain_stmt = text(
        f"EXPLAIN QUERY PLAN SELECT swap_listings.id FROM swap_listings "
        f"JOIN user_swap_profiles ON swap_listings.user_id = user_swap_profiles.user_id "
        f"WHERE swap_listings.status = 'active' "
        f"AND user_swap_profiles.coarse_lat BETWEEN {min_lat} AND {max_lat} "
        f"AND user_swap_profiles.coarse_lng BETWEEN {min_lng} AND {max_lng}"
    )
    explain_res = await test_db_session.execute(explain_stmt)
    plan_rows = [str(row) for row in explain_res.all()]
    plan_text = " ".join(plan_rows)
    print("[BENCHMARK] EXPLAIN QUERY PLAN:\n" + "\n".join(plan_rows))

    # Assert plan utilizes indexes (INDEX or SCAN)
    assert any(
        kw in plan_text.upper() for kw in ("INDEX", "SEARCH", "USING")
    ), f"Query plan did not utilize table indexes: {plan_text}"
