---
description: HTTP contract of the payment gateway - routes, status codes, headers and error bodies.
last_verified: 2026-10-22 (implemented)
---

# API
REST at Richardson level 2, no hypermedia ([ADR 0001](../adr/0001-rest-api-style.md)). No version prefix, as in Checkout.com's API (`https://{prefix}.api.checkout.com/payments/{id}`, "Get payment details", https://www.checkout.com/docs/payments/manage-payments/get-payment-details, accessed 2026-10-22; user decision 2026-10-22). JSON bodies, UTF-8 (A-06), `snake_case` fields (A-13).

| Method + route | Request | Success | Errors | Requirement |
|---|---|---|---|---|
| `POST /payments` | payment request; optional header `Cko-Idempotency-Key` (FR-12) | `201` payment, status `Authorized` or `Declined`; no `Location` header (Q-07) | `422` validation `Rejected` (A-08); `503` bank failure `Rejected` (FR-13) | FR-01..FR-10, FR-12, FR-13 |
| `GET /payments/{id}` | `id`: payment UUID (A-12) | `200` payment | `404` unknown `id` (A-10) | FR-11 |

Fields (user decision 2026-10-22):
- Request: `card_number`, `expiry_month`, `expiry_year`, `currency`, `amount`, `cvv` (types and rules FR-05..FR-10; unknown fields ignored, A-15).
- Payment response (`201` and `200`): `id`, `status`, `masked_card_number`, `expiry_month`, `expiry_year`, `currency`, `amount`. `masked_card_number` keeps the last four digits visible and replaces every other digit with `*`, same length (e.g. `"************1111"`, FR-01). Never a field named `card_number` or `cvv` in a response (NFR-01); the name says the value is masked, so no reader mistakes it for the full card number.

Error bodies: `422` and `503` share the shape `{"status": "Rejected", "error_type": ..., "error_codes": [...]}`; values in A-08 and FR-13.
