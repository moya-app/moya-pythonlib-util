from moya.util.cmd import run_async

# Because this screws with event loop it will break if we run alongside the standard test suite


def test_run_async() -> None:
    async def basic_main() -> None:
        pass

    run_async(basic_main())


def test_run_async_exit_code() -> None:
    async def main_with_error() -> int:
        return 1

    # You can then use sys.exit(run_async(main_with_error())) to handle exit codes
    assert run_async(main_with_error()) == 1
