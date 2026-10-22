"""Outbound adapter: in-memory storage standing in for a database (ADR 0006)."""

from uuid import UUID

from payment_gateway_api.domain.payment import Payment


class InMemoryPaymentRepository:
    """Stands in for a database (ADR 0006); also the test fake."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Payment] = {}
        self._id_by_key: dict[str, UUID] = {}

    async def add(self, payment: Payment) -> None:
        self._by_id[payment.id] = payment
        if payment.idempotency_key is not None:
            self._id_by_key[payment.idempotency_key] = payment.id

    async def get(self, payment_id: UUID) -> Payment | None:
        return self._by_id.get(payment_id)

    async def find_by_idempotency_key(self, key: str) -> Payment | None:
        payment_id = self._id_by_key.get(key)
        return None if payment_id is None else self._by_id[payment_id]
