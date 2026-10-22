"""Use case: retrieve a previously processed payment (FR-11)."""

from uuid import UUID

from payment_gateway_api.application.ports import PaymentRepository
from payment_gateway_api.domain.payment import Payment


class GetPayment:
    """Look up a payment by id; `None` becomes `404` at the API edge (A-10)."""

    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    async def execute(self, payment_id: UUID) -> Payment | None:
        return await self._repository.get(payment_id)
