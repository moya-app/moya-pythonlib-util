import typing as t
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import NotModifiedResponse


def should_return_304(request: Request, response: Response) -> bool:
    if_modified_since = parsedate(request.headers.get("If-Modified-Since"))
    last_modified = parsedate(response.headers.get("last-modified"))

    if request.method in ("GET", "HEAD") and if_modified_since and last_modified and last_modified <= if_modified_since:
        return True

    return False


class IfModifiedSinceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: t.Callable[[Request], t.Awaitable[Response]]) -> Response:
        """
        If the response has a last-modified header which is older than the
        if-modified-since header, return a 304 without content to optimize
        bandwidth and rely on the client's cache.

        This middleware is only needed if the response has a last-modified
        header and skip_if_not_modified was not set below.
        """
        response = await call_next(request)

        if should_return_304(request, response):
            return NotModifiedResponse(response.headers)

        return response


def _parse_time_input(input: str | int | float | datetime) -> str:
    if isinstance(input, (int, float)):
        input = datetime.fromtimestamp(input, timezone.utc)
    if isinstance(input, datetime):
        if input.tzinfo != timezone.utc:
            input = input.astimezone(timezone.utc)
        input = format_datetime(input, usegmt=True)
    return input


def set_cache_headers(
    request: Request,
    response: Response,
    last_modified: str | int | float | datetime | None = None,
    expires: str | int | float | datetime | None = None,
    expires_in: int | None = None,
    max_age: int | None = None,
    stale_if_error: int = 60 * 60,
    public: bool = True,
    skip_if_not_modified: bool = True,
) -> None:
    """
    Set cache headers on the response

    :param response: The response object to set headers on
    :param last_modified: The last modified date of the content. If str is
        passed, it will be used as is. If int/float (unix epoch) or datetime is
        passed, it will be converted to a http timestamp.
    :param expires: Expires header, parsed the same as last_modified
    :param expires_in: Set expires parameter to now + this many seconds
    :param max_age: The maximum time the content should be cached for as an integer. Defaults to expires_in
        if that is set.
    :param stale_if_error: The time the content can be used if there is a server error. Defaults to 1 hour
    :param public: If the content can be cached by public caches. Defaults to True
    :param skip_if_not_modified: If the further processing should be skipped
        via an HTTPException response if the If-Modified-Since header is present
        and the content has not been modified. Defaults to True
    """
    # Handle the cache-control header
    cache_control = []
    if max_age or expires_in:
        cache_control.append(f"max-age={max_age or expires_in}")
    if stale_if_error:
        cache_control.append(f"stale-if-error={stale_if_error}")
    if public:
        cache_control.append("public")
    response.headers["Cache-Control"] = ", ".join(cache_control)

    if expires_in and expires:
        raise ValueError("Cannot set both expires and expires_in")

    if expires_in:
        expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if expires:
        # TODO: Assert > now?
        expires = _parse_time_input(expires)
        response.headers["expires"] = expires

    if last_modified:
        last_modified = _parse_time_input(last_modified)
        response.headers["last-modified"] = last_modified

        # See if we should just return a 304 no updated data response based on the last-mod time
        if skip_if_not_modified and should_return_304(request, response):
            # Same as a NotModifiedResponse but bypassing further processing
            raise HTTPException(
                status_code=304,
                headers={name: value for name, value in response.headers.items() if name in NotModifiedResponse.NOT_MODIFIED_HEADERS},
            )
