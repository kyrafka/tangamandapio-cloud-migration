import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


APP_PATH = Path(__file__).resolve().parents[1] / "current" / "app.py"
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="portal-platform-import-")
_import_environment = {
    "DATABASE_URL": "",
    "DATABASE_PATH": str(Path(_bootstrap_dir.name) / "bootstrap.sqlite3"),
    "APP_SESSION_SECRET": "test-only-platform-secret",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "DB_SECRET_ARN": "",
    "VOICE_RECORDINGS_BUCKET": "",
    "VOICE_RECORDINGS_ENABLED": "false",
}
with patch.dict(os.environ, _import_environment):
    if str(APP_PATH.parent) not in sys.path:
        sys.path.insert(0, str(APP_PATH.parent))
    spec = importlib.util.spec_from_file_location("portal_platform_release", APP_PATH)
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)


class FakeCloudWatch:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def get_metric_data(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        timestamp = datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc)
        return {
            "MetricDataResults": [
                {
                    "Id": query["Id"],
                    "Label": query["Label"],
                    "StatusCode": "Complete",
                    "Timestamps": [timestamp, timestamp.replace(minute=5)],
                    "Values": [2, 4],
                }
                for query in kwargs["MetricDataQueries"]
            ]
        }


class FakeJsonResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class FakeSNS:
    def __init__(self):
        self.topic = "arn:aws:sns:us-east-1:841113066612:tangamandapio-test-alarms"
        self.subscriptions = [
            {
                "Protocol": "email",
                "Endpoint": "confirmed@example.test",
                "SubscriptionArn": self.topic + ":confirmed-id",
            },
            {
                "Protocol": "email",
                "Endpoint": "pending@example.test",
                "SubscriptionArn": "PendingConfirmation",
            },
            {
                "Protocol": "https",
                "Endpoint": "https://receiver.example.test/hook",
                "SubscriptionArn": self.topic + ":https-id",
            },
        ]
        self.calls = []

    def list_subscriptions_by_topic(self, **kwargs):
        self.calls.append(("list", kwargs))
        return {"Subscriptions": list(self.subscriptions)}

    def subscribe(self, **kwargs):
        self.calls.append(("subscribe", kwargs))
        self.subscriptions.append(
            {
                "Protocol": "email",
                "Endpoint": kwargs["Endpoint"],
                "SubscriptionArn": "PendingConfirmation",
            }
        )
        return {"SubscriptionArn": "PendingConfirmation"}

    def unsubscribe(self, **kwargs):
        self.calls.append(("unsubscribe", kwargs))
        self.subscriptions = [
            item
            for item in self.subscriptions
            if item["SubscriptionArn"] != kwargs["SubscriptionArn"]
        ]


class PlatformConsoleTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="portal-platform-test-")
        self.cloudwatch = FakeCloudWatch()
        self.app = portal.create_app(
            {
                "TESTING": True,
                "METRICS_ENABLED": False,
                "DATABASE_URL": "",
                "DATABASE_PATH": str(Path(self.tempdir.name) / "portal.sqlite3"),
                "SECRET_KEY": "test-session-secret-for-platform",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@example.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Admin-Password-For-Tests-2026",
                "VOICE_RECORDINGS_ENABLED": False,
                "AUTO_DISPATCH_EVENTS": False,
                "LOGIN_RATE_LIMIT_MAX": 2,
                "LOGIN_RATE_LIMIT_SECONDS": 300,
                "CLOUDWATCH_CLIENT": self.cloudwatch,
                "CLOUDWATCH_REGION_NAME": "us-east-1",
                "CLOUDWATCH_LOAD_BALANCER_FULL_NAME": "app/tangamandapio-test/abc123",
                "CLOUDWATCH_TARGET_GROUP_FULL_NAME": "targetgroup/tangamandapio-test/def456",
                "CLOUDWATCH_RDS_INSTANCE_ID": "tangamandapio-postgres",
                "CLOUDWATCH_AUTO_SCALING_GROUP": "tangamandapio-asg",
                "CLOUDWATCH_WAF_WEB_ACL_NAME": "tangamandapio-acl",
                "CLOUDWATCH_WAF_REGION": "us-east-1",
            }
        )
        self.admin, self.admin_csrf = self.login("admin@example.test", "Admin-Password-For-Tests-2026")
        self.company_id = self.admin.get("/api/auth/session").get_json()["user"]["company_id"]
        self.sales_id = self.create_user("sales@example.test", "sales")
        self.operations_id = self.create_user("operations@example.test", "operations")

    def tearDown(self):
        self.tempdir.cleanup()

    def login(self, username, password):
        client = self.app.test_client()
        csrf = client.get("/api/auth/session").get_json()["csrf_token"]
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return client, client.get("/api/auth/session").get_json()["csrf_token"]

    def test_login_failures_are_throttled_and_success_resets_counter(self):
        client = self.app.test_client()

        def authenticate(password):
            csrf = client.get("/api/auth/session").get_json()["csrf_token"]
            return client.post(
                "/api/auth/login",
                json={"username": "admin@example.test", "password": password},
                headers={"X-CSRF-Token": csrf},
            )

        self.assertEqual(authenticate("incorrecta").status_code, 401)
        self.assertEqual(authenticate("Admin-Password-For-Tests-2026").status_code, 200)
        self.assertEqual(authenticate("incorrecta").status_code, 401)
        self.assertEqual(authenticate("incorrecta").status_code, 401)

        limited = authenticate("incorrecta")
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.get_json()["error"], "too_many_attempts")
        self.assertGreaterEqual(int(limited.headers["Retry-After"]), 1)

        with portal.connect(self.app.config["DATABASE_PATH"]) as connection:
            attempt_keys = connection.execute(
                "SELECT attempt_key FROM login_attempts"
            ).fetchall()
        self.assertEqual(len(attempt_keys), 1)
        self.assertNotIn("admin@example.test", attempt_keys[0]["attempt_key"])

    def create_user(self, username, role):
        response = self.admin.post(
            "/api/admin/users",
            json={
                "username": username,
                "password": "Temporary-Password-2026",
                "role": role,
                "company_id": self.company_id,
            },
            headers={"X-CSRF-Token": self.admin_csrf},
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["user"]["id"]

    def test_admin_and_operations_can_open_console_but_other_roles_cannot(self):
        response = self.admin.get("/platform")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nube, seguridad y capacidad", response.get_data())
        response.close()
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        response = operations.get("/platform")
        self.assertEqual(response.status_code, 200)
        response.close()
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        self.assertEqual(sales.get("/platform").status_code, 403)
        self.assertEqual(sales.get("/api/platform/overview").status_code, 403)

    def test_release_api_authorization_matrix_for_portal_roles(self):
        warehouse_id = self.create_user("warehouse@example.test", "warehouse")
        auditor_id = self.create_user("auditor@example.test", "auditor")
        customer_id = self.create_user("customer@example.test", "customer")
        self.assertTrue(warehouse_id and auditor_id and customer_id)

        clients = {
            "admin": (self.admin, self.admin_csrf),
            "operations": self.login("operations@example.test", "Temporary-Password-2026"),
            "sales": self.login("sales@example.test", "Temporary-Password-2026"),
            "warehouse": self.login("warehouse@example.test", "Temporary-Password-2026"),
            "auditor": self.login("auditor@example.test", "Temporary-Password-2026"),
            "customer": self.login("customer@example.test", "Temporary-Password-2026"),
        }
        all_roles = {"admin", "operations", "sales", "warehouse", "auditor", "customer"}
        allowed = {
            "/api/orders": all_roles,
            "/api/outbox": {"admin", "operations", "warehouse", "auditor"},
            "/api/audit": {"admin", "operations", "auditor"},
            "/api/admin/users": {"admin"},
            "/api/platform/overview": {"admin", "operations"},
            "/api/voice/directory": {"admin", "operations", "sales"},
            "/api/erp/access": {"admin", "operations", "sales", "warehouse", "auditor"},
            "/api/erp/partners": {"admin", "sales", "auditor"},
            "/api/erp/finance/documents": {"admin", "auditor"},
            "/api/multicloud": {"admin", "operations", "warehouse", "auditor"},
        }

        self.app.config["AZURE_FULFILLMENT_URL"] = "https://wms.azurewebsites.net"
        with patch.object(portal, "urlopen", return_value=FakeJsonResponse({"status": "ok"})):
            for path, allowed_roles in allowed.items():
                for role, (client, _csrf) in clients.items():
                    with self.subTest(path=path, role=role):
                        response = client.get(path)
                        self.assertEqual(response.status_code, 200 if role in allowed_roles else 403)

        for role, (client, csrf) in clients.items():
            with self.subTest(action="create_order", role=role):
                response = client.post(
                    "/api/orders",
                    json={"customer": f"RBAC {role}", "total": 1},
                    headers={"X-CSRF-Token": csrf},
                )
                self.assertEqual(response.status_code, 201 if role in {"admin", "sales", "customer"} else 403)

            with self.subTest(action="create_expense", role=role):
                response = client.post(
                    "/api/erp/finance/expenses",
                    json={"description": "Prueba de permisos", "amount": 1},
                    headers={"X-CSRF-Token": csrf},
                )
                self.assertEqual(response.status_code, 201 if role == "admin" else 403)

    def test_console_assets_are_served_from_the_same_origin(self):
        for path in (
            "/assets/platform-console.js",
            "/assets/platform-console.css",
            "/assets/platform-shortcut.js",
        ):
            response = self.admin.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertGreater(len(response.get_data()), 100, path)
            response.close()

    def test_release_homepage_references_assets_served_by_flask(self):
        page = self.admin.get("/")
        try:
            self.assertEqual(page.status_code, 200)
            assets = set(re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', page.get_data()))
            self.assertTrue(assets, "el HTML del release debe declarar sus bundles")
        finally:
            page.close()

        for asset_path in assets:
            with self.subTest(asset=asset_path.decode("ascii")):
                asset = self.admin.get(asset_path.decode("ascii"))
                try:
                    self.assertEqual(asset.status_code, 200)
                    self.assertGreater(len(asset.get_data()), 100)
                finally:
                    asset.close()

    def test_anonymous_user_is_redirected_and_api_requires_login(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get("/platform").status_code, 303)
        self.assertEqual(anonymous.get("/api/platform/overview").status_code, 401)

    def test_public_diagnostics_do_not_expose_internal_hostnames(self):
        anonymous = self.app.test_client()
        for path in ("/api", "/health", "/ready"):
            with self.subTest(path=path):
                response = anonymous.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("instance", response.get_json())
                if path == "/health":
                    self.assertEqual(response.get_json()["status"], "ok")
                    self.assertNotIn("database", response.get_json())

    def test_health_failure_does_not_identify_the_dependency(self):
        with patch.object(portal, "connect", side_effect=RuntimeError("postgres.internal:5432")):
            response = self.app.test_client().get("/health")
        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["status"], "degraded")
        self.assertNotIn("database", payload)
        self.assertNotIn("postgres.internal", json.dumps(payload))

    def test_metrics_are_disabled_by_default_and_can_be_enabled_explicitly(self):
        anonymous = self.app.test_client()
        disabled = anonymous.get("/metrics")
        self.assertEqual(disabled.status_code, 404)
        self.assertEqual(disabled.get_data(), b"")

        self.app.config["METRICS_ENABLED"] = True
        self.assertEqual(anonymous.get("/metrics").status_code, 401)
        enabled = self.admin.get("/metrics")
        self.assertEqual(enabled.status_code, 200)
        self.assertIn(b"tangamandapio_http_requests_total", enabled.get_data())
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        self.assertEqual(sales.get("/metrics").status_code, 403)

    def test_outbox_is_visible_to_operations_but_not_sales(self):
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        response = operations.get("/api/outbox")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        self.assertEqual(sales.get("/api/outbox").status_code, 403)
        self.assertIn(b"fulfillment-status", self.admin.get("/assets/platform-console.js").get_data())

    def test_auto_dispatch_runs_after_the_order_and_outbox_are_committed(self):
        self.app.config["AUTO_DISPATCH_EVENTS"] = True
        observed = {}

        def dispatch_after_commit(app, database_path, event_id):
            with portal.connect(database_path) as connection:
                event = connection.execute(
                    "SELECT status FROM outbox_events WHERE event_id = ?", (event_id,)
                ).fetchone()
            observed["event_id"] = event_id
            observed["status_before_dispatch"] = event["status"]
            return {"status": "delivered", "event_id": event_id}

        with patch.object(portal, "dispatch_outbox_event", side_effect=dispatch_after_commit) as dispatch:
            response = self.admin.post(
                "/api/orders",
                json={"customer": "Prueba automática", "reference": "AUTO-DISPATCH-TEST", "total": 1.0},
                headers={"X-CSRF-Token": self.admin_csrf},
            )

        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()["fulfillment"]["status"], "delivered")
        self.assertEqual(observed["event_id"], response.get_json()["fulfillment"]["event_id"])
        self.assertEqual(observed["status_before_dispatch"], "pending")
        dispatch.assert_called_once_with(self.app, self.app.config["DATABASE_PATH"], observed["event_id"])

    def test_wms_inventory_is_proxied_server_side_and_role_protected(self):
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test/api/fulfillment/events",
            AZURE_FUNCTION_KEY="secret-test-key",
        )
        inventory = {
            "mode": "demo-inventory-ledger",
            "is_real_erp": False,
            "items": [{"sku": "SKU-ARROZ-001", "on_hand": 25}],
        }
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        sales, _ = self.login("sales@example.test", "Temporary-Password-2026")
        with patch.object(portal, "urlopen", return_value=FakeJsonResponse(inventory)) as upstream:
            response = operations.get("/api/wms/inventory")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"][0]["on_hand"], 25)
        request = upstream.call_args.args[0]
        self.assertEqual(request.full_url, "https://wms.example.test/api/wms/inventory")
        self.assertEqual(request.get_header("X-functions-key"), "secret-test-key")
        self.assertEqual(sales.get("/api/wms/inventory").status_code, 403)

    def test_demo_order_persists_sku_quantity_and_durable_outbox_event(self):
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test/api/fulfillment/events",
            AZURE_FUNCTION_KEY="secret-test-key",
        )
        inventory = {
            "mode": "demo-inventory-ledger",
            "items": [{"sku": "SKU-ARROZ-001", "on_hand": 25}],
        }
        operations, csrf = self.login("operations@example.test", "Temporary-Password-2026")
        with patch.object(portal, "urlopen", return_value=FakeJsonResponse(inventory)):
            response = operations.post(
                "/api/wms/demo-orders",
                json={"sku": "SKU-ARROZ-001", "quantity": 2},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(response.status_code, 201, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload["total"], 85.0)
        with portal.connect(portal.configured_database_target(self.app.config)) as connection:
            order = connection.execute("SELECT items_json FROM orders WHERE id = ?", (payload["id"],)).fetchone()
            event = connection.execute("SELECT payload, status FROM outbox_events WHERE event_id = ?", (payload["event_id"],)).fetchone()
            audit = connection.execute(
                "SELECT action FROM audit_log WHERE subject_type = 'order' AND subject_id = ?",
                (str(payload["id"]),),
            ).fetchone()
        self.assertEqual(json.loads(order["items_json"])[0]["quantity"], 2)
        self.assertEqual(json.loads(event["payload"])["order"]["items"], [{"sku": "SKU-ARROZ-001", "quantity": 2}])
        self.assertEqual(event["status"], "pending")
        self.assertEqual(audit["action"], "wms.demo_order.create")

    def test_demo_order_rejects_quantity_above_available_stock_without_insert(self):
        self.app.config.update(
            AZURE_FULFILLMENT_URL="https://wms.example.test/api/fulfillment/events",
            AZURE_FUNCTION_KEY="secret-test-key",
        )
        inventory = {"mode": "demo-inventory-ledger", "items": [{"sku": "SKU-ARROZ-001", "on_hand": 1}]}
        operations, csrf = self.login("operations@example.test", "Temporary-Password-2026")
        before = len(operations.get("/api/orders").get_json())
        with patch.object(portal, "urlopen", return_value=FakeJsonResponse(inventory)):
            response = operations.post(
                "/api/wms/demo-orders",
                json={"sku": "SKU-ARROZ-001", "quantity": 2},
                headers={"X-CSRF-Token": csrf},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"], "insufficient_demo_stock")
        self.assertEqual(len(operations.get("/api/orders").get_json()), before)

    def test_cloudwatch_metric_query_returns_series_and_posture(self):
        response = self.admin.get("/api/platform/overview?window=360")
        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertEqual(payload["cloudwatch"]["status"], "ok")
        self.assertEqual(payload["cloudwatch"]["window_minutes"], 360)
        self.assertEqual(payload["cloudwatch"]["metrics"]["alb_requests"]["latest"], 4)
        self.assertEqual(payload["cloudwatch"]["metrics"]["waf_blocked"]["points"][0]["value"], 2)
        self.assertEqual(self.cloudwatch.calls[0]["MetricDataQueries"][0]["MetricStat"]["Period"], 300)
        self.assertEqual(payload["security"]["database"], "sqlite_demo")
        self.assertTrue(payload["security"]["waf_enabled"])
        self.assertTrue(payload["security"]["csrf"] == "enabled")

    def test_waf_posture_is_false_when_no_web_acl_metrics_are_configured(self):
        self.app.config["CLOUDWATCH_WAF_WEB_ACL_NAME"] = ""
        self.app.config["CLOUDWATCH_WAF_REGION"] = ""

        response = self.admin.get("/api/platform/overview?window=60")

        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertFalse(response.get_json()["security"]["waf_enabled"])

    def test_missing_metric_identifiers_are_reported_not_fabricated(self):
        app = portal.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": str(Path(self.tempdir.name) / "no-metrics.sqlite3"),
                "SECRET_KEY": "test-session-secret-for-platform",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@example.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Admin-Password-For-Tests-2026",
                "VOICE_RECORDINGS_ENABLED": False,
                "AUTO_DISPATCH_EVENTS": False,
                "CLOUDWATCH_CLIENT": self.cloudwatch,
                "CLOUDWATCH_LOAD_BALANCER_FULL_NAME": "",
                "CLOUDWATCH_TARGET_GROUP_FULL_NAME": "",
                "CLOUDWATCH_RDS_INSTANCE_ID": "",
                "CLOUDWATCH_AUTO_SCALING_GROUP": "",
                "CLOUDWATCH_WAF_WEB_ACL_NAME": "",
                "CLOUDWATCH_WAF_REGION": "",
            }
        )
        with app.test_client() as test_client:
            csrf = test_client.get("/api/auth/session").get_json()["csrf_token"]
            logged_in = test_client.post(
                "/api/auth/login",
                json={"username": "admin@example.test", "password": "Admin-Password-For-Tests-2026"},
                headers={"X-CSRF-Token": csrf},
            )
            self.assertEqual(logged_in.status_code, 200)
            result = test_client.get("/api/platform/overview").get_json()["cloudwatch"]
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(self.cloudwatch.calls, [])

    def test_denied_cloudwatch_permissions_are_safe_and_explicit(self):
        class AccessDenied(Exception):
            response = {"Error": {"Code": "AccessDeniedException", "Message": "details should not be returned"}}

        self.app.config["CLOUDWATCH_CLIENT"] = FakeCloudWatch(error=AccessDenied())
        result = self.admin.get("/api/platform/overview").get_json()["cloudwatch"]
        self.assertEqual(result["status"], "access_denied")
        self.assertNotIn("details should not be returned", str(result))

    def test_unsupported_metrics_window_is_rejected(self):
        self.assertEqual(self.admin.get("/api/platform/overview?window=5").status_code, 400)

    def test_administration_console_is_an_admin_only_full_view(self):
        admin_response = self.admin.get("/administracion")
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b"Administraci\xc3\xb3n general", admin_response.data)
        self.assertIn(b"Destinatarios de alarmas", admin_response.data)
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        self.assertEqual(operations.get("/administracion").status_code, 403)
        self.assertEqual(operations.get("/api/admin/alarm-subscriptions").status_code, 403)
        self.assertEqual(self.app.test_client().get("/api/admin/alarm-subscriptions").status_code, 401)

    def test_alarm_subscriptions_are_admin_only_and_email_only(self):
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = FakeSNS().topic
        sns = FakeSNS()
        with patch.object(portal, "_alarm_sns_client", return_value=sns):
            result = self.admin.get("/api/admin/alarm-subscriptions")
        self.assertEqual(result.status_code, 200, result.get_json())
        payload = result.get_json()
        self.assertEqual(payload["topic_configured"], True)
        self.assertEqual([item["endpoint"] for item in payload["subscriptions"]], [
            "confirmed@example.test", "pending@example.test"
        ])
        self.assertEqual(
            [item["status"] for item in payload["subscriptions"]],
            ["confirmed", "pending_confirmation"],
        )
        self.assertNotIn("https://receiver.example.test/hook", str(payload))
        operations, _ = self.login("operations@example.test", "Temporary-Password-2026")
        self.assertEqual(operations.get("/api/admin/alarm-subscriptions").status_code, 403)

    def test_alarm_subscription_add_requires_valid_email_and_confirmation(self):
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = FakeSNS().topic
        sns = FakeSNS()
        with patch.object(portal, "_alarm_sns_client", return_value=sns):
            invalid = self.admin.post(
                "/api/admin/alarm-subscriptions",
                json={"email": "not-an-email"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
            self.assertEqual(invalid.status_code, 400)
            self.assertEqual(sns.calls, [])
            duplicate = self.admin.post(
                "/api/admin/alarm-subscriptions",
                json={"email": "CONFIRMED@example.test"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
            self.assertEqual(duplicate.status_code, 200)
            self.assertTrue(duplicate.get_json()["already_exists"])
            created = self.admin.post(
                "/api/admin/alarm-subscriptions",
                json={"email": "alerts@example.test"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()["subscription"]["status"], "pending_confirmation")
        self.assertEqual(created.get_json()["subscription"]["endpoint"], "alerts@example.test")
        audit = self.admin.get("/api/audit").get_json()
        entry = next(item for item in audit if item["action"] == "alarm_subscription.create")
        self.assertNotIn("alerts@example.test", str(entry))

    def test_alarm_unsubscribe_requires_exact_confirmed_subscription_and_uses_unsigned_sns(self):
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = FakeSNS().topic
        sns = FakeSNS()
        clients = []

        def sns_client(_config, unsigned=False):
            clients.append(unsigned)
            return sns

        with patch.object(portal, "_alarm_sns_client", side_effect=sns_client):
            foreign = self.admin.delete(
                "/api/admin/alarm-subscriptions",
                json={"subscription_arn": "arn:aws:sns:us-east-1:999999999999:other-topic:foreign"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
            pending = self.admin.delete(
                "/api/admin/alarm-subscriptions",
                json={"subscription_arn": "PendingConfirmation"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
            removed = self.admin.delete(
                "/api/admin/alarm-subscriptions",
                json={"subscription_arn": sns.topic + ":confirmed-id"},
                headers={"X-CSRF-Token": self.admin_csrf},
            )
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(pending.status_code, 404)
        self.assertEqual(removed.status_code, 200, removed.get_json())
        self.assertEqual(clients, [False, True])
        self.assertIn(("unsubscribe", {"SubscriptionArn": sns.topic + ":confirmed-id"}), sns.calls)
        audit = self.admin.get("/api/audit").get_json()
        self.assertTrue(any(item["action"] == "alarm_subscription.remove" for item in audit))

    def test_alarm_routes_report_missing_topic_without_calling_aws(self):
        self.app.config["ALARM_NOTIFICATION_TOPIC_ARN"] = ""
        with patch.object(portal, "_alarm_sns_client") as sns_factory:
            response = self.admin.get("/api/admin/alarm-subscriptions")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "alarm_notifications_not_configured"})
        sns_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
