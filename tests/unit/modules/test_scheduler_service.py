from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository
from app.modules.scheduler.service import (
    execute_cycle_job,
    get_current_mode,
    get_next_run_time,
    scheduler,
    set_current_mode,
    start_scheduler,
    stop_scheduler,
)


async def test_set_and_get_current_mode(db_session: AsyncSession) -> None:
    await set_current_mode("recurring", db_session=db_session)
    assert get_current_mode() == "recurring"

    await set_current_mode("once", db_session=db_session)
    assert get_current_mode() == "once"

    await set_current_mode("invalid_mode", db_session=db_session)
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
    await set_current_mode("once", db_session=db_session)
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


async def test_execute_cycle_job_recurring_mode_limit(db_session: AsyncSession) -> None:
    await set_current_mode("recurring", db_session=db_session)
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

    await set_current_mode("once", db_session=db_session)


async def test_execute_cycle_job_recurring_mode_under_limit(db_session: AsyncSession) -> None:
    await set_current_mode("recurring", db_session=db_session)
    mock_batch = MagicMock(id=None, invoice_count=10)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        with patch(
            "app.modules.invoice.service.InvoiceService.issue_batch", return_value=mock_batch
        ):
            await execute_cycle_job(trigger_type="scheduled")

    repo = ScheduleCycleRepository(session=db_session)
    count = await repo.get_completed_cycle_count(trigger_type="scheduled")
    assert count == 1
    await set_current_mode("once", db_session=db_session)


async def test_execute_cycle_job_failure_branch(db_session: AsyncSession) -> None:
    await set_current_mode("once", db_session=db_session)
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


async def test_start_and_stop_scheduler(db_session: AsyncSession) -> None:
    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        await start_scheduler()
        _ = get_next_run_time()
        stop_scheduler()

        # Test when scheduler is not running and jobs already exist to trigger reschedule branches
        mock_sched = MagicMock()
        mock_sched.running = False
        mock_sched.get_job.return_value = MagicMock()
        with patch("app.modules.scheduler.service.scheduler", mock_sched):
            await start_scheduler()
            assert mock_sched.reschedule_job.called


async def test_start_scheduler_exception_handling(db_session: AsyncSession) -> None:
    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        with patch.object(scheduler, "add_job", side_effect=RuntimeError("APScheduler error")):
            with patch.object(scheduler, "get_job", return_value=None):
                await start_scheduler()
