import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from src.app import create_app
from src.azure_service import create_azure_app


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return BytesIO(json.dumps(self.payload).encode("utf-8")).read()


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(database_path),
                "AZURE_FULFILLMENT_URL": "http://azure-service:8081",
                "AZURE_FUNCTION_KEY": "test-key",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_reports_database(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["database"], "ok")

    def test_portal_identifies_tangamandapio(self):
        response = self.client.get("/")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Tangamandapio S.A.C.", response.data)
        finally:
            response.close()

    def test_readiness_reports_dependencies(self):
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["dependencies"]["database"], "ok")

    def test_security_headers_and_request_id_are_present(self):
        response = self.client.get("/health", headers={"X-Request-ID": "trace-123"})
        self.assertEqual(response.headers["X-Request-ID"], "trace-123")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_order_round_trip(self):
        created = self.client.post(
            "/api/orders", json={"customer": "Cliente de prueba", "total": 49.90}
        )
        self.assertEqual(created.status_code, 201)

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        orders = listed.get_json()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["customer"], "Cliente de prueba")

    def test_invalid_order_is_rejected(self):
        response = self.client.post("/api/orders", json={"customer": "", "total": -1})
        self.assertEqual(response.status_code, 400)

    def test_oversized_customer_and_non_finite_total_are_rejected(self):
        too_long = self.client.post(
            "/api/orders", json={"customer": "x" * 121, "total": 10}
        )
        non_finite = self.client.post(
            "/api/orders", json={"customer": "Cliente", "total": "NaN"}
        )
        self.assertEqual(too_long.status_code, 400)
        self.assertEqual(non_finite.status_code, 400)

    @patch("src.app.urlopen")
    def test_multicloud_health(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse({"status": "ok", "provider": "Azure"})
        response = self.client.get("/api/multicloud")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "connected")

    @patch("src.app.urlopen")
    def test_multicloud_sync(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(
            {"status": "accepted", "event": {"sequence": 1}}
        )
        response = self.client.post(
            "/api/multicloud/sync", json={"order_id": 101, "action": "backup"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "synchronized")

    @patch("src.app.urlopen", side_effect=URLError("offline"))
    def test_multicloud_unavailable_is_reported_without_details(self, _mock_urlopen):
        response = self.client.get("/api/multicloud")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "URLError", "status": "unavailable"})


class AzureServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_azure_app({"TESTING": True, "FUNCTION_KEY": "test-key"})
        self.client = self.app.test_client()

    def test_authentication_is_required(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 401)

    def test_wrong_token_is_rejected(self):
        response = self.client.get(
            "/health", headers={"x-functions-key": "incorrecto"}
        )
        self.assertEqual(response.status_code, 401)

    def test_azure_security_headers_are_present(self):
        response = self.client.get(
            "/health", headers={"x-functions-key": "test-key"}
        )
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("X-Request-ID", response.headers)

    def test_azure_readiness_requires_authentication(self):
        unauthorized = self.client.get("/ready")
        authorized = self.client.get(
            "/ready", headers={"x-functions-key": "test-key"}
        )
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)

    def test_event_is_received_with_valid_token(self):
        headers = {"x-functions-key": "test-key"}
        created = self.client.post(
            "/api/fulfillment/events",
            json={"event_id": "evt-20260925-0001", "event_type": "order.created"},
            headers=headers,
        )
        self.assertEqual(created.status_code, 202)

        duplicate = self.client.post(
            "/api/fulfillment/events",
            json={"event_id": "evt-20260925-0001", "event_type": "order.created"},
            headers=headers,
        )
        self.assertEqual(duplicate.status_code, 200)
        listed = self.client.get("/api/events", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()), 1)


if __name__ == "__main__":
    unittest.main()
