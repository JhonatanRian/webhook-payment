import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any


def run_in_thread[**P, R](func: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Decorator to offload synchronous blocking functions (like StarkBank SDK calls)

    to an asyncio worker thread.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper
