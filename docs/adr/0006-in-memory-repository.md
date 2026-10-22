# 0006. In-memory repository as a simulated database
- Status: accepted (user decision 2026-10-22)

## Context
The Brief does not require a real database: "You do not need to integrate with a real storage engine or database. It is fine to use the test double repository provided in the sample code to represent this." (§Note: Payment Storage) and asks for a simple design. The user wants the database treated like the bank: an external service behind an interface.

## Decision
`PaymentRepository` is an interface (`typing.Protocol`) in `application/`. `InMemoryPaymentRepository` in `infrastructure/persistence/` implements it with a dict keyed by payment `id` and a second dict from `idempotency_key` to `id`. It stores only `Authorized` and `Declined` payments with the masked card (A-02, A-14). The same class is the test fake.

Why: no database server, no migrations, nothing to install; replacing it with a real database touches only `infrastructure/persistence/` and `main.py`.

Alternatives rejected:
- SQLite or PostgreSQL: durability the Brief does not require, plus schema and container work.

## Consequences
- Data is lost on restart.
- One process only: uvicorn runs without extra workers (ADR 0002).
- Concurrency limit on the idempotency key (ADR 0004).
