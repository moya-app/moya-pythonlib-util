import re

from starlette.types import ASGIApp, Receive, Scope, Send

repeated_quotes = re.compile(r"//+")
bytes_repeated_quotes = re.compile(rb"//+")


class MultipleSlashesMiddleware:
    """
    This HTTP middleware removes repeated slashes from the requested path to make
    it work correctly with FastAPI routing.

    Typically used for handling bad clients better.

    There are rumours that nginx should be surpressing this by default via the
    `merge_slashes` option, but this doesn't seem to work in all cases -
    perhaps due to the nature of proxying.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if "root_path" in scope:
            scope["root_path"] = repeated_quotes.sub("/", scope["root_path"])
        if "path" in scope:
            scope["path"] = repeated_quotes.sub("/", scope["path"])
        if "raw_path" in scope:
            scope["raw_path"] = bytes_repeated_quotes.sub(b"/", scope["raw_path"])
        await self.app(scope, receive, send)
