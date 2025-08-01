import logging
from unittest.mock import patch

from moya.util.logging import LoggingSettings, setup_logging


def test_setup_logging_default_level() -> None:
    """Test that the default log level is WARNING."""
    with patch("logging.StreamHandler") as mock_handler:
        with patch("logging.basicConfig") as mock_basic_config:
            setup_logging()
            mock_handler.return_value.setLevel.assert_called_with(logging.WARNING)
            mock_basic_config.assert_called_once()


def test_setup_logging_custom_level() -> None:
    """Test that a custom log level is used."""
    with patch("moya.util.logging.log_settings", LoggingSettings(log_level="DEBUG")):
        with patch("logging.StreamHandler") as mock_handler:
            with patch("logging.basicConfig") as mock_basic_config:
                setup_logging()
                mock_handler.return_value.setLevel.assert_called_with(logging.DEBUG)
                mock_basic_config.assert_called_once()
