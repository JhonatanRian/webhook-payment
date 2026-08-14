from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.starkbank_exceptions import StarkBankIntegrationError
from app.modules.invoice.repository import InvoiceBatchRepository
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.repository import ScheduleCycleRepository


async def test_generate_random_invoice_data(db_session: AsyncSession) -> None:
    service = InvoiceService(session=db_session)
    data = service.generate_random_invoice_data(10)
    assert len(data) == 10
    for item in data:
        assert "amount" in item
        assert 1000 <= item["amount"] <= 50000
        assert "tax_id" in item
        assert "name" in item


async def test_issue_batch_invoice_success(db_session: AsyncSession) -> None:
    service = InvoiceService(session=db_session)

    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=10000, status="created") for i in range(10)
    ]

    with patch("starkbank.invoice.create", return_value=mock_stark_invoices) as mock_create:
        batch = await service.issue_batch(cycle_index=1, count=10, trigger_type="manual")

        assert mock_create.called
        assert batch.cycle_index == 1
        assert batch.invoice_count == 10
        assert batch.status == "completed"
        assert len(batch.invoices) == 10
        assert batch.invoices[0].stark_invoice_id == "stark_inv_0"

    batch_repo = InvoiceBatchRepository(session=db_session)
    retrieved = await batch_repo.get_by_cycle(1)
    assert retrieved is not None
    assert retrieved.id == batch.id

    cycle_repo = ScheduleCycleRepository(session=db_session)
    cycle = await cycle_repo.get_by_cycle_index(1)
    assert cycle is not None
    assert cycle.status == "completed"
    assert cycle.trigger_type == "manual"


async def test_issue_batch_failure_branch(db_session: AsyncSession) -> None:
    service = InvoiceService(session=db_session)

    with patch("starkbank.invoice.create", side_effect=RuntimeError("SDK Error")):
        with pytest.raises(StarkBankIntegrationError):
            await service.issue_batch(cycle_index=2, count=5, trigger_type="manual")

    batch_repo = InvoiceBatchRepository(session=db_session)
    failed_batch = await batch_repo.get_by_cycle(2)
    assert failed_batch is not None
    assert failed_batch.status == "failed"

    cycle_repo = ScheduleCycleRepository(session=db_session)
    cycle = await cycle_repo.get_by_cycle_index(2)
    assert cycle is not None
    assert cycle.status == "failed"
