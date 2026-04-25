"""Basic tests for the Catch-Up backend."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_catchup_endpoints_exist():
    """Verify all critical endpoints return something (not 404)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # These should all return 200 (even if just stubs)
        for path in ["/users/me", "/friends", "/groups", "/catchups", "/memories", "/feedbacks"]:
            r = await client.get(path)
            assert r.status_code == 200, f"{path} returned {r.status_code}"
