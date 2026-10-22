import asyncio
import json
import unittest
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

import httpx

from payment_gateway_api.domain.errors import BankUnavailableError
from payment_gateway_api.domain.payment import CardPayment
from payment_gateway_api.infrastructure.bank.client import HttpAcquiringBank

PAYMENT_ID = UUID("12345678-1234-5678-1234-567812345678")
CARD = CardPayment(
    card_number="2222405343248877",
    expiry_month=4,
    expiry_year=2027,
    currency="GBP",
    amount=100,
    cvv="123",
)

Handler = (
    Callable[[httpx.Request], httpx.Response]
    | Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]
)


class HttpAcquiringBankTest(unittest.IsolatedAsyncioTestCase):
    async def _authorize(self, handler: Handler, timeout_seconds: float = 5.0) -> bool:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://bank.test"
        ) as client:
            bank = HttpAcquiringBank(client, timeout_seconds=timeout_seconds)
            return await bank.authorize(PAYMENT_ID, CARD)

    async def _cause(self, handler: Handler, timeout_seconds: float = 5.0) -> str:
        with self.assertRaises(BankUnavailableError) as ctx:
            await self._authorize(handler, timeout_seconds)
        return ctx.exception.cause

    async def test_fr_02_authorized_true(self) -> None:
        result = await self._authorize(lambda _: httpx.Response(200, json={"authorized": True}))
        self.assertIs(result, True)

    async def test_fr_03_authorized_false(self) -> None:
        result = await self._authorize(lambda _: httpx.Response(200, json={"authorized": False}))
        self.assertIs(result, False)

    async def test_fr_01_sends_one_post_with_exact_json(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"authorized": True})

        await self._authorize(handler)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].url.path, "/payments")
        self.assertEqual(
            json.loads(requests[0].content),
            {
                "card_number": "2222405343248877",
                "expiry_date": "04/2027",
                "currency": "GBP",
                "amount": 100,
                "cvv": "123",
                "payment_id": str(PAYMENT_ID),
            },
        )

    async def test_fr_13_bank_503_is_unavailable(self) -> None:
        self.assertEqual(await self._cause(lambda _: httpx.Response(503)), "bank_503")

    async def test_fr_13_bank_400_is_unavailable(self) -> None:
        self.assertEqual(await self._cause(lambda _: httpx.Response(400)), "bank_400")

    async def test_fr_13_connect_error_is_connection(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        self.assertEqual(await self._cause(handler), "connection")

    async def test_fr_13_total_timeout(self) -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            await asyncio.sleep(1)
            return httpx.Response(200, json={"authorized": True})

        self.assertEqual(await self._cause(handler, timeout_seconds=0.05), "timeout")

    async def test_fr_13_read_timeout_is_timeout(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow")

        self.assertEqual(await self._cause(handler), "timeout")

    async def test_fr_13_non_json_body_is_invalid_response(self) -> None:
        cause = await self._cause(lambda _: httpx.Response(200, content=b"not json"))
        self.assertEqual(cause, "invalid_response")

    async def test_fr_13_missing_authorized_is_invalid_response(self) -> None:
        cause = await self._cause(lambda _: httpx.Response(200, json={"ok": True}))
        self.assertEqual(cause, "invalid_response")

    async def test_fr_13_non_bool_authorized_is_invalid_response(self) -> None:
        cause = await self._cause(lambda _: httpx.Response(200, json={"authorized": "yes"}))
        self.assertEqual(cause, "invalid_response")
