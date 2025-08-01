from unittest import mock

import pytest

from moya.util.argparse import EnvArgumentParser, PydanticArguments


def test_env_argument_parser() -> None:
    """
    Test that EnvArgumentParser correctly uses environment variables for default values.
    """
    parser = EnvArgumentParser()
    with mock.patch.dict("os.environ", {"APP_FOO": "bar"}):
        parser.add_argument("--foo", default="baz")
        args = parser.parse_args([])
        assert args.foo == "bar"


def test_env_argument_parser_with_no_env_var() -> None:
    """
    Test that EnvArgumentParser uses the default value when no environment variable is set.
    """
    parser = EnvArgumentParser()
    parser.add_argument("--foo", default="baz")
    args = parser.parse_args([])
    assert args.foo == "baz"


def test_pydantic_arguments_run() -> None:
    """
    Test that PydanticArguments.run() correctly parses arguments.
    """

    class MyArgs(PydanticArguments):
        foo: str

    with mock.patch("sys.argv", ["test", "--foo", "bar"]):
        assert MyArgs.run() == 0


def test_pydantic_arguments_run_with_validation_error() -> None:
    """
    Test that PydanticArguments.run() handles validation errors.
    """

    class MyArgs(PydanticArguments):
        foo: int

    with mock.patch("sys.argv", ["test", "--foo", "bar"]):
        with pytest.raises(SystemExit) as e:
            MyArgs.run()
        assert e.value.code != 0
