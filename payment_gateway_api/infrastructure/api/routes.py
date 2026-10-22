"""HTTP routes (inbound adapter): REST level 2, ADR 0001. No business logic here."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from payment_gateway_api.application.get_payment import GetPayment
from payment_gateway_api.application.process_payment import ProcessPayment
from payment_gateway_api.infrastructure.api.schemas import PaymentRequest, PaymentResponse


def build_router(process_payment: ProcessPayment, get_payment: GetPayment) -> APIRouter:
    """Build the routes around the injected use cases (no globals, easy to test)."""
    router = APIRouter()

    @router.get("/")
    async def ping() -> dict[str, str]:
        return {"app": "payment-gateway-api"}

    @router.post("/payments", status_code=201)
    async def create_payment(
        request: PaymentRequest,
        idempotency_key: Annotated[str | None, Header(alias="Cko-Idempotency-Key")] = None,
    ) -> PaymentResponse:
        """Process a payment: `201` Authorized/Declined; optional `Cko-Idempotency-Key` (FR-12)."""
        payment = await process_payment.execute(request.to_domain(), idempotency_key)
        return PaymentResponse.from_domain(payment)

    @router.get("/payments/{payment_id}")
    async def read_payment(payment_id: str) -> PaymentResponse:
        """Retrieve a payment; a malformed or unknown id is `404` (A-10)."""
        try:
            parsed = UUID(payment_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Payment not found") from None
        payment = await get_payment.execute(parsed)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return PaymentResponse.from_domain(payment)

    return router
