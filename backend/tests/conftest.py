"""
Pytest Configuration and Fixtures
===================================
Provides shared fixtures for all backend tests:
- Async test client (TestClient wrapping the FastAPI app)
- In-memory test database (Stage 1+)
- Auth helpers (Stage 2+)
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP test client for the FastAPI app."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
