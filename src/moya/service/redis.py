import typing as t
from contextlib import asynccontextmanager
from functools import cache

import redis.asyncio as aioredis
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError
from redis.retry import Retry

from moya.util.config import MoyaSettings


class RedisSettings(MoyaSettings):
    """
    Pull settings from standardized redis environment variables
    """

    redis_url: str
    redis_password: str


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
    retry = Retry(ExponentialBackoff(), 10)
    return aioredis.ConnectionPool.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        password=settings.redis_password,
        retry=retry,
        retry_on_error=[ConnectionError, TimeoutError],
    )


@asynccontextmanager
async def redis(settings: RedisSettings = None) -> t.AsyncGenerator[aioredis.Redis, None]:
    """
    Return a redis connection from the pool, and close it correctly when completed. Usage:

    from moya.service.redis import redis, ConnectionError

    try:
        async with redis() as redis_conn:
            content = await redis_conn.get("key")
            ... stuff with redis_conn ...
    except ConnectionError as e:
        logger.exception("Redis connection error", exc_info=e)
    """
    if settings is None:
        settings = redis_settings()
    conn = aioredis.Redis.from_pool(pool(settings))
    yield conn
    await conn.aclose()
