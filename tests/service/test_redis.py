import os
import typing as t
import uuid
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import ANY, patch

import pytest
from pydantic import BaseModel
from redis.asyncio.client import Redis
from redis.asyncio.sentinel import MasterNotFoundError
from redis.exceptions import ReadOnlyError

import moya.service.redis as r


@asynccontextmanager
async def random_key() -> t.AsyncGenerator[str, None]:
    yield f"test:{uuid.uuid4()}"


@contextmanager
def fake_redis_config(env: dict[str, str]) -> t.Generator[None, None, None]:
    default_test_env = {
        "APP_REDIS_TIMEOUT": "0.1",
        "APP_REDIS_CONNECT_RETRIES": "1",
        "APP_REDIS_PASSWORD": "testpassword",
    }
    with patch.dict(os.environ, {**default_test_env, **env}):
        # Recreate the base redis() client with the new config
        r._redis = r.MoyaRedisClient()
        r.redis = r._redis.get_connection
        r.redis_try_run = r._redis.try_run

        yield


def test_settings() -> None:
    with fake_redis_config({"APP_REDIS_URL": "redis://localhost:6379/0"}):
        s = r.RedisSettings()
        assert s, "Should work with standard config"
        assert s.is_sentinel is False, "Should not be sentinel config"
        assert r._redis._standard_connection_kwargs() == {
            "encoding": "utf-8",
            "decode_responses": True,
            "username": None,
            "password": "testpassword",
            "socket_connect_timeout": 0.1,
            "socket_timeout": 0.1,
            "retry": ANY,
            "retry_on_error": [r.ConnectionError, r.TimeoutError],
        }, "Should have correct pool connection setup"

    sentinel_good_envs = [
        {"APP_REDIS_SENTINEL_HOSTS": '[["1.2.3.4", 1234]]'},
        {"APP_REDIS_SENTINEL_HOSTS": '[["1.2.3.4", 1234], ["1.2.3.4", 1235]]'},
    ]
    for env in sentinel_good_envs:
        with fake_redis_config(env):
            s = r.RedisSettings()
            assert s, f"Should work with sentinel config {env}"
            assert s.is_sentinel is True, f"Should be sentinel config {env}"

    with fake_redis_config({}), pytest.raises(ValueError, match="Must specify APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS"):
        r.RedisSettings()

    with (
        fake_redis_config(
            {
                "APP_REDIS_URL": "redis://localhost:6379/0",
                "APP_REDIS_SENTINEL_HOSTS": '[["1.2.3.4", 1234]]',
            },
        ),
        pytest.raises(ValueError, match="Must only specify one of APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS"),
    ):
        r.RedisSettings()


@pytest.mark.skipif("SENTINEL_HOSTS" not in os.environ or "REDIS_URL" not in os.environ, reason="Requires docker-compose redis env")
async def test_redis(subtests: t.Any, no_background_tasks: None) -> None:
    for config, readonly_enforced, writeable in (
        ({"APP_REDIS_URL": os.environ["REDIS_URL"]}, False, True),
        ({"APP_REDIS_URL": os.environ["REDIS_SLAVE_URL"]}, True, False),
        ({"APP_REDIS_SENTINEL_HOSTS": os.environ["SENTINEL_HOSTS"]}, True, True),
    ):
        with fake_redis_config(config):
            for readonly in (True, False):
                if readonly and readonly_enforced or not writeable:
                    with subtests.test(f"redis() {config} readonly={readonly}"):
                        with pytest.raises(ReadOnlyError):
                            async with r.redis(readonly) as redis_conn, random_key() as key:
                                await redis_conn.set(key, "value")

                    with subtests.test(f"redis_try_run() {config} readonly={readonly}"):

                        async def runner(redis_conn: Redis) -> None:
                            with pytest.raises(ReadOnlyError):
                                async with random_key() as key:
                                    await redis_conn.set(key, "value")

                        await r.redis_try_run(runner, readonly=readonly)
                else:
                    with subtests.test(f"redis() {config} readonly={readonly}"):
                        async with r.redis(readonly) as redis_conn, random_key() as key:
                            ok = await redis_conn.set(key, "value")
                            assert ok, "Should have been able to set redis key"
                            assert await redis_conn.get(key) == "value", "Should have been able to get redis key"

                    with subtests.test(f"redis_try_run() {config} readonly={readonly}"):

                        async def runner(redis_conn: Redis) -> None:
                            async with random_key() as key:
                                ok = await redis_conn.set(key, "value")
                                assert ok, "Should have been able to set redis key"
                                assert await redis_conn.get(key) == "value", "Should have been able to get redis key"

                        await r.redis_try_run(runner, readonly=readonly)


async def test_redis_bad_host(subtests: t.Any, no_background_tasks: None) -> None:
    redis_url = "redis://10.0.0.1:6379/0"
    sentinel_hosts = '[["10.0.0.1", 26379]]'

    @r.redis_cached(key="test")
    async def cache_test(value: int) -> int:
        return value + 1

    i = 0
    for config in [{"APP_REDIS_URL": redis_url}, {"APP_REDIS_SENTINEL_HOSTS": sentinel_hosts}]:
        with fake_redis_config(config):
            s = r.RedisSettings()
            with subtests.test(f"redis({s})"), pytest.raises(MasterNotFoundError if s.is_sentinel else r.TimeoutError):
                async with r.redis() as redis_conn:
                    # Need some redis activity to trigger the connection attempt
                    await redis_conn.get("test")

            with subtests.test(f"redis_try_run({r._redis.settings})"):
                was_run = False

                async def runner(redis_conn: Redis) -> bool:
                    await redis_conn.get("test")
                    nonlocal was_run
                    was_run = True
                    return True

                assert await r.redis_try_run(runner) is None, "Should return None value"
                assert was_run is False, "Should not have run runner due to connection failure"

            with subtests.test(f"@redis_cached({r._redis.settings})"):
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1


class CacheTest(BaseModel):
    value: int


@pytest.mark.skipif("SENTINEL_HOSTS" not in os.environ or "REDIS_URL" not in os.environ, reason="Requires docker-compose redis env")
async def test_redis_cached(subtests: t.Any, no_background_tasks: None) -> None:
    for config in [
        {"APP_REDIS_URL": os.environ["REDIS_URL"]},
        {"APP_REDIS_SENTINEL_HOSTS": os.environ["SENTINEL_HOSTS"]},
    ]:
        with fake_redis_config(config), subtests.test(f"@redis_cached {config}"):
            cache_call_count = 0

            @r.redis_cached(key=f"cachetest:{uuid.uuid4()}")
            async def cache_test(value: int) -> int:
                nonlocal cache_call_count
                cache_call_count += 1
                return value + 1

            assert await cache_test(1) == 2, "Decorator should have worked"
            assert cache_call_count == 1
            assert await cache_test(1) == 2, "Should now have been cached"
            assert cache_call_count == 1

            assert await cache_test(2) == 3, "New value should recalculate"
            assert cache_call_count == 2

            await cache_test.delete_entry(1)
            assert await cache_test(1) == 2, "Should have been recalculated"
            assert cache_call_count == 3, "When entry was deleted should have recalculated"

            cache_call_count = 0

            @r.redis_cached(key=f"cachetest:{uuid.uuid4()}")
            async def cache_pydantic(value: int) -> CacheTest:
                nonlocal cache_call_count
                cache_call_count += 1
                return CacheTest(value=value + 1)

            assert await cache_pydantic(1) == CacheTest(value=2), "Decorator should have worked"
            assert cache_call_count == 1
            assert await cache_pydantic(1) == CacheTest(value=2), "Should now have been cached"
            assert cache_call_count == 1


# TODO: Lots of mocking for different connection error scenarios like sentinel available but redis not etc
