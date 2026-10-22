"""Use case: process a payment (FR-01..FR-03, FR-12, FR-13)."""

import logging
import time
from collections.abc import Callable
from uuid import UUID, uuid4

from payment_gateway_api.application.ports import AcquiringBank, PaymentRepository
from payment_gateway_api.domain.errors import BankUnavailableError
from payment_gateway_api.domain.payment import CardPayment, Payment, PaymentStatus
from payment_gateway_api.domain.rules import mask_card_number

logger = logging.getLogger(__name__)


class ProcessPayment:
    """Send a validated payment to the bank once and store the result.

    Flow: idempotency lookup -> new `payment_id` -> one bank call -> store the masked payment.
    A bank failure is logged with its cause, re-raised and nothing is stored (FR-13, ADR 0005).
    `new_id` is injectable so tests get predictable ids.
    """

    def __init__(
        self,
        bank: AcquiringBank,
        repository: PaymentRepository,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self._bank = bank
        self._repository = repository
        self._new_id = new_id

    async def execute(self, card_payment: CardPayment, idempotency_key: str | None) -> Payment:
        """Return the stored payment for a repeated key, otherwise process a new one."""
        if idempotency_key is not None:
            existing = await self._repository.find_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        payment_id = self._new_id()
        started = time.perf_counter()
        try:
            authorized = await self._bank.authorize(payment_id, card_payment)
        except BankUnavailableError as error:
            # FR-13: one call, no retry, nothing stored; the cause stays in the log.
            logger.warning(
                "bank_failure payment_id=%s cause=%s idempotency_key=%s",
                payment_id,
                error.cause,
                idempotency_key,
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000

        payment = Payment(
            id=payment_id,
            status=PaymentStatus.AUTHORIZED if authorized else PaymentStatus.DECLINED,
            masked_card_number=mask_card_number(card_payment.card_number),
            expiry_month=card_payment.expiry_month,
            expiry_year=card_payment.expiry_year,
            currency=card_payment.currency,
            amount=card_payment.amount,
            idempotency_key=idempotency_key,
        )
        await self._repository.add(payment)
        logger.info(
            "payment_processed payment_id=%s status=%s currency=%s amount=%s bank_ms=%.1f",
            payment.id,
            payment.status,
            payment.currency,
            payment.amount,
            duration_ms,
        )
        return payment
