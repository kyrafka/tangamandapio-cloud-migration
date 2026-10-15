import os
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

_test_root = tempfile.TemporaryDirectory(prefix="tangamandapio-release-tests-")
os.environ.setdefault("DATABASE_PATH", str(Path(_test_root.name) / "module-import.db"))
os.environ.setdefault("APP_SESSION_SECRET", "release-test-session-secret-not-for-production")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin@release.test")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "Release-Test-Admin-Password-2026!")

import app as portal


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


class ErpReleaseTests(unittest.TestCase):
    def setUp(self):
        self._db = tempfile.TemporaryDirectory(prefix="tangamandapio-erp-test-")
        self.database = str(Path(self._db.name) / "portal.sqlite")
        self.application = portal.create_app({
            "TESTING": True,
            "DATABASE_URL": "",
            "DATABASE_PATH": self.database,
            "APP_SESSION_SECRET": "release-test-session-secret-not-for-production",
            "BOOTSTRAP_ADMIN_USERNAME": "admin@release.test",
            "BOOTSTRAP_ADMIN_PASSWORD": "Release-Test-Admin-Password-2026!",
            "INTERNAL_ERP_ENABLED": True,
            "AZURE_FULFILLMENT_URL": "",
        })
        self.client = self.application.test_client()
        self.login(self.client, "admin@release.test", "Release-Test-Admin-Password-2026!")

    def tearDown(self):
        self._db.cleanup()

    @staticmethod
    def login(client, username, password):
        session = client.get("/api/auth/session").get_json()
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": session["csrf_token"]},
        )
        if response.status_code != 200:
            raise AssertionError(f"login failed: {response.status_code} {response.get_json()}")
        session = client.get("/api/auth/session").get_json()
        client.csrf = session["csrf_token"]

    def post(self, client, path, payload):
        return client.post(path, json=payload, headers={"X-CSRF-Token": client.csrf})

    def test_admin_can_open_module_and_database_has_additive_schema(self):
        page = self.client.get("/erp")
        self.assertEqual(page.status_code, 200)
        page.close()
        access = self.client.get("/api/erp/access")
        self.assertEqual(access.status_code, 200)
        self.assertIn("erp_admin", access.get_json()["roles"])
        with portal.connect(self.database) as connection:
            names = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        self.assertTrue({"erp_products", "erp_sales_orders", "erp_purchase_orders", "erp_financial_documents", "internal_messages"}.issubset(names))

    @patch("app.insert_audit", side_effect=RuntimeError("audit store unavailable"))
    def test_admin_user_creation_rolls_back_when_audit_insert_fails(self, _insert_audit):
        with self.assertRaisesRegex(RuntimeError, "audit store unavailable"):
            self.post(self.client, "/api/admin/users", {
                "username": "auditoria-falla@release.test",
                "password": "Release-Test-Sales-Password-2026!",
                "role": "sales",
            })

        users = self.client.get("/api/admin/users")
        self.assertEqual(users.status_code, 200)
        self.assertFalse(
            any(user["username"] == "auditoria-falla@release.test" for user in users.get_json())
        )

    def test_admin_user_update_rolls_back_when_audit_insert_fails(self):
        created = self.post(self.client, "/api/admin/users", {
            "username": "desactivar@release.test",
            "password": "Release-Test-Sales-Password-2026!",
            "role": "sales",
        })
        user_id = created.get_json()["user"]["id"]

        with patch("app.insert_audit", side_effect=RuntimeError("audit store unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit store unavailable"):
                self.client.patch(
                    f"/api/admin/users/{user_id}",
                    json={"active": False},
                    headers={"X-CSRF-Token": self.client.csrf},
                )

        users = self.client.get("/api/admin/users").get_json()
        user = next(item for item in users if item["id"] == user_id)
        self.assertTrue(user["active"])

    def test_admin_password_reset_rolls_back_when_audit_insert_fails(self):
        original_password = "Release-Test-Sales-Password-2026!"
        created = self.post(self.client, "/api/admin/users", {
            "username": "reset-rollback@release.test",
            "password": original_password,
            "role": "sales",
        })
        user_id = created.get_json()["user"]["id"]
        previous_session = self.application.test_client()
        self.login(previous_session, "reset-rollback@release.test", original_password)

        with patch("app.insert_audit", side_effect=RuntimeError("audit store unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit store unavailable"):
                self.post(self.client, f"/api/admin/users/{user_id}/reset-password", {})

        self.assertTrue(previous_session.get("/api/auth/session").get_json()["authenticated"])
        fresh_session = self.application.test_client()
        self.login(fresh_session, "reset-rollback@release.test", original_password)

    def test_sales_purchase_and_finance_workflows_persist_and_emit_outbox(self):
        partner = self.post(self.client, "/api/erp/partners", {
            "kind": "both", "name": "Socio ERP test", "tax_id": "ERP-TEST-01", "email": "erp@example.test",
        })
        self.assertEqual(partner.status_code, 201)
        inventory = ({"mode": "demo-inventory-ledger", "items": [{"sku": "SKU-ARROZ-001", "on_hand": 25}]}, None)
        with patch("erp_service.fetch_wms_inventory", return_value=inventory):
            sale = self.post(self.client, "/api/erp/sales/orders", {
                "partner_id": partner.get_json()["id"],
                "items": [{"sku": "SKU-ARROZ-001", "quantity": 2}],
            })
            purchase = self.post(self.client, "/api/erp/purchases/orders", {
                "partner_id": partner.get_json()["id"],
                "items": [{"sku": "SKU-ARROZ-001", "quantity": 4}],
            })
        self.assertEqual(sale.status_code, 201)
        self.assertEqual(purchase.status_code, 201)
        received = self.post(self.client, f"/api/erp/purchases/orders/{purchase.get_json()['id']}/receive", {})
        self.assertEqual(received.status_code, 202)
        self.assertEqual(received.get_json()["status"], "receipt_pending")
        expense = self.post(self.client, "/api/erp/finance/expenses", {"description": "Gasto de prueba", "amount": 18.25})
        self.assertEqual(expense.status_code, 201)
        settled = self.post(self.client, f"/api/erp/finance/documents/{expense.get_json()['id']}/settle", {})
        self.assertEqual(settled.get_json()["status"], "paid")
        with portal.connect(self.database) as connection:
            outbox_count = connection.execute("SELECT COUNT(*) AS n FROM outbox_events").fetchone()["n"]
        self.assertGreaterEqual(outbox_count, 2)

    def test_internal_mail_is_private_csrf_protected_and_role_aware(self):
        no_csrf = self.client.post("/api/erp/mail", json={"recipient_id": 1, "subject": "x", "body": "y"})
        self.assertEqual(no_csrf.status_code, 403)
        created = self.post(self.client, "/api/admin/users", {
            "username": "ventas@release.test",
            "password": "Release-Test-Sales-Password-2026!",
            "role": "sales",
        })
        self.assertEqual(created.status_code, 201)
        sales_user = created.get_json()["user"]
        sales_client = self.application.test_client()
        self.login(sales_client, "ventas@release.test", "Release-Test-Sales-Password-2026!")
        roles = sales_client.get("/api/erp/access").get_json()["roles"]
        self.assertIn("erp_sales", roles)
        self.assertEqual(sales_client.get("/api/erp/finance/documents").status_code, 403)
        sent = self.post(sales_client, "/api/erp/mail", {
            "recipient_id": 1, "subject": "Coordinación", "body": "Pedido listo para revisión.",
        })
        self.assertEqual(sent.status_code, 201)
        inbox = self.client.get("/api/erp/mail?folder=inbox").get_json()
        self.assertEqual(inbox[0]["subject"], "Coordinación")
        self.assertTrue(inbox[0]["unread"])
        read = self.post(self.client, f"/api/erp/mail/{inbox[0]['id']}/read", {})
        self.assertTrue(read.get_json()["read"])
        stranger = sales_client.get("/api/erp/mail?folder=invalid")
        self.assertEqual(stranger.status_code, 400)

    def test_internal_mail_is_dispatched_to_configured_smtp_relay(self):
        created = self.post(self.client, "/api/admin/users", {
            "username": "ventas@release.test",
            "password": "Release-Test-Sales-Password-2026!",
            "role": "sales",
        })
        self.assertEqual(created.status_code, 201)
        smtp = CapturingSMTPServer()
        smtp_thread = threading.Thread(target=smtp.serve_forever, daemon=True)
        smtp_thread.start()
        self.addCleanup(smtp.server_close)
        self.addCleanup(smtp.shutdown)
        self.application.config.update({
            "ERP_SMTP_HOST": "127.0.0.1",
            "ERP_SMTP_PORT": smtp.server_address[1],
            "ERP_SMTP_SECURITY": "none",
            "ERP_SMTP_FROM": "no-reply@release.test",
            "ERP_SMTP_RECIPIENT_DOMAIN": "release.test",
        })
        sent = self.post(self.client, "/api/erp/mail", {
            "recipient_id": created.get_json()["user"]["id"],
            "subject": "Release SMTP check",
            "body": "This message uses the SMTP protocol.",
        })
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(sent.get_json()["smtp_status"], "accepted_by_smtp")
        self.assertEqual(len(smtp.messages), 1)
        self.assertIn("To: ventas@release.test", smtp.messages[0])
        self.assertEqual(self.client.get("/api/erp/mail?folder=sent").get_json()[0]["smtp_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
