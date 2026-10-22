# 0004. Minimal idempotency with `Cko-Idempotency-Key`
- Status: accepted (user decision 2026-10-22)

## Context
A merchant that loses a response may resend a payment and charge the customer twice. Checkout.com uses an optional `Cko-Idempotency-Key` header and, in full, a body hash, `409` for a request in flight and a 72-hour expiry (Q-13, https://www.checkout.com/docs/developer-resources/api/idempotency, accessed 2026-10-22). NFR-05 requires an ADR for this extra component.

## Decision
Minimal version (FR-12, A-12): the optional header `Cko-Idempotency-Key` (internally `idempotency_key`) is stored with each `Authorized` or `Declined` payment. A repeat with the same key returns the stored payment without calling the bank. Without the header there is no protection. `Rejected` stores nothing, so a repeat is processed as a new payment.

Why: it covers the common case (a resend after a lost response) with one lookup in the repository, and it uses Checkout.com's header name.

Alternatives rejected:
- No idempotency: simplest, but a resend charges twice.
- Full Checkout.com behaviour: correct, but the concurrency, hashing and expiry it needs are not in the Brief's scope.

## Consequences
Known limits (FR-12): two concurrent requests with the same key can both reach the bank; reusing a key with a different body returns the first payment; keys never expire; a repeat after a bank failure is a new payment (FR-13). The full behaviour is a production gap for `docs/review.md`.
