"""
Health Endpoint Tests
======================
Stage 0 test: Verify /health and /ready return 200.
These are the only endpoints that exist before Stage 1.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /health should return 200 with status: ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


@pytest.mark.asyncio
async def test_ready_returns_ready(client: AsyncClient) -> None:
    """GET /ready should return 200 with status: ready."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
