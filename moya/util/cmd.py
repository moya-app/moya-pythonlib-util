"Tools for running Moya command-line processes"

import asyncio
import typing as t

import uvloop

from moya.util.logging import setup_logging
from moya.util.sentry import init as setup_sentry

Res = t.TypeVar("Res", bound=None | int)


def setup() -> None:
    setup_sentry()
    setup_logging()


def run_async(coro: t.Awaitable[Res]) -> Res:
    """
    Set up various standard logging etc and run the specified coroutine returning its result if any.
    """
    setup()
    # Once min supported version is python 3.12 just use uvloop.run(coro)
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    return asyncio.run(coro)  # type: ignore[arg-type] # looks like linting doesnt know it can return
