import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from src.app import PostgreSQLConnection, create_app, insert_and_return_id
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


class FakePostgreSQLCursor:
    def __init__(self, row=None):
        self.row = row or {"id": 99}
        self.statement = None
        self.params = None

    def execute(self, statement, params):
        self.statement = statement
        self.params = params

    def fetchone(self):
        return self.row


class FakePostgreSQLRawConnection:
    def __init__(self):
        self.cursor_instance = FakePostgreSQLCursor()
        self.closed = False

    def cursor(self, cursor_factory):
        self.cursor_factory = cursor_factory
        return self.cursor_instance

    def commit(self):
        pass

    def close(self):
        self.closed = True


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
                "AUTO_DISPATCH_EVENTS": False,
                "BOOTSTRAP_ADMIN_USERNAME": "admin@tangamandapio.local",
                "BOOTSTRAP_ADMIN_PASSWORD": "Temporal-Admin-2026",
                "SECRET_KEY": "test-session-secret",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin@tangamandapio.local", "password": "Temporal-Admin-2026"},
        )
        self.assertEqual(response.status_code, 200)

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
        self.login()
        created = self.client.post(
            "/api/orders", json={"customer": "Cliente de prueba", "total": 49.90}
        )
        self.assertEqual(created.status_code, 201)

        listed = self.client.get("/api/orders")
        self.assertEqual(listed.status_code, 200)
        orders = listed.get_json()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["customer"], "Cliente de prueba")

        outbox = self.client.get("/api/outbox")
        self.assertEqual(outbox.status_code, 200)
        self.assertEqual(outbox.get_json()[0]["status"], "pending")

    @patch("src.app.urlopen")
    def test_order_is_dispatched_after_durable_commit(self, mock_urlopen):
        self.login()
        self.app.config["AUTO_DISPATCH_EVENTS"] = True
        mock_urlopen.return_value = FakeResponse({"status": "queued"})

        created = self.client.post(
            "/api/orders", json={"customer": "Cliente integrado", "total": 70}
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()["fulfillment"]["status"], "delivered")
        self.assertTrue(mock_urlopen.called)
        outbox = self.client.get("/api/outbox").get_json()
        self.assertEqual(outbox[0]["status"], "delivered")

    def test_prometheus_metrics_include_orders_and_outbox(self):
        self.login()
        self.client.post("/api/orders", json={"customer": "Metrica", "total": 10})
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"tangamandapio_orders_created_total 1", response.data)
        self.assertIn("text/plain", response.headers["Content-Type"])

    def test_invalid_order_is_rejected(self):
        self.login()
        response = self.client.post("/api/orders", json={"customer": "", "total": -1})
        self.assertEqual(response.status_code, 400)

    def test_oversized_customer_and_non_finite_total_are_rejected(self):
        self.login()
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
        self.login()
        mock_urlopen.return_value = FakeResponse({"status": "ok", "provider": "Azure"})
        response = self.client.get("/api/multicloud")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "connected")

    @patch("src.app.urlopen")
    def test_multicloud_sync(self, mock_urlopen):
        self.login()
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
        self.login()
        response = self.client.get("/api/multicloud")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "URLError", "status": "unavailable"})

    def test_order_api_requires_an_authenticated_session(self):
        response = self.client.get("/api/orders")
        self.assertEqual(response.status_code, 401)

    def test_admin_creates_a_role_bound_user_and_audit_entry(self):
        self.login()
        created = self.client.post(
            "/api/admin/users",
            json={
                "username": "operaciones@tangamandapio.local",
                "password": "Temporal-Operaciones-2026",
                "role": "operations",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.get_json()["user"]["role"], "operations")
        audit = self.client.get("/api/audit")
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(any(item["action"] == "user.create" for item in audit.get_json()))

    def test_admin_company_list_is_case_insensitive(self):
        self.login()
        for name, slug in (("Zeta Logistics", "zeta-logistics"), ("alfa Distribución", "alfa-distribucion")):
            response = self.client.post(
                "/api/admin/companies", json={"name": name, "slug": slug}
            )
            self.assertEqual(response.status_code, 201)

        response = self.client.get("/api/admin/companies")

        self.assertEqual(response.status_code, 200)
        names = [company["name"] for company in response.get_json()]
        self.assertEqual(names, sorted(names, key=str.casefold))

    def test_customer_cannot_view_orders_from_another_company(self):
        self.login()
        created = self.client.post(
            "/api/orders", json={"customer": "Pedido interno", "total": 42.50}
        )
        self.assertEqual(created.status_code, 201)

        company = self.client.post(
            "/api/admin/companies",
            json={"name": "Cliente Externo S.A.C.", "slug": "cliente-externo"},
        )
        self.assertEqual(company.status_code, 201)
        companies = self.client.get("/api/admin/companies")
        self.assertEqual(companies.status_code, 200)
        self.assertTrue(any(item["slug"] == "cliente-externo" for item in companies.get_json()))
        user = self.client.post(
            "/api/admin/users",
            json={
                "username": "cliente@externo.local",
                "password": "Temporal-Cliente-2026",
                "role": "customer",
                "company_id": company.get_json()["id"],
            },
        )
        self.assertEqual(user.status_code, 201)
        self.client.post("/api/auth/logout")
        signed_in = self.client.post(
            "/api/auth/login",
            json={"username": "cliente@externo.local", "password": "Temporal-Cliente-2026"},
        )
        self.assertEqual(signed_in.status_code, 200)
        visible_orders = self.client.get("/api/orders")
        self.assertEqual(visible_orders.status_code, 200)
        self.assertEqual(visible_orders.get_json(), [])
        self.assertEqual(self.client.get("/api/outbox").status_code, 403)

        own_order = self.client.post(
            "/api/orders", json={"customer": "Pedido externo", "total": 81.20}
        )
        self.assertEqual(own_order.status_code, 201)
        visible_orders = self.client.get("/api/orders")
        self.assertEqual(len(visible_orders.get_json()), 1)
        self.assertEqual(visible_orders.get_json()[0]["customer"], "Pedido externo")

    def test_postgresql_adapter_translates_parameters_and_returns_ids(self):
        raw = FakePostgreSQLRawConnection()
        connection = PostgreSQLConnection(raw)
        connection.execute("SELECT id FROM companies WHERE slug = ?", ("cliente",))
        self.assertEqual(
            raw.cursor_instance.statement,
            "SELECT id FROM companies WHERE slug = %s",
        )
        inserted_id = insert_and_return_id(
            connection,
            "INSERT INTO companies(name, slug, created_at) VALUES (?, ?, ?)",
            ("Cliente", "cliente", "2026-10-02T00:00:00+00:00"),
        )
        self.assertEqual(inserted_id, 99)
        self.assertIn("RETURNING id", raw.cursor_instance.statement)


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
