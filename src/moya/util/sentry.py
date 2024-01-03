import typing as t

import sentry_sdk

from moya.util.config import MoyaSettings


class SentrySettings(MoyaSettings):
    environment: t.Optional[str] = "dev"
    commit_tag: str = "dev"
    sentry_dsn: t.Optional[str] = None


sentry_settings = SentrySettings()


def init(ignore_exceptions: t.Sequence[t.Type[Exception]] = ()) -> None:
    """
    Initialize sentry; should be done as soon as possible in the program.

    :param ignore_exceptions: A list of exception types to ignore to surpress reporting them.
    """
    if not sentry_settings.sentry_dsn:
        return

    def sentry_before_send(event: t.Any, hint: t.Any) -> t.Any:
        if "exc_info" in hint:
            exc_type, exc_value, tb = hint["exc_info"]
            if any(isinstance(exc_value, ex) for ex in ignore_exceptions):
                return None

        return event

    sentry_sdk.init(
        dsn=sentry_settings.sentry_dsn,
        environment=sentry_settings.environment,
        release=sentry_settings.commit_tag,
        traces_sample_rate=0,
        before_send=sentry_before_send,
    )
