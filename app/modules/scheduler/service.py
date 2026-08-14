import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import AsyncSessionLocal
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository, SchedulerStateRepository

logger = logging.getLogger(__name__)

SchedulerMode = Literal["once", "recurring"]

scheduler = AsyncIOScheduler()

current_mode: SchedulerMode = settings.SCHEDULER_MODE


def get_current_mode() -> SchedulerMode:
    return current_mode


async def set_current_mode(mode: str, db_session: AsyncSession | None = None) -> SchedulerMode:
    global current_mode
    valid_mode: SchedulerMode = "recurring" if mode.lower().strip() == "recurring" else "once"
    current_mode = valid_mode

    if db_session is not None:
        state_repo = SchedulerStateRepository(session=db_session)
        await state_repo.set_mode(valid_mode)
    else:
        async with AsyncSessionLocal() as session:
            state_repo = SchedulerStateRepository(session=session)
            await state_repo.set_mode(valid_mode)

    return current_mode


async def init_scheduler_state() -> SchedulerMode:
    global current_mode
    async with AsyncSessionLocal() as session:
        state_repo = SchedulerStateRepository(session=session)
        state = await state_repo.get_or_create_state(default_mode=settings.SCHEDULER_MODE)
        valid_mode: SchedulerMode = (
            "recurring" if state.mode.lower().strip() == "recurring" else "once"
        )
        current_mode = valid_mode
        logger.info("Scheduler state initialized from database with mode: '%s'", current_mode)
        return current_mode


def get_next_run_time() -> datetime | None:
    if scheduler.running:
        job = scheduler.get_job("invoice_batch_cycle_job")
        if job and job.next_run_time:
            return job.next_run_time
    return None


async def get_next_run_delay_seconds() -> int:
    interval_seconds = settings.SCHEDULER_INTERVAL_MINUTES * 60
    async with AsyncSessionLocal() as session:
        cycle_repo = ScheduleCycleRepository(session=session)
        last_cycle = await cycle_repo.get_last_scheduled_cycle()
        if last_cycle and last_cycle.executed_at:
            last_run = last_cycle.executed_at
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - last_run).total_seconds()
            if elapsed < interval_seconds:
                remaining = max(1, int(interval_seconds - elapsed))
                logger.info(
                    "Recent scheduled cycle (%ds ago). Next cycle scheduled in %ds.",
                    int(elapsed),
                    remaining,
                )
                return remaining
            logger.info(
                "Elapsed time since last cycle (%ds) exceeds interval (%ds). Triggering catch-up.",
                int(elapsed),
                interval_seconds,
            )
            return 1

    return interval_seconds


async def _run_cycle_with_session(session: AsyncSession, trigger_type: str, mode: str) -> None:
    max_cycles = settings.max_cycles
    cycle_repo = ScheduleCycleRepository(session=session)
    state_repo = SchedulerStateRepository(session=session)

    if trigger_type == "manual":
        total_manual = await cycle_repo.get_manual_trigger_count()
        cycle_index = total_manual + 1
        logger.info("Executing MANUAL trigger on demand (batch %d)...", cycle_index)
    else:
        if mode == "once":
            completed_scheduled = await cycle_repo.get_completed_cycle_count(
                trigger_type="scheduled"
            )
            if completed_scheduled >= max_cycles:
                logger.info(
                    "Configured limit of %d cycles reached in 'once' mode. Scheduled run skipped.",
                    max_cycles,
                )
                return
            cycle_index = completed_scheduled + 1
        else:
            completed_24h = await cycle_repo.get_completed_cycle_count_in_24h(
                trigger_type="scheduled"
            )
            if completed_24h >= max_cycles:
                logger.info(
                    "Limit of %d scheduled cycles in 24h reached in 'recurring' mode. Run skipped.",
                    max_cycles,
                )
                return
            total_scheduled = await cycle_repo.get_completed_cycle_count(trigger_type="scheduled")
            cycle_index = total_scheduled + 1

        logger.info("Starting SCHEDULED cycle %d/%d (%s)...", cycle_index, max_cycles, mode)

    try:
        invoice_service = InvoiceService(session=session)
        batch = await invoice_service.issue_batch(cycle_index=cycle_index)

        cycle_rec = ScheduleCycleRecord(
            cycle_index=cycle_index,
            status="completed",
            trigger_type=trigger_type,
            invoice_count=batch.invoice_count,
            batch_id=batch.id,
        )
        await cycle_repo.create(cycle_rec, autocommit=True)

        if trigger_type == "scheduled":
            await state_repo.update_last_scheduled_run(datetime.now(UTC))

        logger.info(
            "Cycle %d (%s) completed with %d invoices.",
            cycle_index,
            trigger_type,
            batch.invoice_count,
        )
    except Exception as err:
        logger.error("Failed to execute cycle %d (%s): %s", cycle_index, trigger_type, err)
        cycle_rec = ScheduleCycleRecord(
            cycle_index=cycle_index,
            status="failed",
            trigger_type=trigger_type,
            invoice_count=0,
        )
        await cycle_repo.create(cycle_rec, autocommit=True)


async def execute_cycle_job(
    trigger_type: str = "scheduled", db_session: AsyncSession | None = None
) -> None:
    mode = get_current_mode()

    if db_session is not None:
        await _run_cycle_with_session(db_session, trigger_type, mode)
    else:
        async with AsyncSessionLocal() as session:
            await _run_cycle_with_session(session, trigger_type, mode)


async def start_scheduler(run_on_startup: bool = True) -> None:
    try:
        await init_scheduler_state()
        delay_seconds = await get_next_run_delay_seconds()
        start_time = datetime.now(UTC) + timedelta(seconds=delay_seconds)

        if not scheduler.running:
            job = scheduler.get_job("invoice_batch_cycle_job")
            if job:
                scheduler.reschedule_job(
                    "invoice_batch_cycle_job",
                    trigger="interval",
                    minutes=settings.SCHEDULER_INTERVAL_MINUTES,
                    start_date=start_time,
                )
            else:
                scheduler.add_job(
                    execute_cycle_job,
                    trigger="interval",
                    minutes=settings.SCHEDULER_INTERVAL_MINUTES,
                    start_date=start_time,
                    id="invoice_batch_cycle_job",
                    replace_existing=True,
                    coalesce=True,
                    misfire_grace_time=3600,
                )
            scheduler.start()
            logger.info(
                "APScheduler started (first run in %ds, interval: %d min, coalesce=True).",
                delay_seconds,
                settings.SCHEDULER_INTERVAL_MINUTES,
            )
    except Exception as err:
        logger.error("Failed to start scheduler: %s", err)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
