import logging

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.schema import DashboardSummaryResponse
from app.modules.invoice.model import InvoiceRecord
from app.modules.transfer.model import TransferRecord

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary(self) -> DashboardSummaryResponse:
        """Computes system-wide financial aggregation metrics directly in database."""
        # 1. Aggregate invoice statistics
        inv_query = select(
            func.coalesce(func.sum(InvoiceRecord.amount), 0).label("total_invoiced"),
            func.count(InvoiceRecord.id).label("total_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            InvoiceRecord.status.in_(["credited", "paid"]),
                            InvoiceRecord.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("credited_invoiced"),
            func.coalesce(
                func.sum(
                    case(
                        (InvoiceRecord.status.in_(["credited", "paid"]), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("credited_count"),
        )
        inv_res = (await self.session.execute(inv_query)).one()

        total_invoiced = int(inv_res.total_invoiced)
        total_count = int(inv_res.total_count)
        credited_invoiced = int(inv_res.credited_invoiced)
        credited_count = int(inv_res.credited_count)

        # 2. Aggregate transfer statistics
        tr_query = select(
            func.coalesce(func.sum(TransferRecord.net_amount), 0).label("total_liquidated"),
            func.count(TransferRecord.id).label("total_transfers_count"),
        ).where(TransferRecord.status == "success")

        tr_res = (await self.session.execute(tr_query)).one()

        total_liquidated = int(tr_res.total_liquidated)
        total_liquidated_count = int(tr_res.total_transfers_count)

        conversion_rate = round((credited_count / total_count) * 100, 2) if total_count > 0 else 0.0

        return DashboardSummaryResponse(
            total_invoiced_cents=total_invoiced,
            total_invoices_count=total_count,
            total_credited_cents=credited_invoiced,
            total_credited_count=credited_count,
            total_liquidated_cents=total_liquidated,
            total_liquidated_count=total_liquidated_count,
            conversion_rate_percentage=conversion_rate,
        )
