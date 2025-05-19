import os
import sys
import typing as t
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI, Response
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from moya.middleware.connection_stats import ConnectionStatsMiddleware
from moya.util.config import MoyaSettings


class FastAPISettings(MoyaSettings):
    commit_tag: str = "dev"
    hide_docs: bool = True


class VersionResponse(BaseModel):
    version: str = Field(examples=["1.2.9"])


def generate_otel_lifespan(lifespan: t.Optional[t.Callable[[t.Any], t.AsyncContextManager[None]]] = None) -> t.Callable[[t.Any], t.AsyncContextManager[None]]:
    lifespan = lifespan or nullcontext

    @asynccontextmanager
    async def otel_lifespan(app: FastAPI) -> t.AsyncIterator[None]:
        if "PYTHONPATH" not in os.environ:
            os.environ["PYTHONPATH"] = ":".join(sys.path)

        # This import will trigger auto-instrumentation for this process, which is needed for anything with multiple
        # worker processes (e.g. gunicorn, uvicorn)
        import opentelemetry.instrumentation.auto_instrumentation.sitecustomize  # noqa

        # Call the existing lifespan context manager
        async with lifespan(app):
            yield

    return otel_lifespan


def setup_fastapi(openapi_tags: list[dict[str, str]] = [], **kwargs: t.Any) -> FastAPI:
    """
    Return a preconfigured FastAPI app with standard endpoints and OTEL
    tracking.
    """
    settings = FastAPISettings()

    kwargs["version"] = settings.commit_tag
    kwargs["openapi_url"] = None if settings.hide_docs else "/openapi.json"

    # Override lifespan to add OTEL post-fork for gunicorn, uvicorn, etc.
    kwargs["lifespan"] = generate_otel_lifespan(kwargs.get("lifespan"))

    # More performant than standard JSON response
    if "default_response_class" not in kwargs:
        kwargs["default_response_class"] = ORJSONResponse

    # According to the fastapi docs, this should auto-populate but per
    # https://github.com/fastapi/fastapi/discussions/12226 it does not.
    if "servers" not in kwargs:
        kwargs["servers"] = [{"url": "/"}]

    if not any(d["name"] == "Meta" for d in openapi_tags):
        openapi_tags.append({"name": "Meta", "description": "endpoints for health checks and other meta operations"})

    fastapi = FastAPI(openapi_tags=openapi_tags, **kwargs)
    fastapi.add_middleware(ConnectionStatsMiddleware)
    FastAPIInstrumentor.instrument_app(fastapi)

    # Add in standard endpoints so the app doesn't have to
    @fastapi.get("/version", tags=["Meta"])
    async def version(response: Response) -> VersionResponse:
        """
        Return the version of this service in JSON format
        """
        response.headers["Cache-Control"] = "no-cache"
        return VersionResponse(version=settings.commit_tag)

    return fastapi
