from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scheduler_status_api(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/scheduler/status")
    assert res.status_code == 200
    data = res.json()
    assert data["completed_cycles"] == 0
    assert data["max_cycles"] == 8
    assert data["remaining_cycles"] == 8


@pytest.mark.asyncio
async def test_trigger_manual_cycle_api(async_client: AsyncClient) -> None:
    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=12000, status="created") for i in range(10)
    ]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        res = await async_client.post("/api/v1/scheduler/trigger")
        assert res.status_code == 202
        assert "message" in res.json()
