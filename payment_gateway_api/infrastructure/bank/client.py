"""Outbound adapter: HTTP client for the acquiring bank (bank simulator, ADR 0005)."""

import asyncio
from uuid import UUID

import httpx

from payment_gateway_api.domain.errors import BankUnavailableError
from payment_gateway_api.domain.payment import CardPayment

BANK_TIMEOUT_SECONDS = 10.0


class HttpAcquiringBank:
    """Outbound adapter for the acquiring bank: exactly one POST /payments, no retry (ADR 0005)."""

    def __init__(
        self, client: httpx.AsyncClient, timeout_seconds: float = BANK_TIMEOUT_SECONDS
    ) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    async def authorize(self, payment_id: UUID, card_payment: CardPayment) -> bool:
        """POST the payment once and return `authorized`.

        Timeout, connection error, non-200 status or a malformed body all raise
        `BankUnavailableError`; the cause goes to the logs, never to the merchant (FR-13).
        """
        payload = {
            "card_number": card_payment.card_number,
            "expiry_date": f"{card_payment.expiry_month:02d}/{card_payment.expiry_year}",
            "currency": card_payment.currency,
            "amount": card_payment.amount,
            "cvv": card_payment.cvv,
            "payment_id": str(payment_id),
        }
        try:
            # httpx timeouts are per phase; asyncio.timeout bounds the whole call.
            async with asyncio.timeout(self._timeout_seconds):
                response = await self._client.post("/payments", json=payload)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise BankUnavailableError("timeout") from exc
        except httpx.TransportError as exc:
            raise BankUnavailableError("connection") from exc

        if response.status_code != 200:
            raise BankUnavailableError(f"bank_{response.status_code}")
        try:
            authorized = response.json()["authorized"]
        except (ValueError, KeyError, TypeError) as exc:
            raise BankUnavailableError("invalid_response") from exc
        if not isinstance(authorized, bool):
            raise BankUnavailableError("invalid_response")
        return authorized
