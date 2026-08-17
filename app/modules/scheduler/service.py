import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import AsyncSessionLocal
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.reconciliation import ReconciliationService
from app.modules.scheduler.repository import ScheduleCycleRepository, SchedulerStateRepository
from app.modules.scheduler.schema import SchedulerMode, TriggerType

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

current_mode: SchedulerMode = settings.SCHEDULER_MODE


def get_current_mode() -> SchedulerMode:
    return current_mode


async def set_current_mode(
    mode: SchedulerMode | str, db_session: AsyncSession | None = None
) -> SchedulerMode:
    global current_mode
    valid_mode: SchedulerMode = (
        SchedulerMode.RECURRING
        if str(mode).lower().strip() == SchedulerMode.RECURRING.value
        else SchedulerMode.ONCE
    )
    current_mode = valid_mode

    try:
        if db_session is not None:
            state_repo = SchedulerStateRepository(session=db_session)
            await state_repo.set_mode(valid_mode.value)
        else:
            async with AsyncSessionLocal() as session:
                state_repo = SchedulerStateRepository(session=session)
                await state_repo.set_mode(valid_mode.value)
    except Exception as err:
        logger.warning("Could not persist scheduler mode to database: %s", err)

    return current_mode


async def init_scheduler_state() -> SchedulerMode:
    global current_mode
    try:
        async with AsyncSessionLocal() as session:
            state_repo = SchedulerStateRepository(session=session)
            state = await state_repo.get_or_create_state(default_mode=settings.SCHEDULER_MODE)
            valid_mode: SchedulerMode = (
                SchedulerMode.RECURRING
                if state.mode.lower().strip() == SchedulerMode.RECURRING.value
                else SchedulerMode.ONCE
            )
            current_mode = valid_mode
            logger.info("Scheduler state initialized from database with mode: '%s'", current_mode)
    except Exception as err:
        logger.warning("Could not initialize scheduler state from database: %s", err)
        current_mode = (
            SchedulerMode.RECURRING
            if settings.SCHEDULER_MODE == SchedulerMode.RECURRING.value
            else SchedulerMode.ONCE
        )

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


async def _run_cycle_with_session(
    session: AsyncSession, trigger_type: TriggerType | str, mode: SchedulerMode | str
) -> None:
    max_cycles = settings.max_cycles
    cycle_repo = ScheduleCycleRepository(session=session)
    state_repo = SchedulerStateRepository(session=session)

    trigger_val = trigger_type.value if isinstance(trigger_type, TriggerType) else str(trigger_type)
    mode_val = mode.value if isinstance(mode, SchedulerMode) else str(mode)

    if trigger_val == TriggerType.MANUAL.value:
        total_manual = await cycle_repo.get_manual_trigger_count()
        cycle_index = total_manual + 1
        logger.info("Executing MANUAL trigger on demand (batch %d)...", cycle_index)
    else:
        if mode_val == SchedulerMode.ONCE.value:
            completed_scheduled = await cycle_repo.get_completed_cycle_count(
                trigger_type=TriggerType.SCHEDULED.value
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
                trigger_type=TriggerType.SCHEDULED.value
            )
            if completed_24h >= max_cycles:
                logger.info(
                    "Limit of %d scheduled cycles in 24h reached in 'recurring' mode. Run skipped.",
                    max_cycles,
                )
                return
            total_scheduled = await cycle_repo.get_completed_cycle_count(
                trigger_type=TriggerType.SCHEDULED.value
            )
            cycle_index = total_scheduled + 1

        logger.info("Starting SCHEDULED cycle %d/%d (%s)...", cycle_index, max_cycles, mode_val)

    try:
        invoice_service = InvoiceService(session=session)
        batch = await invoice_service.issue_batch(cycle_index=cycle_index)

        cycle_rec = ScheduleCycleRecord(
            cycle_index=cycle_index,
            status="completed",
            trigger_type=trigger_val,
            invoice_count=batch.invoice_count,
            batch_id=batch.id,
        )
        await cycle_repo.create(cycle_rec, autocommit=True)

        if trigger_val == TriggerType.SCHEDULED.value:
            await state_repo.update_last_scheduled_run(datetime.now(UTC))

        logger.info(
            "Cycle %d (%s) completed with %d invoices.",
            cycle_index,
            trigger_val,
            batch.invoice_count,
        )
    except Exception as err:
        logger.error("Failed to execute cycle %d (%s): %s", cycle_index, trigger_val, err)
        cycle_rec = ScheduleCycleRecord(
            cycle_index=cycle_index,
            status="failed",
            trigger_type=trigger_val,
            invoice_count=0,
        )
        await cycle_repo.create(cycle_rec, autocommit=True)


async def execute_cycle_job(
    trigger_type: TriggerType | str = TriggerType.SCHEDULED,
    db_session: AsyncSession | None = None,
) -> None:
    mode = get_current_mode()

    if db_session is not None:
        await _run_cycle_with_session(db_session, trigger_type, mode)
    else:
        async with AsyncSessionLocal() as session:
            await _run_cycle_with_session(session, trigger_type, mode)


async def execute_reconciliation_job(
    db_session: AsyncSession | None = None,
) -> dict[str, Any]:
    logger.info("Executing scheduled financial reconciliation job...")
    if db_session is not None:
        service = ReconciliationService(session=db_session)
        return await service.run_reconciliation()
    else:
        async with AsyncSessionLocal() as session:
            service = ReconciliationService(session=session)
            return await service.run_reconciliation()


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

            if settings.RECONCILIATION_ENABLED:
                tz = ZoneInfo(settings.APP_TIMEZONE)
                cron_trigger = CronTrigger(
                    hour=settings.RECONCILIATION_HOUR,
                    minute=settings.RECONCILIATION_MINUTE,
                    timezone=tz,
                )
                reconcile_job = scheduler.get_job("daily_reconciliation_job")
                if reconcile_job:
                    scheduler.reschedule_job(
                        "daily_reconciliation_job",
                        trigger=cron_trigger,
                    )
                else:
                    scheduler.add_job(
                        execute_reconciliation_job,
                        trigger=cron_trigger,
                        id="daily_reconciliation_job",
                        replace_existing=True,
                        coalesce=True,
                        misfire_grace_time=3600,
                    )
                logger.info(
                    "Daily financial reconciliation scheduled at %02d:%02d (%s).",
                    settings.RECONCILIATION_HOUR,
                    settings.RECONCILIATION_MINUTE,
                    settings.APP_TIMEZONE,
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
