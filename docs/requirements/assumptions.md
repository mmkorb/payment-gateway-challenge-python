---
description: Assumptions, out-of-scope items and open questions that block or shape the requirements.
last_verified: 2026-10-22 (9ffcd48)
---

# Assumptions

"Brief" and "user decision" as in [functional.md](functional.md). Checkout.com Docs pages cited below were all accessed 2026-10-22.

## Assumptions
- A-01: the bank simulator contract in Brief §Calling the simulator (`POST /payments`, `expiry_date` as `MM/YYYY`, reply `authorized` + `authorization_code`) is the only acquirer contract — impact if wrong: the bank adapter changes.
- A-02: a `Rejected` request creates no stored payment (Brief: "No payment could be created") — impact if wrong: FR-04 and FR-11 change.
- A-03: one process holds all payments; data is lost on restart (Brief: test double repository is fine) — impact if wrong: a real storage engine is needed.
- A-04: removed 2026-10-22 — card numbers are validated literally, separators are `Rejected` (FR-05).
- A-05: payments are processed now, so each currency uses its current ISO 4217 definition, ignoring historical subunits (e.g. JPY sen): ISO 4217 List One, SIX Group, published 2026-09-17, retrieved 2026-10-22, https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml (`JPY` 392 → 0, `BRL` 986 → 2, `KWD` 414 → 3 decimals). The 3 codes and minor units are a constant in the code, not a data file (user decision 2026-10-22) — impact if wrong: amounts get the wrong number of decimals; when ISO publishes a minor-unit change, update the constant and both dates.
- A-06: request bodies are UTF-8 JSON (RFC 8259 §8.1) and every validated text field accepts ASCII only: card number and CVV use ASCII `0`-`9` (fullwidth `４` or Arabic-Indic `٤` are `Rejected`); ISO 4217 alphabetic codes are always 3 Latin letters `A`-`Z`, so symbols (`¥`, `R$`, `د.ك`) are `Rejected` (user decision 2026-10-22) — impact if wrong: a value that looks valid to a person is `Rejected`.
- A-07: an amount must be greater than zero and contain no decimals, so `0`, negatives and decimals are `Rejected`; a 0-amount card verification (`Card Verified` status) is a separate flow, out of scope — source: "Format the amount value" (FR-09) and "Verify a card" (https://www.checkout.com/docs/payments/authenticate-payments/verify-a-card) — impact if wrong: FR-09 boundaries change.
- A-08: a `Rejected` request returns HTTP `422 Unprocessable Content` with body `{"status": "Rejected", "error_type": "request_invalid", "error_codes": [...]}`. Error codes, one per failing rule (user decision 2026-10-22): card number `card_number_required` / `card_number_invalid` (incl. Luhn); expiry month `card_expiry_month_required` / `card_expiry_month_invalid`; expiry year `card_expiry_year_required` / `card_expiry_year_invalid`; month + year in the past `card_expired`; currency `currency_required` / `currency_invalid` (incl. codes outside FR-08's list); amount `amount_required` / `amount_invalid`; CVV `cvv_required` / `cvv_invalid`. `_required` = missing or `null`; `_invalid` = wrong type, format or value. All names are on Checkout.com's error-codes list (https://www.checkout.com/docs/developer-resources/codes/error-codes, accessed 2026-10-22) except `amount_required` and `cvv_required`, which are ours, following its `<field>_required` pattern. `status: Rejected` comes from the Brief (§Requirements lists `Rejected` as a response type; the Brief wins when it differs from Checkout.com, user decision 2026-10-22); the rest from Checkout.com. Checkout.com's `request_id` is left out: a `Rejected` request is never sent to the bank or stored, so the id would point to nothing (user decision 2026-10-22, simplest version; Q-21) — sources: "API response codes" (https://www.checkout.com/docs/developer-resources/codes/api-response-codes: "422 – Unprocessable Content"), "Void a payment" (https://www.checkout.com/docs/payments/manage-payments/void-a-payment: example body with `request_id`, `error_type`, `error_codes`), "Error codes" (https://www.checkout.com/docs/developer-resources/codes/error-codes) — impact if wrong: the FR-04 response contract changes.
- A-09: an `Authorized` payment returns HTTP `201` with the payment resource — source: "Accept a payment using the Payments API" (https://www.checkout.com/docs/payments/accept-payments/accept-a-payment-using-the-payments-api: "If you receive a `201` response ... the authorization was successful") — impact if wrong: the FR-02 status code changes.
- A-10: an unknown payment id returns HTTP `404` (Payment not found) — source: "Get payment details" (https://www.checkout.com/docs/payments/manage-payments/get-payment-details: "If a payment matching the ID you provided was not found, you'll receive a `404 – Payment not found` error.") — impact if wrong: the FR-11 error contract changes.
- A-11: a card expires at the end of its printed month, so "month + year in the future" (Brief §Processing a payment) means `(year, month) >= (current year, current month)`; "now" is the server clock in UTC (user decision 2026-10-22, reading B of the Brief) — impact if wrong: cards in their last valid month are `Rejected`; near midnight UTC on a month's last day, a shopper in another time zone may see a few hours' difference.
- A-12: two identifiers only, named as the sources name them:
  1. payment `id` (Brief §Processing a payment: "the payment id which will be used to retrieve the payment details"): a UUID the gateway creates for every valid request before the bank call, used for retrieval, reconciliation and logs, and sent to the bank as the extra field `payment_id`; log lines also name it `payment_id` (same value as `id`; a bare `id=` is ambiguous in a log, and one search then finds the gateway and bank sides; user decision 2026-10-22) in the single bank request (FR-01, FR-13). The simulator ignores extra fields: its predicates only check that the required fields exist. The payment is stored only when `Authorized` or `Declined`; after a bank failure the `id` exists only in the bank request and the `WARNING` log line (NFR-09), for reconciliation, and `GET` by that `id` returns `404` (A-10) (user decision 2026-10-22).
  2. idempotency key: the optional HTTP header `Cko-Idempotency-Key`, created by the merchant, internally `idempotency_key` (FR-12). Source: "Idempotency" (https://www.checkout.com/docs/developer-resources/api/idempotency): you "provide" the key to make a request idempotent; the page does not make it required.

  No other ids (no transaction id, no per-call bank id): one bank call per payment means the payment `id` identifies it end to end, and the Brief asks to avoid over-engineering (user decisions 2026-10-22, simplest version; Q-21) — impact if wrong: the bank contract needs a request-id field.
- A-13: naming (user decision 2026-10-22): JSON fields `snake_case` (e.g. `card_number`, `expiry_month`), as in the bank simulator contract and Checkout.com's API; HTTP headers `Hyphenated-Pascal-Case` (e.g. `Cko-Idempotency-Key`), matched case-insensitively (RFC 9110 §5.1); Python per PEP 8 (`snake_case` modules, functions, variables; `PascalCase` classes; `UPPER_SNAKE_CASE` constants); statuses exactly as the Brief writes them: `Authorized`, `Declined`, `Rejected` — impact if wrong: inconsistent contract names.
- A-14: data classification (user decision 2026-10-22, Q-16):
  - full card number (PAN): sensitive cardholder data; CVV: sensitive authentication data (PCI DSS: never stored after authorization, even encrypted). Both stay in memory only for the single bank call; never stored, logged or returned. Only the masked card number (FR-01) is stored and returned.
  - expiry month and year: cardholder data, low risk without the PAN; stored and returned (Brief).
  - currency, amount, status, payment `id`, `Cko-Idempotency-Key`: not sensitive; may be stored and logged (the key is stored for FR-12).

  Impact if wrong: storage, logs and responses must be re-checked.
- A-15: unknown fields in the request body are ignored: never validated, stored, logged, returned or forwarded to the bank; only the six fields of FR-05..FR-10 are read. A typo in a required field name is still `Rejected` as missing, because no field is optional (user decision 2026-10-22, Q-22). Brief: silent (§Processing a payment lists only required fields). Checkout.com: not verified whether its API ignores or rejects unknown fields; `invalid_option` ("you included a field in your request that is not a valid option", https://www.checkout.com/docs/developer-resources/codes/error-codes) refers to an invalid option, not clearly an unknown field; its payment request examples carry merchant data in a dedicated `metadata` object (https://www.checkout.com/docs/payments/accept-payments/accept-a-payment-using-the-payments-api), the production path if merchants need extra data — impact if wrong: unknown fields become `Rejected` (one parser setting plus an error code).
- A-16: a bank failure (FR-13) is also reported as `Rejected`, although the Brief defines `Rejected` as a payment refused "without calling the acquiring bank" (§Requirements). Reason: no payment was created and the Brief defines no other status. The two cases are told apart by HTTP code and `error_type`: `422` + `request_invalid` (bank not called, A-08) vs `503` + `service_unavailable` (bank called once and failed, FR-13). Deliberate deviation from the Brief (user decision 2026-10-22).

## Out of scope
- Real database — Brief §Payment Storage allows an in-memory repository.
- Capture, void, refund, settlement, 3-D Secure — the Brief lists only process and retrieve for this phase.
- Real acquiring bank — Brief: the acquirer is simulated.
- 0-amount card verification (`Card Verified`) — a separate Checkout.com flow (A-07).
- Merchant authentication and scoping — the Brief asks only to process and retrieve and warns against over-engineering, so there is no authentication and no merchant concept: anyone who knows a payment `id` can retrieve it (the `id` is a random UUID, the card number is masked, FR-11). Production: each merchant authenticates with its own secret key (Checkout.com uses `Authorization: Bearer <secret key>`, not verified on the page) and can retrieve only its own payments (user decision 2026-10-22, Q-12).
- Per-merchant currency enablement — one global list of 3 codes (FR-08) meets the Brief; no merchant concept yet (user decision 2026-10-22).

## Open questions
Owner: candidate (decision), unless marked recruiter. All resolved or removed on 2026-10-22; the decision lives where each line points.
- Q-01: which 3 ISO 4217 codes, case-sensitive? — resolved: FR-08.
- Q-02: card number and CVV as strings or numbers? — resolved: strings (FR-05, FR-10).
- Q-03: amount `0`, negative, maximum, `"100"` / `100.0`? — resolved: FR-09, A-07.
- Q-04: is the current month a valid expiry; which clock defines "now"? — resolved: A-11.
- Q-05: Luhn check required? — resolved: yes, always on (FR-05).
- Q-06: how is `Rejected` returned? — resolved: A-08.
- Q-07: HTTP code for a processed payment? — resolved: `201` for both, no `Location` header (FR-02, FR-03).
- Q-08: what does the merchant receive when the bank fails? — resolved: FR-13.
- Q-09: retry strategy for the bank call? — resolved: no retry, one bank request per payment (FR-13; timeout: NFR-06). Research kept for the interview: Checkout.com recommends exponential backoff with jitter only for `429` and says payment retries are safe only with an idempotency key (https://www.checkout.com/docs/developer-resources/api/api-rate-limits, https://www.checkout.com/docs/developer-resources/api/idempotency); a retry after a read timeout risks a double charge.
- Q-10: response for an unknown payment id? — resolved: A-10.
- Q-11: payment id format? — resolved: UUID (FR-01).
- Q-12: merchant authentication / retrieval scoping in scope? — resolved: no (Out of scope).
- Q-13: idempotency key on process in scope? — resolved: minimal version (FR-12); full Checkout.com behaviour (body hash, `409` in flight, 72-hour expiry; https://www.checkout.com/docs/developer-resources/api/idempotency) is a production gap.
- Q-14: minimum test coverage? — resolved: NFR-04.
- Q-15: logging / observability requirement? — resolved: NFR-09.
- Q-16: confirm data classification? — resolved: A-14.
- Q-17: string formats for expiry month? — removed: month is an integer (FR-06).
- Q-18: formats for expiry year? — resolved: four-digit integer (FR-07).
- Q-19: who can disable the Luhn check? — removed: always on (FR-05).
- Q-20: masked card number format? — resolved: FR-01.
- Q-21: is `Cko-Idempotency-Key` required; does the `Rejected` body keep `request_id`; is a separate transaction id needed? — resolved: optional key, no `request_id`, no other id (A-08, A-12).
- Q-22: unknown request fields ignored or `Rejected`? — resolved: ignored (A-15).
