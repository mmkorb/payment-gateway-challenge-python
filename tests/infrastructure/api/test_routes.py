import unittest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from payment_gateway_api.main import create_app


class PingTest(unittest.TestCase):
    def test_ping_returns_app_name(self) -> None:
        client = TestClient(create_app(bank=AsyncMock()))

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"app": "payment-gateway-api"})
