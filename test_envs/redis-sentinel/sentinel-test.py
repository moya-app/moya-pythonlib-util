import asyncio
import moya.service.redis as r
import os

# docker inspect $(docker-compose ps -q redis-sentinel)
sentinels = [('192.168.144.2', 26379)]

os.environ['APP_REDIS_PASSWORD'] = 'testpassword'
os.environ['APP_REDIS_SENTINEL_HOSTS'] = f'[["{sentinels[0][0]}", {sentinels[0][1]}]]'

async def main():
    async def runner(redis_conn) -> None:

        ok = await redis_conn.set("key", "value")
        print(ok)
        print(await redis_conn.get("key"))

    await r.redis_try_run(runner, readonly=False)
    await r.redis_try_run(runner, readonly=True)

asyncio.run(main())
