import os

from moya.util.config import MoyaSettings


class BearSettings(MoyaSettings):
    use_beartype: bool = False


def maybe_setup_beartype(packages: list[str] = ["app", "main"]) -> None:
    """
    Optionally use beartype to pick up typing violations during testing and on
    systest (assuming APP_USE_BEARTYPE is set to True)
    """
    if os.environ.get("PYTEST_VERSION") is not None or BearSettings().use_beartype:
        from beartype.claw import beartype_packages

        beartype_packages(packages)
