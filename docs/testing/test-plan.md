---
description: Test strategy per layer and traceability matrix FR/NFR -> tests.
last_verified: 2026-10-22 (implemented)
---

# Test plan
Stdlib `unittest` only (NFR-04). Run: `coverage run -m unittest discover -s tests -t .` then `coverage report --fail-under=90` (branch coverage). Test names carry the requirement id, e.g. `test_fr_05_rejects_card_number_with_spaces`. Layout mirrors [architecture.md](../design/architecture.md).

| Level | Folder | Doubles | Tool |
|---|---|---|---|
| Domain (unit) | `tests/domain/` | none | `TestCase` |
| Application (unit) | `tests/application/` | `InMemoryPaymentRepository`, fake `AcquiringBank` | `IsolatedAsyncioTestCase` |
| Bank adapter | `tests/infrastructure/bank/` | `httpx.MockTransport`, small injected timeout | `IsolatedAsyncioTestCase` |
| API (component) | `tests/infrastructure/api/` | fake bank via the composition root | FastAPI `TestClient` |
| End to end | `tests/e2e/` | none; bank simulator from `docker compose up`; skipped when it is not running | `TestCase` + httpx |

## Traceability matrix
All rows passing (2026-10-22): 89 unit/API tests, 98% branch coverage; 8 e2e tests against Docker. Performance: `tests/performance/load_test.py` (no target in the requirements; measured 500 requests, 20 concurrent, 0 failures, ~333 req/s, p95 79 ms on a laptop).

| Requirement | Test(s) | Level |
|---|---|---|
| FR-01 | `tests/infrastructure/api/test_payments_api.py`: valid request -> `201`, fields, mask, one bank call with `payment_id`; unknown fields ignored (A-15) | API, application |
| FR-02 | same file: bank authorized -> `201` `Authorized` | API |
| FR-03 | same file: bank declined -> `201` `Declined`, no `Location` | API |
| FR-04 | same file: invalid request -> `422` A-08 body, bank not called, nothing stored | API |
| FR-05 | `tests/domain/test_rules.py` (Luhn, ASCII digits); API: 14/19 digits, separators; API: JSON number, missing -> codes | domain, API |
| FR-06 | API: month `1`/`12` ok; `0`, `13`, `"4"`, `4.0`, `true`, `null` -> `card_expiry_month_*` | API |
| FR-07 | `tests/domain/test_rules.py` (current month valid, past, year boundary, UTC, injected clock); API: types -> `card_expiry_year_*`, `card_expired` | domain, API |
| FR-08 | API: `"jpy"` uppercased, `USD`, `"ＪＰＹ"` -> `currency_invalid` | domain, API |
| FR-09 | API: `1`, `999999999` ok; `0`, `-1`, `1000000000`, `10.5`, `100.0`, `"100"`, `true` -> `amount_*` | API |
| FR-10 | API: `"012"`, `"1234"` ok and sent unchanged; `123`, 2 or 5 chars, non-ASCII -> `cvv_*` | API |
| FR-11 | `tests/infrastructure/api/test_payments_api.py`: same fields as FR-01; unknown `id` -> `404` | API |
| FR-12 | `tests/application/test_process_payment.py`: same key -> same payment, bank not called; no key -> two payments; key after `Rejected` -> new payment | application, API |
| FR-13 | `tests/infrastructure/bank/test_client.py`: bank `503`, connection error, timeout -> domain error; API: `503` identical body, nothing stored, one call | bank, API |
| NFR-01 | API: no response contains `card_number`, `cvv` or the full number | API |
| NFR-02 | application: stored payment holds masked form only; logs checked in NFR-09 | application |
| NFR-03 | `ruff format --check`, `ruff check`, `mypy --strict` | command |
| NFR-04 | `coverage report --fail-under=90` | command |
| NFR-05 | review in `docs/review.md` | review |
| NFR-06 | bank adapter: one call, timeout constant injected; e2e: card ending `0` -> `503` | bank, e2e |
| NFR-07 | `poetry install`, `docker compose up` | command |
| NFR-08 | review of `docs/` | review |
| NFR-09 | `assertLogs` per outcome: fields present, no card number or CVV | application, bank |
