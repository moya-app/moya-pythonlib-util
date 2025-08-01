import asyncio
import logging
import typing as t
from unittest.mock import Mock, patch

import pytest

from moya.util.background_tasks import repeat_every


@pytest.fixture
def mock_ensure_future() -> t.Generator[tuple[Mock, list[asyncio.Task[None]]], None, None]:
    """A fixture to patch asyncio.ensure_future and capture the created task."""
    created_tasks: list[asyncio.Task[None]] = []

    def side_effect(coro: t.Any) -> asyncio.Task[None]:
        task: asyncio.Task[None] = asyncio.Task(coro)
        created_tasks.append(task)
        return task

    with patch("moya.util.background_tasks.ensure_future", side_effect=side_effect) as mock:
        yield mock, created_tasks


@pytest.mark.asyncio
async def test_repeat_every_async_function(mock_ensure_future: t.Any) -> None:
    """Test that an async function is repeatedly called."""
    mock_func = Mock()
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.01)
    async def my_task() -> None:
        mock_func()

    await my_task()
    await asyncio.sleep(0.05)
    for task in created_tasks:
        task.cancel()
    assert mock_func.call_count > 2


@pytest.mark.asyncio
async def test_repeat_every_sync_function(mock_ensure_future: t.Any) -> None:
    """Test that a sync function is repeatedly called."""
    mock_func = Mock()
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.01)
    def my_task() -> None:
        mock_func()

    await my_task()
    await asyncio.sleep(0.05)
    for task in created_tasks:
        task.cancel()
    assert mock_func.call_count > 2


@pytest.mark.asyncio
async def test_repeat_every_wait_first(mock_ensure_future: t.Any) -> None:
    """Test that the first call is delayed when wait_first is True."""
    mock_func = Mock()
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.1, wait_first=True)
    async def my_task() -> None:
        mock_func()

    await my_task()
    mock_func.assert_not_called()
    await asyncio.sleep(0.15)
    for task in created_tasks:
        task.cancel()
    assert mock_func.call_count >= 1


@pytest.mark.asyncio
async def test_repeat_every_max_repetitions(mock_ensure_future: t.Any) -> None:
    """Test that the function stops after max_repetitions."""
    mock_func = Mock()
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.01, max_repetitions=3)
    async def my_task() -> None:
        mock_func()

    await my_task()
    await asyncio.sleep(0.1)
    assert mock_func.call_count == 3
    # No need to cancel tasks here as they should complete on their own


@pytest.mark.asyncio
async def test_repeat_every_logs_exception(mock_ensure_future: t.Any) -> None:
    """Test that exceptions are logged."""
    mock_logger = Mock(spec=logging.Logger)
    mock_func = Mock(side_effect=ValueError("test error"))
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.01, logger=mock_logger)
    def my_task() -> None:
        mock_func()

    await my_task()
    await asyncio.sleep(0.05)
    for task in created_tasks:
        task.cancel()
    mock_logger.exception.assert_called()
    assert mock_func.call_count > 2  # It should continue running


@pytest.mark.asyncio
async def test_repeat_every_raise_exceptions(mock_ensure_future: t.Any) -> None:
    """Test that exceptions are raised and the loop stops."""
    mock_func = Mock(side_effect=ValueError("test error"))
    _, created_tasks = mock_ensure_future

    @repeat_every(seconds=0.01, raise_exceptions=True)
    def my_task() -> None:
        mock_func()

    await my_task()
    with pytest.raises(ValueError, match="test error"):
        for task in created_tasks:
            await task

    mock_func.assert_called_once()
