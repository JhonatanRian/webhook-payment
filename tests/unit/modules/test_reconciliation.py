from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoice.model import InvoiceRecord
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.scheduler.reconciliation import ReconciliationService
from app.modules.scheduler.service import execute_reconciliation_job
from app.modules.transfer.model import TransferRecord
from app.modules.transfer.repository import TransferRepository


@pytest.mark.asyncio
async def test_reconcile_invoices_paid_recovers_payout(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)
    tr_repo = TransferRepository(session=db_session)

    inv = InvoiceRecord(
        stark_invoice_id="inv_rec_1",
        amount=10000,
        tax_id="12345678909",
        name="Customer 1",
        status="created",
    )
    await inv_repo.create(inv, autocommit=True)

    mock_stark_inv = MagicMock(id="inv_rec_1", amount=10000, fee=100, status="paid")
    mock_stark_tr = MagicMock(id="tr_rec_recovered_1", status="success")

    service = ReconciliationService(session=db_session)

    with patch("starkbank.invoice.get", return_value=mock_stark_inv):
        with patch("starkbank.transfer.create", return_value=[mock_stark_tr]):
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            updated_count = await service.reconcile_invoices(cutoff=cutoff)

            assert updated_count == 1

    updated_inv = await inv_repo.get_by_stark_id("inv_rec_1")
    assert updated_inv is not None
    assert updated_inv.status == "paid"

    recovered_tr = await tr_repo.get_by_invoice_id("inv_rec_1")
    assert recovered_tr is not None
    assert recovered_tr.net_amount == 9900


@pytest.mark.asyncio
async def test_reconcile_invoices_already_has_transfer(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)
    tr_repo = TransferRepository(session=db_session)

    inv = InvoiceRecord(
        stark_invoice_id="inv_rec_2",
        amount=15000,
        tax_id="12345678909",
        name="Customer 2",
        status="created",
    )
    await inv_repo.create(inv, autocommit=True)

    tr = TransferRecord(
        stark_invoice_id="inv_rec_2",
        amount=15000,
        fee=200,
        net_amount=14800,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="success",
    )
    await tr_repo.create(tr, autocommit=True)

    mock_stark_inv = MagicMock(id="inv_rec_2", amount=15000, fee=200, status="credited")

    service = ReconciliationService(session=db_session)

    with patch("starkbank.invoice.get", return_value=mock_stark_inv):
        with patch("starkbank.transfer.create") as mock_tr_create:
            cutoff = datetime.now(UTC) - timedelta(hours=24)
            updated_count = await service.reconcile_invoices(cutoff=cutoff)

            assert updated_count == 1
            assert not mock_tr_create.called


@pytest.mark.asyncio
async def test_reconcile_invoices_still_created_or_error(db_session: AsyncSession) -> None:
    inv_repo = InvoiceRecordRepository(session=db_session)

    inv1 = InvoiceRecord(
        stark_invoice_id="inv_rec_3",
        amount=5000,
        tax_id="12345678909",
        name="Customer 3",
        status="created",
    )
    inv2 = InvoiceRecord(
        stark_invoice_id="inv_rec_4",
        amount=5000,
        tax_id="12345678909",
        name="Customer 4",
        status="created",
    )
    inv3_no_status = InvoiceRecord(
        stark_invoice_id="inv_rec_5_no_status",
        amount=5000,
        tax_id="12345678909",
        name="Customer 5",
        status="created",
    )
    inv_no_id = InvoiceRecord(
        stark_invoice_id=None,
        amount=5000,
        tax_id="12345678909",
        name="Customer No ID",
        status="created",
    )
    await inv_repo.create(inv1, autocommit=True)
    await inv_repo.create(inv2, autocommit=True)
    await inv_repo.create(inv3_no_status, autocommit=True)
    await inv_repo.create(inv_no_id, autocommit=True)

    mock_stark_inv1 = MagicMock(id="inv_rec_3", status="created")
    mock_stark_inv3 = MagicMock(id="inv_rec_5_no_status", status=None)

    service = ReconciliationService(session=db_session)

    def mock_get(inv_id: str):
        if inv_id == "inv_rec_3":
            return mock_stark_inv1
        if inv_id == "inv_rec_5_no_status":
            return mock_stark_inv3
        raise RuntimeError("Stark API error")

    with patch("starkbank.invoice.get", side_effect=mock_get):
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        updated_count = await service.reconcile_invoices(cutoff=cutoff)

        assert updated_count == 0


@pytest.mark.asyncio
async def test_reconcile_transfers_status_transitions(db_session: AsyncSession) -> None:
    tr_repo = TransferRepository(session=db_session)

    tr1 = TransferRecord(
        stark_transfer_id="stark_tr_1",
        amount=10000,
        fee=100,
        net_amount=9900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="processing",
    )
    tr2 = TransferRecord(
        stark_transfer_id="stark_tr_2",
        amount=10000,
        fee=100,
        net_amount=9900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    tr3_error = TransferRecord(
        stark_transfer_id="stark_tr_3_err",
        amount=10000,
        fee=100,
        net_amount=9900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    tr_no_id = TransferRecord(
        stark_transfer_id=None,
        amount=10000,
        fee=100,
        net_amount=9900,
        target_bank_code="20018183",
        target_branch="0001",
        target_account="6341320293482496",
        target_name="Stark Bank S.A.",
        target_tax_id="20018183000180",
        target_account_type="payment",
        status="created",
    )
    await tr_repo.create(tr1, autocommit=True)
    await tr_repo.create(tr2, autocommit=True)
    await tr_repo.create(tr3_error, autocommit=True)
    await tr_repo.create(tr_no_id, autocommit=True)

    mock_tr1 = MagicMock(id="stark_tr_1", status="success")
    mock_tr2 = MagicMock(id="stark_tr_2", status="failed")

    def mock_transfer_get(tr_id: str):
        if tr_id == "stark_tr_1":
            return mock_tr1
        if tr_id == "stark_tr_2":
            return mock_tr2
        raise RuntimeError("Network Error on Transfer")

    service = ReconciliationService(session=db_session)

    with patch("starkbank.transfer.get", side_effect=mock_transfer_get):
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        updated_count = await service.reconcile_transfers(cutoff=cutoff)

        assert updated_count == 2

    updated_tr1 = await tr_repo.get_by_stark_id("stark_tr_1")
    assert updated_tr1 is not None
    assert updated_tr1.status == "success"

    updated_tr2 = await tr_repo.get_by_stark_id("stark_tr_2")
    assert updated_tr2 is not None
    assert updated_tr2.status == "failed"


@pytest.mark.asyncio
async def test_reconciliation_service_run_reconciliation(db_session: AsyncSession) -> None:
    service = ReconciliationService(session=db_session)
    with patch.object(service, "reconcile_invoices", return_value=3):
        with patch.object(service, "reconcile_transfers", return_value=2):
            res = await service.run_reconciliation(lookback_hours=12)

            assert res["status"] == "success"
            assert res["invoices_updated"] == 3
            assert res["transfers_updated"] == 2
            assert res["lookback_hours"] == 12
            assert "executed_at" in res


@pytest.mark.asyncio
async def test_execute_reconciliation_job(db_session: AsyncSession) -> None:
    with patch(
        "app.modules.scheduler.reconciliation.ReconciliationService.run_reconciliation",
        return_value={"status": "success"},
    ):
        res1 = await execute_reconciliation_job(db_session=db_session)
        assert res1["status"] == "success"

        with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
            res2 = await execute_reconciliation_job()
            assert res2["status"] == "success"
