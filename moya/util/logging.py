import logging
from typing import Literal

from moya.util.config import MoyaSettings

# Basic setup/config for python logging


class LoggingSettings(MoyaSettings):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING"


log_settings = LoggingSettings()


def setup_logging() -> None:
    """
    Initial logging setup
    """
    logging.basicConfig(
        level=logging.getLevelName(log_settings.log_level),
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    )
