import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager

logger = logging.getLogger("asyncpool")

T = t.TypeVar("T")


async def _run_worker(queue: asyncio.Queue[T], fn: t.Callable[[T], t.Awaitable[None]]) -> None:
    while True:
        item = await queue.get()

        # Wrap in exception handler to still catch errors
        try:
            await fn(item)
        except Exception as e:
            logger.exception(f"Error processing item {item}", exc_info=e)
        finally:
            queue.task_done()


@asynccontextmanager
async def asyncpool(fn: t.Callable[[T], t.Awaitable[None]], worker_count: int = 5, maxsize: int = 0) -> t.AsyncIterator[t.Callable[[T], t.Awaitable[None]]]:
    """
    Run a pool of workers to process items from a queue. The queue is returned
    from the context manager and can be used to enqueue items for processing.

    The queue is automatically closed when the context manager exits.

    Exceptions in the worker function will be logged but never passed back to the caller.

    :param fn: The function to run for each item in the queue.
    :param worker_count: The number of workers to run
    :param maxsize: The maximum size of the queue. If 0, the queue is unbounded.

    Usage:

    async def worker(item):
        ... do stuff ...

    async def ...:
        async with asyncpool(worker, worker_count=10) as enqueue:
            for i in range(100):
                await enqueue(i)
    """

    queue: asyncio.Queue[T] = asyncio.Queue(maxsize=maxsize)
    workers = [asyncio.create_task(_run_worker(queue, fn)) for _ in range(worker_count)]

    try:
        yield queue.put
    finally:
        await queue.join()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
