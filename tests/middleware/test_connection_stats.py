import typing as t
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from moya.middleware.connection_stats import ConnectionStatsMiddleware


@asynccontextmanager
async def patch_trace() -> t.AsyncGenerator[dict[str, t.Any], None]:
    called: dict[str, t.Any] = {}

    def record(key: str, value: t.Any) -> None:
        called[key] = value

    # This is what happens when opentelemtry span is logged but opentelemetry is not running
    with patch("opentelemetry.trace.span.INVALID_SPAN.set_attribute", side_effect=record):
        yield called


async def test_fastapi() -> None:
    app = FastAPI()
    app.add_middleware(ConnectionStatsMiddleware)

    class TestItem(BaseModel):
        name: str

    @app.get("/item")
    async def read_item() -> TestItem:
        return TestItem(name="Foo")

    @app.post("/item")
    async def create_item(test_item: TestItem) -> TestItem:
        return test_item

    async with patch_trace() as called, httpx.AsyncClient(app=app, base_url="http://test") as client:
        await client.get("/item")
        assert called == {"bytes.rx": 0, "bytes.tx": 14}

    async with patch_trace() as called, httpx.AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/item", json={"name": "Bar"})
        assert called == {"bytes.rx": 15, "bytes.tx": 14}
