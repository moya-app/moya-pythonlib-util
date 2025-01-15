import os
from unittest.mock import patch

import httpx
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel

from moya.util.fastapi import setup_fastapi


async def test_basics() -> None:
    trace.set_tracer_provider(TracerProvider())
    spans = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(spans))  # type: ignore

    app = setup_fastapi()

    class TestItem(BaseModel):
        name: str

    @app.get("/item")
    async def read_item() -> TestItem:
        assert trace.get_current_span().is_recording()
        return TestItem(name="Foo")

    @app.post("/item")
    async def create_item(test_item: TestItem) -> TestItem:
        assert trace.get_current_span().is_recording()
        return test_item

    client = httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test")
    await client.get("/item")
    attrs = spans.get_finished_spans()[-1].attributes
    assert attrs
    assert attrs["http.server_name"] == "test", "Should have come from fastapi otel instrumentation"
    assert attrs["bytes.rx"] == 0
    assert attrs["bytes.tx"] == 14
    spans.clear()
    await client.post("/item", json={"name": "Bar"})
    attrs = spans.get_finished_spans()[-1].attributes
    assert attrs
    assert attrs["http.server_name"] == "test", "Should have come from fastapi otel instrumentation"
    assert attrs["bytes.rx"] == 14
    assert attrs["bytes.tx"] == 14
    spans.clear()

    res = await client.get("/version")
    assert res.status_code == 200
    assert res.json() == {"version": "dev"}

    res = await client.get("/openapi.json")
    assert res.status_code == 404


async def test_docs() -> None:
    with patch.dict(os.environ, {"APP_COMMIT_TAG": "1.0.0", "APP_HIDE_DOCS": "false"}):
        app = setup_fastapi()
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test")
        res = await client.get("/openapi.json")
        assert res.status_code == 200
        assert res.json()["info"]["version"] == "1.0.0"

        res = await client.get("/version")
        assert res.status_code == 200
        assert res.json() == {"version": "1.0.0"}
