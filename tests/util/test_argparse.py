from argparse import ArgumentParser
from unittest import mock

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


async def test_pydantic_arguments_run() -> None:
    """
    Test that PydanticArguments.run() correctly parses arguments.
    """

    run_args: "MyArgs" | None = None

    class MyArgs(PydanticArguments):
        foo: str

        async def cli_cmd(self) -> None:
            nonlocal run_args
            run_args = self

    with mock.patch("sys.argv", ["test", "--foo", "bar"]):
        assert MyArgs.run() == 0
        assert run_args
        assert run_args.foo == "bar"


def test_pydantic_arguments_run_with_validation_error() -> None:
    """
    Test that PydanticArguments.run() handles validation errors.
    """

    class MyArgs(PydanticArguments):
        foo: int

    with mock.patch("sys.argv", ["test", "--foo", "bar"]), mock.patch.object(ArgumentParser, "exit", autospec=True) as exit_override:
        MyArgs.run()
        exit_override.assert_called_once_with(
            mock.ANY, 2, "test: error: \nargument foo: Input should be a valid integer, unable to parse string as an integer\n"
        )
