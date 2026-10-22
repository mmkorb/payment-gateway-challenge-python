import unittest
from uuid import UUID, uuid4

from payment_gateway_api.domain.payment import Payment, PaymentStatus
from payment_gateway_api.infrastructure.persistence.memory import InMemoryPaymentRepository


def make_payment(key: str | None = None, payment_id: UUID | None = None) -> Payment:
    return Payment(
        id=payment_id or uuid4(),
        status=PaymentStatus.AUTHORIZED,
        masked_card_number="************1111",
        expiry_month=12,
        expiry_year=2030,
        currency="JPY",
        amount=100,
        idempotency_key=key,
    )


class InMemoryPaymentRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = InMemoryPaymentRepository()

    async def test_fr_11_add_then_get_returns_payment(self) -> None:
        payment = make_payment()
        await self.repository.add(payment)
        self.assertEqual(await self.repository.get(payment.id), payment)

    async def test_fr_11_get_unknown_id_returns_none(self) -> None:
        self.assertIsNone(await self.repository.get(uuid4()))

    async def test_fr_12_find_by_idempotency_key_returns_payment(self) -> None:
        payment = make_payment(key="k1")
        await self.repository.add(payment)
        self.assertEqual(await self.repository.find_by_idempotency_key("k1"), payment)

    async def test_fr_12_unknown_key_returns_none(self) -> None:
        await self.repository.add(make_payment(key="k1"))
        self.assertIsNone(await self.repository.find_by_idempotency_key("other"))

    async def test_fr_12_payment_without_key_is_not_indexed(self) -> None:
        await self.repository.add(make_payment())
        self.assertIsNone(await self.repository.find_by_idempotency_key("None"))


if __name__ == "__main__":
    unittest.main()
