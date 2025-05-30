import logging
from typing import Literal

from moya.util.config import MoyaSettings

# Basic setup/config for python logging


class LoggingSettings(MoyaSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"


log_settings = LoggingSettings()


def setup_logging() -> None:
    """
    Initial logging setup.

    Sets default format and level to that specified by `APP_LOG_LEVEL`, or `WARNING` if not set.
    """
    default_handler = logging.StreamHandler()
    default_handler.setLevel(logging.getLevelName(log_settings.log_level))
    default_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s"))

    # Ensure that the root logger gets all messages, as we may want another log handler (eg opentelemetry) to be able
    # to fetch messages of lower level than we output to the console.
    logging.basicConfig(
        level=logging.NOTSET,
        handlers=[default_handler],
    )
