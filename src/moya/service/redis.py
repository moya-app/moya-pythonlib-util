import logging
import pickle
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

from moya.util.background import run_in_background
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
    redis_sentinel_password: t.Optional[str] = None  # if None then redis_password is used

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


def _standard_connection_kwargs(settings: RedisSettings, decode_responses: bool = True) -> dict[str, t.Any]:
    """
    Return a dict of standard connection kwargs for all redis pools
    """
    # Retry only applies to trying to get a connection, not if an individual connection times out.
    retry = Retry(ExponentialBackoff(), settings.redis_connect_retries)  # type: ignore
    return {
        "encoding": "utf-8",
        "decode_responses": decode_responses,
        "password": settings.redis_password,
        "socket_connect_timeout": settings.redis_timeout,
        "socket_timeout": settings.redis_timeout,
        "retry": retry,
        "retry_on_error": [ConnectionError, TimeoutError],
    }


@cache
def sentinel(settings: RedisSettings, **kwargs: t.Any) -> aioredis.sentinel.Sentinel:
    "Create a redis sentinel client"
    return aioredis.sentinel.Sentinel(  # type: ignore
        settings.redis_sentinel_hosts,
        **_standard_connection_kwargs(settings, **kwargs),
        sentinel_kwargs={
            **_standard_connection_kwargs(settings, **kwargs),
            "password": settings.redis_sentinel_password or settings.redis_password,
        },
    )


@cache
def pool(settings: RedisSettings, **kwargs: t.Any) -> aioredis.ConnectionPool:
    "Create a redis connection pool"
    if not settings.redis_url:
        raise ValueError("Redis URL is not set")
    return aioredis.ConnectionPool.from_url(settings.redis_url, **_standard_connection_kwargs(settings, **kwargs))


@asynccontextmanager
async def redis(
    readonly: bool = False, settings: RedisSettings | None = None, **kwargs: t.Any
) -> t.AsyncGenerator[aioredis.Redis, None]:
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
        sent = sentinel(settings, **kwargs)
        if readonly:
            conn = sent.slave_for(settings.redis_sentinel_service)
        else:
            conn = sent.master_for(settings.redis_sentinel_service)
    else:
        conn = aioredis.Redis.from_pool(pool(settings, **kwargs))

    # For some reason this occasionally happens during redis failover rather
    # than from_pool just raising the exception
    if not conn:
        raise ConnectionError("Could not connect to redis")
    yield conn
    await conn.aclose()


Result = t.TypeVar("Result")


async def redis_try_run(
    coro: t.Callable[[aioredis.Redis], t.Awaitable[Result]], readonly: bool = False, **kwargs: t.Any
) -> t.Optional[Result]:
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
        async with redis(readonly, **kwargs) as redis_conn:
            return await coro(redis_conn)
    except (ConnectionError, TimeoutError) as e:
        logger.exception("Redis connection error", exc_info=e)
        return None
    except RedisError as e:
        logger.exception("Redis general error", exc_info=e)
        return None


class RedisCached:
    def __init__(
        self, func: t.Callable[..., t.Awaitable[Result]], key: str, expiry: int | None = None, cache_none: bool = True
    ) -> None:
        self.func = func
        self.key = key
        self.expiry = expiry
        self.cache_none = cache_none

    def get_cache_key(self, *args: t.Any, **kwargs: t.Any) -> str:
        return f"pickle:{self.key}:{args}:{kwargs}"

    async def __call__(self, *args: t.Any, **kwargs: t.Any) -> Result:
        async def fetch(redis_conn: Redis) -> Result | None:
            data = await redis_conn.get(self.get_cache_key(args, kwargs))
            if data:
                return t.cast(Result, pickle.loads(data))
            return None

        cached = await redis_try_run(fetch, readonly=True, decode_responses=False)
        if cached:
            return cached

        result = await self.func(*args, **kwargs)

        # TypeVar of Result may include a return of None, or it may not - we
        # don't know. MyPy thinks this statement in unreachable because it
        # doesn't believe the return from here could be None though.
        if result is None and not self.cache_none:  # type: ignore
            return result  # type: ignore

        # Dump the result to a local variable as it would be saved to redis
        # here before the background task runs. There may be a race if the
        # result is modified by the caller before the update_redis() function
        # is run.
        saved_result = pickle.dumps(result)

        async def update_redis(redis_conn: Redis) -> None:
            await redis_conn.set(self.get_cache_key(args, kwargs), saved_result, ex=self.expiry)

        await run_in_background(redis_try_run(update_redis, decode_responses=False))
        return result

    async def delete_entry(self, *args: t.Any, **kwargs: t.Any) -> None:
        async def delete(redis_conn: Redis) -> None:
            await redis_conn.delete(self.get_cache_key(args, kwargs))

        await redis_try_run(delete)


def redis_cached(
    key: str, expiry: int | None = None, cache_none: bool = True
) -> t.Callable[[t.Callable[..., t.Awaitable[Result]]], RedisCached]:
    """
    Decorator to cache the result of a function in redis

    :param key: The key prefix to use for the cache (it will serialize all the
      arguments to the function as part of the key too).
    :param expiry: The expiry time in seconds. If not set, the result will be cached forever.
    :param cache_none: If set to False, the result will not be cached if it is None.
    """

    def decorator(func: t.Callable[..., t.Awaitable[Result]]) -> RedisCached:
        return RedisCached(func, key, expiry, cache_none=cache_none)

    return decorator


def _mypy_test_fn() -> None:
    """
    Validation that @redis_cached wraps return type correctly. Cannot put in
    test suite because that doesnt have the same level of checking as actual
    code. Code not intended to ever be executed
    """

    @redis_cached(key="internal_test")
    async def _test_cached() -> int:
        return 1

    async def foo() -> int:
        return await _test_cached()

    @redis_cached(key="internal_test2")
    async def _test_cached2() -> int | None:
        return None

    async def foo2() -> int | None:
        return await _test_cached2()
