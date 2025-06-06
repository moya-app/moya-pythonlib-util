import enum
from moya.util.autoenum import AutoName

def test_autoname():
    class Test(AutoName):
        FOO = enum.auto()
        bar = enum.auto()

    assert Test.FOO == "FOO"
    assert Test.bar == "bar"
