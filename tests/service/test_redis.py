import os
import typing as t
import uuid
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import ANY, patch

import pytest

import moya.service.redis as r


@asynccontextmanager
async def random_key():
    yield f"test:{uuid.uuid4()}"


def reset_redis_caches():
    # Clear @cache'd values in our the redis library. Must be done when
    # environment variables change so that new config is picked up.
    r.pool.cache_clear()
    r.sentinel.cache_clear()
    r.redis_settings.cache_clear()


@contextmanager
def fake_redis_config(env: dict) -> t.Generator[None, None, None]:
    default_test_env = {
        "APP_REDIS_TIMEOUT": "0.1",
        "APP_REDIS_CONNECT_RETRIES": "1",
        "APP_REDIS_PASSWORD": "testpassword",
    }
    with patch.dict(os.environ, {**default_test_env, **env}):
        reset_redis_caches()
        yield


def test_settings():
    with fake_redis_config({"APP_REDIS_URL": "redis://localhost:6379/0"}):
        s = r.RedisSettings()
        assert s, "Should work with standard config"
        assert s.is_sentinel is False, "Should not be sentinel config"
        assert r._standard_connection_kwargs(s) == {
            "encoding": "utf-8",
            "decode_responses": True,
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

    with fake_redis_config({}), pytest.raises(
        ValueError, match="Must specify APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS"
    ):
        r.RedisSettings()

    with fake_redis_config(
        {
            "APP_REDIS_URL": "redis://localhost:6379/0",
            "APP_REDIS_SENTINEL_HOSTS": '[["1.2.3.4", 1234]]',
        },
    ), pytest.raises(ValueError, match="Must only specify one of APP_REDIS_URL or APP_REDIS_SENTINEL_HOSTS"):
        r.RedisSettings()


@pytest.mark.skip("Only on live testing")
async def test_redis(subtests):
    # TODO: Only if docker-compose env is up for local testing
    # docker inspect $(docker-compose ps -q redis-sentinel)
    redis_url = "redis://192.168.144.3:6379/0"
    sentinel_hosts = '[["192.168.144.2", 26379]]'

    @r.redis_cached(key="test")
    async def cache_test(value: int) -> int:
        return value + 1

    i = 0
    for config in [{"APP_REDIS_URL": redis_url}, {"APP_REDIS_SENTINEL_HOSTS": sentinel_hosts}]:
        with fake_redis_config(config):
            for readonly in (True, False):
                with subtests.test(f"redis() {config} readonly={readonly}"):
                    async with r.redis(readonly) as redis_conn, random_key() as key:
                        ok = await redis_conn.set(key, "value")
                        assert ok, "Should have been able to set redis key"
                        assert await redis_conn.get(key) == "value", "Should have been able to get redis key"

                with subtests.test(f"redis_try_run() {config} readonly={readonly}"):

                    async def runner(redis_conn) -> None:
                        async with random_key() as key:
                            ok = await redis_conn.set(key, "value")
                            assert ok, "Should have been able to set redis key"
                            assert await redis_conn.get(key) == "value", "Should have been able to get redis key"

                    await r.redis_try_run(runner, readonly=readonly)

            with subtests.test(f"@redis_cached {config}"):
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1


async def test_redis_bad_host(subtests):
    redis_url = "redis://10.0.0.1:6379/0"
    sentinel_hosts = '[["10.0.0.1", 26379]]'

    @r.redis_cached(key="test")
    async def cache_test(value: int) -> int:
        return value + 1

    i = 0
    for config in [{"APP_REDIS_URL": redis_url}, {"APP_REDIS_SENTINEL_HOSTS": sentinel_hosts}]:
        with fake_redis_config(config):
            s = r.redis_settings()
            with subtests.test(f"redis({s})"), pytest.raises(r.ConnectionError if s.is_sentinel else r.TimeoutError):
                async with r.redis() as redis_conn:
                    # Need some redis activity to trigger the connection attempt
                    await redis_conn.get("test")

            with subtests.test(f"redis_try_run({r.redis_settings()})"):
                was_run = False

                async def runner(redis_conn) -> bool:
                    await redis_conn.get("test")
                    nonlocal was_run
                    was_run = True
                    return True

                assert await r.redis_try_run(runner) is None, "Should return None value"
                assert was_run is False, "Should not have run runner due to connection failure"

            with subtests.test(f"@redis_cached({r.redis_settings()})"):
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1
                assert await cache_test(i) == i + 1, "Decorator should have worked"
                i += 1


# TODO: Lots of mocking for different connection error scenarios like sentinel available but redis not etc
