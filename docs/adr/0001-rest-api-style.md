# 0001. REST API style (Richardson level 2)
- Status: accepted (user decision 2026-10-22)

## Context
The gateway exposes two operations to merchants: process a payment (FR-01..FR-10, FR-12, FR-13) and retrieve it (FR-11). The requirements already give HTTP status codes a meaning: `201` Authorized/Declined (A-09, FR-03), `422` validation Rejected (A-08), `503` bank failure (FR-13), `404` unknown id (A-10). The Brief asks for a simple design without over-engineering (NFR-05). The starter ships FastAPI, and the bank simulator is HTTP+JSON.

Terms, as used in this project:
- **HTTP API (not REST)**: HTTP is only a transport for function calls (RPC), e.g. `POST /process-payment`; the outcome travels in the body.
- **REST**: resources identified by URLs, HTTP verbs for intent, status codes for outcome. This is level 2 of the Richardson Maturity Model (Martin Fowler, "Richardson Maturity Model", 2010-03-18, https://martinfowler.com/articles/richardsonMaturityModel.html, accessed 2026-10-22: Level 0, Level 1 - Resources, Level 2 - HTTP Verbs, Level 3 - Hypermedia Controls).
- **RESTful (strict)**: REST plus hypermedia controls (HATEOAS, level 3). Roy Fielding, "REST APIs must be hypertext-driven", 2008-10-20, https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven, accessed 2026-10-22: "...is not being driven by hypertext, then it cannot be RESTful and cannot be a REST API. Period."

Checkout.com: retrieval is `GET` on `/payments/{id}`, and the example responses carry `_links` with `self`, `actions` and, in one example, `refund` (Checkout.com Docs, "Get payment details", https://www.checkout.com/docs/payments/manage-payments/get-payment-details, accessed 2026-10-22).

## Decision
Use REST at Richardson level 2: `payments` is the resource, created with `POST` and read with `GET` by `id`, JSON bodies, and the outcome carried by the status codes above. No hypermedia (`_links`) in responses. Exact paths, versioning and headers are defined in `docs/design/api.md`.

Why:
- It is the only style that keeps every decided status code (A-08, A-09, A-10, FR-13) without reopening requirements.
- It matches the shape of Checkout.com's API, so merchants meet familiar conventions.
- It is the smallest option: FastAPI maps routes, verbs and status codes directly, and tests assert status code and body only.
- Hypermedia pays off when a client must discover follow-up actions. Checkout.com's `_links` point to `actions` and `refund`, but capture, void and refund are out of scope (Brief: process and retrieve only), so a lone `_links.self` would add a host-dependent field that no FR needs.

Alternatives rejected:
- HTTP API (RPC): the outcome moves into the body, `GET` is no longer safe or cacheable, and A-08, A-09, A-10 and FR-13 would have to change.
- RESTful (level 3): `_links` with no follow-up action to link to; over-engineering under NFR-05.

## Consequences
- By Fielding's definition this API is not strictly RESTful. The docs call it "REST (Richardson level 2)" so the label stays accurate.
- Clients build URLs themselves (`/payments/{id}`) instead of following links.
- When capture, void or refund enter scope, adding `_links` (level 3) is an additive, non-breaking change; that is the growth path.
- `GET` is safe and idempotent by HTTP semantics. `POST` is not, which is why repeat protection is the `Cko-Idempotency-Key` header (FR-12, A-12).
