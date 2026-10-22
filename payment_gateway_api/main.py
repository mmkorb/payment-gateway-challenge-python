"""Composition root: the only module that knows every layer and wires them (ADR 0003)."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from payment_gateway_api.application.get_payment import GetPayment
from payment_gateway_api.application.ports import AcquiringBank, PaymentRepository
from payment_gateway_api.application.process_payment import ProcessPayment
from payment_gateway_api.infrastructure.api.errors import register_error_handlers
from payment_gateway_api.infrastructure.api.routes import build_router
from payment_gateway_api.infrastructure.bank.client import HttpAcquiringBank
from payment_gateway_api.infrastructure.persistence.memory import InMemoryPaymentRepository


def create_app(
    bank: AcquiringBank | None = None,
    repository: PaymentRepository | None = None,
) -> FastAPI:
    """Create the app. Tests inject a fake bank and repository; production builds the real ones.

    The httpx client has no per-phase timeout: the 10 s total limit lives in the bank adapter
    (ADR 0005). Run with `uvicorn --factory payment_gateway_api.main:create_app`.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    client: httpx.AsyncClient | None = None
    if bank is None:
        client = httpx.AsyncClient(
            base_url=os.environ.get("BANK_URL", "http://localhost:8080"), timeout=None
        )
        bank = HttpAcquiringBank(client)
    repository = repository if repository is not None else InMemoryPaymentRepository()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if client is not None:
                await client.aclose()

    app = FastAPI(title="Payment Gateway API", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(build_router(ProcessPayment(bank, repository), GetPayment(repository)))
    return app
