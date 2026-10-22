---
description: Functional requirements (FR-xx) of the payment gateway, with Given/When/Then acceptance criteria and source.
last_verified: 2026-10-22 (9ffcd48)
---

# Functional requirements

- "Brief" = the Checkout.com assessment README (https://github.com/cko-recruitment); `§` names its section. "User decision" = decision taken by the candidate in the planning sessions.
- Status of every FR: implemented and tested (2026-10-22): unit and API tests under `tests/`, e2e against the bank simulator in `tests/e2e/`. Traceability: [test-plan.md](../testing/test-plan.md).
- A-xx, Q-xx and out of scope: [assumptions.md](assumptions.md).

## Process a payment

### FR-01 Process a valid payment
- Description: the system shall accept a payment request from a merchant, send it to the acquiring bank and return the result.
- Acceptance criteria:
  - Given a request passing FR-05..FR-10, when submitted, then the gateway creates the payment `id` (a UUID), calls the bank exactly once with that id as the extra field `payment_id` (A-12), and the response contains `id`, `status`, masked card number, expiry month, expiry year, currency and amount.
  - Masked card number: every digit `*` except the last four, original length kept: `4111111111111111` → `"************1111"`; one string, never the first six / `bin`. The same masked form is stored and returned by FR-11.
  - Given a processed payment, when the response is returned, then it never contains the full card number or the CVV (NFR-01).
  - Given a valid request with an unknown field (e.g. `"reference": "order-42"` or `"cvc": "123"`), when submitted, then it is processed normally and the unknown field appears in no response, bank request, stored payment or log line (A-15).
  - Given an unknown field and an invalid known field, when submitted, then the request is `Rejected` and `error_codes` lists only the known field's code (A-15).
- Source: Brief §Requirements, §Processing a payment ("Feel free to choose whatever format ... e.g. a GUID is fine"). UUID chosen; Checkout.com's `pay_` + 26 characters not adopted (Q-11). Mask format: Q-20.

### FR-02 Authorized payment
- Description: the system shall return status `Authorized` when the bank authorizes the payment.
- Acceptance criteria:
  - Given a valid request, when the bank answers authorized, then the response is HTTP `201` with status `Authorized` (A-09).
- Source: Brief §Requirements.

### FR-03 Declined payment
- Description: the system shall return status `Declined` when the bank declines the payment.
- Acceptance criteria:
  - Given a valid request, when the bank answers not authorized, then the response is HTTP `201` with status `Declined`. No `Location` header (FR-02 included).
- Source: Brief §Requirements; §Processing a payment gives `Authorized` and `Declined` the same response ("Responses for payments that were successfully sent to the acquiring bank"), hence the same `201` (user decision 2026-10-22, Q-07).

### FR-04 Rejected payment
- Description: the system shall reject a request with invalid information without calling the bank.
- Acceptance criteria:
  - Given a request failing any rule in FR-05..FR-10, when submitted, then the response is HTTP `422` with the A-08 body and the bank is not called.
  - Given a rejected request, when the merchant later looks for it, then no payment exists for it (A-02).
- Source: Brief §Requirements ("No payment could be created ... without calling the acquiring bank").

## Request validation

Every failure below means `Rejected` (FR-04). Text fields accept ASCII only (A-06).

### FR-05 Card number
- Description: the card number shall be a required JSON string of 14-19 ASCII digits `0`-`9`, validated exactly as received (no separators removed, no trimming), and passing the Luhn check.
- Acceptance criteria:
  - Given 14 or 19 digits, when submitted, then accepted.
  - Given separators (`"4111 1111 1111 1111"`, `"4111-1111-1111-1111"`) or surrounding spaces, when submitted, then `Rejected`.
  - Given a missing value, a JSON number (`4111111111111111`), 13 or 20 digits, or any character other than ASCII `0`-`9` (including non-ASCII digits), when submitted, then `Rejected`.
  - Given a Luhn failure (`4111111111111112`), when submitted, then `Rejected`. The check is always on; nothing can disable it.
- Source: Brief §Processing a payment; user decision 2026-10-22 (string, literal validation, Luhn always on). Why: a card number is an identifier, not a quantity: JSON numbers are interoperable only up to 2^53-1 (16 digits, RFC 8259 §6) and cannot carry leading zeros, and the bank contract already sends a string. The Brief gives a validation rule, not a cleanup rule, so formatting belongs to the merchant's UI (as FR-10 never alters the CVV). The last digit is the Luhn check digit.

### FR-06 Expiry month
- Description: the expiry month shall be a required JSON integer from 1 to 12.
- Acceptance criteria:
  - Given `1` or `12`, when submitted, then accepted.
  - Given missing or `null`, `0`, `13`, `-1`, a string (`"4"`), a decimal (`4.0`) or a boolean (`true`), when submitted, then `Rejected`.
- Source: Brief §Processing a payment ("Value must be between 1-12"); user decision 2026-10-22 (integer, strict type).

### FR-07 Expiry date in the future
- Description: the expiry year shall be a required four-digit JSON integer, and expiry month + year shall be in the future (A-11).
- Acceptance criteria:
  - Given `2027`, when submitted, then accepted as the year.
  - Given missing or `null`, a two-digit year (`27`), a string (`"2027"`), a decimal (`2027.0`) or a boolean, when submitted, then `Rejected`.
  - Given a month + year before the current month, when submitted, then `Rejected`.
  - Given the current month and year (`10` / `2026` on 2026-10-31), when submitted, then accepted: a card expires at the end of its printed month.
  - Given December of the current year and January of the next year, when submitted, then both follow the same month + year comparison across the year boundary.
- Source: Brief §Processing a payment; user decision 2026-10-22 (four-digit integer, strict; wider formats can be added later without breaking merchants). Current month and UTC clock: A-11.

### FR-08 Currency
- Description: the currency shall be a required 3-character JSON string, one of `JPY` (0 decimals), `BRL` (2), `KWD` (3) (A-05).
- Acceptance criteria:
  - Given `JPY`, `BRL` or `KWD`, when submitted, then accepted.
  - Given `"jpy"` or `"Brl"`, when submitted, then it is uppercased and accepted; the uppercase code is sent to the bank, stored and returned.
  - Given a currency with any non-ASCII character (e.g. fullwidth `"ＪＰＹ"`), when submitted, then `Rejected` with `currency_invalid`: the value is checked for ASCII letters `A`-`Z`/`a`-`z` before uppercasing, because `str.upper()` maps some non-ASCII letters to ASCII (e.g. `ı` to `I`) (A-06; user decision 2026-10-22).
  - Given a missing currency, a length other than 3, a symbol (`¥`), or an ISO 4217 code outside the list (`USD`, `GBP`: the Brief's example codes), when submitted, then `Rejected` (A-06).
- Source: Brief §Processing a payment ("no more than 3 currency codes"); user decision 2026-10-22 (one currency per minor-unit size 0, 2, 3; any letter case, compared in uppercase).
- References: minor units: A-05. Brief's reference site: https://www.xe.com/currency/jpy-japanese-yen/, https://www.xe.com/currency/brl-brazilian-real/, https://www.xe.com/currency/kwd-kuwaiti-dinar/. xe lists JPY's historical subunit (1/100 sen); the gateway follows ISO 4217's 0 decimals.

### FR-09 Amount
- Description: the amount shall be a required JSON integer in the currency's minor unit, from `1` to `999999999` (nine digits), the same for every currency.
- Acceptance criteria:
  - Given `1050` with `JPY`, `BRL` or `KWD`, when submitted, then accepted and sent to the bank unchanged; it means ¥1050, R$10.50 or KWD 1.050 (FR-08).
  - Given `1` or `999999999`, when submitted, then accepted.
  - Given `1000000000`, when submitted, then `Rejected`.
  - Given `0`, a negative (`-1`) or a decimal (`10.5`, or `100.0`: a JSON integer only, as in FR-06/FR-07), when submitted, then `Rejected` (A-07).
  - Given a missing amount, a string (`"100"`) or a boolean (`true`), when submitted, then `Rejected` (Brief: "Must be an integer").
- Source: Brief §Processing a payment ("Must be an integer"); user decision 2026-10-22 (JSON integer; nine-digit maximum from Checkout.com's API contract). The maximum is a technical API limit, not a risk or credit rule: business limits belong to the acquiring bank.
- References: Checkout.com Docs, "Format the amount value", accessed 2026-10-22, https://www.checkout.com/docs/payments/accept-payments/format-the-payment-amount ("the `amount` value must: Be greater than zero; Not contain decimals; Not contain more than nine digits").

### FR-10 CVV
- Description: the CVV shall be a required JSON string of 3-4 ASCII digits, used exactly as received (never padded, trimmed or changed).
- Acceptance criteria:
  - Given `"012"`, `"123"` or `"1234"`, when submitted, then accepted and sent to the bank unchanged.
  - Given a missing CVV, a JSON number (`123`), 2 or 5 characters, or any character other than ASCII `0`-`9` (including spaces and non-ASCII digits), when submitted, then `Rejected`.
- Source: Brief §Processing a payment; user decision 2026-10-22 (string because leading zeros are significant; the gateway never fills or alters it).

### FR-12 Repeated request returns the original result (minimal idempotency)
- Description: when the merchant repeats a payment request with the same optional `Cko-Idempotency-Key` header (internally `idempotency_key`, A-12), the system shall return the stored result of the first request without calling the bank again.
- Acceptance criteria:
  - Given two identical requests without the header, when both are submitted, then the bank is called twice and two payments with different `id`s are created (the merchant must send the key on retries).
  - Given a payment processed as `Authorized` or `Declined` with key `K`, when a request with key `K` is sent again, then the response is the same payment (same `id`, `status`, body) and the bank is not called.
  - Given a request with key `K` that ended `Rejected` (validation, FR-04, or bank failure, FR-13), when a request with key `K` is sent again, then it is processed as a new payment (nothing is stored for `Rejected`, A-02): validated again and, if valid, sent to the bank with a new `payment_id`. The merchant should send a new key after a `Rejected`.
- Known limits (accepted, minimal version): two concurrent requests with the same key can both reach the bank; reusing a key with a different body returns the first payment; keys never expire. Production adds a body hash, `409` for a request in flight and a 72-hour expiry (Q-13).
- Source: user decision 2026-10-22 (minimal version in scope; Q-21).

### FR-13 Bank failure
- Description: when the single bank call fails, the system shall cancel the payment and return `Rejected` with an error. The `Rejected` is final: the gateway never retries; the merchant must submit a new payment request, which gets a new `payment_id` (FR-12).
- Acceptance criteria:
  - Given a valid request, when the bank answers `503` (simulator: card number ending in `0`), the connection fails, or no answer arrives within the total timeout (NFR-06), then the bank was called exactly once (no retry), the response is HTTP `503` with body `{"status": "Rejected", "error_type": "service_unavailable", "error_codes": ["service_unavailable"]}` (A-08 shape), and no payment is stored (A-02).
  - Given any of these failures, when the response is returned, then the body is identical for all: it reveals no cause (timeout, connection, bank status), bank reply or internal detail.
  - Given a bank failure, when the response is returned, then it never reports `Authorized` or `Declined`.
- Known limits (accepted; the implementation stays simple and adds nothing for them):
  - After a timeout the bank may have authorized while the gateway reports `Rejected`; there is no void or status query to the bank (Brief scope: process and retrieve only). The `payment_id` sent to the bank lets both sides be matched later.
  - Double charge: if that first payment was authorized and the merchant then submits the new payment, the customer can be charged twice. Detection is manual reconciliation by `payment_id`; the production fix is listed in `docs/review.md`.
- Source: user decision 2026-10-22 (single request, no retry, timeout cancels the payment; `503` with the A-08 shape, no unnecessary information). Why `Rejected` despite the Brief's definition: A-16. Why no retry: Q-09. The `service_unavailable` names are a candidate choice, not from Checkout.com's error code list (Q-08).

## Retrieve a payment

### FR-11 Retrieve a previous payment
- Description: the system shall return the details of a previously processed payment by its `id`.
- Acceptance criteria:
  - Given a payment processed as `Authorized` or `Declined`, when the merchant requests it by `id`, then the response contains the same fields and values as FR-01 (masked card number included).
  - Given a retrieved payment, when the response is returned, then it never contains the full card number or the CVV (NFR-01).
  - Given an `id` with no stored payment, when requested, then the response is HTTP `404` (A-10).
- Source: Brief §Retrieving a payment's details.
