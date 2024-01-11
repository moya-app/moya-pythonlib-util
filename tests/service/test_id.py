import pytest

from moya.service.id import IDDetails, parse_rsa_id


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

    assert parse_rsa_id("9307035489087") == IDDetails(date_of_birth=741657600, gender="Male", citizenship="SA Citizen")
    assert parse_rsa_id("7201015075085") == IDDetails(date_of_birth=63072000, gender="Male", citizenship="SA Citizen")
    assert parse_rsa_id("7104134800088") == IDDetails(
        date_of_birth=40348800, gender="Female", citizenship="SA Citizen"
    )
    assert parse_rsa_id("7104134800187") == IDDetails(
        date_of_birth=40348800, gender="Female", citizenship="Permanent Resident"
    )
