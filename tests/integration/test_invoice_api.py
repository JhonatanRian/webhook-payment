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
    res = await async_client.get("/api/v1/invoices/batches?page=1&size=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert data["page"] == 1
    assert data["size"] == 10
    assert isinstance(data["items"], list)


async def test_list_invoices_api(async_client: AsyncClient) -> None:
    res = await async_client.get("/api/v1/invoices?page=1&size=10&status=created")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["size"] == 10
    assert isinstance(data["items"], list)
