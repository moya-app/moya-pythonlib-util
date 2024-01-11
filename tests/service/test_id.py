import pytest

from moya.service.id import parse_rsa_id


def test_parser_rsa_id() -> None:
    for bad_data in (
        "foo",
        "",
        "123456789012345",
        "12345678901234567890123456789012345678901234567890123456789012345678901234567890",
        "7201015075086",
    ):
        with pytest.raises(ValueError):
            parse_rsa_id(bad_data)

    assert parse_rsa_id("9307035489087") == (741657600, "Male", "SA Citizen")
    assert parse_rsa_id("7201015075085") == (63072000, "Male", "SA Citizen")
