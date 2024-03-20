import typing as t

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from moya.middleware.connection_stats import ConnectionStatsMiddleware
from moya.util.config import MoyaSettings


class FastAPISettings(MoyaSettings):
    commit_tag: str = "dev"
    hide_docs: bool = True


def setup_fastapi(**kwargs: t.Any) -> FastAPI:
    """
    Return a preconfigured FastAPI app with standard endpoints and OTEL
    tracking.
    """
    settings = FastAPISettings()

    kwargs["version"] = settings.commit_tag
    kwargs["openapi_url"] = None if settings.hide_docs else "/openapi.json"

    fastapi = FastAPI(**kwargs)
    fastapi.add_middleware(ConnectionStatsMiddleware)
    FastAPIInstrumentor.instrument_app(fastapi)

    # Add in standard endpoints so the app doesn't have to
    @fastapi.get("/version")
    async def version() -> JSONResponse:
        return JSONResponse({"version": settings.commit_tag}, headers={"Cache-Control": "no-cache"})

    return fastapi
