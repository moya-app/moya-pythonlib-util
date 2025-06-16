import typing as t
from enum import StrEnum


class CaseInsensitiveEnum(StrEnum):
    """
    Like StrEnum but allows it to be instantiated with any case-insensitive version of themselves. Useful for pydantic
    FastAPI inbound models to allow laxness in user input:

        class MyEnum(CaseInsensitiveEnum):
            MY_VALUE = enum.auto()
            OTHER_VALUE = enum.auto()

    str(MyEnum("mY_vaLue")) # 'my_value'
    """

    @classmethod
    def _missing_(cls, value: str) -> t.Any | None:  # type: ignore[override]
        value = value.lower()
        for member in cls:
            if member.lower() == value:
                return member
        return None


class CaseInsensitiveUppercaseEnum(CaseInsensitiveEnum):
    """
    As CaseInsensitiveEnum, but enum.auto() will generate strings of the same case as their attributes:

        class MyEnum(CaseInsensitiveUppercaseEnum):
            MY_VALUE = enum.auto()
            other_value = enum.auto()

    str(MyEnum("mY_vAlue")) # 'MY_VALUE'
    str(MyEnum("OTHER_value")) # 'other_value'
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[t.Any]) -> t.Any:
        return name
