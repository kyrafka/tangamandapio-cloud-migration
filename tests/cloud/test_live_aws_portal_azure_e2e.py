from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_aws_portal_azure_e2e as live_e2e  # noqa: E402


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask release dependencies are required")
class TemporaryRoleMatrixIntegrationTests(unittest.TestCase):
    """Exercise the real matrix against the portal without any cloud calls."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="tangama-role-matrix-")
        self.addCleanup(self.temp.cleanup)
        release = Path(__file__).resolve().parents[2] / "app" / "aws_release" / "current"
        sys.path.insert(0, str(release))
        self.addCleanup(sys.path.remove, str(release))
        environment = {
            "DATABASE_URL": "",
            "DATABASE_PATH": str(Path(self.temp.name) / "import.sqlite"),
            "APP_SESSION_SECRET": "integration-test-session-secret-only",
            "BOOTSTRAP_ADMIN_USERNAME": live_e2e.ADMIN_USERNAME,
            "BOOTSTRAP_ADMIN_PASSWORD": "Temporary-Admin-Test-Password!",
            "OUTBOX_RETRY_INTERVAL": "0",
        }
        with patch.dict(os.environ, environment):
            spec = importlib.util.spec_from_file_location("matrix_test_portal", release / "app.py")
            portal = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(portal)
        self.app = portal.create_app({
            "TESTING": True,
            "DATABASE_URL": "",
            "DATABASE_PATH": str(Path(self.temp.name) / "matrix.sqlite"),
            "APP_SESSION_SECRET": "integration-test-session-secret-only",
            "BOOTSTRAP_ADMIN_USERNAME": live_e2e.ADMIN_USERNAME,
            "BOOTSTRAP_ADMIN_PASSWORD": "Temporary-Admin-Test-Password!",
            "FORCE_INITIAL_PASSWORD_CHANGE": True,
            "INTERNAL_ERP_ENABLED": True,
            "OUTBOX_RETRY_INTERVAL": 0,
            "AZURE_FULFILLMENT_URL": "",
        })

        class FlaskOpener:
            def __init__(self, client):
                self.client = client

            def open(self, request, timeout=None):
                parsed = urlsplit(request.full_url)
                path = parsed.path + ("?" + parsed.query if parsed.query else "")
                response = self.client.open(
                    path,
                    method=request.get_method(),
                    data=request.data,
                    headers=dict(request.header_items()),
                    base_url=f"{parsed.scheme}://{parsed.netloc}",
                )
                if response.status_code >= 400:
                    raise HTTPError(request.full_url, response.status_code, "error", response.headers, io.BytesIO(response.data))

                class Result:
                    status = response.status_code
                    headers = response.headers

                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        response.close()

                    def read(self):
                        return response.get_data()

                return Result()

        opener = patch.object(live_e2e, "build_opener", side_effect=lambda *args: FlaskOpener(self.app.test_client()))
        opener.start()
        self.addCleanup(opener.stop)
        # Access to the pre-existing demo account or its SSM parameter must not be needed.
        parameter = patch.object(live_e2e, "get_secure_parameter", side_effect=AssertionError("unexpected QA parameter lookup"))
        parameter.start()
        self.addCleanup(parameter.stop)
        self.admin = live_e2e.PortalClient("loopback")
        self.admin.login(username=live_e2e.ADMIN_USERNAME, password="Temporary-Admin-Test-Password!")

    def test_matrix_rotates_temporary_passwords_and_deactivates_all_without_demo_user(self) -> None:
        result = live_e2e.exercise_erp_role_matrix(self.admin)
        self.assertEqual(result["temporary_account_count"], 5)
        self.assertEqual(result["probe_count"], 48)
        self.assertEqual(set(result["roles"]), {"erp_admin", "erp_sales", "erp_finance", "erp_purchasing", "erp_master_data", "erp_auditor"})
        _, users = self.admin.request("GET", "/api/admin/users")
        qa_users = [user for user in users if user["username"].startswith("qa-erp_")]
        self.assertEqual(len(qa_users), 5)
        self.assertTrue(all(not user["active"] for user in qa_users))
        self.assertTrue(all(not user["must_change_password"] for user in qa_users))
        self.assertFalse(any(user["username"] == live_e2e.ROLE_ACCOUNTS[0][1] for user in users))

    def test_password_rotation_failure_still_deactivates_created_account(self) -> None:
        self.app.view_functions["change_own_password"] = lambda: ("unavailable", 500)
        with self.assertRaises(live_e2e.SmokeFailure):
            live_e2e.exercise_erp_role_matrix(self.admin)
        _, users = self.admin.request("GET", "/api/admin/users")
        qa_users = [user for user in users if user["username"].startswith("qa-erp_")]
        self.assertEqual(len(qa_users), 1)
        self.assertFalse(qa_users[0]["active"])

    def test_matrix_rotates_new_users_even_if_a_demo_account_exists(self) -> None:
        self.app.config["FORCE_INITIAL_PASSWORD_CHANGE"] = False
        status, created = self.admin.request("POST", "/api/admin/users", {
            "username": live_e2e.ROLE_ACCOUNTS[0][1],
            "password": "Temporary-Demo-Test-Password!",
            "role": "sales",
        })
        self.assertEqual(status, 201)
        self.app.config["FORCE_INITIAL_PASSWORD_CHANGE"] = True
        with patch.object(live_e2e, "get_secure_parameter", return_value="Temporary-Demo-Test-Password!"):
            result = live_e2e.exercise_erp_role_matrix(self.admin)
        self.assertEqual(result["temporary_account_count"], 5)
        _, users = self.admin.request("GET", "/api/admin/users")
        demo = next(user for user in users if user["id"] == created["user"]["id"])
        self.assertTrue(demo["active"])
        self.assertFalse(demo["must_change_password"])

    def test_name_conflict_does_not_deactivate_an_existing_account(self) -> None:
        username = "qa-erp_sales-20261103120000-collision@tangamandapio.local"
        status, created = self.admin.request("POST", "/api/admin/users", {
            "username": username,
            "password": "Preexisting-Test-Password!",
            "role": "sales",
        })
        self.assertEqual(status, 201)
        with (
            patch.object(live_e2e, "datetime") as clock,
            patch.object(live_e2e.secrets, "token_hex", return_value="collision"),
            self.assertRaises(live_e2e.SmokeFailure),
        ):
            clock.now.return_value = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
            live_e2e.exercise_erp_role_matrix(self.admin)
        _, users = self.admin.request("GET", "/api/admin/users")
        existing = next(user for user in users if user["id"] == created["user"]["id"])
        self.assertTrue(existing["active"])

    def test_cleanup_continues_after_unexpected_failure_for_one_user(self) -> None:
        original_request = self.admin.request
        failed_once = False

        def fail_first_deactivation(method, path, payload=None, accepted_statuses=()):
            nonlocal failed_once
            if method == "PATCH" and path.startswith("/api/admin/users/") and not failed_once:
                failed_once = True
                raise RuntimeError("synthetic cleanup failure")
            return original_request(method, path, payload, accepted_statuses)

        with patch.object(self.admin, "request", side_effect=fail_first_deactivation):
            with self.assertRaisesRegex(live_e2e.SmokeFailure, "could not all be confirmed inactive"):
                live_e2e.exercise_erp_role_matrix(self.admin)
        _, users = original_request("GET", "/api/admin/users")
        qa_users = [user for user in users if user["username"].startswith("qa-erp_")]
        self.assertEqual(len(qa_users), 5)
        self.assertEqual(sum(bool(user["active"]) for user in qa_users), 1)


class PortalLoginRoleTests(unittest.TestCase):
    def _client_with_role(self, role: str) -> live_e2e.PortalClient:
        client = live_e2e.PortalClient()
        request_patch = patch.object(
            client,
            "request",
            side_effect=(
                (200, {"user": {"role": role}}),
                (
                    200,
                    {
                        "authenticated": True,
                        "user": {"role": role},
                        "csrf_token": "x" * 32,
                    },
                ),
            ),
        )
        client.request = request_patch.start()
        self.addCleanup(request_patch.stop)
        return client

    def test_sales_account_can_be_checked_as_sales(self) -> None:
        client = self._client_with_role("sales")
        with patch.object(live_e2e, "get_secure_parameter", return_value="synthetic-only"):
            client.login("commercial@example.invalid", "/test/sales", expected_role="sales")
        self.assertEqual(client.csrf, "x" * 32)

    def test_operations_account_can_be_checked_as_operations(self) -> None:
        client = self._client_with_role("operations")
        with patch.object(live_e2e, "get_secure_parameter", return_value="synthetic-only"):
            client.login("operations@example.invalid", "/test/operations", expected_role="operations")
        self.assertEqual(client.csrf, "x" * 32)

    def test_admin_remains_the_default_expected_role(self) -> None:
        client = self._client_with_role("admin")
        with patch.object(live_e2e, "get_secure_parameter", return_value="synthetic-only"):
            client.login()
        self.assertEqual(client.csrf, "x" * 32)

    def test_unexpected_role_fails_closed(self) -> None:
        client = self._client_with_role("sales")
        with patch.object(live_e2e, "get_secure_parameter", return_value="synthetic-only"):
            with self.assertRaisesRegex(live_e2e.SmokeFailure, "expected admin role"):
                client.login()


class LiveTargetSelectionTests(unittest.TestCase):
    def test_loopback_is_the_safe_default(self) -> None:
        with patch.dict(live_e2e.os.environ, {}, clear=False):
            live_e2e.os.environ.pop("LIVE_E2E_TARGET", None)
            client = live_e2e.PortalClient()
        self.assertEqual(client.target, "loopback")
        self.assertEqual(client.base_url, "http://127.0.0.1:8080")

    def test_alb_target_is_explicit_and_allowlisted(self) -> None:
        with patch.dict(live_e2e.os.environ, {"LIVE_E2E_TARGET": "alb"}):
            client = live_e2e.PortalClient()
        self.assertEqual(
            client.base_url,
            "http://tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com",
        )

    def test_https_domain_target_is_explicit_and_allowlisted(self) -> None:
        with patch.dict(live_e2e.os.environ, {"LIVE_E2E_TARGET": "https"}):
            client = live_e2e.PortalClient()
        self.assertEqual(client.target, "https")
        self.assertEqual(
            client.base_url,
            "https://tangamandapio.kendellnm.me",
        )

    def test_alb_origin_target_uses_domain_for_https(self) -> None:
        with patch.dict(live_e2e.os.environ, {}, clear=False):
            live_e2e.os.environ.pop("LIVE_E2E_TARGET", None)
            client = live_e2e.PortalClient("alb-origin-https")
        self.assertEqual(client.base_url, "https://tangamandapio.kendellnm.me")
        self.assertTrue(
            any(
                isinstance(handler, live_e2e._ALBOriginHTTPSHandler)
                for handler in client.opener.handlers
            )
        )

    def test_alb_origin_connection_keeps_tls_hostname_and_uses_alb_dns(self) -> None:
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        context = MagicMock()
        context.wrap_socket.return_value = tls_socket
        connection = live_e2e._ALBOriginHTTPSConnection(
            "tangamandapio.kendellnm.me",
            origin_host=live_e2e.ALB_ORIGIN_DNS,
            context=context,
        )
        with patch.object(
            live_e2e.socket, "create_connection", return_value=raw_socket
        ) as create:
            connection.connect()
        create.assert_called_once_with(
            (live_e2e.ALB_ORIGIN_DNS, 443), connection.timeout, connection.source_address
        )
        context.wrap_socket.assert_called_once_with(
            raw_socket, server_hostname="tangamandapio.kendellnm.me"
        )
        self.assertIs(connection.sock, tls_socket)

    def test_arbitrary_target_fails_closed(self) -> None:
        with self.assertRaisesRegex(live_e2e.SmokeFailure, "Unsupported live E2E target"):
            live_e2e.PortalClient("http://example.invalid")


class PortalRequestHeaderTests(unittest.TestCase):
    def _request(self, method: str) -> live_e2e.Request:
        client = live_e2e.PortalClient("https")
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"{}"
        with patch.object(client.opener, "open", return_value=response) as open_request:
            client.csrf = "csrf-test-token"
            client.request(method, "/api/test", payload={"synthetic": True})
        return open_request.call_args.args[0]

    def test_unsafe_https_request_uses_same_origin_headers_and_csrf(self) -> None:
        request = self._request("POST")
        self.assertEqual(request.get_header("Origin"), "https://tangamandapio.kendellnm.me")
        self.assertEqual(request.get_header("Referer"), "https://tangamandapio.kendellnm.me/")
        self.assertEqual(request.get_header("X-csrf-token"), "csrf-test-token")

    def test_safe_request_does_not_add_mutation_headers(self) -> None:
        request = self._request("GET")
        self.assertIsNone(request.get_header("Origin"))
        self.assertIsNone(request.get_header("Referer"))
        self.assertIsNone(request.get_header("X-csrf-token"))

    def test_request_with_headers_exposes_pagination_metadata(self) -> None:
        client = live_e2e.PortalClient("https")
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"[]"
        response.headers.items.return_value = [("X-Total-Count", "45")]
        with patch.object(client.opener, "open", return_value=response):
            status, body, headers = client.request_with_headers("GET", "/api/outbox")
        self.assertEqual(status, 200)
        self.assertEqual(body, [])
        self.assertEqual(headers["x-total-count"], "45")

    def test_http_error_reports_safe_edge_diagnostics_without_body(self) -> None:
        client = live_e2e.PortalClient("https")
        headers = Message()
        headers["Server"] = "cloudflare"
        headers["CF-Ray"] = "8fabc1234-ORD"
        error = HTTPError(
            "https://tangamandapio.kendellnm.me/api/admin/users",
            403,
            "Forbidden",
            headers,
            None,
        )
        with patch.object(client.opener, "open", side_effect=error):
            with self.assertRaises(live_e2e.SmokeFailure) as caught:
                client.request_with_headers("GET", "/api/admin/users")
        message = str(caught.exception)
        self.assertIn("edge=cloudflare", message)
        self.assertIn("cf-ray=8fabc1234-ORD", message)
        self.assertNotIn("Forbidden", message)


class LiveModeOptInTests(unittest.TestCase):
    def test_readonly_mode_requires_its_own_non_mutating_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "https",
                    "LIVE_E2E_MODE": "admin-readonly",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.OPT_IN,
                },
                clear=True,
            ),
            patch.object(live_e2e, "main_admin_readonly_smoke") as smoke,
        ):
            self.assertEqual(live_e2e.main(), 2)
        smoke.assert_not_called()

    def test_readonly_mode_runs_only_with_dedicated_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "https",
                    "LIVE_E2E_MODE": "admin-readonly",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.READ_ONLY_OPT_IN,
                },
                clear=True,
            ),
            patch.object(live_e2e, "main_admin_readonly_smoke", return_value=0) as smoke,
        ):
            self.assertEqual(live_e2e.main(), 0)
        smoke.assert_called_once_with("https")

    def test_recording_readonly_mode_rejects_generic_e2e_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "https",
                    "LIVE_E2E_MODE": "admin-recording-readonly",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.OPT_IN,
                },
                clear=True,
            ),
            patch.object(live_e2e, "main_admin_recording_readonly_smoke") as smoke,
        ):
            self.assertEqual(live_e2e.main(), 2)
        smoke.assert_not_called()

    def test_recording_readonly_mode_uses_the_non_mutating_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "https",
                    "LIVE_E2E_MODE": "admin-recording-readonly",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.READ_ONLY_OPT_IN,
                },
                clear=True,
            ),
            patch.object(
                live_e2e, "main_admin_recording_readonly_smoke", return_value=0
            ) as smoke,
        ):
            self.assertEqual(live_e2e.main(), 0)
        smoke.assert_called_once_with("https")

    def test_role_matrix_mode_rejects_generic_e2e_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "alb-origin-https",
                    "LIVE_E2E_MODE": "admin-role-matrix",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.OPT_IN,
                },
                clear=True,
            ),
            patch.object(live_e2e, "main_admin_role_matrix") as smoke,
        ):
            self.assertEqual(live_e2e.main(), 2)
        smoke.assert_not_called()

    def test_role_matrix_mode_runs_only_with_temporary_account_opt_in(self) -> None:
        with (
            patch.dict(
                live_e2e.os.environ,
                {
                    "LIVE_E2E_TARGET": "alb-origin-https",
                    "LIVE_E2E_MODE": "admin-role-matrix",
                    "RUN_LIVE_DEPLOYED_E2E": live_e2e.ROLE_MATRIX_OPT_IN,
                },
                clear=True,
            ),
            patch.object(live_e2e, "main_admin_role_matrix", return_value=0) as smoke,
        ):
            self.assertEqual(live_e2e.main(), 0)
        smoke.assert_called_once_with("alb-origin-https")


class AdminReadonlySmokeTests(unittest.TestCase):
    def test_admin_readonly_smoke_includes_role_matrix(self) -> None:
        client = MagicMock()
        client.target = "alb-origin-https"
        client.json.return_value = {"roles": ["erp_admin"]}
        client.request.return_value = (200, {"recordings": []})
        role_matrix = {
            "comercial": {"/api/erp/sales/orders": 200},
            "operaciones": {"/api/wms/inventory": 200},
        }
        with (
            patch.object(live_e2e, "PortalClient", return_value=client),
            patch.object(live_e2e, "verify_role_authorization", return_value=role_matrix) as roles,
            patch.object(live_e2e, "inspect_admin_dashboard_consistency", return_value={"order_count": 1}),
            patch.object(live_e2e, "verify_admin_alarm_subscriptions", return_value={"subscription_count": 2}),
            patch.object(
                live_e2e,
                "measure_read_only_database_load",
                return_value={"requests": 24, "concurrency": 6, "p95_ms": 123.45, "all_http_200": True},
            ) as read_load,
            patch("builtins.print") as output,
        ):
            result = live_e2e.main_admin_readonly_smoke("alb-origin-https")
        self.assertEqual(result, 0)
        roles.assert_called_once_with("alb-origin-https")
        read_load.assert_called_once_with(client)
        payload = live_e2e.json.loads(output.call_args.args[0])
        self.assertEqual(payload["role_authorization"], role_matrix)
        self.assertEqual(payload["read_only_load"]["requests"], 24)
        self.assertEqual(payload["recording_playback"]["playback"], "no_saved_recordings")
        client.logout.assert_called_once_with()


class SavedVoiceRecordingPlaybackTests(unittest.TestCase):
    def test_private_playback_route_validates_audio_and_reports_only_metadata(self) -> None:
        client = live_e2e.PortalClient("alb-origin-https")
        client.request = MagicMock(return_value=(200, {
            "recordings": [{
                "file_url": "/api/voice/recordings/rec-test/file",
                "size_bytes": 4,
            }]
        }))
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers.get.return_value = "audio/webm; codecs=opus"
        response.read.return_value = b"test"

        with patch.object(client.opener, "open", return_value=response):
            result = live_e2e.verify_saved_voice_recording_playback(client)

        self.assertEqual(result, {
            "saved_recordings": 1,
            "playback": "passed",
            "bytes": 4,
            "content_type": "audio/webm",
        })

    def test_empty_catalog_does_not_attempt_file_access(self) -> None:
        client = live_e2e.PortalClient("alb-origin-https")
        client.request = MagicMock(return_value=(200, {"recordings": []}))
        with patch.object(client.opener, "open", side_effect=AssertionError("must not fetch")):
            result = live_e2e.verify_saved_voice_recording_playback(client)
        self.assertEqual(result, {"saved_recordings": 0, "playback": "no_saved_recordings"})


class ReadOnlyLoadTransportTests(unittest.TestCase):
    def test_load_probe_reuses_the_target_specific_opener(self) -> None:
        client = live_e2e.PortalClient("alb-origin-https")
        client.cookies = [SimpleNamespace(name="session", value="synthetic-session")]
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"[]"

        with (
            patch.object(client.opener, "open", return_value=response) as open_request,
            patch.object(live_e2e, "urlopen", side_effect=AssertionError("wrong transport")),
        ):
            result = live_e2e.measure_read_only_database_load(client)

        self.assertEqual(result["requests"], live_e2e.READ_ONLY_LOAD_REQUESTS)
        self.assertTrue(result["all_http_200"])
        self.assertEqual(open_request.call_count, live_e2e.READ_ONLY_LOAD_REQUESTS)


class RoleTargetPropagationTests(unittest.TestCase):
    def test_role_checks_use_the_same_target_as_the_e2e(self) -> None:
        client = MagicMock()
        client.json.return_value = {"user": {"role": "sales"}}
        client.request.return_value = (200, {})
        accounts = (("sales", "sales@example.invalid", "/parameter", "sales", {"/api/orders": 200}),)
        with (
            patch.object(live_e2e, "PortalClient", return_value=client) as factory,
            patch.object(live_e2e, "ROLE_ACCOUNTS", accounts),
        ):
            result = live_e2e.verify_role_authorization("https")

        factory.assert_called_once_with("https")
        self.assertEqual(result, {"sales": {"/api/orders": 200}})


class AdminAlarmSubscriptionSmokeTests(unittest.TestCase):
    class FakeClient:
        def __init__(self, response: dict) -> None:
            self.response = response
            self.calls: list[tuple[str, str]] = []

        def json(self, method: str, path: str) -> dict:
            self.calls.append((method, path))
            return self.response

    @staticmethod
    def _subscription(endpoint: str, arn: str, status: str = "confirmed") -> dict:
        return {
            "protocol": "email",
            "endpoint": endpoint,
            "subscription_arn": arn,
            "status": status,
        }

    def test_admin_check_returns_aggregate_counts_without_sensitive_values(self) -> None:
        email = "alert-test@example.invalid"
        arn = "arn:aws:sns:us-east-1:123456789012:topic:subscription"
        client = self.FakeClient(
            {
                "topic_configured": True,
                "confirmation_required": True,
                "subscriptions": [
                    self._subscription(email, arn),
                    self._subscription("pending@example.invalid", "PendingConfirmation", "pending_confirmation"),
                ],
            }
        )

        result = live_e2e.verify_admin_alarm_subscriptions(client)  # type: ignore[arg-type]

        self.assertEqual(
            result,
            {
                "topic_configured": True,
                "confirmation_required": True,
                "subscription_count": 2,
                "confirmed_count": 1,
                "pending_confirmation_count": 1,
            },
        )
        self.assertNotIn(email, str(result))
        self.assertNotIn(arn, str(result))
        self.assertEqual(client.calls, [("GET", "/api/admin/alarm-subscriptions")])

    def test_admin_check_fails_when_topic_is_not_configured(self) -> None:
        client = self.FakeClient({"error": "alarm_notifications_not_configured"})
        with self.assertRaisesRegex(live_e2e.SmokeFailure, "not configured"):
            live_e2e.verify_admin_alarm_subscriptions(client)  # type: ignore[arg-type]

    def test_admin_check_rejects_invalid_protocol_and_confirmation_state(self) -> None:
        for subscription in (
            {**self._subscription("alert@example.invalid", "arn"), "protocol": "sms"},
            {**self._subscription("alert@example.invalid", "arn"), "status": "unknown"},
        ):
            with self.subTest(subscription=subscription):
                client = self.FakeClient(
                    {
                        "topic_configured": True,
                        "confirmation_required": True,
                        "subscriptions": [subscription],
                    }
                )
                with self.assertRaises(live_e2e.SmokeFailure):
                    live_e2e.verify_admin_alarm_subscriptions(client)  # type: ignore[arg-type]

    def test_admin_check_rejects_case_insensitive_duplicate_addresses(self) -> None:
        client = self.FakeClient(
            {
                "topic_configured": True,
                "confirmation_required": True,
                "subscriptions": [
                    self._subscription("Alert@example.invalid", "arn:one"),
                    self._subscription("alert@example.invalid", "arn:two"),
                ],
            }
        )
        with self.assertRaisesRegex(live_e2e.SmokeFailure, "duplicate"):
            live_e2e.verify_admin_alarm_subscriptions(client)  # type: ignore[arg-type]


class AdminModuleSmokeTests(unittest.TestCase):
    class FakeFinanceClient:
        target = "https"

        def __init__(self) -> None:
            self.document: dict = {}

        def request(self, method: str, path: str, payload: dict | None = None):
            if method == "POST" and path == "/api/erp/finance/expenses":
                self.document = {
                    "id": 73,
                    "reference": payload["reference"],
                    "amount": payload["amount"],
                    "status": "open",
                }
                return 201, dict(self.document)
            if method == "POST" and path == "/api/erp/finance/documents/73/settle":
                self.document["status"] = "paid"
                return 200, {"id": 73, "status": "paid"}
            if method == "GET" and path == "/api/erp/finance/documents":
                return 200, [dict(self.document)]
            raise AssertionError(f"Unexpected finance request: {method} {path}")

    def test_finance_workflow_creates_settles_and_verifies_persisted_record(self) -> None:
        client = self.FakeFinanceClient()
        result = live_e2e.exercise_finance_workflow(client)  # type: ignore[arg-type]
        self.assertEqual(result, {"status": "paid", "amount": 0.05})
        self.assertEqual(client.document["status"], "paid")

    def test_mail_test_skips_external_send_when_smtp_is_configured(self) -> None:
        client = MagicMock()
        client.json.return_value = {"smtp_configured": True, "transport": "smtp"}
        result = live_e2e.exercise_internal_portal_mail(client)
        self.assertEqual(
            result,
            {"status": "not_sent_smtp_relay_configured", "smtp_configured": True},
        )
        client.request.assert_not_called()

    def test_portal_only_mail_is_received_and_marked_read_by_recipient(self) -> None:
        message_id = 91
        subject = "[QA] synthetic"
        body = "Mensaje sintético de prueba cloud; no enviar fuera del portal."
        sender = MagicMock()
        sender.target = "https"
        sender.json.return_value = {"smtp_configured": False, "transport": "portal_only"}
        captured_subject = [subject]

        def sender_request(method: str, path: str, payload: dict | None = None):
            if method == "GET" and path == "/api/erp/mail/users":
                return 200, [{"id": 2, "username": live_e2e.ROLE_ACCOUNTS[0][1]}]
            if method == "POST" and path == "/api/erp/mail":
                captured_subject[0] = payload["subject"]
                return 201, {
                    "id": message_id,
                    "subject": captured_subject[0],
                    "status": "sent_internal",
                    "smtp_status": "portal_only",
                }
            if method == "GET" and path == "/api/erp/mail?folder=sent":
                return 200, [{"id": message_id, "subject": captured_subject[0]}]
            raise AssertionError(f"Unexpected mail request: {method} {path}")

        sender.request.side_effect = sender_request
        recipient = MagicMock()

        def recipient_request(method: str, path: str, payload: dict | None = None):
            if method == "GET" and path == "/api/erp/mail?folder=inbox":
                return 200, [
                    {"id": message_id, "subject": captured_subject[0], "body": body, "unread": True}
                ]
            if method == "POST" and path == f"/api/erp/mail/{message_id}/read":
                return 200, {"id": message_id, "read": True}
            raise AssertionError(f"Unexpected recipient mail request: {method} {path}")

        recipient.request.side_effect = recipient_request
        with patch.object(live_e2e, "PortalClient", return_value=recipient) as factory:
            result = live_e2e.exercise_internal_portal_mail(sender)  # type: ignore[arg-type]
        factory.assert_called_once_with("https")
        recipient.login.assert_called_once_with(
            username=live_e2e.ROLE_ACCOUNTS[0][1],
            parameter=live_e2e.ROLE_ACCOUNTS[0][2],
            expected_role=live_e2e.ROLE_ACCOUNTS[0][3],
        )
        recipient.logout.assert_called_once()
        self.assertEqual(
            result,
            {"status": "portal_only_sent_and_read", "smtp_configured": False},
        )

    def test_poison_queue_probe_only_reads_sanitized_count(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = (
            b'{"status":"ok","queue":"fulfillment-events-poison",'
            b'"approximate_message_count":3,"payloads_exposed":false}'
        )
        function_key = "synthetic-function-key-never-output"
        with (
            patch.object(
                live_e2e,
                "_aws_cli_text",
                side_effect=["test/function-key-secret", function_key],
            ) as aws_text,
            patch.object(live_e2e, "urlopen", return_value=response) as open_url,
        ):
            result = live_e2e.inspect_azure_poison_queue()
        self.assertEqual(aws_text.call_count, 2)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, live_e2e.AZURE_POISON_QUEUE_URL)
        self.assertIn(function_key, str(request.headers))
        self.assertNotIn(function_key, str(result))
        self.assertEqual(
            result,
            {"status": "ok", "approximate_message_count": 3, "payloads_exposed": False},
        )

    def test_poison_queue_probe_rejects_unexpected_payload_without_exposing_it(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b'{"message":"sensitive poison payload"}'
        with (
            patch.object(
                live_e2e,
                "_aws_cli_text",
                side_effect=["secret-name", "synthetic-fake-function-key"],
            ),
            patch.object(live_e2e, "urlopen", return_value=response),
        ):
            with self.assertRaisesRegex(live_e2e.SmokeFailure, "safe poison-queue count") as error:
                live_e2e.inspect_azure_poison_queue()
        self.assertNotIn("sensitive poison payload", str(error.exception))

    def test_dashboard_reconciliation_checks_complete_order_and_outbox_counts(self) -> None:
        client = MagicMock()
        client.json.return_value = {
            "role": "admin",
            "orders": 2,
            "outbox": {"pending": 1, "delivered": 2},
        }

        def request(method: str, path: str):
            if path == "/api/orders":
                return 200, [{"id": 1}, {"id": 2}]
            raise AssertionError(f"Unexpected reconciliation request: {method} {path}")

        client.request.side_effect = request
        client.request_with_headers.return_value = (
            200,
            [
                {"event_id": "evt-1", "status": "delivered"},
                {"event_id": "evt-2", "status": "delivered"},
                {"event_id": "evt-3", "status": "pending"},
            ],
            {"x-total-count": "3", "x-page-limit": "30", "x-page-offset": "0"},
        )
        self.assertEqual(
            live_e2e.inspect_admin_dashboard_consistency(client),
            {
                "order_count": 2,
                "visible_orders": 2,
                "orders_match_complete_list": True,
                "outbox_pending": 1,
                "outbox_delivered": 2,
                "visible_outbox_rows": 3,
                "outbox_total": 3,
                "outbox_reconciliation": "complete_paginated",
            },
        )

    def test_dashboard_reconciliation_reads_multiple_outbox_pages_and_matches_totals(self) -> None:
        client = MagicMock()
        client.json.return_value = {
            "role": "admin",
            "orders": 1,
            "outbox": {"pending": 0, "delivered": 45},
        }
        client.request.side_effect = [(200, [{"id": 1}])]
        first_page = [
            {"event_id": f"evt-{number}", "status": "delivered"}
            for number in range(30)
        ]
        second_page = [
            {"event_id": f"evt-{number}", "status": "delivered"}
            for number in range(30, 45)
        ]
        page_headers = {"x-total-count": "45", "x-page-limit": "30"}
        client.request_with_headers.side_effect = [
            (200, first_page, {**page_headers, "x-page-offset": "0"}),
            (200, second_page, {**page_headers, "x-page-offset": "30"}),
        ]
        result = live_e2e.inspect_admin_dashboard_consistency(client)
        self.assertEqual(result["outbox_reconciliation"], "complete_paginated")
        self.assertEqual(result["outbox_delivered"], 45)
        self.assertEqual(result["visible_outbox_rows"], 45)
        self.assertEqual(result["outbox_total"], 45)

    def test_dashboard_reconciliation_rejects_inconsistent_outbox_totals(self) -> None:
        client = MagicMock()
        client.json.return_value = {
            "role": "admin",
            "orders": 0,
            "outbox": {"pending": 0, "delivered": 8},
        }
        client.request.side_effect = [(200, [])]
        client.request_with_headers.return_value = (
            200,
            [
                {"event_id": "evt-1", "status": "delivered"},
                {"event_id": "evt-2", "status": "pending"},
            ],
            {"x-total-count": "2", "x-page-limit": "30", "x-page-offset": "0"},
        )
        with self.assertRaisesRegex(
            live_e2e.SmokeFailure, "lower than the visible event rows"
        ):
            live_e2e.inspect_admin_dashboard_consistency(client)

    def test_dashboard_reconciliation_rejects_duplicate_or_missing_events(self) -> None:
        client = MagicMock()
        client.json.return_value = {
            "role": "admin",
            "orders": 0,
            "outbox": {"pending": 0, "delivered": 2},
        }
        client.request.return_value = (200, [])
        client.request_with_headers.return_value = (
            200,
            [
                {"event_id": "evt-1", "status": "delivered"},
                {"event_id": "evt-1", "status": "delivered"},
            ],
            {"x-total-count": "2", "x-page-limit": "30", "x-page-offset": "0"},
        )
        with self.assertRaisesRegex(
            live_e2e.SmokeFailure, "duplicates or omitted events"
        ):
            live_e2e.inspect_admin_dashboard_consistency(client)


class DuplicateOutboxDeliveryTests(unittest.TestCase):
    class FakeClient:
        def __init__(self, after_stock: int = 10) -> None:
            self.inventory_reads = 0
            self.after_stock = after_stock
            self.attempts = 4

        def json(self, method: str, path: str) -> dict:
            if method == "GET" and path == "/api/wms/inventory":
                self.inventory_reads += 1
                stock = 10 if self.inventory_reads == 1 else self.after_stock
                return {
                    "mode": "demo-inventory-ledger",
                    "items": [{"sku": "SKU-SYNTHETIC", "on_hand": stock}],
                }
            raise AssertionError(f"Unexpected JSON request: {method} {path}")

        def request(self, method: str, path: str, payload: dict | None = None):
            if method == "GET" and path == "/api/outbox?limit=100&offset=0":
                return 200, [{"event_id": "evt-synthetic", "status": "delivered", "attempts": self.attempts}]
            if method == "GET" and path == "/api/outbox/evt-synthetic/fulfillment-status":
                return 200, {"fulfillment_status": "demo_restock_completed"}
            if method == "POST" and path == "/api/outbox/evt-synthetic/retry":
                self.attempts += 1
                return 200, {"status": "delivered", "upstream": "queued_duplicate"}
            raise AssertionError(f"Unexpected request: {method} {path}")

    def test_duplicate_delivery_is_acknowledged_and_leaves_demo_stock_unchanged(self) -> None:
        client = self.FakeClient()
        with patch.object(live_e2e.time, "sleep") as sleep:
            result = live_e2e.exercise_duplicate_outbox_delivery(client)  # type: ignore[arg-type]

        sleep.assert_called_once_with(3)
        self.assertEqual(result["retry_upstream"], "queued_duplicate")
        self.assertEqual(result["attempts_before"], 4)
        self.assertEqual(result["attempts_after"], 5)
        self.assertTrue(result["inventory_unchanged"])
        self.assertEqual(result["inventory_mode"], "demo-inventory-ledger")

    def test_duplicate_delivery_fails_if_demo_stock_changes(self) -> None:
        client = self.FakeClient(after_stock=9)
        with (
            patch.object(live_e2e.time, "sleep"),
            self.assertRaisesRegex(live_e2e.SmokeFailure, "changed the synthetic ledger stock"),
        ):
            live_e2e.exercise_duplicate_outbox_delivery(client)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
