import unittest
from uuid import uuid4

from payment_gateway_api.domain.payment import CardPayment, Payment, PaymentStatus


class CardPaymentTests(unittest.TestCase):
    def test_nfr_02_repr_hides_card_number_and_cvv(self) -> None:
        card = CardPayment("4111111111111111", 12, 2030, "JPY", 100, "737")
        text = repr(card)
        self.assertNotIn("4111111111111111", text)
        self.assertNotIn("737", text)
        self.assertNotIn("cvv", text)
        self.assertNotIn("card_number", text)
        self.assertIn("JPY", text)

    def test_nfr_02_str_hides_card_number_and_cvv(self) -> None:
        card = CardPayment("4111111111111111", 12, 2030, "JPY", 100, "737")
        self.assertNotIn("4111111111111111", str(card))
        self.assertNotIn("737", str(card))


class PaymentTests(unittest.TestCase):
    def test_a_14_payment_holds_masked_number_only(self) -> None:
        payment = Payment(
            id=uuid4(),
            status=PaymentStatus.AUTHORIZED,
            masked_card_number="************1111",
            expiry_month=12,
            expiry_year=2030,
            currency="JPY",
            amount=100,
        )
        self.assertIsNone(payment.idempotency_key)
        self.assertNotIn("4111111111111111", repr(payment))

    def test_fr_02_fr_03_status_values(self) -> None:
        self.assertEqual(PaymentStatus.AUTHORIZED, "Authorized")
        self.assertEqual(PaymentStatus.DECLINED, "Declined")


if __name__ == "__main__":
    unittest.main()
