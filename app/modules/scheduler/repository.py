from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.shared.repository import BaseRepository


class ScheduleCycleRepository(BaseRepository[ScheduleCycleRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ScheduleCycleRecord, session=session)

    async def get_completed_cycle_count(self, trigger_type: str = "scheduled") -> int:
        query = select(func.count(ScheduleCycleRecord.id)).where(
            ScheduleCycleRecord.status == "completed",
            ScheduleCycleRecord.trigger_type == trigger_type,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_completed_cycle_count_in_24h(self, trigger_type: str = "scheduled") -> int:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        query = select(func.count(ScheduleCycleRecord.id)).where(
            ScheduleCycleRecord.status == "completed",
            ScheduleCycleRecord.trigger_type == trigger_type,
            ScheduleCycleRecord.executed_at >= cutoff,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_manual_trigger_count(self) -> int:
        query = select(func.count(ScheduleCycleRecord.id)).where(
            ScheduleCycleRecord.status == "completed",
            ScheduleCycleRecord.trigger_type == "manual",
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() or 0

    async def get_by_cycle_index(self, cycle_index: int) -> ScheduleCycleRecord | None:
        query = select(ScheduleCycleRecord).where(ScheduleCycleRecord.cycle_index == cycle_index)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def reset_cycles(self) -> int:
        stmt = delete(ScheduleCycleRecord)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount or 0
