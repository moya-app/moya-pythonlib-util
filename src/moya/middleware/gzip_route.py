# TODO: We should rename this to inbound_compression or similar because it
# handles more than just gzip now.
import zlib
from typing import Callable

import brotli
from fastapi import Response
from fastapi.routing import APIRoute
from starlette.requests import Request


class GzipRequest(Request):
    """
    ASGI Middleware to decompress inbound gzip or brotli requests which is a
    custom protocol that the Moya app uses to talk with services.
    """

    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            content_encoding = self.headers.getlist("Content-Encoding")

            # TODO: Streaming decompression
            if "gzip" in content_encoding:
                decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
                body = decompressor.decompress(decompressor.unconsumed_tail + body)
            elif "br" in content_encoding:
                body = brotli.decompress(body)

            self._body = body.decode("utf8")  # type:ignore  #TODO: Check if this can be removed
        return self._body


class GzipRoute(APIRoute):
    """
    FastAPI route that decompresses inbound gzip or brotli requests. Usage:

    router = APIRouter(prefix="/v1/requests", route_class=GzipRoute)

    Note that this does not propagate to sub-routers so has to be specified on
    the router which your endpoints requiring this functionality are defined
    on.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = GzipRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler
