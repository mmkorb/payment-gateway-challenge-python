"""Black-box end-to-end tests against a running gateway (env GATEWAY_URL)."""

import os
import unittest
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx

BASE_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")


def luhn_check_digit(body: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(body)):
        digit = int(ch)
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10


def card_ending_in(last_digit: int) -> str:
    """Return a 16-digit Luhn-valid card number whose last digit is `last_digit`."""
    for suffix in range(1000):
        body = f"411111111111{suffix:03d}"
        if luhn_check_digit(body) == last_digit:
            card = f"{body}{last_digit}"
            assert card[-1] == str(last_digit)
            return card
    raise AssertionError(f"no Luhn-valid card ends in {last_digit}")


def payment_request(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "card_number": card_ending_in(1),
        "expiry_month": 12,
        "expiry_year": datetime.now(UTC).year + 2,
        "currency": "JPY",
        "amount": 1050,
        "cvv": "123",
    }
    body.update(overrides)
    return body


class PaymentsE2ETest(unittest.TestCase):
    client: ClassVar[httpx.Client]

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = httpx.Client(base_url=BASE_URL, timeout=10)
        try:
            cls.client.get("/")
        except httpx.ConnectError:
            cls.client.close()
            raise unittest.SkipTest("gateway not running") from None

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_fr_02_authorized(self) -> None:
        response = self.client.post("/payments", json=payment_request())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "Authorized")
        self.assertTrue(body["masked_card_number"].endswith("1"))
        self.assertEqual(body["currency"], "JPY")
        self.assertEqual(body["amount"], 1050)
        uuid.UUID(body["id"])

    def test_fr_03_declined(self) -> None:
        response = self.client.post(
            "/payments", json=payment_request(card_number=card_ending_in(2))
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "Declined")

    def test_fr_13_bank_unavailable_503(self) -> None:
        response = self.client.post(
            "/payments", json=payment_request(card_number=card_ending_in(0))
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "Rejected",
                "error_type": "service_unavailable",
                "error_codes": ["service_unavailable"],
            },
        )

    def test_fr_09_amount_zero_422(self) -> None:
        response = self.client.post("/payments", json=payment_request(amount=0))

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["status"], "Rejected")
        self.assertEqual(body["error_type"], "request_invalid")
        self.assertIn("amount_invalid", body["error_codes"])

    def test_fr_11_get_returns_same_body(self) -> None:
        created = self.client.post("/payments", json=payment_request()).json()

        response = self.client.get(f"/payments/{created['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_fr_11_unknown_id_404(self) -> None:
        response = self.client.get(f"/payments/{uuid.uuid4()}")

        self.assertEqual(response.status_code, 404)

    def test_fr_12_same_idempotency_key_same_id(self) -> None:
        headers = {"Cko-Idempotency-Key": str(uuid.uuid4())}

        first = self.client.post("/payments", json=payment_request(), headers=headers)
        second = self.client.post("/payments", json=payment_request(), headers=headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])

    def test_nfr_01_no_full_card_number_or_cvv(self) -> None:
        card = card_ending_in(1)

        response = self.client.post("/payments", json=payment_request(card_number=card, cvv="987"))

        self.assertEqual(response.status_code, 201)
        self.assertNotIn(card, response.text)
        self.assertNotIn("card_number", response.json())
        self.assertNotIn("cvv", response.json())
        self.assertEqual(response.json()["masked_card_number"], "*" * 12 + card[-4:])
