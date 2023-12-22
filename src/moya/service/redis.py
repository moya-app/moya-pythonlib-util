import logging
import typing as t
from contextlib import asynccontextmanager
from functools import cache

import redis.asyncio as aioredis
from redis import Redis  # noqa: F401 for reexport
from redis.backoff import ExponentialBackoff
from redis.exceptions import (  # noqa: F401 for reexport
    ConnectionError,
    RedisError,
    TimeoutError,
)
from redis.retry import Retry

from moya.util.config import MoyaSettings

logger = logging.getLogger("moya-redis")


class RedisSettings(MoyaSettings):
    """
    Pull settings from standardized redis environment variables
    """

    redis_url: str
    redis_password: str

    # By default, redis will hang forever if the connection connects but
    # cannot send/receive data. Ensure it blows up rather than hangs.
    redis_timeout: float = 1.0
    redis_connect_retries: int = 3


@cache
def redis_settings() -> RedisSettings:
    """
    Lazy load Redis settings from env vars
    """
    return RedisSettings()


@cache
def pool(settings: RedisSettings) -> aioredis.ConnectionPool:
    """
    Create a redis connection pool
    """
    # Retry only applies to trying to get a connection, not if an individual connection times out.
    retry = Retry(ExponentialBackoff(), settings.redis_connect_retries)
    return aioredis.ConnectionPool.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        password=settings.redis_password,
        socket_connect_timeout=settings.redis_timeout,
        socket_timeout=settings.redis_timeout,
        retry=retry,
        retry_on_error=[ConnectionError, TimeoutError],
    )


@asynccontextmanager
async def redis(settings: RedisSettings = None) -> t.AsyncGenerator[aioredis.Redis, None]:
    """
    Return a redis connection from the pool, and close it correctly when completed. Usage:

    from moya.service.redis import redis, ConnectionError, TimeoutError

    try:
        async with redis() as redis_conn:
            content = await redis_conn.get("key")
            ... stuff with redis_conn ...
    except (TimeoutError, ConnectionError) as e:
        logger.exception("Redis connection error", exc_info=e)
    except RedisError as e:
        logger.exception("Other redis error", exc_info=e)
    """
    if settings is None:
        settings = redis_settings()
    conn = aioredis.Redis.from_pool(pool(settings))

    # For some reason this occasionally happens during redis failover rather
    # than from_pool just raising the exception
    if not conn:
        raise ConnectionError("Could not connect to redis")
    yield conn
    await conn.aclose()


async def redis_try_run(coro: t.Callable[[t.Any], t.Awaitable[t.Any]]) -> t.Optional[t.Any]:
    """
    Run a coroutine and log and ignore redis-specific errors. Depending on
    whether connection succeeds the coroutine may never even be run.

    It will return the value returned by the coroutine, or None if there was a
    redis-related error. Other exceptions are raised in the usual way.

    Usage:

    from moya.service.redis import redis_try_run, Redis

    async def fetch(redis_conn: Redis) -> t.Optional[dict]:
        return await redis_conn.get("key")

    return await redis_try_run(fetch)
    """
    try:
        async with redis() as redis_conn:
            return await coro(redis_conn)
    except (ConnectionError, TimeoutError) as e:
        logger.exception("Redis connection error", exc_info=e)
        return None
    except RedisError as e:
        logger.exception("Redis general error", exc_info=e)
        return None
