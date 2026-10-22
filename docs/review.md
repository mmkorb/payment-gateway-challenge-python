---
description: Trade-offs taken for the take-home and the gaps a production gateway would close.
last_verified: 2026-10-22 (no git history)
---

# Review

## Trade-offs
| Decision | Gain | Cost | ADR |
|---|---|---|---|
| REST level 2, no hypermedia | Smallest contract; matches Checkout.com's shape | Clients build URLs themselves | [0001](adr/0001-rest-api-style.md) |
| FastAPI + Pydantic strict | One model gives types, validation and Swagger (`/docs`) | Pydantic errors are mapped to A-08 codes by hand | [0002](adr/0002-fastapi-pydantic-httpx.md) |
| Clean Architecture, three rings | Core testable without frameworks; bank and storage replaceable | Manual mapping between API models and domain | [0003](adr/0003-clean-architecture.md) |
| Minimal idempotency | Resends after a lost response do not charge twice | No body hash, no in-flight lock, no expiry | [0004](adr/0004-minimal-idempotency.md) |
| One bank call, no retry, 10 s total | Predictable; no retry-induced double charge | A transient bank error is final; the merchant resubmits | [0005](adr/0005-single-bank-call.md) |
| In-memory repository | Nothing to install | Data lost on restart; one process only | [0006](adr/0006-in-memory-repository.md) |
| Bank failure reported as `Rejected` (A-16) | No new status beyond the Brief's three | Deviates from the Brief's "without calling the bank" | — |

## Production gaps
| Gap | Risk | Suggested next step |
|---|---|---|
| No merchant authentication or scoping | Any caller can create or read any payment | Per-merchant secret key (`Authorization: Bearer`), payments scoped to the owning merchant |
| Timeout vs bank authorization | Gateway reports `Rejected` while the bank authorized; a resubmission can charge twice | Store the attempt before the bank call; status query or void by `payment_id`; reconciliation job |
| Idempotency is minimal | Concurrent duplicates reach the bank; a reused key with another body returns the first payment | Body hash, `409` while in flight, 72-hour key expiry (Checkout.com behaviour) |
| In-memory storage | Data loss, no horizontal scaling | Database behind `PaymentRepository` with a unique index on `idempotency_key` |
| Plain-text logs, no metrics | Hard to search and alert | JSON logs, request id, metrics for bank latency and failure rate |
| No rate limiting | One merchant can exhaust the gateway or the bank | Per-merchant limits returning `429` |
| HTTP only, no TLS in the container | Card data in clear on the network | TLS termination at the edge; PCI DSS scope review |
| `request_body_invalid` code (body not a JSON object) | Name chosen during implementation, not from Checkout.com's list | Confirm or replace with a listed code |
