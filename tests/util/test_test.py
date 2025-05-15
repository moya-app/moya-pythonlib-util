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
