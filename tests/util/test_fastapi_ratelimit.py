import os
import typing as t
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# from moya.service.redis import redis
from httpx import AsyncClient

from moya.util.fastapi_ratelimit import (  # , MemLimiter
    RateLimit,
    RateLimiter,
    RateLimiterDep,
)
from moya.util.ratelimit import MemLimiter, RedisLimiter


async def ensure_verified(credentials: t.Annotated[HTTPBasicCredentials, Depends(HTTPBasic())]):
    """
    FastAPI hack for test user verification
    """
    return None if credentials.username == "admin" else credentials.username


async def test_basic_memlimiter(time_machine) -> None:
    with patch.dict(os.environ, {"APP_RATELIMITS": '{"test": {"per_minute": 2, "per_hour": 4}}'}):
        limiter = RateLimiter("test", Depends(ensure_verified), limiter_class=MemLimiter)

        await do_tests(time_machine, limiter)

    # TODO: Test RateLimiterDep


@pytest.mark.skipif("SENTINEL_HOSTS" not in os.environ, reason="SENTINEL_HOSTS not specified")
async def test_redis_limiter(time_machine) -> None:
    with patch.dict(
        os.environ,
        {
            "APP_RATELIMITS": '{"test": {"per_minute": 2, "per_hour": 4}}',
            "APP_REDIS_PASSWORD": "testpassword",
            "APP_REDIS_SENTINEL_HOSTS": os.environ["SENTINEL_HOSTS"],
        },
    ):
        limiter = RateLimiter("test", Depends(ensure_verified), limiter_class=RedisLimiter)

        await do_tests(time_machine, limiter)


async def test_empty_limits() -> None:
    """
    When limits are blank it should just work
    """
    with patch.dict(os.environ, {"APP_RATELIMITS": '{"test": {}}'}):
        app = FastAPI()

        @app.get("/{id}", dependencies=[RateLimiterDep("test", Depends(ensure_verified), limiter_class=MemLimiter)])
        async def root():
            return {"message": "Hello World"}

        tester = AsyncClient(app=app, base_url="http://test")
        for i in range(10):
            res = await tester.get("/1", auth=("user1", "pass"))
            assert res.status_code == 200, "Should be no limits in place"


async def test_env_pickups_named() -> None:
    with patch.dict(os.environ, {"APP_RATELIMITS": '{"test": {"per_minute": 2, "per_hour": 4}}'}):
        app = FastAPI()

        # If no default limit should blow up
        with pytest.raises(KeyError, match="No ratelimits configured for limiter 'foo'"):
            RateLimiterDep("foo", Depends(ensure_verified), limiter_class=MemLimiter)

        # No limit but a default should work correctly
        @app.get(
            "/{id}",
            dependencies=[
                RateLimiterDep(
                    "foo", Depends(ensure_verified), default_limits=RateLimit(per_second=1), limiter_class=MemLimiter
                )
            ],
        )
        async def root():
            return {"message": "Hello World"}

        tester = AsyncClient(app=app, base_url="http://test")
        res = await tester.get("/1", auth=("user1", "pass"))
        assert res.status_code == 200, "First request should be allowed"
        res = await tester.get("/2", auth=("user1", "pass"))
        assert res.status_code == 429, "Second request should be blocked"


async def test_env_pickups_default() -> None:
    with patch.dict(os.environ, {"APP_RATELIMITS": '{"*": {"per_second": 1}}'}):
        app = FastAPI()

        # If default should work correctly
        @app.get("/{id}", dependencies=[RateLimiterDep("foo", Depends(ensure_verified), limiter_class=MemLimiter)])
        async def root():
            return {"message": "Hello World"}

        tester = AsyncClient(app=app, base_url="http://test")
        res = await tester.get("/1", auth=("user1", "pass"))
        assert res.status_code == 200, "First request should be allowed"
        res = await tester.get("/2", auth=("user1", "pass"))
        assert res.status_code == 429, "Second request should be blocked"


async def do_tests(time_machine, limiter) -> None:
    """
    General full test for a limiter
    """
    time_machine.move_to("2021-01-01 00:00:00")
    app = FastAPI()

    @app.get("/{id}", dependencies=[limiter.dependency])
    async def root():
        return {"message": "Hello World"}

    tester = AsyncClient(app=app, base_url="http://test")
    res = await tester.get("/1", auth=("user1", "pass"))
    assert res.status_code == 200, "First request should be allowed"
    res = await tester.get("/2", auth=("user1", "pass"))
    assert res.status_code == 200, "Second request should be allowed"
    res = await tester.get("/3", auth=("user1", "pass"))
    assert res.status_code == 429, "3rd request should be ratelimited"
    res = await tester.get("/4", auth=("user2", "pass"))
    assert res.status_code == 200, "Request from a different user should not be ratelimited"
    res = await tester.get("/5", auth=("user1", "pass"))
    assert res.status_code == 429, "4rd request should be ratelimited"

    for i in range(10):
        res = await tester.get("/admin", auth=("admin", "pass"))
        assert res.status_code == 200, "None user should never be ratelimited"

    time_machine.shift(61)
    res = await tester.get("/6", auth=("user1", "pass"))
    assert res.status_code == 200, "After 1 minute, 2 requests should be allowed again"
    res = await tester.get("/7", auth=("user1", "pass"))
    assert res.status_code == 200, "After 1 minute, 2 requests should be allowed again"
    res = await tester.get("/8", auth=("user1", "pass"))
    assert res.status_code == 429, "After 1 minute, 2 requests should be allowed again"

    time_machine.shift(61)
    for i in range(2):  # Block user2
        res = await tester.get("/4", auth=("user2", "pass"))

    for user in ("user1", "user2"):
        res = await tester.get("/9", auth=(user, "pass"))
        assert res.status_code == 429, "Both users should now be blocked"

    await limiter.reset_user("user1")
    res = await tester.get("/6", auth=("user1", "pass"))
    assert res.status_code == 200, "After a reset, requests should be allowed again"
    res = await tester.get("/7", auth=("user1", "pass"))
    assert res.status_code == 200, "After a reset, requests should be allowed again"
    res = await tester.get("/9", auth=("user2", "pass"))
    assert res.status_code == 429, "user2 should still be blocked after resetting user1"
    time_machine.shift(61)
    res = await tester.get("/7", auth=("user1", "pass"))
    assert res.status_code == 200, "After a reset, requests should be allowed again"
    res = await tester.get("/7", auth=("user1", "pass"))
    assert res.status_code == 200, "After a reset, requests should be allowed again"
    res = await tester.get("/8", auth=("user1", "pass"))
    assert res.status_code == 429, "Should be blocked now"

    for i in range(2):  # Block user2
        res = await tester.get("/4", auth=("user2", "pass"))
    res = await tester.get("/7", auth=("user2", "pass"))
    assert res.status_code == 429, "User2 should also be blocked now"
    await limiter.reset_all()
    for user in ("user1", "user2"):
        res = await tester.get("/7", auth=(user, "pass"))
        assert res.status_code == 200, "After a full reset, requests should be allowed again from all users"
