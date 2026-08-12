from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.service import execute_cycle_job

router = APIRouter(prefix="/api/v1/scheduler", tags=["Scheduler"])


class SchedulerStatusResponse(BaseModel):
    completed_cycles: int
    max_cycles: int = 8
    remaining_cycles: int


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    db: AsyncSession = Depends(get_db),
) -> SchedulerStatusResponse:
    repo = ScheduleCycleRepository(session=db)
    completed = await repo.get_completed_cycle_count()
    return SchedulerStatusResponse(
        completed_cycles=completed,
        max_cycles=8,
        remaining_cycles=max(0, 8 - completed),
    )


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_cycle() -> dict[str, str]:
    await execute_cycle_job()
    return {"message": "Scheduled cycle job triggered successfully."}
