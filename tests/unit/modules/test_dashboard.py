from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.service import DashboardService
from app.modules.invoice.model import InvoiceRecord
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository


async def test_dashboard_summary_empty_database(db_session: AsyncSession) -> None:
    service = DashboardService(session=db_session)
    summary = await service.get_summary()

    assert summary.total_invoiced_cents == 0
    assert summary.total_invoices_count == 0
    assert summary.total_credited_cents == 0
    assert summary.total_credited_count == 0
    assert summary.total_liquidated_cents == 0
    assert summary.total_liquidated_count == 0
    assert summary.conversion_rate_percentage == 0.0


async def test_dashboard_summary_populated_database(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)
    tr_repo = TransferRepository(session=db_session)

    # 1. Create Invoices
    inv1 = InvoiceRecord(
        stark_invoice_id="inv_db_1",
        amount=10000,
        tax_id="12345678909",
        name="User 1",
        status="credited",
    )
    inv2 = InvoiceRecord(
        stark_invoice_id="inv_db_2",
        amount=20000,
        tax_id="12345678909",
        name="User 2",
        status="paid",
    )
    inv3 = InvoiceRecord(
        stark_invoice_id="inv_db_3",
        amount=15000,
        tax_id="12345678909",
        name="User 3",
        status="created",
    )
    inv4 = InvoiceRecord(
        stark_invoice_id="inv_db_4",
        amount=5000,
        tax_id="12345678909",
        name="User 4",
        status="canceled",
    )

    await inv_repo.create(inv1, autocommit=False)
    await inv_repo.create(inv2, autocommit=False)
    await inv_repo.create(inv3, autocommit=False)
    await inv_repo.create(inv4, autocommit=False)

    # 2. Create Transfers
    tr1 = TransferRecord(
        stark_transfer_id="tr_db_1",
        stark_invoice_id="inv_db_1",
        event_id="evt_db_1",
        amount=10000,
        fee=100,
        net_amount=9900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="123456",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="success",
    )
    tr2 = TransferRecord(
        stark_transfer_id="tr_db_2",
        stark_invoice_id="inv_db_2",
        event_id="evt_db_2",
        amount=20000,
        fee=200,
        net_amount=19800,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="123456",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="failed",
    )

    await tr_repo.create(tr1, autocommit=False)
    await tr_repo.create(tr2, autocommit=True)

    service = DashboardService(session=db_session)
    summary = await service.get_summary()

    # Total Invoiced = 10000 + 20000 + 15000 + 5000 = 50000 cents
    assert summary.total_invoiced_cents == 50000
    assert summary.total_invoices_count == 4

    # Total Credited/Paid = 10000 (credited) + 20000 (paid) = 30000 cents
    assert summary.total_credited_cents == 30000
    assert summary.total_credited_count == 2

    # Total Liquidated (only success) = 9900 cents
    assert summary.total_liquidated_cents == 9900
    assert summary.total_liquidated_count == 1

    # Conversion Rate = 2 / 4 * 100 = 50.0%
    assert summary.conversion_rate_percentage == 50.0
