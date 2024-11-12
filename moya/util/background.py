import asyncio
import logging
from typing import Any, Awaitable

bg_logger = logging.getLogger("background-tasks")

_never_run_in_background = False


def never_run_in_background(value: bool) -> None:
    """
    Set whether background tasks should be run immediately or not. This is
    useful for testing.
    """
    global _never_run_in_background
    _never_run_in_background = value


async def background_task_wrapper(task: Awaitable[Any]) -> None:
    """
    Run the given task logging exceptions to sentry
    """
    try:
        await task
    except Exception as e:
        bg_logger.exception("Exception in background task", exc_info=e)


async def run_in_background(task: Awaitable[Any]) -> None:
    """
    Run a task in the background returning immediately, logging exceptions if
    they occur.

    Usage:

    async def task():
        ... do stuff ...

    await run_in_background(task())
    """
    # Note that this routine doesn't need to be async but setting it to this
    # for consistency and to allow us to do other things in future.
    if _never_run_in_background:
        await task
    else:
        asyncio.create_task(background_task_wrapper(task))
