from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.service import (
    execute_cycle_job,
    get_current_mode,
    get_next_run_time,
    set_current_mode,
    start_scheduler,
    stop_scheduler,
)


async def test_set_and_get_current_mode() -> None:
    set_current_mode("recurring")
    assert get_current_mode() == "recurring"

    set_current_mode("once")
    assert get_current_mode() == "once"

    set_current_mode("invalid_mode")
    assert get_current_mode() == "once"


async def test_execute_manual_cycle_job_does_not_consume_scheduled_quota(
    db_session: AsyncSession,
) -> None:
    repo = ScheduleCycleRepository(session=db_session)
    mock_batch = MagicMock(id=None, invoice_count=10)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        with patch(
            "app.modules.invoice.service.InvoiceService.issue_batch", return_value=mock_batch
        ):
            await execute_cycle_job(trigger_type="manual")

    scheduled_count = await repo.get_completed_cycle_count(trigger_type="scheduled")
    manual_count = await repo.get_manual_trigger_count()

    assert scheduled_count == 0
    assert manual_count == 1


async def test_execute_cycle_job_once_mode_limit(db_session: AsyncSession) -> None:
    set_current_mode("once")
    repo = ScheduleCycleRepository(session=db_session)
    for i in range(1, 9):
        await repo.create(
            ScheduleCycleRecord(
                cycle_index=i, status="completed", trigger_type="scheduled", invoice_count=10
            ),
            autocommit=True,
        )

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        await execute_cycle_job(trigger_type="scheduled")

    scheduled_count = await repo.get_completed_cycle_count(trigger_type="scheduled")
    assert scheduled_count == 8


async def test_execute_cycle_job_recurring_mode(db_session: AsyncSession) -> None:
    set_current_mode("recurring")
    repo = ScheduleCycleRepository(session=db_session)
    for i in range(1, 9):
        await repo.create(
            ScheduleCycleRecord(
                cycle_index=i, status="completed", trigger_type="scheduled", invoice_count=10
            ),
            autocommit=True,
        )

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        await execute_cycle_job(trigger_type="scheduled")

    set_current_mode("once")


async def test_execute_cycle_job_failure_branch(db_session: AsyncSession) -> None:
    set_current_mode("once")
    repo = ScheduleCycleRepository(session=db_session)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        with patch(
            "app.modules.invoice.service.InvoiceService.issue_batch",
            side_effect=RuntimeError("Invoice Generation Error"),
        ):
            await execute_cycle_job(trigger_type="scheduled")

    rec = await repo.get_by_cycle_index(1)
    assert rec is not None
    assert rec.status == "failed"
    assert rec.invoice_count == 0


async def test_start_and_stop_scheduler() -> None:
    start_scheduler()
    _ = get_next_run_time()
    stop_scheduler()
