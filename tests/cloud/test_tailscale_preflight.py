from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "iac" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import check_tailscale_prerequisites as preflight  # noqa: E402


class TailscalePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.which = patch.object(preflight.shutil, "which", side_effect=lambda name: name)
        self.which.start()
        self.addCleanup(self.which.stop)
        self.key = patch.dict(os.environ, {"TAILSCALE_AUTH_KEY": "tskey-secret-test"})
        self.key.start()
        self.addCleanup(self.key.stop)
        self.commands: dict[tuple[str, ...], tuple[int, object]] = {
            ("tailscale", "status", "--json"): (
                0,
                {"BackendState": "Running", "Self": {"Online": True}},
            ),
            ("aws", "sts", "get-caller-identity", "--output", "json"): (
                0,
                {"Account": "000000000000", "Arn": "must-not-be-printed"},
            ),
            ("aws", "ec2", "describe-vpcs", "--region", "us-east-1", "--output", "json"): (
                0,
                {"Vpcs": [{"CidrBlock": "10.10.0.0/16", "State": "available"}]},
            ),
            ("az", "account", "show", "--output", "json"): (0, {"id": "subscription-id"}),
            ("az", "network", "vnet", "list", "--output", "json"): (
                0,
                [
                    {
                        "name": "vnet-tangama-private",
                        "resourceGroup": "rg-tangama-private-network",
                        "addressSpace": {"addressPrefixes": ["10.20.0.0/16"]},
                    }
                ],
            ),
        }

    def _run_mock(self, command: list[str], **kwargs: object) -> object:
        code, payload = self.commands[tuple(command)]

        class Result:
            returncode = code
            stdout = json.dumps(payload)
            stderr = "sensitive stderr must not be surfaced"

        return Result()

    def test_ready_state_requires_both_clouds_and_tailnet(self) -> None:
        with patch.object(preflight.subprocess, "run", side_effect=self._run_mock):
            report = preflight.evaluate()
        self.assertEqual(report["result"], "READY_FOR_MANUAL_REVIEW")
        self.assertTrue(report["read_only"])
        self.assertEqual(report["blockers"], [])
        self.assertNotIn("must-not-be-printed", json.dumps(report))
        self.assertNotIn("tskey-secret-test", json.dumps(report))

    def test_missing_azure_network_blocks_without_claiming_readiness(self) -> None:
        self.commands[("az", "network", "vnet", "list", "--output", "json")] = (0, [])
        with patch.object(preflight.subprocess, "run", side_effect=self._run_mock):
            report = preflight.evaluate()
        self.assertEqual(report["result"], "BLOCKED")
        self.assertFalse(report["checks"]["azure_vnet_present"])
        self.assertTrue(any("No se encontró exactamente una VNet" in item for item in report["blockers"]))

    def test_logged_out_tailnet_and_missing_key_are_blockers(self) -> None:
        self.commands[("tailscale", "status", "--json")] = (
            0,
            {"BackendState": "NoState", "Self": {"Online": False}},
        )
        with patch.dict(preflight.os.environ, {}, clear=True), patch.object(
            preflight.subprocess, "run", side_effect=self._run_mock
        ):
            report = preflight.evaluate()
        self.assertFalse(report["checks"]["tailscale_connected"])
        self.assertFalse(report["checks"]["ephemeral_auth_key_present"])
        self.assertEqual(report["result"], "BLOCKED")

    def test_overlapping_networks_block_readiness(self) -> None:
        with patch.object(preflight.subprocess, "run", side_effect=self._run_mock):
            report = preflight.evaluate(azure_cidr="10.10.1.0/24")
        self.assertFalse(report["checks"]["cidrs_non_overlapping"])
        self.assertEqual(report["result"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
