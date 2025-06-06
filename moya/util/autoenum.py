import enum
import typing as t


class AutoName(str, enum.Enum):
    """
    Automatically set the value to the same as the name of the attribute
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[t.Any]) -> t.Any:
        return name
