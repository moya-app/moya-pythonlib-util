import json
import typing as t
from pathlib import Path

import pytest

ValuesType: t.TypeAlias = list[t.Any] | dict[str, t.Any]


class AssertValuesMatchExpected(t.Protocol):
    def __call__(self, values: ValuesType, filename: Path, **kwargs: t.Any) -> None: ...


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--regenerate",
        action="store_true",
        help="Regenerate the .expected files",
    )


@pytest.fixture(scope="session")
def regenerate(pytestconfig: pytest.Config) -> bool:
    return t.cast(bool, pytestconfig.getoption("regenerate"))


@pytest.fixture
def assert_values_match_expected(regenerate: bool) -> AssertValuesMatchExpected:
    def _assert_values_match_expected(values: ValuesType, filename: Path, **kwargs: t.Any) -> None:
        if regenerate:
            with filename.open("w") as fh:
                json.dump(values, fh, indent=2, **kwargs)
        else:
            with filename.open() as fh:
                expected = json.load(fh)
            json_values = json.loads(json.dumps(values, **kwargs))
            assert json_values == expected

    return _assert_values_match_expected
