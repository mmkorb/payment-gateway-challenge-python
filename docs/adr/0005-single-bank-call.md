# 0005. Single bank call, no retry, 10-second total timeout
- Status: accepted (user decision 2026-10-22)

## Context
The bank simulator returns `503` for cards ending in `0` (Brief §Bank simulator), and a real bank can be slow or unreachable. Retrying a payment is safe only with an idempotency key at the bank (Checkout.com, https://www.checkout.com/docs/developer-resources/api/idempotency; backoff only for `429`, https://www.checkout.com/docs/developer-resources/api/api-rate-limits; both accessed 2026-10-22, Q-09). The simulator offers no such key.

## Decision
Exactly one bank call per payment, carrying the gateway's `payment_id` (A-12). A 10-second total timeout, implemented as `asyncio.timeout` because httpx timeouts are per phase (ADR 0002), is kept as a constant in the bank adapter and injected smaller in tests. A timeout, connection error or bank `503` returns HTTP `503` `Rejected` with one identical body (FR-13, A-08 shape, A-16), stores nothing and is final; the merchant submits a new payment.

Why: a retry after a read timeout can charge twice; one call keeps the behaviour predictable and the code small.

Alternatives rejected:
- Retry with backoff and jitter: risks a double charge without a bank-side idempotency key.
- Circuit breaker: no value for one process and a simulator.

## Consequences
- After a timeout the bank may have authorized while the gateway reports `Rejected`; a new payment can then charge twice. Detection is manual reconciliation by `payment_id` (FR-13 known limits).
- Production gaps for `docs/review.md`: void or status query to the bank, a bank-side idempotency key, persistence of in-flight attempts.
