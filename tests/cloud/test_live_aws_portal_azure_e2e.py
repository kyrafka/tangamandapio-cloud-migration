from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_aws_portal_azure_e2e as live_e2e  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
