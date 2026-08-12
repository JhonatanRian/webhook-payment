import time

from app.core.concurrency import run_in_thread


@run_in_thread
def sync_blocking_func(x: int, y: int) -> int:
    time.sleep(0.01)
    return x + y


async def test_run_in_thread_decorator() -> None:
    result = await sync_blocking_func(10, 20)
    assert result == 30
