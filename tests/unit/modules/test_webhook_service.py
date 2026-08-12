from unittest.mock import MagicMock, patch

import pytest
import starkbank
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import (
    DuplicateEventError,
    WebhookSignatureError,
)
from app.modules.webhook.service import WebhookService


@pytest.mark.asyncio
async def test_webhook_missing_signature(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with pytest.raises(WebhookSignatureError):
        await service.process_webhook(body_bytes=b"{}", signature=None)


@pytest.mark.asyncio
async def test_webhook_invalid_signature(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)
    with patch(
        "starkbank.event.parse",
        side_effect=starkbank.error.InvalidSignatureError("Invalid signature"),
    ):
        with pytest.raises(WebhookSignatureError):
            await service.process_webhook(body_bytes=b"{}", signature="bad_sig")


@pytest.mark.asyncio
async def test_webhook_credited_invoice_flow(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_invoice = MagicMock(id="inv_100", amount=20000, fee=100)
    mock_log = MagicMock(type="credited", invoice=mock_invoice)
    mock_event = MagicMock(id="evt_555", subscription="invoice", log=mock_log)

    mock_transfer_record = MagicMock(id="tr_record_id")

    with patch("starkbank.event.parse", return_value=mock_event):
        with patch.object(
            service.transfer_service,
            "transfer_credited_invoice",
            return_value=mock_transfer_record,
        ) as mock_transfer_call:
            res = await service.process_webhook(body_bytes=b"{}", signature="valid_sig")

            assert res["status"] == "success"
            assert res["event_id"] == "evt_555"
            assert res["transfer_id"] == "tr_record_id"
            mock_transfer_call.assert_called_once_with(
                gross_amount=20000,
                fee=100,
                stark_invoice_id="inv_100",
                event_id="evt_555",
            )


@pytest.mark.asyncio
async def test_webhook_duplicate_event_id(db_session: AsyncSession) -> None:
    service = WebhookService(session=db_session)

    mock_event = MagicMock(id="evt_duplicate", subscription="invoice", log=MagicMock(type="other"))

    with patch("starkbank.event.parse", return_value=mock_event):
        # Process first time
        await service.process_webhook(body_bytes=b"{}", signature="sig1")

        # Process second time -> duplicate
        with pytest.raises(DuplicateEventError):
            await service.process_webhook(body_bytes=b"{}", signature="sig2")
