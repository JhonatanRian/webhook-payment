from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import BusinessRuleViolationError
from app.modules.transfer.service import TransferService


@pytest.mark.asyncio
async def test_transfer_credited_invoice_success(db_session: AsyncSession) -> None:
    service = TransferService(session=db_session)
    mock_transfer = MagicMock(id="stark_tr_123", status="success")

    with patch("starkbank.transfer.create", return_value=[mock_transfer]) as mock_create:
        record = await service.transfer_credited_invoice(
            gross_amount=10000,
            fee=500,
            stark_invoice_id="inv_999",
            event_id="evt_888",
        )

        assert mock_create.called
        assert record.amount == 10000
        assert record.fee == 500
        assert record.net_amount == 9500
        assert record.stark_transfer_id == "stark_tr_123"
        assert record.status == "success"


@pytest.mark.asyncio
async def test_transfer_credited_invoice_zero_or_negative_net_amount(
    db_session: AsyncSession,
) -> None:
    service = TransferService(session=db_session)
    with pytest.raises(BusinessRuleViolationError):
        await service.transfer_credited_invoice(gross_amount=500, fee=500)
