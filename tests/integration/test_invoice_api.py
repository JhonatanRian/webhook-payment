from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def test_trigger_invoice_batch_api(async_client: AsyncClient) -> None:
    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=10000, status="created") for i in range(8)
    ]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        res = await async_client.post("/api/v1/invoices/batch?count=8")
        assert res.status_code == 201
        data = res.json()
        assert data["cycle_index"] == 0
        assert data["invoice_count"] == 8
        assert data["status"] == "completed"
        assert len(data["invoices"]) == 8


async def test_list_invoice_batches_api(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/invoices/batches")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
