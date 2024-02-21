import typing as t
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from moya.middleware.http_cache import IfModifiedSinceMiddleware, set_cache_headers


@pytest.mark.parametrize(
    "last_modified",
    [
        # Try the 3 variations of last_modified being allowed
        "Fri, 16 Feb 2024 10:37:38 GMT",
        1708079858,
        1708079858.2,
        datetime(2024, 2, 16, 10, 37, 38, tzinfo=timezone.utc),
    ],
)
async def test_cache_headers(subtests: t.Any, last_modified: str | int | datetime) -> None:
    app = FastAPI()
    client = httpx.AsyncClient(app=app, base_url="http://test")

    class TestItem(BaseModel):
        name: str

    @app.get("/item")
    async def read_item(request: Request, response: Response) -> TestItem:
        set_cache_headers(request, response, last_modified=last_modified, max_age=3600)
        return TestItem(name="Foo")

    for headers in (
        t.cast(dict[str, str], {}),
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:37 GMT"},
        {"If-Modified-Since": "Invalid data"},
    ):
        with subtests.test(f"Headers: {headers}"):
            response = await client.get("/item", headers=headers)
            assert response.headers["cache-control"] == "max-age=3600, stale-if-error=3600, public"
            assert response.headers["last-modified"] == "Fri, 16 Feb 2024 10:37:38 GMT"
            assert response.status_code == 200
            assert response.json() == {"name": "Foo"}

    for headers in (
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:38 GMT"},
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:39 GMT"},
    ):
        with subtests.test(f"Headers: {headers}"):
            response = await client.get("/item", headers=headers)
            assert response.headers["cache-control"] == "max-age=3600, stale-if-error=3600, public"
            assert "last-modified" not in response.headers
            assert response.status_code == 304
            assert response.text == ""

    @app.post("/item")
    async def create_item(test_item: TestItem, response: Response, request: Request) -> TestItem:
        set_cache_headers(request, response, last_modified="Fri, 16 Feb 2024 10:37:38 GMT", max_age=3600)
        return test_item

    for headers in (
        t.cast(dict[str, str], {}),
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:37 GMT"},
        {"If-Modified-Since": "Invalid data"},
    ):
        with subtests.test(f"Headers: {headers}"):
            response = await client.post("/item", json={"name": "Foo"}, headers=headers)
            assert response.headers["cache-control"] == "max-age=3600, stale-if-error=3600, public"
            assert response.headers["last-modified"] == "Fri, 16 Feb 2024 10:37:38 GMT"
            assert response.status_code == 200
            assert response.json() == {"name": "Foo"}


async def test_if_modified_middleware() -> None:
    app = FastAPI()
    client = httpx.AsyncClient(app=app, base_url="http://test")
    app.add_middleware(IfModifiedSinceMiddleware)

    class TestItem(BaseModel):
        name: str

    @app.get("/item")
    async def read_item(request: Request, response: Response) -> TestItem:
        set_cache_headers(request, response, last_modified="Fri, 16 Feb 2024 10:37:38 GMT", max_age=3600)
        return TestItem(name="Foo")

    for headers in (
        t.cast(dict[str, str], {}),
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:37 GMT"},
    ):
        response = await client.get("/item", headers=headers)
        assert response.headers["cache-control"] == "max-age=3600, stale-if-error=3600, public"
        assert response.headers["last-modified"] == "Fri, 16 Feb 2024 10:37:38 GMT"
        assert response.status_code == 200
        assert response.json() == {"name": "Foo"}

    # But when the If-Modified-Since header is later than the last-modified
    # header, it should return 304 and no content
    for headers in (
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:38 GMT"},
        {"If-Modified-Since": "Fri, 16 Feb 2024 10:37:39 GMT"},
    ):
        response = await client.get("/item", headers=headers)
        assert response.status_code == 304
        assert response.text == ""
