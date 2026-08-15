from unittest.mock import MagicMock, patch

import pytest
import starkbank
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import (
    DuplicateEventError,
    WebhookSignatureError,
)
from app.modules.invoice.model import InvoiceRecord
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository
from app.modules.webhook.service import WebhookService


async def test_webhook_missing_signature(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with pytest.raises(WebhookSignatureError):
        await service.process_webhook(body_bytes=b"{}", signature=None)

    with pytest.raises(WebhookSignatureError):
        await service.process_webhook(body_bytes=b"{}", signature="")


async def test_webhook_invalid_signature(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with patch("starkbank.event.parse", side_effect=Exception("Invalid signature")):
        with pytest.raises(WebhookSignatureError):
            await service.process_webhook(body_bytes=b"{}", signature="bad_sig")


async def test_webhook_stark_invalid_signature_error(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with patch(
        "starkbank.event.parse",
        side_effect=starkbank.error.InvalidSignatureError("Digital signature validation failed"),
    ):
        with pytest.raises(WebhookSignatureError):
            await service.process_webhook(body_bytes=b"{}", signature="bad_stark_sig")


async def test_webhook_general_parsing_exception(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with patch("starkbank.event.parse", side_effect=ValueError("Malformed JSON")):
        with pytest.raises(WebhookSignatureError):
            await service.process_webhook(body_bytes=b"{}", signature="some_sig")


async def test_webhook_credited_invoice_flow(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)
    inv_record = InvoiceRecord(
        stark_invoice_id="inv_123",
        amount=5000,
        tax_id="12345678909",
        name="Customer",
        status="created",
    )
    await inv_repo.create(inv_record, autocommit=True)

    service = WebhookService(session=db_session)
    mock_invoice = MagicMock(id="inv_123", amount=5000, fee=100)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_123", subscription="invoice", log=mock_log)

    mock_transfer_rec = MagicMock(id="tr_rec_999")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch(
            "app.modules.transfer.service.TransferService.transfer_credited_invoice",
            return_value=mock_transfer_rec,
        ) as mock_transfer:
            res = await service.process_webhook(body_bytes=b"{}", signature="sig_ok")

            assert res["status"] == "success"
            assert res["event_id"] == "evt_123"
            assert res["transfer_id"] == "tr_rec_999"
            assert mock_transfer.called

    updated_inv = await inv_repo.get_by_stark_id("inv_123")
    assert updated_inv is not None
    assert updated_inv.status == "credited"


async def test_webhook_credited_unknown_invoice_skips_transfer(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    mock_invoice = MagicMock(id="unknown_inv_999", amount=7500, fee=150)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_unknown", subscription="invoice", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch(
            "app.modules.transfer.service.TransferService.transfer_credited_invoice"
        ) as mock_transfer:
            res = await service.process_webhook(body_bytes=b"{}", signature="sig_ok")

            assert res["status"] == "success"
            assert res["event_id"] == "evt_unknown"
            assert res["transfer_id"] is None
            assert not mock_transfer.called


async def test_webhook_non_credited_event(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_log = MagicMock(type="created")
    mock_event = MagicMock(id="evt_reg_1", subscription="invoice", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_reg")
        assert res["status"] == "success"
        assert res["event_id"] == "evt_reg_1"
        assert res["transfer_id"] is None


async def test_webhook_duplicate_event_id(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_event = MagicMock(id="evt_duplicate", subscription="invoice", log=MagicMock(type="other"))

    with patch("starkbank.event.parse", return_value=mock_event):
        await service.process_webhook(body_bytes=b"{}", signature="sig1")

        with pytest.raises(DuplicateEventError):
            await service.process_webhook(body_bytes=b"{}", signature="sig2")


async def test_webhook_integrity_error_rollback(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_event = MagicMock(id="evt_integ", subscription="invoice", log=MagicMock(type="other"))

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch.object(
            service,
            "_persist_and_dispatch",
            side_effect=IntegrityError("stmt", {}, Exception("dup")),
        ):
            with pytest.raises(DuplicateEventError):
                await service.process_webhook(body_bytes=b"{}", signature="sig_integ")


async def test_webhook_unhandled_exception_rollback(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_event = MagicMock(id="evt_err", subscription="invoice", log=MagicMock(type="other"))

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch.object(
            service,
            "_persist_and_dispatch",
            side_effect=RuntimeError("Unexpected error during processing"),
        ):
            with pytest.raises(RuntimeError):
                await service.process_webhook(body_bytes=b"{}", signature="sig_err")


async def test_webhook_transfer_status_update(db_session: AsyncSession) -> None:
    """Stark Bank sends a transfer webhook — we update the local TransferRecord status."""
    # Create a local TransferRecord that was previously created with status "created"
    transfer_rec = TransferRecord(
        stark_transfer_id="stark_tr_001",
        stark_invoice_id="inv_001",
        event_id="evt_000",
        amount=5000,
        fee=0,
        net_amount=5000,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="123456",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    repo = TransferRepository(session=db_session)
    await repo.create(transfer_rec, autocommit=True)

    service = WebhookService(session=db_session)

    mock_transfer_obj = MagicMock(id="stark_tr_001", status="success")
    mock_log = MagicMock(type="success", transfer=mock_transfer_obj)
    mock_event = MagicMock(id="evt_transfer_001", subscription="transfer", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_transfer")

    assert res["status"] == "success"
    assert res["event_id"] == "evt_transfer_001"
    assert res["transfer_id"] is not None

    updated = await repo.get_by_stark_id("stark_tr_001")
    assert updated is not None
    assert updated.status == "success"


async def test_webhook_transfer_status_unknown_id_skips(db_session: AsyncSession) -> None:
    """Transfer webhook for an unknown stark_transfer_id should not raise — just skip."""
    service = WebhookService(session=db_session)

    mock_transfer_obj = MagicMock(id="stark_tr_unknown_999", status="success")
    mock_log = MagicMock(type="success", transfer=mock_transfer_obj)
    mock_event = MagicMock(id="evt_transfer_002", subscription="transfer", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_tr_unknown")

    assert res["status"] == "success"
    assert res["transfer_id"] is None


async def test_webhook_transfer_missing_transfer_obj_skips(db_session: AsyncSession) -> None:
    """Transfer webhook with no transfer object in log should be recorded but not crash."""
    service = WebhookService(session=db_session)

    mock_log = MagicMock(type="success", transfer=None)
    mock_event = MagicMock(id="evt_transfer_003", subscription="transfer", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_tr_none")

    assert res["status"] == "success"
    assert res["transfer_id"] is None


async def test_webhook_invoice_handler_no_invoice_obj_skips(db_session: AsyncSession) -> None:
    """Invoice handler should skip gracefully when log.invoice is None despite 'credited' type."""
    service = WebhookService(session=db_session)

    mock_log = MagicMock(type="credited", invoice=None)
    mock_event = MagicMock(id="evt_invoice_no_obj", subscription="invoice", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_inv_none")

    assert res["status"] == "success"
    assert res["transfer_id"] is None


async def test_webhook_transfer_handler_no_id_or_status_skips(db_session: AsyncSession) -> None:
    """Transfer handler should skip when transfer_obj has no id or status."""
    service = WebhookService(session=db_session)

    mock_transfer_obj = MagicMock(id=None, status=None)
    mock_log = MagicMock(type="success", transfer=mock_transfer_obj)
    mock_event = MagicMock(id="evt_transfer_no_id", subscription="transfer", log=mock_log)

    with patch("starkbank.event.parse", return_value=mock_event):
        res = await service.process_webhook(body_bytes=b"{}", signature="sig_tr_no_id")

    assert res["status"] == "success"
    assert res["transfer_id"] is None
