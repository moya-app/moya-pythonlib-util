import pytest

pytest_plugins = ["pytester"]  # pytester to run pytest inside the test


@pytest.mark.parametrize("should_set_flag", [True, False])
def test_regenerate(pytester: pytest.Pytester, should_set_flag: bool) -> None:
    # value of regenerate should be True if --regenerate is passed, otherwise False
    pytester.makepyfile(f"""\
def test_regenerate_is_{should_set_flag}(regenerate):
    assert regenerate is {should_set_flag}
""")

    result = pytester.runpytest("-p", "moya.util.test.expected", *(["--regenerate"] if should_set_flag else []))
    result.assert_outcomes(passed=1)


def test_assert_values_match_expected(pytester: pytest.Pytester) -> None:
    fname = "test.json.expected"
    pytester.makepyfile(f"""\
from pathlib import Path

def test_assert_values_match_expected(assert_values_match_expected):
    assert_values_match_expected({{1: 2}}, Path("{fname}"))
""")

    # test 1: fail because the file doesn't exist
    result = pytester.runpytest("-p", "moya.util.test.expected")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([f"E       FileNotFoundError: [Errno 2] No such file or directory: '{fname}'"])

    # test 2: file has been created now
    result = pytester.runpytest("-p", "moya.util.test.expected", "--regenerate")
    result.assert_outcomes(passed=1)
    expected_file = pytester.path / fname
    assert expected_file.exists()
    assert expected_file.read_text() == '{\n  "1": 2\n}'

    # test 3: file should already exist
    result = pytester.runpytest("-p", "moya.util.test.expected")
    result.assert_outcomes(passed=1)
