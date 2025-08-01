from unittest.mock import patch

from moya.util.sentry import SentrySettings, init


@patch("sentry_sdk.init")
def test_sentry_init_with_dsn(mock_sentry_init):
    """Test that Sentry is initialized when a DSN is provided."""
    with patch("moya.util.sentry.sentry_settings", SentrySettings(sentry_dsn="https://test.com")):
        init()
        mock_sentry_init.assert_called_once()


@patch("sentry_sdk.init")
def test_sentry_init_without_dsn(mock_sentry_init):
    """Test that Sentry is not initialized when a DSN is not provided."""
    with patch("moya.util.sentry.sentry_settings", SentrySettings(sentry_dsn=None)):
        init()
        mock_sentry_init.assert_not_called()


@patch("sentry_sdk.init")
def test_sentry_before_send_ignores_exception(mock_sentry_init):
    """Test that the before_send function ignores specified exceptions."""
    with patch("moya.util.sentry.sentry_settings", SentrySettings(sentry_dsn="https://test.com")):
        init(ignore_exceptions=[ValueError])
        before_send = mock_sentry_init.call_args.kwargs["before_send"]
        event = {"key": "value"}
        hint = {"exc_info": (ValueError, ValueError("test"), None)}
        assert before_send(event, hint) is None


@patch("sentry_sdk.init")
def test_sentry_before_send_does_not_ignore_exception(mock_sentry_init):
    """Test that the before_send function does not ignore other exceptions."""
    with patch("moya.util.sentry.sentry_settings", SentrySettings(sentry_dsn="https://test.com")):
        init(ignore_exceptions=[TypeError])
        before_send = mock_sentry_init.call_args.kwargs["before_send"]
        event = {"key": "value"}
        hint = {"exc_info": (ValueError, ValueError("test"), None)}
        assert before_send(event, hint) == event


@patch("sentry_sdk.init")
def test_sentry_before_send_no_exc_info(mock_sentry_init):
    """Test that the before_send function handles cases with no exc_info."""
    with patch("moya.util.sentry.sentry_settings", SentrySettings(sentry_dsn="https://test.com")):
        init()
        before_send = mock_sentry_init.call_args.kwargs["before_send"]
        event = {"key": "value"}
        hint = {}
        assert before_send(event, hint) == event
