# Payment Gateway (Python)

A small API that lets a merchant process a card payment through an acquiring bank and retrieve it later.
The bank is the provided simulator (Mountebank). Built with Python 3.13, FastAPI, Pydantic and httpx.

## Quick start

**Prerequisites**
- Docker Desktop, or Docker Engine with Compose v2. This is all you need to run the service.
- Python 3.13 and Poetry 2.x, only to run the tests on your machine.

**Start** the gateway and the bank simulator:
```bash
docker compose up --build -d gateway bank_simulator
```
- Gateway: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Bank simulator: port 8080

**Try it** (bash or zsh):
```bash
curl -s -X POST localhost:8000/payments -H 'Content-Type: application/json' -d '{"card_number":"4111111111111111","expiry_month":12,"expiry_year":2030,"currency":"BRL","amount":1050,"cvv":"123"}'
```
You get `201` with `"status":"Authorized"`, `"masked_card_number":"************1111"` and an `id`.
Fetch the payment with that id:
```bash
curl -s localhost:8000/payments/<id>
```
On Windows, the simplest way is Swagger UI: open http://localhost:8000/docs, choose an endpoint, click "Try it out", and paste the JSON body above.

The bank simulator decides by the last digit of the card number:

| Last digit | Result | Example card (passes Luhn) |
|---|---|---|
| 1, 3, 5, 7, 9 | `201` Authorized | `4111111111111111` |
| 2, 4, 6, 8 | `201` Declined | `4242424242424242` |
| 0 | bank returns 503, gateway returns `503` Rejected | `4000000000000010` |

**Stop**:
```bash
docker compose down
```

## Run the tests
Install the dev tools once (Python 3.13 + Poetry 2.x): `poetry install`. Then pick one:

**1. Unit and API tests** (no Docker needed; bank faked with mocks): 89 tests, 98% branch coverage
```bash
poetry run coverage run -m unittest discover -s tests -t .
poetry run coverage report
```
The e2e tests are found too, but they skip themselves when the gateway is not running.

**2. End-to-end tests** (real gateway + bank simulator; start Docker first): 8 tests
```bash
docker compose up --build -d gateway bank_simulator
poetry run python -m unittest discover -s tests/e2e -t . -v
```

**3. Performance test** (load script; start Docker first): prints throughput and p50/p95/p99 latency
```bash
poetry run python -m tests.performance.load_test --requests 500 --concurrency 20
```
Both 2 and 3 target http://localhost:8000; set `GATEWAY_URL` to point them elsewhere.

**Lint and type checks**
```bash
poetry run ruff format --check . && poetry run ruff check . && poetry run mypy payment_gateway_api tests main.py
```

With `make`, the same steps run inside Docker (no local Python): `make up`, `make test`, `make e2e`, `make perf`, `make lint`, `make down`.

**Run without Docker for the gateway** (hot reload; the bank simulator still runs in Docker):
```bash
docker compose up -d bank_simulator
poetry run python main.py        # gateway on http://localhost:8000, Swagger at /docs
```

## What the API does

| Request | Responses |
|---|---|
| `POST /payments` | `201` Authorized or Declined; `422` Rejected (invalid request); `503` Rejected (bank unavailable) |
| `GET /payments/{id}` | `200` with the payment; `404` if not found |

- Accepted currencies: `JPY`, `BRL`, `KWD`. `amount` is an integer in minor units (`1050` BRL = 10.50).
- A `422` body looks like `{"status":"Rejected","error_type":"request_invalid","error_codes":[...]}`. A `503` uses `error_type` `service_unavailable`.
- Optional header `Cko-Idempotency-Key`: a repeat with the same key returns the stored payment without calling the bank again.

## Project layout

```
payment_gateway_api/
  domain/          entities and rules (Luhn, masking, expiry, currencies); stdlib only
  application/     use cases and the interfaces they need (bank, repository)
  infrastructure/
    api/           FastAPI routes, request/response models, error handlers
    bank/          httpx client for the bank simulator
    persistence/   in-memory repository
  main.py          composition root: create_app()
tests/             unit tests mirroring the package, plus e2e/ and performance/
docs/              requirements, design, decisions, test plan, review
```

## Design decisions

- Clean Architecture in three layers; the domain has no framework imports. See [ADR 0003](docs/adr/0003-clean-architecture.md) and [architecture](docs/design/architecture.md).
- Invalid requests get `422` Rejected with Checkout.com-style error codes, and the bank is not called. See [API design](docs/design/api.md).
- One bank call per payment, no retry, 10 s timeout. Any bank failure returns `503` and nothing is stored. See [ADR 0005](docs/adr/0005-single-bank-call.md).
- Only the masked card number is stored and returned. The full number and CVV are never stored or logged.
- Payments live in memory, so they are lost on restart. See [ADR 0006](docs/adr/0006-in-memory-repository.md) and the production gaps in [review](docs/review.md).

## Documentation

Start at [docs/README.md](docs/README.md). It indexes the requirements and assumptions, design, ADRs, test plan and review.
