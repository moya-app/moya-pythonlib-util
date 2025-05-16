import gzip
import json
import typing as t
import zlib

import brotli
import pytest
from fastapi import APIRouter, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from moya.middleware.gzip_route import GzipRoute


async def test_inbound_gzip(subtests: t.Any) -> None:
    app = FastAPI()
    client = AsyncClient(transport=ASGITransport(app), base_url="http://test")

    router = APIRouter(prefix="", route_class=GzipRoute)

    @router.post("/test")
    async def body_test(request: Request) -> dict:
        return {"body": await request.body()}

    class TestReq(BaseModel):
        blah: str
        foo: int

    @router.post("/test_json")
    async def json_test(detail: TestReq) -> dict:
        return detail.model_dump()

    app.include_router(router)

    with subtests.test("Test that the basics work"):
        raw_data = b"Hello World"
        compressed = gzip.compress(raw_data)
        response = await client.post("/test", headers={"Content-Encoding": "gzip"}, content=compressed)
        assert response.status_code == 200
        assert response.json() == {"body": "Hello World"}

    with subtests.test("Test that the non-compressed things also work"):
        for headers in (None, {"Content-Encoding": ""}, {"Content-Encoding": "invalid"}):
            response = await client.post("/test", headers=headers, content=raw_data)
            assert response.status_code == 200
            assert response.json() == {"body": "Hello World"}

    with subtests.test("Test that pydantic stuff works"):
        test_json = {"blah": "blah", "foo": 1}
        compressed = gzip.compress(json.dumps(test_json).encode("utf8"))
        response = await client.post("/test_json", headers={"Content-Encoding": "gzip"}, content=compressed)
        assert response.status_code == 200
        assert response.json() == test_json

    # TODO: This hopefully gets translated into a 500 error or similar when exposed via http?
    with subtests.test("Test that invalid gzipd data is handled correctly"):
        with pytest.raises(zlib.error):
            response = await client.post("/test", headers={"Content-Encoding": "gzip"}, content=b"foo bar")


async def test_inbound_brotli(subtests: t.Any) -> None:
    app = FastAPI()
    client = AsyncClient(transport=ASGITransport(app), base_url="http://test")

    router = APIRouter(prefix="", route_class=GzipRoute)

    @router.post("/test")
    async def body_test(request: Request) -> dict:
        return {"body": await request.body()}

    class TestReq(BaseModel):
        blah: str
        foo: int

    @router.post("/test_json")
    async def json_test(detail: TestReq) -> dict:
        return detail.model_dump()

    app.include_router(router)

    with subtests.test("Test that the basics work"):
        raw_data = b"Hello World"
        compressed = brotli.compress(raw_data)
        response = await client.post("/test", headers={"Content-Encoding": "br"}, content=compressed)
        assert response.status_code == 200
        assert response.json() == {"body": "Hello World"}

    with subtests.test("Test that pydantic stuff works"):
        test_json = {"blah": "blah", "foo": 1}
        compressed = brotli.compress(json.dumps(test_json).encode("utf8"))
        response = await client.post("/test_json", headers={"Content-Encoding": "br"}, content=compressed)
        assert response.status_code == 200
        assert response.json() == test_json

    # TODO: This hopefully gets translated into a 500 error or similar when exposed via http?
    with subtests.test("Test that invalid brotli data is handled correctly"):
        with pytest.raises(brotli.error):
            response = await client.post("/test", headers={"Content-Encoding": "br"}, content=b"foo bar")
