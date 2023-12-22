import zlib
from typing import Callable

from fastapi import Response
from fastapi.routing import APIRoute
from starlette.requests import Request


class GzipRequest(Request):
    """
    ASGI Middleware to decompress inbound gzip requests which is a custom
    protocol that the Moya app uses to talk with services.
    """

    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            if "gzip" in self.headers.getlist("Content-Encoding"):
                decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
                body = decompressor.decompress(decompressor.unconsumed_tail + body)
            self._body = body.decode("utf8")  # type:ignore  #TODO: Check if this can be removed
        return self._body


class GzipRoute(APIRoute):
    """
    FastAPI route that decompresses inbound gzip requests. Usage:

    router = APIRouter(prefix="/v1/requests", route_class=GzipRoute)
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = GzipRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler
