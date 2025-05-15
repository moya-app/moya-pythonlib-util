import typing as t

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regenerate",
        action="store_true",
        help="Regenerate the .expected files",
    )


@pytest.fixture(scope="session")
def regenerate(pytestconfig: pytest.Config) -> bool:
    return t.cast(bool, pytestconfig.getoption("regenerate"))
