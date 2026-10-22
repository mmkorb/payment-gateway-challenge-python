"""Translate errors to the HTTP contract in one place (A-08, FR-13).

Validation errors -> `422` with our error codes; `BankUnavailableError` -> `503` with one
fixed body, so the merchant never learns the internal cause.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from payment_gateway_api.domain.errors import BankUnavailableError

logger = logging.getLogger(__name__)

# Request field -> prefix of its A-08 codes (`<prefix>_required` / `<prefix>_invalid`).
_FIELD_CODES = {
    "card_number": "card_number",
    "expiry_month": "card_expiry_month",
    "expiry_year": "card_expiry_year",
    "currency": "currency",
    "amount": "amount",
    "cvv": "cvv",
}

# Codes raised by our own validators in schemas.py (PydanticCustomError); kept as they are.
_VALIDATOR_CODES = {
    "card_number_invalid",
    "card_expiry_month_invalid",
    "card_expiry_year_invalid",
    "card_expired",
    "currency_invalid",
    "amount_invalid",
    "cvv_invalid",
}


def _error_code(error: Any) -> str:
    """Map one Pydantic error to an A-08 code.

    Pydantic describes each error with `type`, `loc` (e.g. `("body", "amount")`) and `input`
    (the value received). Our validator codes pass through; a missing or null field becomes
    `<field>_required`; any other error on a field (wrong type) becomes `<field>_invalid`.
    """
    if error["type"] in _VALIDATOR_CODES:
        return str(error["type"])
    loc = error.get("loc", ())
    prefix = _FIELD_CODES.get(str(loc[-1])) if len(loc) == 2 and loc[0] == "body" else None
    if prefix is None:
        return "request_body_invalid"  # body is not a JSON object
    if error["type"] == "missing" or error.get("input") is None:
        return f"{prefix}_required"
    return f"{prefix}_invalid"


def register_error_handlers(app: FastAPI) -> None:
    """Install the `422` and `503` handlers.

    The `422` is logged with error codes only, never the submitted values (NFR-09).
    """

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        codes = list(dict.fromkeys(_error_code(error) for error in exc.errors()))
        logger.info("validation_rejected error_codes=%s", codes)
        return JSONResponse(
            status_code=422,
            content={"status": "Rejected", "error_type": "request_invalid", "error_codes": codes},
        )

    @app.exception_handler(BankUnavailableError)
    async def _bank_unavailable(_: Request, __: BankUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "status": "Rejected",
                "error_type": "service_unavailable",
                "error_codes": ["service_unavailable"],
            },
        )
