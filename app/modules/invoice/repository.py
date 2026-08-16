from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.invoice.model import InvoiceBatch, InvoiceRecord
from app.shared.pagination import PaginatedResult, PaginationParams
from app.shared.repository import BaseRepository


class InvoiceBatchRepository(BaseRepository[InvoiceBatch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=InvoiceBatch, session=session)

    async def get_by_cycle(self, cycle_index: int) -> InvoiceBatch | None:
        query = (
            select(InvoiceBatch)
            .options(selectinload(InvoiceBatch.invoices))
            .where(InvoiceBatch.cycle_index == cycle_index)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_all(self) -> Sequence[InvoiceBatch]:
        query = (
            select(InvoiceBatch)
            .options(selectinload(InvoiceBatch.invoices))
            .order_by(desc(InvoiceBatch.created))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def paginate_batches(
        self,
        params: PaginationParams,
    ) -> PaginatedResult[InvoiceBatch]:
        query = (
            select(InvoiceBatch)
            .options(selectinload(InvoiceBatch.invoices))
            .order_by(desc(InvoiceBatch.created))
        )
        return await self.paginate(params=params, query=query)


class InvoiceRecordRepository(BaseRepository[InvoiceRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=InvoiceRecord, session=session)

    async def get_by_stark_id(self, stark_invoice_id: str) -> InvoiceRecord | None:
        query = select(InvoiceRecord).where(InvoiceRecord.stark_invoice_id == stark_invoice_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_pending_invoices_in_window(self, cutoff: datetime) -> Sequence[InvoiceRecord]:
        query = (
            select(InvoiceRecord)
            .where(
                InvoiceRecord.status.in_(["created", "pending"]),
                InvoiceRecord.created >= cutoff,
            )
            .order_by(desc(InvoiceRecord.created))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def paginate_invoices(
        self,
        params: PaginationParams,
        status: str | None = None,
    ) -> PaginatedResult[InvoiceRecord]:
        query = select(InvoiceRecord).order_by(desc(InvoiceRecord.created))
        if status:
            query = query.where(InvoiceRecord.status == status)
        return await self.paginate(params=params, query=query)
