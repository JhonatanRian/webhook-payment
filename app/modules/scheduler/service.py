import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.infra.db.session import AsyncSessionLocal
from app.modules.invoice.service import InvoiceService
from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def execute_cycle_job() -> None:
    logger.info("Executing scheduled invoice batch cycle job...")
    async with AsyncSessionLocal() as session:
        cycle_repo = ScheduleCycleRepository(session=session)
        completed_count = await cycle_repo.get_completed_cycle_count()

        if completed_count >= 8:
            logger.info("24-hour limit reached (8 cycles executed). Skipping further batches.")
            return

        cycle_index = completed_count + 1
        logger.info(f"Starting batch cycle {cycle_index}/8...")

        try:
            invoice_service = InvoiceService(session=session)
            batch = await invoice_service.issue_batch(cycle_index=cycle_index)

            cycle_rec = ScheduleCycleRecord(
                cycle_index=cycle_index,
                status="completed",
                invoice_count=batch.invoice_count,
                batch_id=batch.id,
            )
            await cycle_repo.create(cycle_rec, autocommit=True)
            logger.info(f"Completed cycle {cycle_index}/8 with {batch.invoice_count} invoices.")
        except Exception as err:
            logger.error(f"Failed to execute batch cycle {cycle_index}: {err}")
            cycle_rec = ScheduleCycleRecord(
                cycle_index=cycle_index,
                status="failed",
                invoice_count=0,
            )
            await cycle_repo.create(cycle_rec, autocommit=True)


def start_scheduler(run_on_startup: bool = True) -> None:
    if not scheduler.running:
        scheduler.add_job(
            execute_cycle_job,
            trigger="interval",
            hours=3,
            id="invoice_batch_cycle_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started. Invoice batch job scheduled every 3 hours.")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
