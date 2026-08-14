import logging
from datetime import datetime
from typing import Literal

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.db.session import AsyncSessionLocal
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository

logger = logging.getLogger(__name__)

SchedulerMode = Literal["once", "recurring"]

jobstores = {"default": SQLAlchemyJobStore(url=settings.SCHEDULER_JOBSTORE_URL)}
scheduler = AsyncIOScheduler(jobstores=jobstores)

current_mode: SchedulerMode = settings.SCHEDULER_MODE


def get_current_mode() -> SchedulerMode:
    return current_mode


def set_current_mode(mode: str) -> SchedulerMode:
    global current_mode
    valid_mode = mode.lower().strip()
    if valid_mode == "recurring":
        current_mode = "recurring"
    else:
        current_mode = "once"
    return current_mode


def get_next_run_time() -> datetime | None:
    if scheduler.running:
        job = scheduler.get_job("invoice_batch_cycle_job")
        if job and job.next_run_time:
            return job.next_run_time
    return None


async def _run_cycle_with_session(session: AsyncSession, trigger_type: str, mode: str) -> None:
    max_cycles = settings.max_cycles
    cycle_repo = ScheduleCycleRepository(session=session)

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


def start_scheduler(run_on_startup: bool = True) -> None:
    if not scheduler.running:
        job = scheduler.get_job("invoice_batch_cycle_job")
        if job:
            scheduler.reschedule_job(
                "invoice_batch_cycle_job",
                trigger="interval",
                minutes=settings.SCHEDULER_INTERVAL_MINUTES,
            )
        else:
            scheduler.add_job(
                execute_cycle_job,
                trigger="interval",
                minutes=settings.SCHEDULER_INTERVAL_MINUTES,
                id="invoice_batch_cycle_job",
                replace_existing=True,
                coalesce=True,
                misfire_grace_time=3600,
            )
        scheduler.start()
        logger.info(
            "APScheduler started with SQLAlchemyJobStore (interval: %d min, "
            "coalesce=True, misfire_grace_time=3600).",
            settings.SCHEDULER_INTERVAL_MINUTES,
        )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
