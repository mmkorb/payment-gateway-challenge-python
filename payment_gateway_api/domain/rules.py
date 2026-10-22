"""Card and money rules of the domain (FR-05..FR-10).

Plain functions with no framework imports, so they are unit-tested without doubles
and reused by the API validators (ADR 0003: rules live in the inner ring).
"""

from datetime import date

SUPPORTED_CURRENCIES = frozenset({"JPY", "BRL", "KWD"})
"""One currency per ISO 4217 minor-unit size: 0, 2 and 3 decimals (FR-08, A-05)."""


def is_ascii_digits(value: str) -> bool:
    """True only for ASCII `0`-`9`.

    `str.isdigit` alone accepts fullwidth and Arabic-Indic digits (A-06).
    """
    return value.isascii() and value.isdigit()


def is_luhn_valid(number: str) -> bool:
    """Luhn (mod 10) check: the last digit of a card number is its check digit (FR-05).

    From the right, every second digit is doubled (minus 9 if above 9); the sum must end in 0.
    """
    total = 0
    for position, char in enumerate(reversed(number)):
        digit = int(char)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def mask_card_number(number: str) -> str:
    """Keep only the last four digits, same length (FR-01, NFR-01).

    `4111111111111111` -> `************1111`.
    """
    return "*" * (len(number) - 4) + number[-4:]


def is_expired(month: int, year: int, today: date) -> bool:
    """A card is valid until the end of its printed month (A-11)."""
    return (year, month) < (today.year, today.month)
