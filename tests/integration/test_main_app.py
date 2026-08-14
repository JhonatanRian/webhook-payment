import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, health_check


@pytest.mark.asyncio
async def test_health_check_direct() -> None:
    res = await health_check()
    assert res == {"status": "ok", "service": "webhook-payment"}


@pytest.mark.asyncio
async def test_health_check_http_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "service": "webhook-payment"}
