import enum
import typing as t


class AutoName(str, enum.Enum):
    """
    Deprecated: Automatically set the value to the same as the name of the attribute like:

        class MyEnum(AutoName):
            VALUE_1 = enum.auto()  # "VALUE_1"
            value_2 = enum.auto()  # "value_2"

    Use enum.StrEnum instead nowadays, although it does automatically lower-case the values.
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[t.Any]) -> t.Any:
        return name
