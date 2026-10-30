"""
Health and Readiness Endpoint Tests
====================================
Tests:
- GET /health (Liveness probe - always returns 200 when service is running)
- GET /ready  (Readiness probe - returns 200 when DB is connected, 503 when unreachable)
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
    assert data["service"] == "nexus-social-api"


@pytest.mark.asyncio
async def test_ready_probe(client: AsyncClient) -> None:
    """
    GET /ready checks database connectivity:
    - Returns 200 with status: ready if DB is connected
    - Returns 503 with status: not_ready if DB is offline
    """
    response = await client.get("/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert data["database"] == "connected"
    else:
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
