from typing import Callable, Any
from ..core.config import settings


def enqueue_background(coro_func: Callable[..., Any], *args, **kwargs) -> None:
    """Abstraction for background job enqueue.

    For now, runs in-process via asyncio.create_task (called by orchestrator).
    If settings.use_redis_queue is True, this will enqueue to Redis RQ (stub).
    """
    if settings.use_redis_queue:
        # Placeholder for RQ integration; we keep in-process for MVP
        import asyncio
        asyncio.create_task(coro_func(*args, **kwargs))
    else:
        import asyncio
        asyncio.create_task(coro_func(*args, **kwargs))

