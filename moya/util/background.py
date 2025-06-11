import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, TypeVar

bg_logger = logging.getLogger("background-tasks")

_never_run_in_background = False


def never_run_in_background(value: bool) -> None:
    """
    Set whether background tasks should be run immediately or not. This is
    useful for testing.
    """
    global _never_run_in_background
    _never_run_in_background = value


T = TypeVar("T")


async def background_task_wrapper(task: Awaitable[T], name: str | None = None) -> T | None:
    """
    Run the given task logging exceptions to sentry
    """
    try:
        return await task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.getLogger(f"background-task[{name or 'Anon'}]").exception("Exception in background task", exc_info=e)
    return None


async def run_in_background(task: Awaitable[T], name: str | None = None, force_run_in_background: bool = False) -> asyncio.Task[T | None]:
    """
    Run a task in the background returning immediately, logging exceptions if
    they occur.

    Usage:

    async def task():
        ... do stuff ...

    task = await run_in_background(task())
    task.cancel()
    try:
        result = await task
    except asyncio.CancelledError:
        pass
    result = task.result()
    """
    if _never_run_in_background and not force_run_in_background:
        res = await task

        async def fake_task() -> T:
            return res

        # Return an empty task so that cancelling/fetching the result works
        ret = asyncio.create_task(fake_task())
        await asyncio.sleep(0)  # let the scheduler finish the task
        return ret
    else:
        return asyncio.create_task(background_task_wrapper(task, name), name=name)


@asynccontextmanager
async def background_task(task: Awaitable[T], name: str | None = None) -> AsyncIterator[asyncio.Task[T | None]]:
    """
    This will always run the task in the background, and will cancel it when the context manager exits. You can await
    the returned task to wait for the result.

    async def task() -> str:
        asyncio.sleep(1)
        return "done"

    async with background_task(task()) as result:
        await asyncio.sleep(2)

    print(result.result())
    """
    _task = asyncio.create_task(background_task_wrapper(task, name), name=name)
    try:
        yield _task
    finally:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass


async def sleep_forever() -> None:
    "Sleep forever helper because I can't find a sensible other way to do this"
    while True:
        await asyncio.sleep(10)
