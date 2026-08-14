from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.scheduler.model import ScheduleCycleRecord
from app.modules.scheduler.repository import ScheduleCycleRepository, SchedulerStateRepository
from app.modules.scheduler.service import (
    get_current_mode,
    get_next_run_delay_seconds,
    init_scheduler_state,
    set_current_mode,
)


@pytest.mark.asyncio
async def test_scheduler_state_repository_crud(db_session: AsyncSession) -> None:
    repo = SchedulerStateRepository(session=db_session)
    state = await repo.get_or_create_state(default_mode="once")
    assert state.key == "default"
    assert state.mode == "once"

    updated = await repo.set_mode("recurring")
    assert updated.mode == "recurring"

    now = datetime.now(UTC)
    updated_run = await repo.update_last_scheduled_run(now)
    assert updated_run.last_scheduled_run is not None


@pytest.mark.asyncio
async def test_init_scheduler_state_and_set_mode_without_session(db_session: AsyncSession) -> None:
    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        mode = await init_scheduler_state()
        assert mode in ("once", "recurring")

        new_mode = await set_current_mode("recurring")
        assert new_mode == "recurring"
        assert get_current_mode() == "recurring"


@pytest.mark.asyncio
async def test_get_next_run_delay_seconds_calculations(db_session: AsyncSession) -> None:
    cycle_repo = ScheduleCycleRepository(session=db_session)

    # 1. No cycles in database: returns standard interval in seconds (180 min = 10800s)
    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        delay = await get_next_run_delay_seconds()
        assert delay == 180 * 60

    # 2. Recent cycle executed 60 minutes ago: should schedule next in ~120 minutes (7200s)
    one_hour_ago = datetime.now(UTC) - timedelta(minutes=60)
    cycle1 = ScheduleCycleRecord(
        cycle_index=1,
        status="completed",
        trigger_type="scheduled",
        executed_at=one_hour_ago,
        invoice_count=8,
    )
    await cycle_repo.create(cycle1, autocommit=True)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        delay = await get_next_run_delay_seconds()
        # Roughly 120 minutes +/- 10 seconds
        assert 7100 <= delay <= 7210

    # 3. Reset and test old cycle (4h ago): exceeds interval (180 min), returns 1s catch-up
    await cycle_repo.reset_cycles()
    four_hours_ago = datetime.now(UTC) - timedelta(hours=4)
    cycle2 = ScheduleCycleRecord(
        cycle_index=1,
        status="completed",
        trigger_type="scheduled",
        executed_at=four_hours_ago,
        invoice_count=10,
    )
    await cycle_repo.create(cycle2, autocommit=True)

    with patch("app.modules.scheduler.service.AsyncSessionLocal", return_value=db_session):
        delay = await get_next_run_delay_seconds()
        assert delay == 1
