import typing as t
from contextlib import contextmanager
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from moya.middleware.connection_stats import (
    ConnectionStatsMiddleware,
    extract_moya_details,
)


@contextmanager
def patch_trace() -> t.Iterator[t.Dict[str, t.Any]]:
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

    @app.post("/error")
    async def raise_err(test_item: TestItem) -> None:
        raise HTTPException(status_code=400, detail="Bad Request")

    @app.get("/file")
    async def read_file() -> FileResponse:
        return FileResponse("tests/fixtures/1.png")

    client = httpx.AsyncClient(app=app, base_url="http://test")
    with patch_trace() as called:
        await client.get("/item")
        assert called == {"bytes.rx": 0, "bytes.tx": 14}

    with patch_trace() as called:
        await client.get("/file")
        assert called == {"bytes.rx": 0, "bytes.tx": 26529}

    with patch_trace() as called:
        await client.post("/item", json={"name": "Bar"})
        assert called == {"bytes.rx": 15, "bytes.tx": 14}

    with patch_trace() as called:
        await client.post("/error", json={"name": "Bar"})
        assert called == {
            "bytes.rx": 15,
            "bytes.tx": 24,
            "error.input": b'{"name": "Bar"}',
            "error.message": b'{"detail":"Bad Request"}',
        }

    client = httpx.AsyncClient(app=app, base_url="http://test", headers={"user-agent": "blah foo Moya/1.0.0 fred"})
    with patch_trace() as called:
        await client.get("/item")
        assert called == {"bytes.rx": 0, "bytes.tx": 14, "moya.platform": "android", "moya.version": "1.0.0"}


@pytest.mark.parametrize(
    "user_agent, expected",
    [
        ("blah foo Moya/1.0.0 fred", ("android", "1.0.0")),
        ("blah foo Moya/1.0.0", ("android", "1.0.0")),
        ("blah foo Moya/1.0.0 ", ("android", "1.0.0")),
        ("blah foo Moya/1.0.0 (fred)", ("android", "1.0.0")),
        ("test foo", None),
        ("blah foo Moya-ios/7.2.3.5 (fred)", ("ios", "7.2.3.5")),
        ("blah foo Moya-IOS/7.2.3.5 (fred)", ("ios", "7.2.3.5")),
    ],
)
def test_extract_moya_details(user_agent, expected):
    assert extract_moya_details(user_agent) == expected
