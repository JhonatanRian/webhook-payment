from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.domain_exceptions import BusinessRuleViolationError
from app.core.exceptions.starkbank_exceptions import StarkBankIntegrationError
from app.modules.invoice.repository import InvoiceBatchRepository
from app.modules.invoice.service import InvoiceService
from app.modules.transfer.service import TransferService


@pytest.mark.asyncio
async def test_invoice_service_issue_batch_sdk_failure(db_session: AsyncSession) -> None:
    """If Stark Bank SDK fails, batch must be recorded as failed and error re-raised."""
    service = InvoiceService(session=db_session)

    with patch("starkbank.invoice.create", side_effect=RuntimeError("SDK Timeout")):
        with pytest.raises(StarkBankIntegrationError):
            await service.issue_batch(cycle_index=99, count=5)

    batch_repo = InvoiceBatchRepository(session=db_session)
    batch = await batch_repo.get_by_cycle(99)
    assert batch is not None
    assert batch.status == "failed"


@pytest.mark.asyncio
async def test_transfer_service_net_amount_zero_or_negative(db_session: AsyncSession) -> None:
    """Transfer where fee >= gross amount must raise BusinessRuleViolationError."""
    service = TransferService(session=db_session)

    # gross == fee (net = 0)
    with pytest.raises(BusinessRuleViolationError) as exc1:
        await service.transfer_credited_invoice(gross_amount=1000, fee=1000)
    assert "must be positive" in str(exc1.value)

    # gross < fee (net < 0)
    with pytest.raises(BusinessRuleViolationError) as exc2:
        await service.transfer_credited_invoice(gross_amount=500, fee=1000)
    assert "must be positive" in str(exc2.value)
