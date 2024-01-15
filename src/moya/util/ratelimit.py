import abc
import time
from functools import cached_property

from pydantic import BaseModel

from moya.service.redis import Redis, redis_try_run
from moya.util.background import run_in_background

"""
Generic ratelimit-related stuff, should have no FastAPI dependencies
"""


class RateLimit(BaseModel):
    per_second: int = None
    per_minute: int = None
    per_hour: int = None
    per_day: int = None

    class Config:
        keep_untouched = (cached_property,)

    @cached_property
    def rates(self) -> list[tuple[int, int]]:
        return [
            (limit, duration)
            for limit, duration in (
                (self.per_second, 1),
                (self.per_minute, 60),
                (self.per_hour, 60 * 60),
                (self.per_day, 24 * 60 * 60),
            )
            if limit is not None
        ]

    @property
    def max_duration(self) -> int:
        return self.rates[-1][1]

    @property
    def is_empty(self) -> bool:
        return self.per_second is None and self.per_minute is None and self.per_hour is None and self.per_day is None


class RateLimitExceeded(Exception):
    """
    Raised because the given endpoint's ratelimit has been exceeded
    """

    pass


class LimitBase:
    """
    Base class for rate limiters
    """

    def __init__(self, rates: RateLimit, base_key: str) -> None:
        self.rates = rates
        self.base_key = base_key
        if len(self.key("")) < 4:
            raise ValueError("base_key is too short. Must be at least 4 characters")

    def key(self, user_id: str) -> str:
        """
        Given a user_id return the base key to use for the ratelimiter
        """
        return ":".join([self.base_key, user_id])

    @abc.abstractmethod
    async def try_ratelimit(self, user_id: str) -> None:
        """
        raise RateLimitExceeded exception if ratelimit is exceeded, otherwise return normally.
        """
        pass

    @abc.abstractmethod
    async def flush_user(self, user_id: str) -> None:
        """
        Flush the given user's ratelimit for this limiter
        """
        pass

    @abc.abstractmethod
    async def reset(self) -> None:
        """
        Reset everything to do with this limiter
        """
        pass


class MemLimiter(LimitBase):
    """
    A memory-based limiter using a dictionary to store the timestamps of each
    request. This is mostly used for testing and should not be used in
    production.
    """

    def __init__(self, rates: RateLimit, base_key: str) -> None:
        super().__init__(rates, base_key)
        self._reset()

    async def try_ratelimit(self, user_id: str) -> None:
        now = time.time()
        cur_limits = self._limits.setdefault(self.key(user_id), [])

        for limit, duration in self.rates.rates:
            if sum(1 for t in cur_limits if t > now - duration) >= limit:
                raise RateLimitExceeded()

        cur_limits.append(now)

    async def flush_user(self, user_id: str) -> None:
        del self._limits[self.key(user_id)]

    def _reset(self) -> None:
        # Ordered list of timestamps for the given limit. Could set it to purge
        # after a certain timestamp if we wanted, but this limiter is mostly
        # just used for testing anyway.
        self._limits: dict[str, list[float]] = {}

    async def reset(self) -> None:
        self._reset()


class RedisLimiter(LimitBase):
    """
    A Redis-based limiter using sorted sets to store the timestamps each user
    accessed a given function. If there is any issue with redis connectivity
    this should fail open, perhaps with a couple of seconds delay to the calls.
    """

    async def try_ratelimit(self, user_id: str) -> None:
        now = time.time()
        key = self.key(user_id)

        async def check_rates(redis: Redis) -> None:
            # Use pipelining to ensure only 1 round-trip
            async with redis.pipeline() as pipe:
                for limit, duration in self.rates.rates:
                    pipe.zcount(key, now - duration, now)
                results = await pipe.execute()

            for (limit, duration), count in zip(self.rates.rates, results):
                if count >= limit:
                    raise RateLimitExceeded()

        await redis_try_run(check_rates, readonly=True)

        async def update_rates(redis: Redis) -> None:
            async with redis.pipeline() as pipe:
                # Log the request
                pipe.zadd(key, {str(now): now})  # TODO: Better key name - random id perhaps?

                # Set expiry for the key as a whole (you cannot set for the individual items)
                pipe.expire(key, self.rates.max_duration)

                # Remove old items from the list
                pipe.zremrangebyscore(key, 0, now - self.rates.max_duration)
                await pipe.execute()

        await run_in_background(redis_try_run(update_rates))

    async def flush_user(self, user_id: str) -> None:
        async def cleanup_rates(redis: Redis) -> None:
            await redis.delete(self.key(user_id))

        await redis_try_run(cleanup_rates)

    async def reset(self) -> None:
        async def reset_redis(redis: Redis) -> None:
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=self.key("*"), count=1000)
                if keys:
                    await redis.delete(*keys)
                if cursor == 0:
                    break

        await redis_try_run(reset_redis)
