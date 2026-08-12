from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_endpoint_missing_signature(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/webhooks/starkbank", json={})
    assert response.status_code == 400
    assert (
        "Digital-Signature" in response.json()["detail"] or "signature" in response.json()["detail"]
    )


@pytest.mark.asyncio
async def test_webhook_endpoint_credited_event(async_client: AsyncClient) -> None:
    mock_invoice = MagicMock(id="inv_test_1", amount=15000, fee=200)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_test_1", subscription="invoice", log=mock_log)
    mock_transfer = MagicMock(id="stark_tr_999", status="success")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch("starkbank.transfer.create", return_value=[mock_transfer]):
            headers = {"Digital-Signature": "valid_signature_string"}
            response = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["event_id"] == "evt_test_1"
            assert data["transfer_id"] is not None


@pytest.mark.asyncio
async def test_webhook_endpoint_duplicate_event_returns_200(async_client: AsyncClient) -> None:
    mock_invoice = MagicMock(id="inv_dup_1", amount=5000, fee=0)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_dup_1", subscription="invoice", log=mock_log)
    mock_transfer = MagicMock(id="tr_dup_1", status="success")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch("starkbank.transfer.create", return_value=[mock_transfer]):
            headers = {"Digital-Signature": "valid_sig"}

            # First post -> 200 OK success
            res1 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res1.status_code == 200

            # Second post with same event.id -> 200 OK ignored duplicate
            res2 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res2.status_code == 200
            assert res2.json()["status"] == "ignored_duplicate"
