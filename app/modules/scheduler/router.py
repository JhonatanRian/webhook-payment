from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import get_db
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.schema import (
    SchedulerControlResponse,
    SchedulerModeUpdateRequest,
    SchedulerStatusResponse,
)
from app.modules.scheduler.service import (
    execute_cycle_job,
    get_current_mode,
    get_next_run_time,
    scheduler,
    set_current_mode,
)

router = APIRouter(prefix="/api/v1/scheduler", tags=["Scheduler"])


@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Get scheduler status",
    description=(
        "Returns scheduled and manual cycle counters, next run time, and scheduler engine state."
    ),
)
async def get_scheduler_status(
    db: AsyncSession = Depends(get_db),
) -> SchedulerStatusResponse:
    repo = ScheduleCycleRepository(session=db)
    scheduled_completed = await repo.get_completed_cycle_count(trigger_type="scheduled")
    manual_completed = await repo.get_manual_trigger_count()
    max_cycles = settings.max_cycles
    mode = get_current_mode()

    if mode == "once":
        remaining = max(0, max_cycles - scheduled_completed)
    else:
        completed_24h = await repo.get_completed_cycle_count_in_24h(trigger_type="scheduled")
        remaining = max(0, max_cycles - completed_24h)

    return SchedulerStatusResponse(
        scheduled_cycles_completed=scheduled_completed,
        manual_triggers_completed=manual_completed,
        max_cycles=max_cycles,
        interval_minutes=settings.SCHEDULER_INTERVAL_MINUTES,
        remaining_cycles=remaining,
        mode=mode,
        is_running=scheduler.running,
        next_run_time=get_next_run_time(),
    )


@router.post(
    "/trigger",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual invoice cycle",
    description=(
        "Immediately triggers an on-demand invoice cycle (does not consume scheduled cycle quota)."
    ),
)
async def trigger_manual_cycle(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await execute_cycle_job(trigger_type="manual", db_session=db)
    return {"message": "Manual invoice batch cycle triggered successfully."}


@router.put(
    "/mode",
    response_model=SchedulerControlResponse,
    summary="Update scheduler operating mode",
    description="Switches between 'once' (one round of max_cycles) and 'recurring' modes.",
)
async def update_scheduler_mode(
    payload: SchedulerModeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SchedulerControlResponse:
    new_mode = await set_current_mode(payload.mode, db_session=db)
    return SchedulerControlResponse(
        message=f"Scheduler mode successfully updated to '{new_mode}'.",
        mode=new_mode,
    )


@router.post(
    "/reset",
    response_model=SchedulerControlResponse,
    summary="Reset scheduler cycle history",
    description="Clears historical cycle records from database.",
)
async def reset_scheduler_cycles(
    db: AsyncSession = Depends(get_db),
) -> SchedulerControlResponse:
    repo = ScheduleCycleRepository(session=db)
    deleted_count = await repo.reset_cycles()
    return SchedulerControlResponse(
        message=f"Scheduler cycles reset successfully. Removed {deleted_count} record(s).",
        mode=get_current_mode(),
    )
