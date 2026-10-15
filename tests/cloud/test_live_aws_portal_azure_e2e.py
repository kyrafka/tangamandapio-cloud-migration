from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_arbitrary_target_fails_closed(self) -> None:
        with self.assertRaisesRegex(live_e2e.SmokeFailure, "Unsupported live E2E target"):
            live_e2e.PortalClient("http://example.invalid")


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
