import enum

from moya.util.enum import CaseInsensitiveEnum, CaseInsensitiveUppercaseEnum


def test_case_insensitive_enum() -> None:
    class MyEnum(CaseInsensitiveEnum):
        MY_VALUE = enum.auto()
        other_value = enum.auto()

    assert str(MyEnum("mY_vaLue")) == "my_value"
    assert str(MyEnum("other_value")) == "other_value"


def test_case_insensitive_uppercase_enum() -> None:
    class MyEnum(CaseInsensitiveUppercaseEnum):
        MY_VALUE = enum.auto()
        other_value = enum.auto()

    assert str(MyEnum("mY_vAlue")) == "MY_VALUE"
    assert str(MyEnum("othEr_vAlue")) == "other_value"
