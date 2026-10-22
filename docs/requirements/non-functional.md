---
description: Non-functional requirements (NFR-xx) with ISO 25010 category, measurable target, verification and source.
last_verified: 2026-10-22 (9ffcd48)
---

# Non-functional requirements

- "Brief" and "user decision" as in [functional.md](functional.md).
- Verified 2026-10-22: 89 unit/API tests pass with 98% branch coverage; `ruff format --check`, `ruff check`, `mypy --strict` clean; `docker compose up` runs gateway and simulator; 8 e2e tests pass; no card number or CVV in the gateway logs. NFR-05 and NFR-08: [review.md](../review.md).

### NFR-01 Card data never leaves in responses
- Category: security
- Target: no API response contains a full card number or a CVV; the card number is returned masked (FR-01).
- Verified by: tests on the response bodies of FR-01 and FR-11.
- Source: Brief §Processing a payment ("cannot return a full card number as this is a serious compliance risk"), §Retrieving a payment's details ("masked card number"); user decision 2026-10-22 (last four only, never the first six).

### NFR-02 Card data never stored or logged
- Category: security
- Target: the full card number and the CVV are absent from stored payments, logs and error messages; only the masked card number is stored (A-14).
- Verified by: tests on the stored payment and on captured log output.
- Source: Brief compliance note (§Processing a payment); A-14 (Q-16).

### NFR-03 Code passes static checks
- Category: maintainability
- Target: `ruff format --check`, `ruff check` and `mypy --strict` report zero errors.
- Verified by: those three commands.
- Source: Brief §Implementation considerations ("Code must compile"); user decision 2026-10-21 (Ruff only, mypy strict).

### NFR-04 Automated tests
- Category: maintainability
- Target: every FR has at least one passing test named with its id; stdlib `unittest`; total coverage ≥ 90% with branch coverage (`coverage.py`, `branch = true`).
- Verified by: `coverage run -m unittest`, then `coverage report --fail-under=90`; traceability matrix in `docs/testing/test-plan.md`.
- Source: Brief §Implementation considerations ("covered by automated tests"); user decisions 2026-10-20 (unittest, no pytest) and 2026-10-22 (90% branch coverage, Q-14).

### NFR-05 Simple design
- Category: maintainability
- Target: only the components FR-01..FR-13 need; each extra component (idempotency) has an ADR; authentication is out of scope (Q-12).
- Verified by: review step in `docs/review.md`.
- Source: Brief §Implementation considerations ("simple and maintainable ... do not want to encourage over-engineering").

### NFR-06 Bank failures handled
- Category: reliability
- Target: on a bank error or timeout the gateway behaves as FR-13 (one call, HTTP `503` + `Rejected`, no crash). Total timeout: 10 seconds per bank call, a constant in the bank adapter; tests inject a much smaller value.
- Verified by: integration test against a fake bank and one run against the simulator.
- Source: Brief §Bank simulator; user decision 2026-10-22 (single request, no retry, 10-second timeout; Q-09).

### NFR-07 Runtime and packaging
- Category: portability
- Target: Python 3.13.x (`requires-python = ">=3.13,<3.14"`) on the host and in Docker (`python:3.13-slim`); dependencies managed by Poetry 2.5.1 and locked in `poetry.lock`. Locked versions (2026-10-22): runtime fastapi 0.161.0 (starlette 1.6.0), pydantic 2.14.1 (pydantic-core 2.50.1), uvicorn 0.54.0, httpx 0.28.1; dev ruff 0.17.2, mypy 2.4.0, coverage 7.17.0. Gateway and bank simulator start with Docker Compose.
- Why 3.13: the host already has Python 3.13.9, so unit and API tests, lint and type checks run locally before `docker compose up`, and the same version runs in the container. Every library above supports 3.13 (PyPI `requires-python`, checked 2026-10-22).
- Verified by: `poetry install` and `make test` locally; `docker compose up` (not runnable yet).
- Source: user decisions 2026-10-20 (Poetry, Docker; no uv) and 2026-10-22 (Python 3.13, replacing 3.14, so tests run before Docker is up); Brief §Starting the simulator.

### NFR-08 Design and assumptions documented
- Category: maintainability
- Target: key design decisions are in `docs/adr/`, assumptions in [assumptions.md](assumptions.md).
- Verified by: review of `docs/` before submission.
- Source: Brief §Documentation.

### NFR-09 One log line per outcome
- Category: maintainability (analysability)
- Target: stdlib `logging`, plain `key=value` text, no extra library:
  - one `INFO` per processed payment: `payment_id`, `status`, `currency`, `amount`, bank call duration;
  - one `WARNING` per bank failure: `payment_id` and the internal cause (`timeout`, `connection`, `bank_503`), which never reaches the merchant (FR-13);
  - one `INFO` per validation `Rejected`: its error codes only, never the submitted values;
  - no line contains the full card number or the CVV (NFR-02).
- Verified by: `unittest` `assertLogs` tests per outcome, asserting the fields above and the absence of card number and CVV.
- Source: user decision 2026-10-22 (Q-15); payment `id` as log id: A-12. Structured JSON logs, request ids and metrics are a production gap.
