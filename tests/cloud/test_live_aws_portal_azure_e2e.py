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


if __name__ == "__main__":
    unittest.main()
