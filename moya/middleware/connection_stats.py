import re

from opentelemetry import trace
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def extract_moya_details(user_agent: str) -> tuple[str, str] | None:
    ua_match = re.search(r"\bMoya(-ios)?[-/]([\d\.]+)", user_agent, re.IGNORECASE)
    if ua_match is None:
        return None
    platform = "ios" if ua_match.group(1) else "android"
    version = ua_match.group(2)
    return platform, version


def set_attribute(key: str, value: bytes | str | int) -> None:
    # print(key, value)
    trace.get_current_span().set_attribute(key, value)


class ConnectionStatsMiddleware:
    """
    A standard Moya ASGI middleware to log the following for each request via OTEL traces:
    - bytes.tx/rx: sizes for each request for size tracking (before any outbound
      gzip compression, and not including the header overhead)
    - moya.platform and moya.version from the user-agent header
    - error.message and error.input if the response status code is >= 400
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        initial_body_size = body_size = 0

        # Push an initial value based on the content-length header, but it
        # could be spoofed so if anything was actually sent/received then log
        # the better value.
        for k, v in scope["headers"]:
            if k == b"content-length":
                try:
                    initial_body_size = int(v.decode("utf-8"))
                except ValueError:
                    pass
            elif k == b"user-agent":
                moya_details = extract_moya_details(v.decode("utf-8"))
                if moya_details:
                    set_attribute("moya.platform", moya_details[0])
                    set_attribute("moya.version", moya_details[1])

        request_content_start = None

        async def wrapped_receive() -> Message:
            nonlocal body_size, request_content_start

            message = await receive()
            # assert message["type"] == "http.request"

            body_size += len(message.get("body", b""))
            if not request_content_start:
                # TODO: Should we try to decode the body according to the content-type? Otherwise may get
                # "Byte attribute could not be decoded" error
                request_content_start = message.get("body", b"")[0:1024]

            # print('rx', message)
            return message

        status = 0

        async def wrapped_send(message: Message) -> None:
            nonlocal status
            # print('tx', message)
            if message["type"] == "http.response.start":
                status = message["status"]
                if status >= 400:
                    if request_content_start:
                        set_attribute("error.input", request_content_start)
            if message["type"] == "http.response.body":
                set_attribute("bytes.tx", len(message.get("body", b"")))
                if status >= 400:
                    set_attribute("error.message", message.get("body", b"")[0:4096])

            # If we send the OTEL stat in receive handler it seems like it does
            # not correctly get sent into the FastAPI instrumentation
            set_attribute("bytes.rx", body_size or initial_body_size)
            await send(message)

        await self.app(scope, wrapped_receive, wrapped_send)
