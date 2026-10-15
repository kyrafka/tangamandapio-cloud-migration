import json
import re
import sqlite3
import socketserver
import threading
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


class CapturingSMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 smtp-test ready\r\n")
        in_data = False
        message = []
        while True:
            line = self.rfile.readline()
            if not line:
                break
            command = line.decode("utf-8", "replace").rstrip("\r\n")
            upper = command.upper()
            if in_data:
                if command == ".":
                    self.server.messages.append("".join(message))
                    message = []
                    in_data = False
                    self.wfile.write(b"250 queued\r\n")
                else:
                    message.append(command + "\n")
            elif upper.startswith(("EHLO ", "HELO ")):
                self.wfile.write(b"250-smtp-test\r\n250 SIZE 1000000\r\n")
            elif upper.startswith(("MAIL FROM:", "RCPT TO:")):
                self.wfile.write(b"250 accepted\r\n")
            elif upper == "DATA":
                in_data = True
                self.wfile.write(b"354 end with dot\r\n")
            elif upper == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                break
            else:
                self.wfile.write(b"250 ok\r\n")


class CapturingSMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), CapturingSMTPHandler)
        self.messages = []


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
                "METRICS_ENABLED": False,
                "AUTO_DISPATCH_EVENTS": False,
                "BOOTSTRAP_ADMIN_USERNAME": "admin@tangamandapio.local",
                "BOOTSTRAP_ADMIN_PASSWORD": "Temporal-Admin-2026",
                "SECRET_KEY": "test-session-secret",
                "CSRF_ENABLED": False,
                "FORCE_BOOTSTRAP_PASSWORD_CHANGE": False,
                "FORCE_INITIAL_PASSWORD_CHANGE": False,
                "LOGIN_RATE_LIMIT_MAX": 2,
                "LOGIN_RATE_LIMIT_SECONDS": 300,
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

    def test_health_reports_aggregate_status_without_dependency_details(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertNotIn("database", payload)
        self.assertNotIn("instance", payload)

    def test_health_reports_unavailable_without_identifying_dependency(self):
        with patch("src.app.connect", side_effect=RuntimeError("postgres.internal:5432")):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["status"], "degraded")
        self.assertNotIn("database", payload)
        self.assertNotIn("postgres.internal", json.dumps(payload))

    def test_public_diagnostics_do_not_expose_internal_hostnames(self):
        for path in ("/api", "/health", "/ready"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("instance", response.get_json())

    def test_portal_identifies_tangamandapio(self):
        response = self.client.get("/")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Tangamandapio S.A.C.", response.data)
        finally:
            response.close()

    def test_vite_homepage_references_assets_served_by_flask(self):
        page = self.client.get("/")
        try:
            self.assertEqual(page.status_code, 200)
            assets = set(re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', page.data))
            self.assertTrue(assets, "el HTML debe declarar sus bundles Vite")
        finally:
            page.close()

        for asset_path in assets:
            with self.subTest(asset=asset_path.decode("ascii")):
                asset = self.client.get(asset_path.decode("ascii"))
                try:
                    self.assertEqual(asset.status_code, 200)
                    self.assertGreater(len(asset.data), 100)
                finally:
                    asset.close()

    def test_cache_policy_revalidates_html_and_keeps_api_uncached(self):
        page = self.client.get("/")
        try:
            self.assertEqual(
                page.headers["Cache-Control"],
                "no-cache, max-age=0, must-revalidate",
            )
        finally:
            page.close()

        health = self.client.get("/health")
        self.assertEqual(health.headers["Cache-Control"], "no-store")

    def test_fingerprinted_frontend_assets_use_immutable_cache(self):
        page = self.client.get("/")
        assets = re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', page.data)
        page.close()
        fingerprinted = next(
            (
                path.decode("ascii")
                for path in assets
                if re.fullmatch(
                    r"/assets/index-[A-Za-z0-9_-]{8,}\.(?:js|css)",
                    path.decode("ascii"),
                )
            ),
            None,
        )
        self.assertIsNotNone(fingerprinted, "la página debe usar un asset con hash")
        asset = self.client.get(fingerprinted)
        try:
            self.assertEqual(asset.status_code, 200)
            self.assertEqual(
                asset.headers["Cache-Control"],
                "public, max-age=31536000, immutable",
            )
        finally:
            asset.close()

    def test_readiness_reports_ready_without_dependency_details(self):
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")
        self.assertNotIn("dependencies", response.get_json())

    def test_security_headers_and_request_id_are_present(self):
        response = self.client.get("/health", headers={"X-Request-ID": "trace-123"})
        self.assertEqual(response.headers["X-Request-ID"], "trace-123")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_login_rate_limit_persists_across_app_instances(self):
        payload = {"username": "admin@tangamandapio.local", "password": "incorrecta"}
        for _ in range(2):
            denied = self.client.post("/api/auth/login", json=payload)
            self.assertEqual(denied.status_code, 401)

        database_path = self.app.config["DATABASE_PATH"]
        restarted_app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": database_path,
                "SECRET_KEY": "test-session-secret",
                "CSRF_ENABLED": False,
                "LOGIN_RATE_LIMIT_MAX": 2,
                "LOGIN_RATE_LIMIT_SECONDS": 300,
            }
        )
        response = restarted_app.test_client().post("/api/auth/login", json=payload)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["error"], "too_many_attempts")
        self.assertGreaterEqual(int(response.headers["Retry-After"]), 1)

        connection = sqlite3.connect(database_path)
        try:
            rows = connection.execute(
                "SELECT attempt_key FROM login_attempts"
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("admin@tangamandapio.local", rows[0][0])

    def test_successful_login_clears_prior_failures(self):
        bad_payload = {"username": "admin@tangamandapio.local", "password": "incorrecta"}
        self.assertEqual(self.client.post("/api/auth/login", json=bad_payload).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"username": "admin@tangamandapio.local", "password": "Temporal-Admin-2026"},
            ).status_code,
            200,
        )
        self.assertEqual(self.client.post("/api/auth/login", json=bad_payload).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json=bad_payload).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json=bad_payload).status_code, 429)

    def test_concurrent_login_failures_are_incremented_atomically(self):
        limiter = self.app.extensions["login_rate_limiter"]
        barrier = threading.Barrier(8)
        errors = []

        def record_failure():
            try:
                barrier.wait(timeout=5)
                limiter.record_failure("parallel-attempt-key")
            except Exception as error:
                errors.append(error)

        workers = [threading.Thread(target=record_failure) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)

        self.assertFalse(any(worker.is_alive() for worker in workers))
        self.assertEqual(errors, [])
        entry = limiter.store.get("parallel-attempt-key")
        self.assertEqual(entry["failures"], 2)
        self.assertGreater(limiter.retry_after("parallel-attempt-key"), 0)

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
        self.app.config["METRICS_ENABLED"] = True
        self.client.post("/api/orders", json={"customer": "Metrica", "total": 10})
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"tangamandapio_orders_created_total 1", response.data)
        self.assertIn("text/plain", response.headers["Content-Type"])

    def test_enabled_prometheus_metrics_require_admin_authentication(self):
        self.app.config["METRICS_ENABLED"] = True
        self.assertEqual(self.app.test_client().get("/metrics").status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/metrics").status_code, 200)

    def test_metrics_are_hidden_without_explicit_opt_in(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, b"")

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

    def test_portal_role_matrix_enforces_read_and_write_boundaries(self):
        self.login()
        clients = {"admin": self.client}
        for role in ("customer", "sales", "warehouse", "operations", "auditor"):
            username = f"rbac.{role}@tangamandapio.local"
            password = f"Test-RBAC-{role}-2026"
            created = self.client.post(
                "/api/admin/users",
                json={"username": username, "password": password, "role": role},
            )
            self.assertEqual(created.status_code, 201, role)
            role_client = self.app.test_client()
            signed_in = role_client.post(
                "/api/auth/login", json={"username": username, "password": password}
            )
            self.assertEqual(signed_in.status_code, 200, role)
            clients[role] = role_client

        allowed_roles = {
            "/api/orders": {"customer", "sales", "warehouse", "operations", "admin", "auditor"},
            "/api/outbox": {"warehouse", "operations", "admin", "auditor"},
            "/api/audit": {"operations", "admin", "auditor"},
            "/api/admin/users": {"admin"},
            "/api/erp/access": {"sales", "warehouse", "operations", "admin", "auditor"},
            "/api/erp/partners": {"sales", "admin", "auditor"},
            "/api/erp/finance/documents": {"admin", "auditor"},
            "/api/multicloud": {"warehouse", "operations", "admin", "auditor"},
        }

        with patch("src.app.urlopen", return_value=FakeResponse({"status": "ok"})):
            for path, allowed in allowed_roles.items():
                for role, role_client in clients.items():
                    with self.subTest(path=path, role=role):
                        response = role_client.get(path)
                        expected_status = 200 if role in allowed else 403
                        self.assertEqual(response.status_code, expected_status)

        for role, role_client in clients.items():
            with self.subTest(action="create_order", role=role):
                response = role_client.post(
                    "/api/orders", json={"customer": f"RBAC {role}", "total": 1}
                )
                expected_status = 201 if role in {"customer", "sales", "admin"} else 403
                self.assertEqual(response.status_code, expected_status)

            with self.subTest(action="create_expense", role=role):
                response = role_client.post(
                    "/api/erp/finance/expenses",
                    json={"description": "Prueba de permisos", "amount": 1},
                )
                self.assertEqual(response.status_code, 201 if role == "admin" else 403)

    def test_admin_user_creation_rolls_back_when_audit_insert_fails(self):
        self.login()
        with patch("src.app.insert_audit", side_effect=RuntimeError("audit store unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit store unavailable"):
                self.client.post(
                    "/api/admin/users",
                    json={
                        "username": "auditoria-falla@tangamandapio.local",
                        "password": "Temporal-Operaciones-2026",
                        "role": "operations",
                    },
                )

        users = self.client.get("/api/admin/users")
        self.assertEqual(users.status_code, 200)
        self.assertFalse(
            any(user["username"] == "auditoria-falla@tangamandapio.local" for user in users.get_json())
        )

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

    def test_admin_company_creation_rolls_back_when_audit_insert_fails(self):
        self.login()
        with patch("src.app.insert_audit", side_effect=RuntimeError("audit store unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit store unavailable"):
                self.client.post(
                    "/api/admin/companies",
                    json={"name": "Audit failure tenant", "slug": "audit-failure-tenant"},
                )

        companies = self.client.get("/api/admin/companies")
        self.assertEqual(companies.status_code, 200)
        self.assertFalse(any(item["slug"] == "audit-failure-tenant" for item in companies.get_json()))

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

    def test_erp_sales_purchase_and_finance_flow_uses_wms_as_stock_authority(self):
        self.login()
        self.app.config["AZURE_FULFILLMENT_URL"] = ""
        customer = self.client.post(
            "/api/erp/partners",
            json={"kind": "customer", "name": "Cliente ERP Demo", "tax_id": "20123456789"},
        )
        supplier = self.client.post(
            "/api/erp/partners",
            json={"kind": "supplier", "name": "Proveedor ERP Demo", "tax_id": "20987654321"},
        )
        self.assertEqual(customer.status_code, 201)
        self.assertEqual(supplier.status_code, 201)

        inventory = {
            "mode": "demo-inventory-ledger",
            "items": [{"sku": "SKU-ARROZ-001", "on_hand": 25}],
        }
        with patch("src.erp_service.fetch_wms_inventory", return_value=(inventory, None)):
            product_catalog = self.client.get("/api/erp/products")
            self.assertEqual(product_catalog.status_code, 200)
            self.assertEqual(len(product_catalog.get_json()["products"]), 12)
            arroz = next(item for item in product_catalog.get_json()["products"] if item["sku"] == "SKU-ARROZ-001")
            self.assertEqual(arroz["on_hand"], 25)
            sale = self.client.post(
                "/api/erp/sales/orders",
                json={"partner_id": customer.get_json()["id"], "items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]},
            )
            purchase = self.client.post(
                "/api/erp/purchases/orders",
                json={"partner_id": supplier.get_json()["id"], "items": [{"sku": "SKU-ARROZ-001", "quantity": 3}]},
            )
        self.assertEqual(sale.status_code, 201)
        self.assertEqual(sale.get_json()["total"], 85.0)
        self.assertEqual(purchase.status_code, 201)
        self.assertEqual(purchase.get_json()["total"], 105.0)

        with patch("src.erp_service.fetch_wms_event", return_value=({"status": "demo_fulfillment_completed", "mode": "demo-inventory-ledger"}, None)):
            reconciled_sale = self.client.post(f"/api/erp/sales/orders/{sale.get_json()['id']}/refresh")
        self.assertEqual(reconciled_sale.status_code, 200)
        self.assertEqual(reconciled_sale.get_json()["status"], "completed_demo")
        documents = self.client.get("/api/erp/finance/documents").get_json()
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["kind"], "receivable")

        received = self.client.post(f"/api/erp/purchases/orders/{purchase.get_json()['id']}/receive")
        self.assertEqual(received.status_code, 202)
        with patch("src.erp_service.fetch_wms_event", return_value=({"status": "demo_restock_completed", "mode": "demo-inventory-ledger"}, None)):
            reconciled_purchase = self.client.post(f"/api/erp/purchases/orders/{purchase.get_json()['id']}/refresh")
        self.assertEqual(reconciled_purchase.status_code, 200)
        self.assertEqual(reconciled_purchase.get_json()["status"], "received_demo")
        duplicate_receipt = self.client.post(f"/api/erp/purchases/orders/{purchase.get_json()['id']}/receive")
        self.assertEqual(duplicate_receipt.status_code, 200)
        self.assertTrue(duplicate_receipt.get_json()["duplicate"])
        documents = self.client.get("/api/erp/finance/documents").get_json()
        self.assertEqual(len(documents), 2)
        self.assertCountEqual([item["kind"] for item in documents], ["receivable", "payable"])

        payable = next(item for item in documents if item["kind"] == "payable")
        settled = self.client.post(f"/api/erp/finance/documents/{payable['id']}/settle")
        self.assertEqual(settled.status_code, 200)
        self.assertEqual(settled.get_json()["status"], "paid")

    def test_admin_bulk_import_validates_entire_catalog_and_syncs_wms_before_database(self):
        self.login()
        products = [
            {"sku": "SKU-NEW-001", "name": "Producto sintético nuevo", "unit": "caja", "sale_price": 12.5, "purchase_cost": 8.75, "initial_stock": 9},
            {"sku": "SKU-ARROZ-001", "name": "Arroz actualizado", "unit": "saco", "sale_price": 45.5, "purchase_cost": 37, "initial_stock": 999},
        ]
        with patch("src.erp_service.update_wms_catalog", return_value=({"mode": "demo-inventory-ledger", "stock_preserved": True}, None)) as sync:
            response = self.client.post("/api/erp/products/import", json={"products": products})
        self.assertEqual(response.status_code, 200, response.get_json())
        result = response.get_json()
        self.assertEqual((result["imported"], result["created"], result["updated"]), (2, 1, 1))
        self.assertTrue(result["stock_preserved"])
        self.assertEqual(sync.call_args.args[1][0]["unit_price"], 12.5)
        with self.app.app_context():
            from src.app import configured_database_target, connect
            with connect(configured_database_target(self.app.config)) as connection:
                rows = connection.execute(
                    "SELECT sku,name,sale_price,purchase_cost FROM erp_products WHERE sku IN (?,?) ORDER BY sku",
                    ("SKU-NEW-001", "SKU-ARROZ-001"),
                ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(next(row["sale_price"] for row in rows if row["sku"] == "SKU-NEW-001"), 12.5)

    def test_admin_bulk_import_accepts_maximum_500_sku_synthetic_batch(self):
        self.login()
        products = [
            {
                "sku": f"SKU-BULK-{index:04d}",
                "name": f"Producto sintético {index:04d}",
                "unit": "caja",
                "sale_price": 10.5,
                "purchase_cost": 7.25,
                "initial_stock": index,
            }
            for index in range(1, 501)
        ]
        with patch(
            "src.erp_service.update_wms_catalog",
            return_value=({"mode": "demo-inventory-ledger", "stock_preserved": True}, None),
        ) as sync:
            response = self.client.post("/api/erp/products/import", json={"products": products})

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["imported"], 500)
        self.assertEqual(response.get_json()["created"], 500)
        self.assertTrue(response.get_json()["stock_preserved"])
        sync.assert_called_once()
        self.assertEqual(len(sync.call_args.args[1]), 500)
        catalog = self.client.get("/api/erp/products")
        self.assertEqual(catalog.status_code, 200)
        bulk_skus = [item["sku"] for item in catalog.get_json()["products"] if item["sku"].startswith("SKU-BULK-")]
        self.assertEqual(len(bulk_skus), 500)

    def test_admin_bulk_import_rejects_501_items_before_wms_or_database_write(self):
        self.login()
        products = [
            {
                "sku": f"SKU-LIMIT-{index:04d}",
                "name": f"Producto sintético {index:04d}",
                "unit": "caja",
                "sale_price": 10.5,
                "purchase_cost": 7.25,
                "initial_stock": 0,
            }
            for index in range(1, 502)
        ]
        with patch("src.erp_service.update_wms_catalog") as sync:
            response = self.client.post("/api/erp/products/import", json={"products": products})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "products_must_contain_1_to_500_items")
        sync.assert_not_called()
        catalog = self.client.get("/api/erp/products")
        self.assertEqual(catalog.status_code, 200)
        self.assertFalse(any(item["sku"].startswith("SKU-LIMIT-") for item in catalog.get_json()["products"]))

    def test_bulk_import_rejects_all_rows_before_wms_or_database_write(self):
        self.login()
        product = {"sku": "SKU-NEW-002", "name": "Producto", "unit": "caja", "sale_price": 12, "purchase_cost": 8, "initial_stock": 9}
        with patch("src.erp_service.update_wms_catalog") as sync:
            response = self.client.post("/api/erp/products/import", json={"products": [product, dict(product, name="Duplicado")]})
        self.assertEqual(response.status_code, 400)
        sync.assert_not_called()
        catalog = self.client.get("/api/erp/products")
        self.assertEqual(catalog.status_code, 200)
        self.assertNotIn("SKU-NEW-002", {item["sku"] for item in catalog.get_json()["products"]})

    def test_bulk_import_rejects_boolean_prices_before_wms_sync(self):
        self.login()
        product = {"sku": "SKU-BOOL-001", "name": "Producto", "unit": "caja", "sale_price": True, "purchase_cost": 8, "initial_stock": 9}
        with patch("src.erp_service.update_wms_catalog") as sync:
            response = self.client.post("/api/erp/products/import", json={"products": [product]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_product_prices")
        sync.assert_not_called()

    def test_bulk_import_fails_closed_when_wms_is_unavailable(self):
        self.login()
        product = {"sku": "SKU-NEW-003", "name": "Producto", "unit": "caja", "sale_price": 12, "purchase_cost": 8, "initial_stock": 9}
        with patch("src.erp_service.update_wms_catalog", return_value=(None, "unavailable")):
            response = self.client.post("/api/erp/products/import", json={"products": [product]})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "wms_catalog_sync_failed")
        self.assertNotIn("SKU-NEW-003", {item["sku"] for item in self.client.get("/api/erp/products").get_json()["products"]})

    def test_erp_permissions_and_internal_mail_are_separate_from_customer_access(self):
        self.login()
        created = self.client.post(
            "/api/admin/users",
            json={"username": "ventas@tangamandapio.local", "password": "Temporal-Ventas-2026", "role": "sales"},
        )
        self.assertEqual(created.status_code, 201)
        erp_users = self.client.get("/api/erp/users").get_json()
        sales_user = next(item for item in erp_users if item["username"] == "ventas@tangamandapio.local")
        self.assertIn("erp_sales", sales_user["erp_roles"])

        sent = self.client.post(
            "/api/erp/mail",
            json={"recipient_id": sales_user["id"], "subject": "Coordinación", "body": "Pedido listo para seguimiento."},
        )
        self.assertEqual(sent.status_code, 201)
        self.client.post("/api/auth/logout")
        signed_in = self.client.post(
            "/api/auth/login",
            json={"username": "ventas@tangamandapio.local", "password": "Temporal-Ventas-2026"},
        )
        self.assertEqual(signed_in.status_code, 200)
        access = self.client.get("/api/erp/access").get_json()
        self.assertIn("sales:write", access["permissions"])
        self.assertNotIn("finance:write", access["permissions"])
        inbox = self.client.get("/api/erp/mail?folder=inbox").get_json()
        self.assertEqual(len(inbox), 1)
        self.assertTrue(inbox[0]["unread"])
        marked = self.client.post(f"/api/erp/mail/{inbox[0]['id']}/read")
        self.assertEqual(marked.status_code, 200)
        blocked_expense = self.client.post("/api/erp/finance/expenses", json={"description": "No debe pasar", "amount": 20})
        self.assertEqual(blocked_expense.status_code, 403)
        self.assertEqual(self.client.get("/api/erp/finance/documents").status_code, 403)

        self.client.post("/api/auth/logout")
        self.login()
        company = self.client.post("/api/admin/companies", json={"name": "Cliente Correo", "slug": "cliente-correo"})
        self.assertEqual(company.status_code, 201)
        customer = self.client.post(
            "/api/admin/users",
            json={"username": "cliente@correo.local", "password": "Temporal-Cliente-Correo-2026", "role": "customer", "company_id": company.get_json()["id"]},
        )
        self.assertEqual(customer.status_code, 201)
        self.client.post("/api/auth/logout")
        customer_login = self.client.post(
            "/api/auth/login",
            json={"username": "cliente@correo.local", "password": "Temporal-Cliente-Correo-2026"},
        )
        self.assertEqual(customer_login.status_code, 200)
        self.assertEqual(self.client.get("/api/erp/mail").status_code, 403)

    def test_erp_overview_only_returns_metrics_allowed_by_assigned_erp_roles(self):
        self.login()
        with patch(
            "src.erp_service.urlopen",
            return_value=FakeResponse({"mode": "demo-inventory-ledger", "items": []}),
        ):
            admin_overview = self.client.get("/api/erp/overview")
        self.assertEqual(admin_overview.status_code, 200)
        self.assertEqual(
            set(admin_overview.get_json()["metrics"]),
            {
                "sales_orders", "purchase_orders", "products", "partners",
                "open_receivables", "open_payables",
            },
        )
        expected = {
            "erp_sales": {"sales_orders", "products", "partners"},
            "erp_master_data": {"products", "partners"},
            "erp_finance": {
                "sales_orders", "purchase_orders", "products", "partners",
                "open_receivables", "open_payables",
            },
        }
        for role_code, visible_metrics in expected.items():
            with self.subTest(role=role_code):
                username = f"overview.{role_code}@tangamandapio.local"
                created = self.client.post(
                    "/api/admin/users",
                    json={"username": username, "password": "Temporal-Overview-2026", "role": "operations"},
                )
                self.assertEqual(created.status_code, 201)
                user_id = created.get_json()["user"]["id"]
                assigned = self.client.put(
                    f"/api/erp/users/{user_id}/roles", json={"roles": [role_code]}
                )
                self.assertEqual(assigned.status_code, 200)
                client = self.app.test_client()
                login = client.post(
                    "/api/auth/login",
                    json={"username": username, "password": "Temporal-Overview-2026"},
                )
                self.assertEqual(login.status_code, 200)

                with patch(
                    "src.erp_service.urlopen",
                    return_value=FakeResponse({"mode": "demo-inventory-ledger", "items": []}),
                ):
                    response = client.get("/api/erp/overview")

                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.get_json()["metrics"]), visible_metrics)

    def test_internal_mail_is_sent_over_smtp_and_kept_in_portal(self):
        self.login()
        created = self.client.post(
            "/api/admin/users",
            json={"username": "ventas@tangamandapio.local", "password": "Temporal-Ventas-2026", "role": "sales"},
        )
        self.assertEqual(created.status_code, 201)
        smtp = CapturingSMTPServer()
        smtp_thread = threading.Thread(target=smtp.serve_forever, daemon=True)
        smtp_thread.start()
        self.addCleanup(smtp.server_close)
        self.addCleanup(smtp.shutdown)
        self.app.config.update({
            "ERP_SMTP_HOST": "127.0.0.1",
            "ERP_SMTP_PORT": smtp.server_address[1],
            "ERP_SMTP_SECURITY": "none",
            "ERP_SMTP_FROM": "no-reply@tangamandapio.local",
            "ERP_SMTP_RECIPIENT_DOMAIN": "tangamandapio.local",
        })
        status = self.client.get("/api/erp/mail/status")
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["smtp_configured"])
        sent = self.client.post("/api/erp/mail", json={
            "recipient_id": created.get_json()["user"]["id"],
            "subject": "Coordinacion de pedido",
            "body": "El pedido quedo listo para revision.",
        })
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(sent.get_json()["smtp_status"], "accepted_by_smtp")
        self.assertEqual(len(smtp.messages), 1)
        self.assertIn("To: ventas@tangamandapio.local", smtp.messages[0])
        self.assertIn("Subject: Coordinacion de pedido", smtp.messages[0])
        sent_folder = self.client.get("/api/erp/mail?folder=sent").get_json()
        self.assertEqual(sent_folder[0]["smtp_status"], "accepted_by_smtp")
        self.assertEqual(sent_folder[0]["smtp_attempts"], 1)
        test_result = self.client.post("/api/erp/mail/smtp-test")
        self.assertEqual(test_result.status_code, 200)
        self.assertEqual(len(smtp.messages), 2)

    def test_mail_remains_delivered_in_portal_when_smtp_is_unavailable(self):
        self.login()
        created = self.client.post(
            "/api/admin/users",
            json={"username": "ventas@tangamandapio.local", "password": "Temporal-Ventas-2026", "role": "sales"},
        )
        self.app.config.update({
            "ERP_SMTP_HOST": "127.0.0.1",
            "ERP_SMTP_PORT": 1,
            "ERP_SMTP_SECURITY": "none",
            "ERP_SMTP_FROM": "no-reply@tangamandapio.local",
            "ERP_SMTP_RECIPIENT_DOMAIN": "tangamandapio.local",
        })
        sent = self.client.post("/api/erp/mail", json={
            "recipient_id": created.get_json()["user"]["id"],
            "subject": "Aviso interno",
            "body": "El contenido debe conservarse aunque SMTP falle.",
        })
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(sent.get_json()["smtp_status"], "smtp_failed")
        sent_folder = self.client.get("/api/erp/mail?folder=sent").get_json()
        self.assertEqual(sent_folder[0]["subject"], "Aviso interno")
        self.assertEqual(sent_folder[0]["smtp_status"], "smtp_failed")

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


class FakeAlarmSNS:
    topic = "arn:aws:sns:us-east-1:841113066612:tangamandapio-test-alarms"

    def __init__(self):
        self.calls = []
        self.subscriptions = [
            {"Protocol": "email", "Endpoint": "confirmed@example.test", "SubscriptionArn": f"{self.topic}:confirmed"},
            {"Protocol": "email", "Endpoint": "pending@example.test", "SubscriptionArn": "PendingConfirmation"},
            {"Protocol": "https", "Endpoint": "https://example.test/hook", "SubscriptionArn": f"{self.topic}:webhook"},
        ]

    def list_subscriptions_by_topic(self, **kwargs):
        self.calls.append(("list", kwargs))
        return {"Subscriptions": list(self.subscriptions)}

    def subscribe(self, **kwargs):
        self.calls.append(("subscribe", kwargs))
        self.subscriptions.append({
            "Protocol": kwargs["Protocol"],
            "Endpoint": kwargs["Endpoint"],
            "SubscriptionArn": "PendingConfirmation",
        })
        return {"SubscriptionArn": "PendingConfirmation"}

    def unsubscribe(self, **kwargs):
        self.calls.append(("unsubscribe", kwargs))
        self.subscriptions = [item for item in self.subscriptions if item["SubscriptionArn"] != kwargs["SubscriptionArn"]]


class AdminConsoleTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": str(Path(self.temp_dir.name) / "admin.db"),
            "BOOTSTRAP_ADMIN_USERNAME": "admin@tangamandapio.local",
            "BOOTSTRAP_ADMIN_PASSWORD": "Temporal-Admin-2026",
            "SECRET_KEY": "admin-console-test-secret",
            "CSRF_ENABLED": False,
            "FORCE_BOOTSTRAP_PASSWORD_CHANGE": False,
            "FORCE_INITIAL_PASSWORD_CHANGE": False,
            "AUTO_DISPATCH_EVENTS": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def login_admin(self):
        response = self.client.post("/api/auth/login", json={
            "username": "admin@tangamandapio.local",
            "password": "Temporal-Admin-2026",
        })
        self.assertEqual(response.status_code, 200)

    def create_user(self, username, role="operations"):
        return self.client.post("/api/admin/users", json={
            "username": username,
            "password": "Temporary-Password-2026",
            "role": role,
        })

    def test_admin_console_is_full_view_and_requires_admin_session(self):
        self.assertEqual(self.client.get("/administracion").status_code, 303)
        self.login_admin()
        page = self.client.get("/administracion")
        try:
            self.assertEqual(page.status_code, 200)
            self.assertIn("Administración general".encode(), page.data)
            self.assertIn("Destinatarios de alarmas".encode(), page.data)
        finally:
            page.close()
        for asset_name in ("admin-console.js", "admin-console.css"):
            asset = self.client.get(f"/assets/{asset_name}")
            try:
                self.assertEqual(asset.status_code, 200, asset_name)
            finally:
                asset.close()

        self.assertEqual(self.create_user("ops@example.test").status_code, 201)
        operations = self.app.test_client()
        signed_in = operations.post("/api/auth/login", json={
            "username": "ops@example.test", "password": "Temporary-Password-2026",
        })
        self.assertEqual(signed_in.status_code, 200)
        self.assertEqual(operations.get("/administracion").status_code, 403)
        self.assertEqual(operations.get("/api/admin/alarm-subscriptions").status_code, 403)

    def test_admin_can_change_user_access_and_change_revokes_the_old_session(self):
        self.login_admin()
        created = self.create_user("ops@example.test")
        self.assertEqual(created.status_code, 201)
        user_id = created.get_json()["user"]["id"]
        operations = self.app.test_client()
        self.assertEqual(operations.post("/api/auth/login", json={
            "username": "ops@example.test", "password": "Temporary-Password-2026",
        }).status_code, 200)

        users = self.client.get("/api/admin/users").get_json()
        target = next(user for user in users if user["id"] == user_id)
        self.assertIn("company_id", target)
        updated = self.client.patch(f"/api/admin/users/{user_id}", json={
            "role": "sales", "company_id": target["company_id"], "active": True,
        })
        self.assertEqual(updated.status_code, 200, updated.get_json())
        self.assertEqual(updated.get_json()["user"]["role"], "sales")
        self.assertFalse(operations.get("/api/auth/session").get_json()["authenticated"])

        self_update = self.client.patch(f"/api/admin/users/{self.client.get('/api/auth/session').get_json()['user']['id']}", json={"role": "sales"})
        self.assertEqual(self_update.status_code, 409)

    def test_alarm_list_is_scoped_to_email_subscriptions_and_confirmation_state(self):
        self.login_admin()
        sns = FakeAlarmSNS()
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = sns.topic
        with patch("src.app._alarm_sns_client", return_value=sns):
            response = self.client.get("/api/admin/alarm-subscriptions")
        self.assertEqual(response.status_code, 200, response.get_json())
        subscriptions = response.get_json()["subscriptions"]
        self.assertEqual([item["status"] for item in subscriptions], ["confirmed", "pending_confirmation"])
        self.assertNotIn("https://example.test/hook", str(response.get_json()))

    def test_alarm_add_validates_deduplicates_and_audits_without_email_address(self):
        self.login_admin()
        sns = FakeAlarmSNS()
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = sns.topic
        with patch("src.app._alarm_sns_client", return_value=sns):
            invalid = self.client.post("/api/admin/alarm-subscriptions", json={"email": "not-an-email"})
            duplicate = self.client.post("/api/admin/alarm-subscriptions", json={"email": "CONFIRMED@example.test"})
            created = self.client.post("/api/admin/alarm-subscriptions", json={"email": " Alerts@Example.Test "})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.get_json()["already_exists"])
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()["subscription"]["endpoint"], "alerts@example.test")
        self.assertEqual(created.get_json()["subscription"]["status"], "pending_confirmation")
        audit = self.client.get("/api/audit").get_json()
        entry = next(item for item in audit if item["action"] == "alarm_subscription.create")
        self.assertNotIn("alerts@example.test", str(entry))

    def test_alarm_removal_requires_exact_confirmed_topic_subscription(self):
        self.login_admin()
        sns = FakeAlarmSNS()
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = sns.topic
        client_options = []
        def create_sns_client(_config, unsigned=False):
            client_options.append(unsigned)
            return sns

        with patch("src.app._alarm_sns_client", side_effect=create_sns_client):
            foreign = self.client.delete("/api/admin/alarm-subscriptions", json={
                "subscription_arn": "arn:aws:sns:us-east-1:999999999999:other-topic:sub",
            })
            pending = self.client.delete("/api/admin/alarm-subscriptions", json={
                "subscription_arn": "PendingConfirmation",
            })
            removed = self.client.delete("/api/admin/alarm-subscriptions", json={
                "subscription_arn": sns.topic + ":confirmed",
            })
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(pending.status_code, 404)
        self.assertEqual(removed.status_code, 200, removed.get_json())
        self.assertEqual(client_options, [False, True])
        self.assertIn(("unsubscribe", {"SubscriptionArn": sns.topic + ":confirmed"}), sns.calls)

    def test_alarm_routes_fail_closed_when_topic_is_not_configured(self):
        self.login_admin()
        with patch("src.app._alarm_sns_client") as sns_factory:
            response = self.client.get("/api/admin/alarm-subscriptions")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "alarm_notifications_not_configured"})
        sns_factory.assert_not_called()


class CsrfProtectionTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": str(Path(self.temp_dir.name) / "csrf.db"),
            "BOOTSTRAP_ADMIN_USERNAME": "admin@tangamandapio.local",
            "BOOTSTRAP_ADMIN_PASSWORD": "Temporal-Admin-2026",
            "SECRET_KEY": "csrf-test-session-secret",
            "AUTO_DISPATCH_EVENTS": False,
                "FORCE_BOOTSTRAP_PASSWORD_CHANGE": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_anonymous_session_token_protects_login_and_rotates_after_authentication(self):
        anonymous_session = self.client.get("/api/auth/session").get_json()
        token = anonymous_session["csrf_token"]
        self.assertFalse(anonymous_session["authenticated"])
        self.assertGreaterEqual(len(token), 32)

        payload = {"username": "admin@tangamandapio.local", "password": "Temporal-Admin-2026"}
        missing = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.get_json()["error"], "csrf_token_required")

        cross_origin = self.client.post(
            "/api/auth/login",
            json=payload,
            headers={"X-CSRF-Token": token, "Origin": "https://attacker.example"},
        )
        self.assertEqual(cross_origin.status_code, 403)
        self.assertEqual(cross_origin.get_json()["error"], "cross_origin_denied")

        malformed_origin = self.client.post(
            "/api/auth/login",
            json=payload,
            headers={"X-CSRF-Token": token, "Origin": "http://["},
        )
        self.assertEqual(malformed_origin.status_code, 403)
        self.assertEqual(malformed_origin.get_json()["error"], "cross_origin_denied")

        signed_in = self.client.post(
            "/api/auth/login",
            json=payload,
            headers={"X-CSRF-Token": token, "Origin": "http://localhost"},
        )
        self.assertEqual(signed_in.status_code, 200)
        authenticated_token = signed_in.get_json()["csrf_token"]
        self.assertNotEqual(authenticated_token, token)

        stale_token = self.client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": token}
        )
        self.assertEqual(stale_token.status_code, 403)

    def test_authenticated_mutations_require_token_and_logout_rotates_anonymous_token(self):
        token = self.client.get("/api/auth/session").get_json()["csrf_token"]
        signed_in = self.client.post(
            "/api/auth/login",
            json={"username": "admin@tangamandapio.local", "password": "Temporal-Admin-2026"},
            headers={"X-CSRF-Token": token},
        )
        authenticated_token = signed_in.get_json()["csrf_token"]

        missing = self.client.post(
            "/api/admin/users",
            json={"username": "csrf-user@tangamandapio.local", "password": "Temporal-Csrf-User-2026", "role": "sales"},
        )
        self.assertEqual(missing.status_code, 403)

        created = self.client.post(
            "/api/admin/users",
            json={"username": "csrf-user@tangamandapio.local", "password": "Temporal-Csrf-User-2026", "role": "sales"},
            headers={"X-CSRF-Token": authenticated_token},
        )
        self.assertEqual(created.status_code, 201)

        logout = self.client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": authenticated_token}
        )
        self.assertEqual(logout.status_code, 204)
        new_anonymous = self.client.get("/api/auth/session").get_json()
        self.assertFalse(new_anonymous["authenticated"])
        self.assertNotEqual(new_anonymous["csrf_token"], authenticated_token)


class PasswordManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "passwords.db")
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "BOOTSTRAP_ADMIN_USERNAME": "admin@tangamandapio.local",
            "BOOTSTRAP_ADMIN_PASSWORD": "Temporal-Admin-2026",
            "SECRET_KEY": "password-test-session-secret",
            "AUTO_DISPATCH_EVENTS": False,
            "FORCE_BOOTSTRAP_PASSWORD_CHANGE": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def session_token(client):
        return client.get("/api/auth/session").get_json()["csrf_token"]

    def login(self, client, username, password):
        token = self.session_token(client)
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": token},
        )
        return response

    def test_admin_reset_revokes_sessions_and_forces_self_service_change(self):
        admin_login = self.login(
            self.client, "admin@tangamandapio.local", "Temporal-Admin-2026"
        )
        self.assertEqual(admin_login.status_code, 200)
        admin_csrf = admin_login.get_json()["csrf_token"]
        created = self.client.post(
            "/api/admin/users",
            json={
                "username": "ventas@tangamandapio.local",
                "password": "Initial-Ventas-Password-2026",
                "role": "sales",
            },
            headers={"X-CSRF-Token": admin_csrf},
        )
        self.assertEqual(created.status_code, 201)
        user_id = created.get_json()["user"]["id"]
        self.assertTrue(created.get_json()["user"]["must_change_password"])

        sales_client = self.app.test_client()
        initial_login = self.login(
            sales_client, "ventas@tangamandapio.local", "Initial-Ventas-Password-2026"
        )
        self.assertEqual(initial_login.status_code, 200)
        self.assertTrue(initial_login.get_json()["user"]["must_change_password"])
        initial_password_change = sales_client.post(
            "/api/auth/password",
            json={
                "current_password": "Initial-Ventas-Password-2026",
                "new_password": "Established-Ventas-Password-2026!",
            },
            headers={"X-CSRF-Token": initial_login.get_json()["csrf_token"]},
        )
        self.assertEqual(initial_password_change.status_code, 200)
        established_login = self.login(
            sales_client, "ventas@tangamandapio.local", "Established-Ventas-Password-2026!"
        )
        self.assertFalse(established_login.get_json()["user"]["must_change_password"])
        forbidden_reset = sales_client.post(
            f"/api/admin/users/{admin_login.get_json()['user']['id']}/reset-password",
            json={},
            headers={"X-CSRF-Token": established_login.get_json()["csrf_token"]},
        )
        self.assertEqual(forbidden_reset.status_code, 403)
        old_session = sales_client.get("/api/auth/session").get_json()
        self.assertTrue(old_session["authenticated"])

        reset = self.client.post(
            f"/api/admin/users/{user_id}/reset-password",
            json={},
            headers={"X-CSRF-Token": admin_csrf},
        )
        self.assertEqual(reset.status_code, 200)
        temporary_password = reset.get_json()["temporary_password"]
        self.assertGreaterEqual(len(temporary_password), 20)
        self.assertTrue(reset.get_json()["must_change_password"])

        revoked = sales_client.get("/api/auth/session").get_json()
        self.assertFalse(revoked["authenticated"])
        self.assertEqual(sales_client.get("/api/orders").status_code, 401)
        old_password_login = self.login(
            sales_client, "ventas@tangamandapio.local", "Established-Ventas-Password-2026!"
        )
        self.assertEqual(old_password_login.status_code, 401)

        temporary_login = self.login(
            sales_client, "ventas@tangamandapio.local", temporary_password
        )
        self.assertEqual(temporary_login.status_code, 200)
        self.assertTrue(temporary_login.get_json()["user"]["must_change_password"])
        self.assertEqual(sales_client.get("/api/orders").status_code, 428)

        changed = sales_client.post(
            "/api/auth/password",
            json={
                "current_password": temporary_password,
                "new_password": "New-Ventas-Password-2026!",
            },
            headers={"X-CSRF-Token": temporary_login.get_json()["csrf_token"]},
        )
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(changed.get_json()["reauthenticate"])
        self.assertFalse(sales_client.get("/api/auth/session").get_json()["authenticated"])

        final_login = self.login(
            sales_client, "ventas@tangamandapio.local", "New-Ventas-Password-2026!"
        )
        self.assertEqual(final_login.status_code, 200)
        self.assertFalse(final_login.get_json()["user"]["must_change_password"])
        self.assertEqual(sales_client.get("/api/orders").status_code, 200)

        connection = sqlite3.connect(self.database_path)
        try:
            reset_audit = connection.execute(
                "SELECT detail FROM audit_log WHERE action = 'user.password_reset'"
            ).fetchone()[0]
            change_audit = connection.execute(
                "SELECT detail FROM audit_log WHERE action = 'auth.password_change'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertNotIn(temporary_password, reset_audit)
        self.assertIn('"sessions_revoked":true', change_audit)

    def test_admin_cannot_reset_own_password_and_invalid_change_is_rejected(self):
        admin_login = self.login(
            self.client, "admin@tangamandapio.local", "Temporal-Admin-2026"
        )
        token = admin_login.get_json()["csrf_token"]
        admin_id = admin_login.get_json()["user"]["id"]
        self_reset = self.client.post(
            f"/api/admin/users/{admin_id}/reset-password",
            json={},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(self_reset.status_code, 409)
        self.assertEqual(
            self_reset.get_json()["error"], "use_self_service_password_change"
        )
        too_short = self.client.post(
            "/api/auth/password",
            json={"current_password": "Temporal-Admin-2026", "new_password": "short"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(too_short.status_code, 400)
        wrong_current = self.client.post(
            "/api/auth/password",
            json={"current_password": "incorrecta", "new_password": "Another-Admin-Password-2026!"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(wrong_current.status_code, 403)
        reuse = self.client.post(
            "/api/auth/password",
            json={
                "current_password": "Temporal-Admin-2026",
                "new_password": "Temporal-Admin-2026",
            },
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(reuse.status_code, 400)

    def test_legacy_sqlite_users_receive_additive_authentication_columns(self):
        legacy_path = str(Path(self.temp_dir.name) / "legacy.db")
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, slug TEXT UNIQUE, created_at TEXT)")
            connection.execute("INSERT INTO companies VALUES (1, 'Tangamandapio', 'tangamandapio', '2026-01-01')")
            connection.execute("""
                CREATE TABLE portal_users (
                    id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
                    role TEXT, company_id INTEGER, active INTEGER, created_at TEXT
                )
            """)
            connection.execute("INSERT INTO portal_users VALUES (7, 'legacy@tangamandapio.local', 'hash', 'sales', 1, 1, '2026-01-01')")
            connection.commit()
        finally:
            connection.close()

        create_app({
            "TESTING": True,
            "DATABASE_PATH": legacy_path,
            "SECRET_KEY": "legacy-migration-test-secret",
            "BOOTSTRAP_ADMIN_PASSWORD": "",
        })
        connection = sqlite3.connect(legacy_path)
        try:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(portal_users)")}
            account = connection.execute(
                "SELECT id, auth_version, must_change_password FROM portal_users WHERE id = 7"
            ).fetchone()
        finally:
            connection.close()
        self.assertTrue({"auth_version", "must_change_password"}.issubset(columns))
        self.assertEqual(account, (7, 1, 0))


class AzureServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "azure-wms.db")
        self.app = create_azure_app({"TESTING": True, "FUNCTION_KEY": "test-key", "DATABASE_PATH": self.database_path})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

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

    def test_inventory_catalog_contains_the_full_synthetic_seed(self):
        inventory = self.client.get("/api/wms/inventory", headers={"x-functions-key": "test-key"})
        self.assertEqual(inventory.status_code, 200)
        payload = inventory.get_json()
        self.assertEqual(len(payload["items"]), 12)
        self.assertEqual(payload["mode"], "demo-inventory-ledger")

    def test_catalog_import_preserves_stock_and_seeds_new_synthetic_sku(self):
        headers = {"x-functions-key": "test-key"}
        initial = self.client.get("/api/wms/inventory", headers=headers).get_json()
        rice_before = next(item["on_hand"] for item in initial["items"] if item["sku"] == "SKU-ARROZ-001")
        imported = self.client.post(
            "/api/wms/catalog",
            headers=headers,
            json={"products": [
                {"sku": "SKU-ARROZ-001", "name": "Arroz actualizado", "unit": "saco", "unit_price": 45, "initial_stock": 999},
                {"sku": "SKU-NEW-101", "name": "Producto sintético", "unit": "caja", "unit_price": 12.5, "initial_stock": 7},
            ]},
        )
        self.assertEqual(imported.status_code, 200, imported.get_json())
        result = imported.get_json()
        self.assertEqual((result["created"], result["updated"]), (1, 1))
        catalog = self.client.get("/api/wms/inventory", headers=headers).get_json()["items"]
        by_sku = {item["sku"]: item for item in catalog}
        self.assertEqual(by_sku["SKU-ARROZ-001"]["on_hand"], rice_before)
        self.assertEqual(by_sku["SKU-NEW-101"]["on_hand"], 7)
        self.assertEqual(by_sku["SKU-NEW-101"]["name"], "Producto sintético")

    def test_catalog_import_rejects_boolean_price(self):
        response = self.client.post(
            "/api/wms/catalog",
            headers={"x-functions-key": "test-key"},
            json={"products": [
                {"sku": "SKU-BOOL-101", "name": "Producto", "unit": "caja", "unit_price": True, "initial_stock": 2},
            ]},
        )
        self.assertEqual(response.status_code, 400)

    def test_sales_and_purchase_events_change_demo_stock_once(self):
        headers = {"x-functions-key": "test-key"}
        sale = {"event_id": "evt-sale-stock-0001", "event_type": "order.created", "order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]}}
        first = self.client.post("/api/fulfillment/events", json=sale, headers=headers)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.get_json()["result"]["status"], "demo_fulfillment_completed")
        duplicate = self.client.post("/api/fulfillment/events", json=sale, headers=headers)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.get_json()["status"], "queued_duplicate")
        stock = self.client.get("/api/wms/inventory", headers=headers).get_json()
        self.assertEqual(next(item["on_hand"] for item in stock["items"] if item["sku"] == "SKU-ARROZ-001"), 23)

        purchase = {"event_id": "evt-purchase-stock-0001", "event_type": "purchase.received", "purchase_order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 4}]}}
        received = self.client.post("/api/fulfillment/events", json=purchase, headers=headers)
        self.assertEqual(received.status_code, 202)
        self.assertEqual(received.get_json()["result"]["status"], "demo_restock_completed")
        repeated = self.client.post("/api/fulfillment/events", json=purchase, headers=headers)
        self.assertEqual(repeated.status_code, 200)
        stock = self.client.get("/api/wms/inventory", headers=headers).get_json()
        self.assertEqual(next(item["on_hand"] for item in stock["items"] if item["sku"] == "SKU-ARROZ-001"), 27)

    def test_catalog_import_is_atomic_additive_and_new_skus_can_be_sold(self):
        headers = {"x-functions-key": "test-key"}
        response = self.client.post(
            "/api/wms/catalog",
            headers=headers,
            json={"products": [
                {"sku": "SKU-ARROZ-001", "name": "Arroz actualizado", "unit": "saco", "unit_price": 45.5, "initial_stock": 999},
                {"sku": "SKU-TEST-001", "name": "Producto sintético", "unit": "caja", "unit_price": 12.25, "initial_stock": 7},
            ]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"created": 1, "updated": 1, "stock_preserved": True, "mode": "demo-inventory-ledger"})

        inventory = self.client.get("/api/wms/inventory", headers=headers).get_json()
        by_sku = {item["sku"]: item for item in inventory["items"]}
        self.assertEqual(by_sku["SKU-ARROZ-001"]["on_hand"], 25)
        self.assertEqual(by_sku["SKU-ARROZ-001"]["unit_price"], 45.5)
        self.assertEqual(by_sku["SKU-TEST-001"]["on_hand"], 7)

        sale = self.client.post(
            "/api/fulfillment/events",
            headers=headers,
            json={"event_id": "evt-new-catalog-001", "event_type": "order.created", "order": {"items": [{"sku": "SKU-TEST-001", "quantity": 2}]}},
        )
        self.assertEqual(sale.status_code, 202)
        self.assertEqual(sale.get_json()["result"]["status"], "demo_fulfillment_completed")
        after_sale = self.client.get("/api/wms/inventory", headers=headers).get_json()
        self.assertEqual(next(item["on_hand"] for item in after_sale["items"] if item["sku"] == "SKU-TEST-001"), 5)

    def test_catalog_import_rejects_duplicate_rows_without_partial_write(self):
        headers = {"x-functions-key": "test-key"}
        response = self.client.post(
            "/api/wms/catalog",
            headers=headers,
            json={"products": [
                {"sku": "SKU-TEST-002", "name": "Uno", "unit": "unidad", "unit_price": 1, "initial_stock": 2},
                {"sku": "SKU-TEST-002", "name": "Duplicado", "unit": "unidad", "unit_price": 1, "initial_stock": 3},
            ]},
        )
        self.assertEqual(response.status_code, 400)
        inventory = self.client.get("/api/wms/inventory", headers=headers).get_json()
        self.assertNotIn("SKU-TEST-002", {item["sku"] for item in inventory["items"]})

    def test_insufficient_demo_stock_rejects_all_lines_without_partial_update(self):
        headers = {"x-functions-key": "test-key"}
        payload = {"event_id": "evt-stock-reject-0001", "event_type": "order.created", "order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 1000}, {"sku": "SKU-AZUCAR-001", "quantity": 1}]}}
        response = self.client.post("/api/fulfillment/events", json=payload, headers=headers)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["result"]["status"], "rejected_insufficient_stock")
        stock = self.client.get("/api/wms/inventory", headers=headers).get_json()
        balances = {item["sku"]: item["on_hand"] for item in stock["items"]}
        self.assertEqual(balances["SKU-ARROZ-001"], 25)
        self.assertEqual(balances["SKU-AZUCAR-001"], 40)


if __name__ == "__main__":
    unittest.main()
