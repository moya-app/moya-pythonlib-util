import asyncio
import random
import time

import pytest

from moya.util.asyncpool import asyncpool, asyncpool_queue


async def test_basic_asyncpool() -> None:
    items: list[int] = []

    total_sleep = 0

    async def worker(item):
        nonlocal total_sleep
        to_sleep = random.random() / 10
        total_sleep += to_sleep
        await asyncio.sleep(to_sleep)  # Yield to allow other tasks to run and to disorder the outputs
        items.append(item * item)

    start = time.time()
    async with asyncpool_queue(worker, worker_count=10) as queue:
        for i in range(100):
            await queue.put(i)
        await queue.join()  # Test we have full functionality
    end = time.time()
    assert end - start < total_sleep / 4, "Queue should have been processed in parallel workers"

    assert items != [i * i for i in range(100)], "Queue should have been processed not in-order"
    assert sorted(items) == [i * i for i in range(100)]

    # Test with asyncpool now
    total_sleep = 0
    items = []
    start = time.time()
    async with asyncpool(worker, worker_count=10) as enqueue:
        for i in range(100):
            await enqueue(i)
    end = time.time()
    assert end - start < total_sleep / 4, "Queue should have been processed in parallel workers"

    assert items != [i * i for i in range(100)], "Queue should have been processed not in-order"
    assert sorted(items) == [i * i for i in range(100)]


async def test_asyncpool_errors(caplog: pytest.LogCaptureFixture) -> None:
    items: list[float] = []

    async def worker(item):
        items.append(10.0 / item)

    # Pop some nulls into the queue to blow it up at various points
    to_push = list(range(100)) + [0] * 5
    random.shuffle(to_push)
    async with asyncpool(worker, worker_count=10) as enqueue:
        for i in to_push:
            await enqueue(i)

    assert sorted(items) == sorted([10.0 / i for i in range(1, 100)])
    assert len(caplog.records) == 6
    assert [r.exc_info[0] for r in caplog.records if r.exc_info] == [ZeroDivisionError] * 6
    assert sum(("Error processing item 0" in r.getMessage() for r in caplog.records)) == 6
