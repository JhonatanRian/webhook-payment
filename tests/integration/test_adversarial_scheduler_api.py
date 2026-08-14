import asyncio
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.modules.scheduler.service import set_current_mode


@pytest.mark.asyncio
async def test_scheduler_concurrent_manual_and_scheduled_triggers(
    async_client: AsyncClient,
) -> None:
    """Concurrent manual triggers should not corrupt batch count or cause deadlocks."""
    mock_invoices = [
        MagicMock(id=f"inv_sched_{i}", amount=10000, status="created") for i in range(10)
    ]

    with patch("starkbank.invoice.create", return_value=mock_invoices):
        tasks = [
            async_client.post("/api/v1/scheduler/trigger"),
            async_client.post("/api/v1/scheduler/trigger"),
        ]
        responses = await asyncio.gather(*tasks)

        for r in responses:
            assert r.status_code == 202

    status_res = await async_client.get("/api/v1/scheduler/status")
    status_data = status_res.json()
    assert status_data["manual_triggers_completed"] >= 2


@pytest.mark.asyncio
async def test_scheduler_invalid_mode_fallback(async_client: AsyncClient) -> None:
    """Invalid scheduler modes should be rejected with HTTP 422 Unprocessable Entity."""
    res = await async_client.put(
        "/api/v1/scheduler/mode",
        json={"mode": "DROP TABLE; --"},
    )
    assert res.status_code == 422

    status_res = await async_client.get("/api/v1/scheduler/status")
    assert status_res.json()["mode"] == "once"

    set_current_mode("once")


@pytest.mark.asyncio
async def test_scheduler_reset_during_active_history(async_client: AsyncClient) -> None:
    """Cycle reset should clear the database and zero all status counters."""
    mock_invoices = [MagicMock(id="inv_reset_1", amount=10000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_invoices):
        await async_client.post("/api/v1/scheduler/trigger")

    reset_res = await async_client.post("/api/v1/scheduler/reset")
    assert reset_res.status_code == 200

    status_res = await async_client.get("/api/v1/scheduler/status")
    assert status_res.json()["manual_triggers_completed"] == 0
    assert status_res.json()["scheduled_cycles_completed"] == 0
