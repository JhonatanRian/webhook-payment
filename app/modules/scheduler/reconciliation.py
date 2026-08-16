import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import starkbank
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import run_in_thread
from app.core.config import settings
from app.modules.invoice.repository import InvoiceRecordRepository
from app.modules.transfer.repository import TransferRepository
from app.modules.transfer.service import TransferService

logger = logging.getLogger(__name__)


class ReconciliationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.invoice_repo = InvoiceRecordRepository(session=session)
        self.transfer_repo = TransferRepository(session=session)
        self.transfer_service = TransferService(session=session)

    @run_in_thread
    def _fetch_stark_invoice(self, stark_invoice_id: str) -> starkbank.Invoice:
        return starkbank.invoice.get(stark_invoice_id)

    @run_in_thread
    def _fetch_stark_transfer(self, stark_transfer_id: str) -> starkbank.Transfer:
        return starkbank.transfer.get(stark_transfer_id)

    async def reconcile_invoices(self, cutoff: datetime) -> int:
        pending_invoices = await self.invoice_repo.get_pending_invoices_in_window(cutoff=cutoff)
        updated_count = 0

        for inv in pending_invoices:
            if not inv.stark_invoice_id:
                continue
            try:
                stark_inv = await self._fetch_stark_invoice(inv.stark_invoice_id)
                stark_status = getattr(stark_inv, "status", None)
                if not stark_status:
                    continue

                if stark_status != inv.status:
                    inv.status = stark_status
                    self.session.add(inv)
                    updated_count += 1
                    logger.info(
                        "Reconciled invoice status [stark_invoice_id=%s, new_status=%s]",
                        inv.stark_invoice_id,
                        stark_status,
                    )

                if stark_status in ("paid", "credited"):
                    existing_transfer = await self.transfer_repo.get_by_invoice_id(
                        inv.stark_invoice_id
                    )
                    if not existing_transfer:
                        fee = getattr(stark_inv, "fee", 0) or 0
                        amount = getattr(stark_inv, "amount", inv.amount)
                        logger.info(
                            "Recovering payout transfer for credited invoice %s",
                            inv.stark_invoice_id,
                        )
                        await self.transfer_service.transfer_credited_invoice(
                            gross_amount=amount,
                            fee=fee,
                            stark_invoice_id=inv.stark_invoice_id,
                            event_id=f"reconcile_{inv.stark_invoice_id}",
                            autocommit=False,
                        )
            except Exception as err:
                logger.error(
                    "Error reconciling invoice %s: %s",
                    inv.stark_invoice_id,
                    err,
                )

        if updated_count > 0:
            await self.session.commit()

        return updated_count

    async def reconcile_transfers(self, cutoff: datetime) -> int:
        pending_transfers = await self.transfer_repo.get_pending_transfers_in_window(cutoff=cutoff)
        updated_count = 0

        for tr in pending_transfers:
            if not tr.stark_transfer_id:
                continue
            try:
                stark_tr = await self._fetch_stark_transfer(tr.stark_transfer_id)
                stark_status = getattr(stark_tr, "status", None)
                if stark_status and stark_status != tr.status:
                    tr.status = stark_status
                    self.session.add(tr)
                    updated_count += 1
                    logger.info(
                        "Reconciled transfer status [stark_transfer_id=%s, new_status=%s]",
                        tr.stark_transfer_id,
                        stark_status,
                    )
            except Exception as err:
                logger.error(
                    "Error reconciling transfer %s: %s",
                    tr.stark_transfer_id,
                    err,
                )

        if updated_count > 0:
            await self.session.commit()

        return updated_count

    async def run_reconciliation(self, lookback_hours: int | None = None) -> dict[str, Any]:
        hours = lookback_hours or settings.RECONCILIATION_LOOKBACK_HOURS
        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        logger.info(
            "Starting financial reconciliation job (lookback=%d hours, cutoff=%s)...",
            hours,
            cutoff.isoformat(),
        )

        invoices_updated = await self.reconcile_invoices(cutoff=cutoff)
        transfers_updated = await self.reconcile_transfers(cutoff=cutoff)

        logger.info(
            "Financial reconciliation completed [invoices_updated=%d, transfers_updated=%d]",
            invoices_updated,
            transfers_updated,
        )

        return {
            "status": "success",
            "invoices_updated": invoices_updated,
            "transfers_updated": transfers_updated,
            "lookback_hours": hours,
            "executed_at": datetime.now(UTC).isoformat(),
        }
