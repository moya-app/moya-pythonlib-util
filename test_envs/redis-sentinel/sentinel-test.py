# Per the README export the env vars and run this tester script like:
#   PYTHONPATH=../.. python sentinel-test.py
# Mess around with turning on/off sentinels and redis servers to see what happens
import asyncio
import os

import moya.service.redis as r

os.environ["APP_REDIS_PASSWORD"] = "testpassword"


async def main():
    async def runner(redis_conn) -> None:
        # ok = await redis_conn.set("key", "value")
        # print(ok)
        print(await redis_conn.get("key"))

    # TODO: Spy on how many connections are being opened
    async def run() -> None:
        while True:
            await r.redis_try_run(runner, readonly=True)
            await asyncio.sleep(0.1)

    await asyncio.gather(*[run() for _ in range(10)])


asyncio.run(main())
