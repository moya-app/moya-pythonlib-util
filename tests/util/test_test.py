import pytest

pytest_plugins = ["pytester"]


@pytest.mark.parametrize("should_set_flag", [True, False])
def test_regenerate(pytester: pytest.Pytester, should_set_flag: bool) -> None:
    """Make sure that our plugin works."""

    # create a temporary pytest test file
    pytester.makepyfile(f"""\
def test_regenerate_is_{should_set_flag}(regenerate):
    assert regenerate is {should_set_flag}
""")

    result = pytester.runpytest("-p", "moya.util.test.expected", *(["--regenerate"] if should_set_flag else []))
    result.assert_outcomes(passed=1)


def test_assert_values_match_expected(pytester: pytest.Pytester) -> None:
    """Make sure that our plugin works."""

    # create a temporary pytest test file
    fname = "test.json.expected"
    pytester.makepyfile(f"""\
from pathlib import Path

def test_assert_values_match_expected(assert_values_match_expected):
    assert_values_match_expected({{1: 2}}, Path("{fname}"))
""")
    result = pytester.runpytest("-p", "moya.util.test.expected")
    result.assert_outcomes(failed=1)  # fail because the file doesn't exist
    result.stdout.fnmatch_lines([f"E       FileNotFoundError: [Errno 2] No such file or directory: '{fname}'"])

    result = pytester.runpytest("-p", "moya.util.test.expected", "--regenerate")
    result.assert_outcomes(passed=1)  # file has been created now
    expected_file = pytester.path / fname
    assert expected_file.exists()
    assert expected_file.read_text() == '{\n  "1": 2\n}'

    result = pytester.runpytest("-p", "moya.util.test.expected")
    result.assert_outcomes(passed=1)  # file should already exist
