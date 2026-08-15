from unittest.mock import MagicMock, patch

from httpx import AsyncClient


async def test_webhook_endpoint_missing_signature(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/webhooks/starkbank", json={})
    assert response.status_code == 400
    assert (
        "Digital-Signature" in response.json()["detail"] or "signature" in response.json()["detail"]
    )


async def test_webhook_endpoint_credited_event(async_client: AsyncClient) -> None:
    mock_stark_invoices = [MagicMock(id="inv_test_1", amount=15000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

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


async def test_webhook_endpoint_duplicate_event_returns_200(async_client: AsyncClient) -> None:
    mock_stark_invoices = [MagicMock(id="inv_dup_1", amount=5000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

    mock_invoice = MagicMock(id="inv_dup_1", amount=5000, fee=0)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_dup_1", subscription="invoice", log=mock_log)
    mock_transfer = MagicMock(id="tr_dup_1", status="success")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch("starkbank.transfer.create", return_value=[mock_transfer]):
            headers = {"Digital-Signature": "valid_sig"}

            res1 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res1.status_code == 200

            res2 = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res2.status_code == 200
            assert res2.json()["status"] == "ignored_duplicate"


async def test_webhook_endpoint_transfer_status_update_event(async_client: AsyncClient) -> None:
    """E2E test: Credited invoice creates a transfer,
    and subsequent transfer webhook updates its status.
    """
    # 1. Create invoice
    mock_stark_invoices = [MagicMock(id="inv_transfer_flow_1", amount=20000, status="created")]
    with patch("starkbank.invoice.create", return_value=mock_stark_invoices):
        await async_client.post("/api/v1/invoices/batch?count=1")

    # 2. Receive invoice credited webhook -> creates transfer with status 'created'
    mock_invoice = MagicMock(id="inv_transfer_flow_1", amount=20000, fee=0)
    mock_log_inv = MagicMock(type="credited", invoice=mock_invoice)
    mock_event_inv = MagicMock(id="evt_inv_flow_1", subscription="invoice", log=mock_log_inv)
    mock_transfer = MagicMock(id="stark_tr_flow_999", status="created")

    headers = {"Digital-Signature": "valid_signature_string"}

    with patch("starkbank.event.parse", return_value=mock_event_inv):
        with patch("starkbank.transfer.create", return_value=[mock_transfer]):
            res_inv = await async_client.post(
                "/api/v1/webhooks/starkbank",
                content=b'{"event": {}}',
                headers=headers,
            )
            assert res_inv.status_code == 200

    # 3. Verify transfer record is initially 'created' in DB
    transfers_before = await async_client.get("/api/v1/transfers")
    items_before = transfers_before.json()["items"]
    target_item = next(
        (t for t in items_before if t["stark_transfer_id"] == "stark_tr_flow_999"), None
    )
    assert target_item is not None
    assert target_item["status"] == "created"

    # 4. Receive transfer webhook event ('success')
    mock_transfer_success = MagicMock(id="stark_tr_flow_999", status="success")
    mock_log_tr = MagicMock(type="success", transfer=mock_transfer_success)
    mock_event_tr = MagicMock(id="evt_tr_flow_1", subscription="transfer", log=mock_log_tr)

    with patch("starkbank.event.parse", return_value=mock_event_tr):
        res_tr = await async_client.post(
            "/api/v1/webhooks/starkbank",
            content=b'{"event": {}}',
            headers=headers,
        )
        assert res_tr.status_code == 200
        assert res_tr.json()["status"] == "success"

    # 5. Verify transfer record status updated to 'success' in DB
    transfers_after = await async_client.get("/api/v1/transfers")
    items_after = transfers_after.json()["items"]
    target_item_after = next(
        (t for t in items_after if t["stark_transfer_id"] == "stark_tr_flow_999"), None
    )
    assert target_item_after is not None
    assert target_item_after["status"] == "success"
