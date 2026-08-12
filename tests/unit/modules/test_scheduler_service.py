from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.service import (
    execute_cycle_job,
    start_scheduler,
    stop_scheduler,
)


async def test_execute_cycle_job_limit_reached(db_session: AsyncSession) -> None:
    repo = ScheduleCycleRepository(session=db_session)
    for i in range(1, 9):
        await repo.create(
            ScheduleCycleRecord(cycle_index=i, status="completed", invoice_count=10),
            autocommit=True,
        )

    completed_count = await repo.get_completed_cycle_count()
    assert completed_count == 8

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        await execute_cycle_job()

    completed_after = await repo.get_completed_cycle_count()
    assert completed_after == 8


async def test_execute_cycle_job_failure_branch(db_session: AsyncSession) -> None:
    repo = ScheduleCycleRepository(session=db_session)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        with patch(
            "app.modules.invoice.service.InvoiceService.issue_batch",
            side_effect=RuntimeError("Invoice Generation Error"),
        ):
            await execute_cycle_job()

    rec = await repo.get_by_cycle_index(1)
    assert rec is not None
    assert rec.status == "failed"
    assert rec.invoice_count == 0


async def test_start_and_stop_scheduler() -> None:
    start_scheduler()
    stop_scheduler()
