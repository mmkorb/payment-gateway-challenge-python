import unittest
from unittest.mock import AsyncMock
from uuid import UUID

from payment_gateway_api.application.process_payment import ProcessPayment
from payment_gateway_api.domain.errors import BankUnavailableError
from payment_gateway_api.domain.payment import CardPayment, PaymentStatus
from payment_gateway_api.infrastructure.persistence.memory import InMemoryPaymentRepository

CARD_NUMBER = "4111111111111111"
CVV = "737"
LOGGER = "payment_gateway_api.application.process_payment"


def make_card() -> CardPayment:
    return CardPayment(CARD_NUMBER, 12, 2030, "JPY", 1050, CVV)


class ProcessPaymentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.ids = [UUID(int=i) for i in range(1, 10)]
        self.bank = AsyncMock()
        self.bank.authorize.return_value = True
        self.repository = InMemoryPaymentRepository()
        self.use_case = ProcessPayment(self.bank, self.repository, new_id=lambda: self.ids.pop(0))

    async def test_fr_02_authorized_is_stored_with_masked_card(self) -> None:
        payment = await self.use_case.execute(make_card(), None)
        self.assertEqual(payment.status, PaymentStatus.AUTHORIZED)
        self.assertEqual(payment.masked_card_number, "************1111")
        self.assertEqual(payment.id, UUID(int=1))
        self.assertEqual(payment.amount, 1050)
        self.assertEqual(await self.repository.get(payment.id), payment)

    async def test_fr_03_declined_is_stored(self) -> None:
        self.bank.authorize.return_value = False
        payment = await self.use_case.execute(make_card(), None)
        self.assertEqual(payment.status, PaymentStatus.DECLINED)
        self.assertEqual(await self.repository.get(payment.id), payment)

    async def test_fr_01_bank_called_once_with_id_and_card(self) -> None:
        card = make_card()
        await self.use_case.execute(card, None)
        self.bank.authorize.assert_awaited_once_with(UUID(int=1), card)

    async def test_fr_13_bank_unavailable_reraised_nothing_stored_and_warned(self) -> None:
        self.bank.authorize.side_effect = BankUnavailableError("timeout")
        with self.assertLogs(LOGGER, "WARNING") as logs, self.assertRaises(BankUnavailableError):
            await self.use_case.execute(make_card(), "key-1")
        self.assertIsNone(await self.repository.get(UUID(int=1)))
        self.assertIsNone(await self.repository.find_by_idempotency_key("key-1"))
        self.assertEqual(len(logs.records), 1)
        message = logs.output[0]
        self.assertIn(str(UUID(int=1)), message)
        self.assertIn("timeout", message)
        self.assertEqual(self.bank.authorize.await_count, 1)

    async def test_fr_12_same_key_returns_stored_payment(self) -> None:
        first = await self.use_case.execute(make_card(), "key-1")
        second = await self.use_case.execute(make_card(), "key-1")
        self.assertEqual(second, first)
        self.bank.authorize.assert_awaited_once()

    async def test_fr_12_no_key_creates_two_payments(self) -> None:
        first = await self.use_case.execute(make_card(), None)
        second = await self.use_case.execute(make_card(), None)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.bank.authorize.await_count, 2)

    async def test_fr_12_different_keys_create_two_payments(self) -> None:
        first = await self.use_case.execute(make_card(), "a")
        second = await self.use_case.execute(make_card(), "b")
        self.assertNotEqual(first.id, second.id)

    async def test_fr_12_key_after_bank_failure_is_processed_as_new(self) -> None:
        self.bank.authorize.side_effect = [BankUnavailableError("down"), True]
        with self.assertLogs(LOGGER, "WARNING"), self.assertRaises(BankUnavailableError):
            await self.use_case.execute(make_card(), "key-1")
        payment = await self.use_case.execute(make_card(), "key-1")
        self.assertEqual(payment.status, PaymentStatus.AUTHORIZED)
        self.assertEqual(payment.id, UUID(int=2))
        self.assertEqual(self.bank.authorize.await_count, 2)

    async def test_nfr_09_info_line_has_id_status_currency_amount(self) -> None:
        with self.assertLogs(LOGGER, "INFO") as logs:
            payment = await self.use_case.execute(make_card(), None)
        info = [r.getMessage() for r in logs.records if r.levelname == "INFO"]
        self.assertEqual(len(info), 1)
        self.assertIn(f"payment_id={payment.id}", info[0])
        self.assertIn("status=Authorized", info[0])
        self.assertIn("currency=JPY", info[0])
        self.assertIn("amount=1050", info[0])

    async def test_nfr_09_no_log_contains_card_number_or_cvv(self) -> None:
        self.bank.authorize.side_effect = [True, BankUnavailableError("down")]
        with self.assertLogs(LOGGER, "DEBUG") as logs:
            await self.use_case.execute(make_card(), "k1")
            with self.assertRaises(BankUnavailableError):
                await self.use_case.execute(make_card(), "k2")
        self.assertGreaterEqual(len(logs.records), 2)
        for line in logs.output:
            self.assertNotIn(CARD_NUMBER, line)
            self.assertNotIn(CVV, line)


if __name__ == "__main__":
    unittest.main()
