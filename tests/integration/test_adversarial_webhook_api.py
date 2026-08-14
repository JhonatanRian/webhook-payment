import asyncio
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_webhook_concurrent_requests_idempotency(async_client: AsyncClient) -> None:
    """Concurrent requests with identical event.id must prevent double payouts."""
    mock_stark_invoices = [MagicMock(id="inv_concurrent_1", amount=20000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

    mock_invoice = MagicMock(id="inv_concurrent_1", amount=20000, fee=100)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_concurrent_999", subscription="invoice", log=mock_log)
    mock_transfer = MagicMock(id="tr_stark_concurrent_1", status="success")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch("starkbank.transfer.create", return_value=[mock_transfer]) as mock_create:
            headers = {"Digital-Signature": "sig_concurrent"}

            tasks = [
                async_client.post(
                    "/api/v1/webhooks/starkbank",
                    content=b'{"event": {}}',
                    headers=headers,
                )
                for _ in range(5)
            ]
            responses = await asyncio.gather(*tasks)

            for res in responses:
                assert res.status_code == 200, f"Response failed: {res.text}"

            success_count = sum(1 for r in responses if r.json().get("status") == "success")
            dup_count = sum(1 for r in responses if r.json().get("status") == "ignored_duplicate")

            assert success_count == 1
            assert dup_count == 4
            assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_webhook_transfer_failure_allows_retry(async_client: AsyncClient) -> None:
    """If transfer fails on first attempt, webhook redelivery must be able to retry."""
    mock_stark_invoices = [MagicMock(id="inv_retry_1", amount=15000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

    mock_invoice = MagicMock(id="inv_retry_1", amount=15000, fee=200)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_fail_then_retry", subscription="invoice", log=mock_log)
    mock_transfer_ok = MagicMock(id="tr_stark_retry_ok", status="success")

    headers = {"Digital-Signature": "sig_retry"}

    with patch("starkbank.event.parse", return_value=mock_event):
        # 1st Attempt: Upstream API failure
        with patch("starkbank.transfer.create", side_effect=RuntimeError("StarkBank Timeout")):
            res1 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res1.status_code == 500

        # 2nd Attempt: Upstream API succeeds
        with patch("starkbank.transfer.create", return_value=[mock_transfer_ok]) as mock_create:
            res2 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res2.status_code == 200
            assert res2.json()["status"] == "success"
            assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_webhook_negative_or_zero_net_amount(async_client: AsyncClient) -> None:
    """Invoices where fee >= gross amount must be rejected with 422 Unprocessable Content."""
    mock_stark_invoices = [MagicMock(id="inv_neg_1", amount=500, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

    mock_invoice = MagicMock(id="inv_neg_1", amount=500, fee=600)  # Net = -100
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_neg_net", subscription="invoice", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        headers = {"Digital-Signature": "sig_neg"}
        res = await async_client.post(
            "/api/v1/webhooks/starkbank",
            content=b'{"event": {}}',
            headers=headers,
        )
        assert res.status_code == 422
        assert "must be positive" in res.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_corrupt_non_utf8_payload(async_client: AsyncClient) -> None:
    """Payloads with corrupt bytes must return 400 Bad Request."""
    headers = {"Digital-Signature": "sig_invalid"}
    res = await async_client.post(
        "/api/v1/webhooks/starkbank",
        content=b"\x80\x81\xfe\xff",
        headers=headers,
    )
    assert res.status_code == 400
