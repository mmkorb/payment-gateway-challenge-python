import unittest
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from payment_gateway_api.domain.errors import BankUnavailableError
from payment_gateway_api.infrastructure.persistence.memory import InMemoryPaymentRepository
from payment_gateway_api.main import create_app

CARD = "4111111111111111"
VALID: dict[str, Any] = {
    "card_number": CARD,
    "expiry_month": 12,
    "expiry_year": 2099,
    "currency": "JPY",
    "amount": 1050,
    "cvv": "123",
}
MISSING = object()
LUHN_14 = "30569309025904"
LUHN_19 = "4111111111111111110"


def rejected(*codes: str) -> dict[str, Any]:
    return {"status": "Rejected", "error_type": "request_invalid", "error_codes": list(codes)}


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.bank = AsyncMock()
        self.bank.authorize.return_value = True
        self.client = TestClient(create_app(bank=self.bank, repository=InMemoryPaymentRepository()))

    def post(self, **changes: Any) -> Any:
        body = dict(VALID)
        for key, value in changes.items():
            if value is MISSING:
                body.pop(key)
            else:
                body[key] = value
        return self.client.post("/payments", json=body)

    def assert_rejected(self, response: Any, *codes: str) -> None:
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), rejected(*codes))
        self.bank.authorize.assert_not_called()

    def assert_field_rejections(self, field: str, values: list[Any], code: str) -> None:
        for value in values:
            with self.subTest(value=value):
                self.bank.authorize.reset_mock()
                self.assert_rejected(self.post(**{field: value}), code)


class ProcessPaymentTest(ApiTestCase):
    def test_fr_01_returns_201_with_masked_payment(self) -> None:
        response = self.post()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "id",
                "status",
                "masked_card_number",
                "expiry_month",
                "expiry_year",
                "currency",
                "amount",
            },
        )
        self.assertEqual(body["masked_card_number"], "************1111")
        self.assertEqual(
            (body["expiry_month"], body["expiry_year"], body["currency"], body["amount"]),
            (12, 2099, "JPY", 1050),
        )
        self.assertNotIn("location", response.headers)
        self.bank.authorize.assert_awaited_once()

    def test_fr_01_ignores_unknown_fields(self) -> None:
        response = self.client.post("/payments", json={**VALID, "reference": "o-42", "cvc": "1"})

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("reference", response.text)
        self.assertNotIn("cvc", response.text)

    def test_fr_01_unknown_plus_invalid_field_lists_only_known_code(self) -> None:
        response = self.client.post("/payments", json={**VALID, "reference": 1, "amount": 0})

        self.assert_rejected(response, "amount_invalid")

    def test_fr_02_authorized(self) -> None:
        response = self.post()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "Authorized")

    def test_fr_03_declined(self) -> None:
        self.bank.authorize.return_value = False

        response = self.post()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "Declined")

    def test_fr_04_invalid_request_is_422_without_bank_call(self) -> None:
        self.assert_rejected(self.post(cvv="1"), "cvv_invalid")

    def test_fr_04_several_errors_are_listed_in_order_without_duplicates(self) -> None:
        response = self.post(card_number="1", cvv=MISSING, amount=0)

        self.assert_rejected(response, "card_number_invalid", "amount_invalid", "cvv_required")

    def test_a_08_non_object_or_non_json_body(self) -> None:
        for content in ("[1]", "not json", "", "null"):
            with self.subTest(content=content):
                response = self.client.post(
                    "/payments", content=content, headers={"Content-Type": "application/json"}
                )
                self.assert_rejected(response, "request_body_invalid")


class ValidationTest(ApiTestCase):
    def test_fr_05_accepts_14_and_19_digits(self) -> None:
        for number in (LUHN_14, LUHN_19):
            with self.subTest(length=len(number)):
                self.assertEqual(self.post(card_number=number).status_code, 201)

    def test_fr_05_rejects_separators_and_spaces(self) -> None:
        self.assert_field_rejections(
            "card_number",
            ["4111 1111 1111 1111", "4111-1111-1111-1111", " 4111111111111111"],
            "card_number_invalid",
        )

    def test_fr_05_rejects_bad_shape(self) -> None:
        self.assert_field_rejections(
            "card_number",
            [
                4111111111111111,
                "4111111111119",
                "41111111111111111111",
                "\uff14\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11\uff11",
                "4111111111111112",
                "abcdefghijklmn",
                True,
                4.0,
            ],
            "card_number_invalid",
        )

    def test_fr_05_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("card_number", [MISSING, None], "card_number_required")

    def test_fr_06_accepts_1_and_12(self) -> None:
        for month in (1, 12):
            self.assertEqual(self.post(expiry_month=month).status_code, 201)

    def test_fr_06_rejects_invalid_month(self) -> None:
        self.assert_field_rejections(
            "expiry_month", [0, 13, -1, "4", 4.0, True], "card_expiry_month_invalid"
        )

    def test_fr_06_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("expiry_month", [MISSING, None], "card_expiry_month_required")

    def test_fr_07_rejects_invalid_year(self) -> None:
        self.assert_field_rejections(
            "expiry_year", [27, "2027", 2027.0, True, 10000], "card_expiry_year_invalid"
        )

    def test_fr_07_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("expiry_year", [MISSING, None], "card_expiry_year_required")

    def test_fr_07_rejects_past_year(self) -> None:
        self.assert_rejected(self.post(expiry_month=1, expiry_year=2000), "card_expired")

    def test_fr_07_accepts_current_month(self) -> None:
        now = datetime.now(UTC)

        response = self.post(expiry_month=now.month, expiry_year=now.year)

        self.assertEqual(response.status_code, 201)

    def test_fr_07_rejects_previous_month(self) -> None:
        now = datetime.now(UTC)
        month, year = (now.month - 1, now.year) if now.month > 1 else (12, now.year - 1)

        self.assert_rejected(self.post(expiry_month=month, expiry_year=year), "card_expired")

    def test_fr_08_accepts_supported_currencies(self) -> None:
        for currency in ("JPY", "BRL", "KWD"):
            self.assertEqual(self.post(currency=currency).status_code, 201)

    def test_fr_08_uppercases_currency(self) -> None:
        response = self.post(currency="jpy")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["currency"], "JPY")
        self.assertEqual(self.bank.authorize.await_args.args[1].currency, "JPY")

    def test_fr_08_rejects_invalid_currency(self) -> None:
        self.assert_field_rejections(
            "currency",
            ["\uff2a\uff30\uff39", "\u0131py", "USD", "GBP", "JP", "JPYY", "\u00a5", 1, True],
            "currency_invalid",
        )

    def test_fr_08_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("currency", [MISSING, None], "currency_required")

    def test_fr_09_accepts_bounds(self) -> None:
        for amount in (1, 999999999):
            self.assertEqual(self.post(amount=amount).status_code, 201)

    def test_fr_09_rejects_invalid_amount(self) -> None:
        self.assert_field_rejections(
            "amount", [0, -1, 1000000000, 10.5, 100.0, "100", True], "amount_invalid"
        )

    def test_fr_09_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("amount", [MISSING, None], "amount_required")

    def test_fr_10_accepts_3_and_4_digits_unchanged(self) -> None:
        for cvv in ("012", "1234"):
            self.assertEqual(self.post(cvv=cvv).status_code, 201)
            self.assertEqual(self.bank.authorize.await_args.args[1].cvv, cvv)

    def test_fr_10_rejects_invalid_cvv(self) -> None:
        self.assert_field_rejections(
            "cvv", [123, "12", "12345", "12 ", "\u0661\u0662\u0663", "abc", True], "cvv_invalid"
        )

    def test_fr_10_missing_or_null_is_required(self) -> None:
        self.assert_field_rejections("cvv", [MISSING, None], "cvv_required")


class RetrievePaymentTest(ApiTestCase):
    def test_fr_11_get_equals_post_body(self) -> None:
        created = self.post().json()

        response = self.client.get(f"/payments/{created['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_fr_11_unknown_id_is_404(self) -> None:
        response = self.client.get("/payments/6f1f1b6e-3b0b-4f0a-9d0e-0a6a3f3f3f3f")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Payment not found"})

    def test_fr_11_non_uuid_id_is_404(self) -> None:
        response = self.client.get("/payments/abc")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Payment not found"})


class IdempotencyTest(ApiTestCase):
    def test_fr_12_same_key_returns_same_payment_and_calls_bank_once(self) -> None:
        headers = {"Cko-Idempotency-Key": "k-1"}

        first = self.client.post("/payments", json=VALID, headers=headers)
        second = self.client.post("/payments", json=VALID, headers=headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.json(), first.json())
        self.bank.authorize.assert_awaited_once()

    def test_fr_12_no_key_creates_two_payments(self) -> None:
        first = self.post().json()
        second = self.post().json()

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(self.bank.authorize.await_count, 2)


class BankFailureTest(ApiTestCase):
    def test_fr_13_bank_unavailable_is_503_and_nothing_stored(self) -> None:
        self.bank.authorize.side_effect = BankUnavailableError("timeout")

        response = self.post()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "Rejected",
                "error_type": "service_unavailable",
                "error_codes": ["service_unavailable"],
            },
        )
        self.assertNotIn("timeout", response.text)
        self.bank.authorize.assert_awaited_once()
        payment_id = self.bank.authorize.await_args.args[0]
        self.assertEqual(self.client.get(f"/payments/{payment_id}").status_code, 404)


class SecurityTest(ApiTestCase):
    def test_nfr_01_no_card_number_or_cvv_in_any_response(self) -> None:
        created = self.post()
        fetched = self.client.get(f"/payments/{created.json()['id']}")
        rejected_response = self.post(cvv="1")

        for response in (created, fetched, rejected_response):
            self.assertNotIn("card_number", response.json())
            self.assertNotIn("cvv", response.json())
            self.assertNotIn(CARD, response.text)
            self.assertNotIn("idempotency_key", response.text)

    def test_nfr_09_logs_contain_no_card_number_or_cvv(self) -> None:
        secret_cvv = "987"
        with self.assertLogs(level="INFO") as logs:
            self.post(cvv=secret_cvv)
            self.post(card_number="4111111111111112", cvv="98")
            self.bank.authorize.side_effect = BankUnavailableError("timeout")
            self.post(cvv=secret_cvv)

        output = "\n".join(logs.output)
        self.assertIn("validation_rejected error_codes=", output)
        self.assertIn("card_number_invalid", output)
        for secret in (CARD, "4111111111111112", secret_cvv):
            self.assertNotIn(secret, output)
