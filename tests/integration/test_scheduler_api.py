from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def test_scheduler_status_api(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/scheduler/status")
    assert res.status_code == 200
    data = res.json()
    assert "scheduled_cycles_completed" in data
    assert "manual_triggers_completed" in data
    assert data["max_cycles"] == 8
    assert data["interval_minutes"] == 180
    assert "remaining_cycles" in data
    assert "mode" in data
    assert "is_running" in data
    assert "is_paused" not in data


async def test_trigger_manual_cycle_does_not_consume_scheduled_quota(
    async_client: AsyncClient,
) -> None:
    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=12000, status="created") for i in range(10)
    ]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        res = await async_client.post("/api/v1/scheduler/trigger")
        assert res.status_code == 202
        assert "message" in res.json()

    status_res = await async_client.get("/api/v1/scheduler/status")
    status_data = status_res.json()
    assert status_data["scheduled_cycles_completed"] == 0
    assert status_data["manual_triggers_completed"] >= 1
    assert status_data["remaining_cycles"] == 8


async def test_invoices_batch_post_increments_manual_triggers_count(
    async_client: AsyncClient,
) -> None:
    initial_res = await async_client.get("/api/v1/scheduler/status")
    initial_manual_count = initial_res.json()["manual_triggers_completed"]

    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=10000, status="created") for i in range(5)
    ]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        res = await async_client.post("/api/v1/invoices/batch?count=5")
        assert res.status_code == 201

    status_res = await async_client.get("/api/v1/scheduler/status")
    status_data = status_res.json()
    assert status_data["manual_triggers_completed"] == initial_manual_count + 1


async def test_update_scheduler_mode_api(async_client: AsyncClient) -> None:
    res = await async_client.put(
        "/api/v1/scheduler/mode",
        json={"mode": "recurring"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "recurring"

    status_res = await async_client.get("/api/v1/scheduler/status")
    assert status_res.json()["mode"] == "recurring"

    # Reset to default once
    await async_client.put(
        "/api/v1/scheduler/mode",
        json={"mode": "once"},
    )


async def test_reset_scheduler_cycles_api(async_client: AsyncClient) -> None:
    res = await async_client.post("/api/v1/scheduler/reset")
    assert res.status_code == 200
    assert "message" in res.json()


async def test_scheduler_status_custom_max_cycles(async_client: AsyncClient) -> None:
    with patch("app.modules.scheduler.router.settings.SCHEDULER_MAX_CYCLES", 12):
        res = await async_client.get("/api/v1/scheduler/status")
        assert res.status_code == 200
        data = res.json()
        assert data["max_cycles"] == 12
