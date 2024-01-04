from opentelemetry import trace
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ConnectionStatsMiddleware:
    """
    A standard Moya ASGI middleware to log body tx/rx sizes for each request via OTEL
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        def set_attribute(key: str, value: int) -> None:
            # print(key, value)
            trace.get_current_span().set_attribute(key, value)

        # Push an initial value based on the content-length header, but it
        # could be spoofed so if anything was actually sent/received then log
        # the better value.
        for k, v in scope["headers"]:
            if k == b"content-length":
                try:
                    set_attribute("bytes.rx", int(v.decode("utf-8")))
                except ValueError:
                    pass

        body_size = 0

        async def wrapped_receive() -> Message:
            nonlocal body_size

            message = await receive()
            # assert message["type"] == "http.request"

            body_size += len(message.get("body", b""))
            # We could look at more_body here but it's probably best just to log everything
            set_attribute("bytes.rx", body_size)

            # print('rx', message)
            return message

        async def wrapped_send(message: Message) -> None:
            # print('tx', message)
            if message["type"] == "http.response.body":
                set_attribute("bytes.tx", len(message.get("body", b"")))

            await send(message)

        await self.app(scope, wrapped_receive, wrapped_send)
