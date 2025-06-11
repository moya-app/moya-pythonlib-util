import typing as t

import pytest

from moya.util.background import never_run_in_background


@pytest.fixture(scope="function")
def no_background_tasks() -> t.Generator[None, None, None]:
    never_run_in_background(True)
    yield
    never_run_in_background(False)
