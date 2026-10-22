"""Domain entities: what a payment is, independent of HTTP, storage or the bank."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class PaymentStatus(StrEnum):
    """Statuses of a stored payment. `Rejected` is a response only and is never stored (A-02)."""

    AUTHORIZED = "Authorized"
    DECLINED = "Declined"


@dataclass(frozen=True, slots=True)
class CardPayment:
    """A validated payment request. Holds the full card number and CVV: never store or log it."""

    card_number: str = field(repr=False)
    expiry_month: int
    expiry_year: int
    currency: str
    amount: int
    cvv: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class Payment:
    """A processed payment as stored and returned: the card number is masked (A-14)."""

    id: UUID
    status: PaymentStatus
    masked_card_number: str
    expiry_month: int
    expiry_year: int
    currency: str
    amount: int
    idempotency_key: str | None = None
