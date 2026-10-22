import unittest
from datetime import date

from payment_gateway_api.domain.rules import (
    is_ascii_digits,
    is_expired,
    is_luhn_valid,
    mask_card_number,
)

TODAY = date(2026, 6, 15)


class LuhnTests(unittest.TestCase):
    def test_fr_05_valid_16_digit_number(self) -> None:
        self.assertTrue(is_luhn_valid("4111111111111111"))

    def test_fr_05_invalid_number(self) -> None:
        self.assertFalse(is_luhn_valid("4111111111111112"))

    def test_fr_05_valid_14_digit_number(self) -> None:
        self.assertTrue(is_luhn_valid("36227206271667"))

    def test_fr_05_valid_19_digit_number(self) -> None:
        self.assertTrue(is_luhn_valid("4111111111111111110"))


class MaskTests(unittest.TestCase):
    def test_nfr_02_mask_keeps_length_and_last_four(self) -> None:
        self.assertEqual(mask_card_number("4111111111111111"), "************1111")

    def test_nfr_02_mask_keeps_length_for_14_and_19_digits(self) -> None:
        for number in ("36227206271667", "4111111111111111110"):
            with self.subTest(number=number):
                masked = mask_card_number(number)
                self.assertEqual(len(masked), len(number))
                self.assertEqual(masked[-4:], number[-4:])
                self.assertEqual(set(masked[:-4]), {"*"})


class AsciiDigitsTests(unittest.TestCase):
    def test_fr_05_accepts_ascii_digits(self) -> None:
        self.assertTrue(is_ascii_digits("0123456789"))

    def test_fr_05_rejects_fullwidth_digit(self) -> None:
        self.assertFalse(is_ascii_digits("\N{FULLWIDTH DIGIT FOUR}"))

    def test_fr_05_rejects_arabic_indic_digit(self) -> None:
        self.assertFalse(is_ascii_digits("\N{ARABIC-INDIC DIGIT FOUR}"))

    def test_fr_05_rejects_empty_and_letters(self) -> None:
        self.assertFalse(is_ascii_digits(""))
        self.assertFalse(is_ascii_digits("12a4"))


class ExpiryTests(unittest.TestCase):
    def test_fr_07_a_11_current_month_is_not_expired(self) -> None:
        self.assertFalse(is_expired(6, 2026, TODAY))

    def test_fr_07_previous_month_is_expired(self) -> None:
        self.assertTrue(is_expired(5, 2026, TODAY))

    def test_fr_07_next_month_is_not_expired(self) -> None:
        self.assertFalse(is_expired(7, 2026, TODAY))

    def test_fr_07_december_this_year_is_not_expired(self) -> None:
        self.assertFalse(is_expired(12, 2026, TODAY))

    def test_fr_07_january_next_year_is_not_expired(self) -> None:
        self.assertFalse(is_expired(1, 2027, TODAY))

    def test_fr_07_december_last_year_is_expired_in_january(self) -> None:
        self.assertTrue(is_expired(12, 2025, date(2026, 1, 1)))

    def test_fr_07_december_is_not_expired_on_last_day_of_month(self) -> None:
        self.assertFalse(is_expired(12, 2026, date(2026, 12, 31)))

    def test_fr_07_december_is_expired_in_january_of_next_year(self) -> None:
        self.assertTrue(is_expired(12, 2026, date(2027, 1, 1)))


if __name__ == "__main__":
    unittest.main()
