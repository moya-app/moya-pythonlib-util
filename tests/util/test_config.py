import os
import typing as t
from unittest.mock import patch

from moya.util.config import BaseModel, MoyaSettings


def test_moya_settings() -> None:
    with patch.dict(
        os.environ,
        {
            "FOO": "foo",
            "APP_FOO": "bar",
            # Implicit integer conversion
            "APP_BAR": "0",
            # Nesting via __s
            "APP_NESTED__FOO": "bar",
            # Nesting via json
            "APP_NESTED2": '{"foo": "bar"}',
        },
    ):

        class Nested(BaseModel):
            foo: str

        class MySettings(MoyaSettings):
            foo: str
            bar: int
            fred: t.Optional[str] = "foo"
            NESTED: Nested
            nested2: Nested

        settings = MySettings()
        assert settings.foo == "bar"
        assert settings.bar == 0
        assert settings.fred == "foo"
        assert settings.NESTED.foo == "bar"
        assert settings.nested2.foo == "bar"
