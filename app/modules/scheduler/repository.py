from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.shared.repository import BaseRepository


class ScheduleCycleRepository(BaseRepository[ScheduleCycleRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ScheduleCycleRecord, session=session)

    async def get_completed_cycle_count(self) -> int:
        query = select(func.count(ScheduleCycleRecord.id)).where(
            ScheduleCycleRecord.status == "completed"
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_by_cycle_index(self, cycle_index: int) -> ScheduleCycleRecord | None:
        query = select(ScheduleCycleRecord).where(ScheduleCycleRecord.cycle_index == cycle_index)
        result = await self.session.execute(query)
        return result.scalars().first()
