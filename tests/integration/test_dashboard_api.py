import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice.model import InvoiceRecord
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository


@pytest.mark.asyncio
async def test_get_dashboard_summary_endpoint(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)
    tr_repo = TransferRepository(session=db_session)

    inv = InvoiceRecord(
        stark_invoice_id="inv_api_1",
        amount=12000,
        tax_id="12345678909",
        name="API User",
        status="credited",
    )
    await inv_repo.create(inv, autocommit=True)

    tr = TransferRecord(
        stark_transfer_id="tr_api_1",
        stark_invoice_id="inv_api_1",
        event_id="evt_api_1",
        amount=12000,
        fee=100,
        net_amount=11900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="123456",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="success",
    )
    await tr_repo.create(tr, autocommit=True)

    response = await async_client.get("/dashboard/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["total_invoiced_cents"] == 12000
    assert data["total_invoices_count"] == 1
    assert data["total_credited_cents"] == 12000
    assert data["total_credited_count"] == 1
    assert data["total_liquidated_cents"] == 11900
    assert data["total_liquidated_count"] == 1
    assert data["conversion_rate_percentage"] == 100.0
