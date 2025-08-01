import os
from unittest import mock

from moya.util.beartype import maybe_setup_beartype


def test_maybe_setup_beartype_with_pytest_version() -> None:
    """
    Test that beartype is set up when PYTEST_VERSION is in the environment.
    """
    with mock.patch.dict(os.environ, {"PYTEST_VERSION": "1"}):
        with mock.patch("beartype.claw.beartype_packages") as mock_beartype_packages:
            maybe_setup_beartype()
            mock_beartype_packages.assert_called_once_with(["app", "main"])


def test_maybe_setup_beartype_with_use_beartype_setting() -> None:
    """
    Test that beartype is set up when the use_beartype setting is True.
    """
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("moya.util.beartype.BearSettings") as mock_bear_settings:
            mock_bear_settings.return_value.use_beartype = True
            with mock.patch("beartype.claw.beartype_packages") as mock_beartype_packages:
                maybe_setup_beartype()
                mock_beartype_packages.assert_called_once_with(["app", "main"])


def test_maybe_setup_beartype_disabled() -> None:
    """
    Test that beartype is not set up when it's not enabled.
    """
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("moya.util.beartype.BearSettings") as mock_bear_settings:
            mock_bear_settings.return_value.use_beartype = False
            with mock.patch("beartype.claw.beartype_packages") as mock_beartype_packages:
                maybe_setup_beartype()
                mock_beartype_packages.assert_not_called()


def test_maybe_setup_beartype_with_custom_packages() -> None:
    """
    Test that beartype is set up with custom packages.
    """
    with mock.patch.dict(os.environ, {"PYTEST_VERSION": "1"}):
        with mock.patch("beartype.claw.beartype_packages") as mock_beartype_packages:
            maybe_setup_beartype(packages=["foo", "bar"])
            mock_beartype_packages.assert_called_once_with(["foo", "bar"])
