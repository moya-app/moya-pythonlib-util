import logging
import typing as t
from contextlib import asynccontextmanager
from functools import cache

import redis.asyncio as aioredis
from pydantic import validator
from redis.asyncio import Redis  # noqa: F401 for reexport
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

    redis_url: t.Optional[str] = None
    redis_password: str

    redis_sentinel_hosts: t.Optional[tuple[tuple[str, int], ...]] = None
    redis_sentinel_service: str = "mymaster"

    # By default, redis will hang forever if the connection connects but
    # cannot send/receive data. Ensure it blows up rather than hangs.
    redis_timeout: float = 1.0
    redis_connect_retries: int = 3

    @validator("redis_sentinel_hosts", always=True)
    def check_valid_connection(cls, sentinel_hosts: str, values: dict[str, t.Any]) -> str:
        url = values.get("redis_url", None)
        if url is None and sentinel_hosts is None:
            raise ValueError("Must specify APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS")
        if url is not None and sentinel_hosts is not None:
            raise ValueError("Must only specify one of APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS")
        return sentinel_hosts

    @property
    def is_sentinel(self) -> bool:
        """
        Return True if this is a sentinel configuration
        """
        return bool(self.redis_sentinel_hosts)


@cache
def redis_settings() -> RedisSettings:
    """
    Lazy load Redis settings from env vars
    """
    return RedisSettings()


def _standard_connection_kwargs(settings: RedisSettings) -> dict[str, t.Any]:
    """
    Return a dict of standard connection kwargs for all redis pools
    """
    # Retry only applies to trying to get a connection, not if an individual connection times out.
    retry = Retry(ExponentialBackoff(), settings.redis_connect_retries)
    return {
        "encoding": "utf-8",
        "decode_responses": True,
        "password": settings.redis_password,
        "socket_connect_timeout": settings.redis_timeout,
        "socket_timeout": settings.redis_timeout,
        "retry": retry,
        "retry_on_error": [ConnectionError, TimeoutError],
    }


@cache
def sentinel(settings: RedisSettings) -> aioredis.sentinel.Sentinel:
    "Create a redis sentinel client"
    return aioredis.sentinel.Sentinel(sentinels=settings.redis_sentinel_hosts, **_standard_connection_kwargs(settings))


@cache
def pool(settings: RedisSettings) -> aioredis.ConnectionPool:
    "Create a redis connection pool"
    return aioredis.ConnectionPool.from_url(settings.redis_url, **_standard_connection_kwargs(settings))


@asynccontextmanager
async def redis(readonly: bool = False, settings: RedisSettings = None) -> t.AsyncGenerator[aioredis.Redis, None]:
    """
    Return a redis connection from the pool, and close it correctly when
    completed. If sentinel is available in the config it will prefer to use
    that.

    :param readonly: If specified it may choose to use a slave server to connect to

    Usage:

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

    if settings.is_sentinel:
        sent = sentinel(settings)
        if readonly:
            conn = sent.slave_for(settings.redis_sentinel_service)
        else:
            conn = sent.master_for(settings.redis_sentinel_service)
    else:
        conn = aioredis.Redis.from_pool(pool(settings))

    # For some reason this occasionally happens during redis failover rather
    # than from_pool just raising the exception
    if not conn:
        raise ConnectionError("Could not connect to redis")
    yield conn
    await conn.aclose()


async def redis_try_run(coro: t.Callable[[t.Any], t.Awaitable[t.Any]], readonly: bool = False) -> t.Optional[t.Any]:
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
        async with redis(readonly) as redis_conn:
            return await coro(redis_conn)
    except (ConnectionError, TimeoutError) as e:
        logger.exception("Redis connection error", exc_info=e)
        return None
    except RedisError as e:
        logger.exception("Redis general error", exc_info=e)
        return None
