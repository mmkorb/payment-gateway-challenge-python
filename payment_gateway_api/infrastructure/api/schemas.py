"""HTTP request/response models (inbound adapter, ADR 0002).

Pydantic strict mode rejects coerced types (`"4"`, `4.0`, `true` for an int); unknown
fields are ignored (A-15). Validators delegate to `domain.rules` and raise our A-08 codes.
"""

from datetime import UTC, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic_core import PydanticCustomError

from payment_gateway_api.domain.payment import CardPayment, Payment
from payment_gateway_api.domain.rules import (
    SUPPORTED_CURRENCIES,
    is_ascii_digits,
    is_expired,
    is_luhn_valid,
)


class PaymentRequest(BaseModel):
    """Body of `POST /payments` (FR-05..FR-10).

    Holds the full card number and CVV in memory only; never stored or logged (NFR-02).
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    card_number: str
    expiry_month: int
    expiry_year: int
    currency: str
    amount: int
    cvv: str

    @field_validator("card_number")
    @classmethod
    def _check_card_number(cls, value: str) -> str:
        if not (is_ascii_digits(value) and 14 <= len(value) <= 19 and is_luhn_valid(value)):
            raise PydanticCustomError("card_number_invalid", "card number is invalid")
        return value

    @field_validator("expiry_month")
    @classmethod
    def _check_month(cls, value: int) -> int:
        if not 1 <= value <= 12:
            raise PydanticCustomError("card_expiry_month_invalid", "expiry month is invalid")
        return value

    @field_validator("expiry_year")
    @classmethod
    def _check_year(cls, value: int) -> int:
        if not 1000 <= value <= 9999:
            raise PydanticCustomError("card_expiry_year_invalid", "expiry year is invalid")
        return value

    @field_validator("currency")
    @classmethod
    def _check_currency(cls, value: str) -> str:
        """Accept any letter case and return it uppercase (FR-08). ASCII check first (A-06)."""
        if not (value.isascii() and value.upper() in SUPPORTED_CURRENCIES):
            raise PydanticCustomError("currency_invalid", "currency is invalid")
        return value.upper()

    @field_validator("amount")
    @classmethod
    def _check_amount(cls, value: int) -> int:
        if not 1 <= value <= 999_999_999:
            raise PydanticCustomError("amount_invalid", "amount is invalid")
        return value

    @field_validator("cvv")
    @classmethod
    def _check_cvv(cls, value: str) -> str:
        if not (is_ascii_digits(value) and 3 <= len(value) <= 4):
            raise PydanticCustomError("cvv_invalid", "cvv is invalid")
        return value

    @model_validator(mode="after")
    def _check_not_expired(self) -> Self:
        """Month + year must not be in the past (FR-07).

        The current month is still valid; "today" is the UTC date (A-11).
        """
        if is_expired(self.expiry_month, self.expiry_year, datetime.now(UTC).date()):
            raise PydanticCustomError("card_expired", "card is expired")
        return self

    def to_domain(self) -> CardPayment:
        """Map to the domain object the use case expects (no framework types cross inward)."""
        return CardPayment(**self.model_dump())


class PaymentResponse(BaseModel):
    """Payment returned by `POST` and `GET`.

    No `card_number` or `cvv` field exists here, so they cannot leak (NFR-01).
    """

    id: UUID
    status: str
    masked_card_number: str
    expiry_month: int
    expiry_year: int
    currency: str
    amount: int

    @classmethod
    def from_domain(cls, payment: Payment) -> Self:
        """Copy the matching fields from the domain `Payment` (extra ones are not exposed)."""
        return cls.model_validate(payment, from_attributes=True)
