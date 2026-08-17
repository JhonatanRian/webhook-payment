from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transfer.model import TransferRecord
from app.shared.pagination import PaginatedResult, PaginationParams
from app.shared.repository import BaseRepository


class TransferRepository(BaseRepository[TransferRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=TransferRecord, session=session)

    async def get_by_stark_id(self, stark_transfer_id: str) -> TransferRecord | None:
        query = select(TransferRecord).where(TransferRecord.stark_transfer_id == stark_transfer_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_invoice_id(self, stark_invoice_id: str) -> TransferRecord | None:
        query = select(TransferRecord).where(TransferRecord.stark_invoice_id == stark_invoice_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_pending_transfers_in_window(self, cutoff: datetime) -> Sequence[TransferRecord]:
        query = (
            select(TransferRecord)
            .where(
                TransferRecord.status.in_(["created", "processing", "pending"]),
                TransferRecord.created >= cutoff,
            )
            .order_by(desc(TransferRecord.created))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def paginate_transfers(
        self,
        params: PaginationParams,
    ) -> PaginatedResult[TransferRecord]:
        query = select(TransferRecord).order_by(desc(TransferRecord.created))
        return await self.paginate(params=params, query=query)
