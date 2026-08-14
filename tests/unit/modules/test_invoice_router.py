import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice.model import InvoiceBatch, InvoiceRecord
from app.modules.invoice.router import list_invoice_batches, list_invoices, trigger_invoice_batch
from app.shared.pagination import PaginatedResult, PaginationParams


@pytest.mark.asyncio
async def test_trigger_invoice_batch_direct(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    mock_batch = InvoiceBatch(
        id=uuid.uuid4(),
        cycle_index=0,
        invoice_count=8,
        status="completed",
        created=now,
        updated=now,
    )
    with patch(
        "app.modules.invoice.service.InvoiceService.issue_batch",
        new_callable=AsyncMock,
        return_value=mock_batch,
    ):
        res = await trigger_invoice_batch(count=8, db=db_session)
        assert res.cycle_index == 0
        assert res.invoice_count == 8


@pytest.mark.asyncio
async def test_list_invoice_batches_direct(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    mock_batch = InvoiceBatch(
        id=uuid.uuid4(),
        cycle_index=1,
        invoice_count=10,
        status="completed",
        created=now,
        updated=now,
    )
    mock_result = PaginatedResult(items=[mock_batch], total=1, page=1, size=20)

    with patch(
        "app.modules.invoice.repository.InvoiceBatchRepository.paginate_batches",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        res = await list_invoice_batches(
            params=PaginationParams(page=1, size=20),
            db=db_session,
        )
        assert res.total == 1
        assert len(res.items) == 1
        assert res.items[0].cycle_index == 1


@pytest.mark.asyncio
async def test_list_invoices_direct(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    mock_invoice = InvoiceRecord(
        id=uuid.uuid4(),
        stark_invoice_id="inv_123",
        amount=1000,
        tax_id="12345678909",
        name="John Doe",
        status="credited",
        created=now,
        updated=now,
    )
    mock_result = PaginatedResult(items=[mock_invoice], total=1, page=1, size=20)

    with patch(
        "app.modules.invoice.repository.InvoiceRecordRepository.paginate_invoices",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        res = await list_invoices(
            status_filter="credited",
            params=PaginationParams(page=1, size=20),
            db=db_session,
        )
        assert res.total == 1
        assert len(res.items) == 1
        assert res.items[0].stark_invoice_id == "inv_123"
