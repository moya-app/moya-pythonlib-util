import typing as t

from fastapi import Depends, HTTPException, status

from moya.util.config import MoyaSettings

from .ratelimit import LimitBase, RateLimit, RateLimitExceeded, RedisLimiter

"""
Easy library for using FastAPI with Ratelimiters
"""


class RateLimitSettings(MoyaSettings):
    """
    Extract environment variable APP_RATELIMITS and use it to configure
    ratelimiters.

    A default entry of "*" can be used to set a default rate limit for all
    endpoints which do not have a specific limiter config set up.
    """

    ratelimits: dict[str, RateLimit]

    def get(self, endpoint: str, default: RateLimit = None) -> RateLimit:
        """
        Get the ratelimiter for the given endpoint name, if exists
        """
        if endpoint in self.ratelimits:
            return self.ratelimits[endpoint]
        elif "*" in self.ratelimits:
            return self.ratelimits["*"]
        elif default is not None:
            return default
        else:
            raise KeyError(
                f"No ratelimits configured for limiter '{endpoint}'."
                " Ensure that APP_RATELIMITS contains at least an entry for '*',"
                " or that default_limits is set in the config"
            )


async def _null_fn() -> None:
    """
    Bypass all rate-limits when no rate limits have been configured for this item
    """
    pass


class _RateLimiter:
    def __init__(
        self,
        limiter: LimitBase,
        user_id_decorator: t.TypeAlias = t.Annotated[None, Depends(_null_fn)],
    ) -> None:
        """
        Create a new rate limiter with the given rates. This class is intended
        to wrap details about different limiters and allow for easy integration
        into FastAPI.

        :param limiter: The limiter to use. This should be an instance of LimitBase.
        :param user_id_decorator: The decorator to use to get the user_id from
            the request. This should be an t.Annotated function (probably using
            Depends()) returning a string or None. If the function returns None
            then no ratelimits will be applied to this user (which is
            potentially useful for admin users to bypass ratelimits).

        """
        self.limiter = limiter
        self.user_id_decorator = user_id_decorator

    async def reset_user(self, user_id: str) -> None:
        """
        Clear all ratelimits for this limiter for the specified user
        """
        await self.limiter.flush_user(user_id)

    async def reset_all(self) -> None:
        """
        Reset all ratelimits for all users using this limiter
        """
        await self.limiter.reset()

    @property
    def dependency(self) -> t.Any:  # Any is the type of Depends() anyway
        if self.limiter.rates.is_empty:
            return Depends(_null_fn)

        async def fn(user_id: self.user_id_decorator) -> None:  # type: ignore
            # TODO: Could use dynamic rate limits here on a per-path basis by
            # using something like the following as the key prefix:
            # [request.method, request['route'].path]

            if user_id is None:
                return

            try:
                await self.limiter.try_ratelimit(user_id)
            except RateLimitExceeded:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

        return Depends(fn)


def RateLimiter(
    name: str,
    user_id_decorator: t.Any,  # Must be a Depends() function which returns a str or None
    default_limits: t.Optional[RateLimit] = None,
    limiter_class: t.Type[LimitBase] = RedisLimiter,
) -> _RateLimiter:
    """
    Easy fastapi dependency to create a rate limiter from environment vars.

    :param name: The name of the limiter to use. This should be the same as the
        name of the endpoint you want to limit and will have limiter config
        pulled from that item in the APP_RATELIMITS config variable.
    :param user_id_decorator: The decorator to use to get the user_id from the
        request. This must be specified and should be a Depends() function
        returning a str or None for no ratelimit for this particular user.
    :param default_limits: The default limits to use if no limits are specified
        in the environment, otherwise if no default limits are specified in the
        environment a startup-time error will be raised.
    :param limiter_class: The class to use for the limiter. This should be a
        subclass of LimitBase. This defaults to RedisLimiter, but could be set
        to MemLimiter for testing.

    Usage:

    async def ensure_verified(
        credentials: t.Annotated[HTTPBasicCredentials, Depends(HTTPBasic())]
    ):
        return credentials.username

    limiter = RateLimiter("foo", Depends(ensure_verified))
    @app.get("/foo", dependencies=[limiter.dependency])
    async def foo():
        await limiter.flush_user("foo@bar.com")

    and set APP_RATELIMITS='{"foo": {"per_minute": 10, "per_day": 20}}' in your environment
    """

    settings = RateLimitSettings()
    return _RateLimiter(
        limiter_class(settings.get(name, default_limits), name), user_id_decorator=t.Annotated[str, user_id_decorator]
    )


def RateLimiterDep(
    name: str,
    user_id_decorator: t.TypeAlias,
    default_limits: t.Optional[RateLimit] = None,
    limiter_class: t.Type[LimitBase] = RedisLimiter,
) -> t.Any:
    """
    As RateLimeter above but returns the dependency directly. This is useful to
    save typing when you don't need to flush or reset the ratelimiter.

    Usage with setup above:

    @app.get("/foo", dependencies=[RateLimiterDep("foo", Depends(ensure_verified))])
    async def foo():
        pass
    """
    return RateLimiter(
        name, user_id_decorator=user_id_decorator, default_limits=default_limits, limiter_class=limiter_class
    ).dependency
