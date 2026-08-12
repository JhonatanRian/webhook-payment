from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice.service import InvoiceService


@pytest.mark.asyncio
async def test_generate_random_invoice_data(db_session: AsyncSession) -> None:
    service = InvoiceService(session=db_session)
    data = service.generate_random_invoice_data(10)
    assert len(data) == 10
    for item in data:
        assert "amount" in item
        assert 1000 <= item["amount"] <= 50000
        assert "tax_id" in item
        assert "name" in item


@pytest.mark.asyncio
async def test_issue_batch_success(db_session: AsyncSession) -> None:
    service = InvoiceService(session=db_session)

    mock_stark_invoices = [
        MagicMock(id=f"stark_inv_{i}", amount=10000, status="created") for i in range(10)
    ]

    with patch("starkbank.invoice.create", return_value=mock_stark_invoices) as mock_create:
        batch = await service.issue_batch(cycle_index=1, count=10)

        assert mock_create.called
        assert batch.cycle_index == 1
        assert batch.invoice_count == 10
        assert batch.status == "completed"
        assert len(batch.invoices) == 10
        assert batch.invoices[0].stark_invoice_id == "stark_inv_0"
