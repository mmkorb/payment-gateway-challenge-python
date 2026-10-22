# 0002. FastAPI + Pydantic (strict) + httpx + uvicorn
- Status: accepted (user decision 2026-10-22)

## Context
The starter ships FastAPI `^0.103.2`, uvicorn, gunicorn, and httpx/requests/pytest as dev dependencies (`pyproject.toml`), pinned for Python `^3.8` (runtime now 3.13, NFR-07). The gateway needs:
- strict JSON types with no coercion (FR-05..FR-10);
- the exact `422` body and error codes of A-08;
- unknown fields ignored (A-15);
- one bank call with a 10-second total timeout, mapped to `503` (FR-13, NFR-06);
- the optional `Cko-Idempotency-Key` header (FR-12);
- 90% branch coverage with `unittest` (NFR-04);
- generated API documentation (Swagger UI) (user request 2026-10-22).

A panel (senior software engineer and staff engineer) compared FastAPI with Pydantic strict mode, FastAPI with hand-written validation, Starlette, Flask, and pure stdlib (`http.server` + `urllib`).

Facts checked on 2026-10-22:
- Pydantic 2.13.4 with `ConfigDict(strict=True, extra="ignore")`, run locally: `4.0`, `true` and `"4"` for an `int` field fail with `int_type`; `123` for a `str` field fails with `string_type`; unknown keys are dropped.
- PyPI `requires-python`: pydantic 2.14.1 (`>=3.10`), fastapi 0.161.0 (`>=3.10`), starlette (`>=3.11`), uvicorn 0.54.0 (`>=3.10`), httpx 0.28.1 (`>=3.8`): all support Python 3.13, the runtime in NFR-07. Locked versions: NFR-07.
- httpx timeouts are per phase, not total: "Read: maximum duration to wait for a chunk of data to be received", default "5 seconds of network inactivity" (https://www.python-httpx.org/advanced/timeouts/, accessed 2026-10-22).

## Decision
- **HTTP routing:** FastAPI, only in the driving adapter (`infrastructure/api`). It reads the `Cko-Idempotency-Key` header and serves Swagger UI at `/docs` from the generated OpenAPI spec.
- **Request validation:** Pydantic models with `strict=True` and `extra="ignore"` for types and required fields. Field validators carry the business rules (Luhn, expiry in the future, the currency list, amount and CVV ranges) and raise our A-08 codes. One exception handler turns every validation error into the A-08 `422` body; FastAPI's default `{"detail": [...]}` body is never returned.
- **Bank client:** `httpx.AsyncClient`, injected into the bank adapter. The 10-second total limit is `asyncio.timeout(10)` around the call, because httpx timeouts are per phase. Timeout, connection error and bank `503` all map to the FR-13 body. Tests inject `httpx.MockTransport` and a smaller timeout.
- **ASGI server:** uvicorn only.
- **Dependencies:** move httpx to the main dependencies. Remove gunicorn (several worker processes cannot share the in-memory store), requests and pytest (unittest only, NFR-04). Versions are pinned to current releases at setup.

Why:
- One source of truth: the same models give types, validation and the Swagger schema, so the docs cannot drift from the code.
- FastAPI is what the starter ships and what reviewers expect; removing it would need a reason.
- The framework stays in the outer ring (Clean Architecture), so the domain does not depend on it.

Alternatives rejected:
- FastAPI with hand-written validation on a raw dict: one place for rules, but the request schema in Swagger would be written by hand and could drift.
- Pure stdlib (`http.server` + `urllib`): no dependencies, but no Swagger, routing and JSON handling written by hand, and Python's docs warn that `http.server` is not for production. The senior engineer accepted it as the simplest code; the staff engineer rejected it on reviewer signal.
- Flask: WSGI and no strict typing. Starlette alone: keeps FastAPI's base without its routing, header parsing or OpenAPI.

## Consequences
- A mapping from Pydantic error types to A-08 codes lives in the exception handler and needs its own tests. Every rule must produce exactly our codes.
- Field validators for business rules sit in the Pydantic request model in the API adapter. Rules that the domain needs too (e.g. masking) stay in `domain`.
- The bank adapter is async; the use case that calls it is async too.
- Dependency upkeep: FastAPI, Starlette and Pydantic release often. Pin them and update deliberately.
