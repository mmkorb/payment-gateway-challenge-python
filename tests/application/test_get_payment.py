import unittest
from uuid import uuid4

from payment_gateway_api.application.get_payment import GetPayment
from payment_gateway_api.domain.payment import Payment, PaymentStatus
from payment_gateway_api.infrastructure.persistence.memory import InMemoryPaymentRepository


class GetPaymentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = InMemoryPaymentRepository()
        self.use_case = GetPayment(self.repository)

    async def test_fr_11_found_returns_stored_payment(self) -> None:
        payment = Payment(
            id=uuid4(),
            status=PaymentStatus.DECLINED,
            masked_card_number="************1111",
            expiry_month=1,
            expiry_year=2031,
            currency="BRL",
            amount=5,
        )
        await self.repository.add(payment)
        self.assertEqual(await self.use_case.execute(payment.id), payment)

    async def test_fr_11_not_found_returns_none(self) -> None:
        self.assertIsNone(await self.use_case.execute(uuid4()))


if __name__ == "__main__":
    unittest.main()
