"""Interfaces the use cases need (dependency inversion, ADR 0003).

Adapters in `infrastructure/` satisfy them structurally; tests use fakes or `AsyncMock`.
"""

from typing import Protocol
from uuid import UUID

from payment_gateway_api.domain.payment import CardPayment, Payment


class AcquiringBank(Protocol):
    """The acquiring bank: one authorization call per payment (ADR 0005)."""

    async def authorize(self, payment_id: UUID, card_payment: CardPayment) -> bool:
        """True if authorized, False if declined; raises BankUnavailableError on failure."""
        ...


class PaymentRepository(Protocol):
    """Storage of processed payments, by id and by idempotency key (ADR 0004, ADR 0006)."""

    async def add(self, payment: Payment) -> None: ...

    async def get(self, payment_id: UUID) -> Payment | None: ...

    async def find_by_idempotency_key(self, key: str) -> Payment | None: ...
