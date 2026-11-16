"""Fail-closed and recovery tests for the AWS-side Tailscale route monitor."""
import importlib.util
from pathlib import Path
import sys
from threading import Barrier
import unittest


PATH = Path(__file__).resolve().parents[2] / "iac/scripts/tailscale_ha_controller.py"
spec = importlib.util.spec_from_file_location("tailscale_ha_controller", PATH)
controller = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controller
spec.loader.exec_module(controller)


class TailscaleHaDecisionTests(unittest.TestCase):
    def test_router_health_probes_run_concurrently(self):
        barrier = Barrier(2)

        def primary():
            barrier.wait(timeout=0.5)
            return "healthy"

        def backup():
            barrier.wait(timeout=0.5)
            return "healthy"

        self.assertEqual(controller.probe_health_pair(primary, backup), ("healthy", "healthy"))

    def test_route_moves_to_backup_after_three_confirmed_primary_failures(self):
        state = {"primary_failures": 0, "primary_recoveries": 0}
        for expected in (1, 2):
            state, action = controller.decide(state, "primary", "unhealthy", "healthy")
            self.assertEqual((state["primary_failures"], action), (expected, None))
        state, action = controller.decide(state, "primary", "unhealthy", "healthy")
        self.assertEqual((state["primary_failures"], action), (3, "switch_to_backup"))

    def test_unknown_health_or_unhealthy_backup_never_switches(self):
        initial = {"primary_failures": 2, "primary_recoveries": 0}
        state, action = controller.decide(initial, "primary", "unknown", "healthy")
        self.assertIsNone(action)
        self.assertEqual(state["primary_failures"], 0)
        state, action = controller.decide(initial, "primary", "unhealthy", "unhealthy")
        self.assertIsNone(action)
        self.assertEqual(state["primary_failures"], 3)

    def test_recovered_primary_gets_route_back_after_ten_healthy_checks(self):
        state = {"primary_failures": 0, "primary_recoveries": 0}
        for expected in range(1, 10):
            state, action = controller.decide(state, "backup", "healthy", "healthy")
            self.assertEqual((state["primary_recoveries"], action), (expected, None))
        state, action = controller.decide(state, "backup", "healthy", "healthy")
        self.assertEqual((state["primary_recoveries"], action), (10, "switch_to_primary"))

    def test_unknown_route_is_never_replaced(self):
        state, action = controller.decide({"primary_failures": 2}, "other", "unhealthy", "healthy")
        self.assertIsNone(action)
        self.assertEqual(state, {"primary_failures": 0, "primary_recoveries": 0})

    def test_route_classifier_accepts_only_the_expected_active_interface(self):
        table = {"Routes": [{"DestinationCidrBlock": "10.20.1.4/32", "State": "active",
                             "NetworkInterfaceId": "eni-primary"}]}
        self.assertEqual(controller.classify_route(table, "10.20.1.4/32", "eni-primary", "eni-backup"), "primary")
        table["Routes"][0]["NetworkInterfaceId"] = "eni-unknown"
        self.assertEqual(controller.classify_route(table, "10.20.1.4/32", "eni-primary", "eni-backup"), "other")
        table["Routes"].append(dict(table["Routes"][0]))
        self.assertEqual(controller.classify_route(table, "10.20.1.4/32", "eni-primary", "eni-backup"), "other")

    def test_controller_configuration_restricts_destination_and_subprocess_arguments(self):
        config = controller.Config("us-east-2", "rtb-0123456789abcdef0", "10.20.1.4/32",
                                   "eni-0123456789abcdef0", "eni-abcdef0123456789", "10.10.10.149",
                                   "tangama-flex-261104.azurewebsites.net", "arn:aws:sns:us-east-2:123456789012:alarms")
        self.assertEqual(config.destination, "10.20.1.4/32")
        self.assertIn("--network-interface-id", controller.replace_route_argv(config, "backup"))
        with self.assertRaises(ValueError):
            controller.Config("us-east-2", "rtb-invalid", "0.0.0.0/0", "eni-123", "eni-456",
                              "10.10.10.149", "bad.azurewebsites.net", "")


if __name__ == "__main__":
    unittest.main()
