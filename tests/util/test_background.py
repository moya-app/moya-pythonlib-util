import asyncio
import time

from moya.util.background import background_task, run_in_background


async def example_task() -> str:
    await asyncio.sleep(1)
    return "done"


async def test_basics() -> None:
    start = time.time()
    res = await run_in_background(example_task())
    assert time.time() - start < 0.1, "Should have run in background"
    await asyncio.sleep(1.1)
    assert res.done(), "Should have finished"
    assert res.result() == "done", "Should have returned result"

    start = time.time()
    res = await run_in_background(example_task())
    await asyncio.sleep(0.1)
    res.cancel()
    assert time.time() - start < 0.2, "Should have run in background for a short time"
    await asyncio.sleep(0)  # let the scheduler finish the task
    assert res.done(), "Should have finished"


async def test_no_run_in_background(no_background_tasks: None) -> None:
    start = time.time()
    res = await run_in_background(example_task())
    assert 0.9 <= time.time() - start < 2, "Should not have run in background"
    assert res.done(), "Should have finished"
    assert res.result() == "done", "Should have returned result"

    start = time.time()
    await run_in_background(asyncio.sleep(1), force_run_in_background=True)
    assert time.time() - start < 0.1, "Should have run in background"
    await asyncio.sleep(1.1)
    assert res.done(), "Should have finished"
    assert res.result() == "done", "Should have returned result"

    # With never_run_in_background set there should be no change in behaviour with the context manager
    await test_background_task_cm()


async def test_background_task_cm() -> None:
    start = time.time()
    async with background_task(example_task()) as res:
        await asyncio.sleep(0.1)
        assert not res.done(), "Should not yet have finished"
        await res

    assert 0.9 < time.time() - start < 1.2, "Should have waited for the task to finish"

    # With auto-cancellation
    start = time.time()
    async with background_task(example_task()) as res:
        await asyncio.sleep(0.1)

    assert res.result() is None, "Should have cancelled the task"
    assert 0.1 < time.time() - start < 0.2, "Should have cancelled the task in reasonable time"
