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


async def background_task_wrapper(task: Awaitable[Any], name: str | None = None) -> None:
    """
    Run the given task logging exceptions to sentry
    """
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        bg_logger.exception(f"Exception in background task '{name or 'Anon'}'", exc_info=e)


async def run_in_background(task: Awaitable[Any], name: str | None = None) -> asyncio.Task[Any]:
    """
    Run a task in the background returning immediately, logging exceptions if
    they occur.

    Usage:

    async def task():
        ... do stuff ...

    t = await run_in_background(task())
    t.cancel()
    """
    if _never_run_in_background:
        await task
        # Return an empty task so that cancelling works
        return asyncio.create_task(asyncio.sleep(0))
    else:
        return asyncio.create_task(background_task_wrapper(task, name), name=name)
