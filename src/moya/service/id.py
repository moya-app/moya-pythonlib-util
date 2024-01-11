from datetime import datetime, timezone

from pydantic import BaseModel


class IDDetails(BaseModel):
    date_of_birth: datetime
    gender: str
    citizenship: str


def is_luhn_valid(id_number: str) -> bool:
    """
    Check if a given ID number is valid according to the Luhn algorithm.
    The Luhn algorithm is a simple checksum formula used to validate a variety of identification numbers.
    It works by summing up the digits of the number, with every second digit doubled.
    If the result is divisible by 10, the number is considered valid.
    """

    def digits_of(n: str | int) -> list[int]:
        return [int(d) for d in str(n)]

    digits = digits_of(id_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = 0
    checksum += sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0


def parse_rsa_id(id_number: str) -> IDDetails:
    """
    Parse details from an RSA ID Number
    """
    id_number = id_number.strip()
    if len(id_number) != 13 or not id_number.isdigit() or not is_luhn_valid(id_number):
        raise ValueError("RSA ID not valid")

    year = int(id_number[0:2]) + 1900
    if year < 1922:
        year += 100
    month = int(id_number[2:4])
    day = int(id_number[4:6])

    gender = "Female" if int(id_number[6:10]) < 5000 else "Male"
    citizenship = "SA Citizen" if id_number[10] == "0" else "Permanent Resident"
    date_of_birth = datetime(year, month, day, tzinfo=timezone.utc).timestamp()

    return IDDetails(date_of_birth=date_of_birth, gender=gender, citizenship=citizenship)
