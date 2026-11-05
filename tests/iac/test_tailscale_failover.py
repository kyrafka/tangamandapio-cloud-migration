"""Decision tests for the private WMS router failover controller."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / "iac/scripts/tailscale_failover.py"
controller = None
if PATH.exists():
    spec = importlib.util.spec_from_file_location("tailscale_failover", PATH)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)


class FailoverDecisionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(controller, "The failover controller must exist")

    def test_requires_three_consecutive_confirmed_primary_failures(self):
        failures = 0
        for expected in (1, 2):
            failures, switch = controller.decide(failures, "unhealthy", "healthy", "primary")
            self.assertEqual((failures, switch), (expected, False))
        self.assertEqual(controller.decide(failures, "unhealthy", "healthy", "primary"), (3, True))

    def test_unknown_primary_or_unhealthy_backup_never_switches(self):
        self.assertEqual(controller.decide(2, "unknown", "healthy", "primary"), (0, False))
        self.assertEqual(controller.decide(2, "unhealthy", "unhealthy", "primary"), (3, False))
        self.assertEqual(controller.decide(2, "unhealthy", "unknown", "primary"), (3, False))

    def test_success_resets_counter_and_never_failbacks_or_changes_unknown_route(self):
        self.assertEqual(controller.decide(2, "healthy", "healthy", "primary"), (0, False))
        self.assertEqual(controller.decide(3, "unhealthy", "healthy", "backup"), (0, False))
        self.assertEqual(controller.decide(3, "unhealthy", "healthy", "other"), (0, False))

    def test_invalid_observation_fails_closed(self):
        with self.assertRaises(ValueError):
            controller.decide(0, "garbage", "healthy", "primary")

    def test_cycle_switches_only_after_health_threshold_and_keeps_backup(self):
        self.assertTrue(hasattr(controller, "run_cycle"), "Failover cycle must exist")
        class Cloud:
            route = "primary"
            changes = 0

            def current_route(self):
                return self.route

            def primary_health(self):
                return "unhealthy"

            def backup_health(self):
                return "healthy"

            def switch_to_backup(self):
                self.changes += 1
                self.route = "backup"

        cloud = Cloud()
        failures = 0
        for _ in range(3):
            failures, _ = controller.run_cycle(cloud, failures)
        self.assertEqual(cloud.changes, 1)
        failures, switched = controller.run_cycle(cloud, failures)
        self.assertEqual((failures, switched, cloud.changes), (0, False, 1))

    def test_inconclusive_route_does_not_trigger_any_probe_or_switch(self):
        self.assertTrue(hasattr(controller, "run_cycle"), "Failover cycle must exist")
        class Cloud:
            def current_route(self):
                return "other"

            def primary_health(self):
                raise AssertionError("unknown route must not be touched")

        self.assertEqual(controller.run_cycle(Cloud(), 2), (0, False))

    def test_api_timeout_clears_old_failures(self):
        class Cloud:
            def current_route(self):
                raise subprocess.TimeoutExpired("aws", 1)

        try:
            result = controller.run_cycle(Cloud(), 2)
        except subprocess.TimeoutExpired:
            self.fail("API timeouts must reset the stale failure counter")
        self.assertEqual(result, (0, False))

    def test_route_parser_accepts_only_expected_active_interfaces(self):
        self.assertTrue(hasattr(controller, "classify_route"), "Route validation must exist")
        primary = {"Routes": [{"DestinationCidrBlock": "10.20.1.4/32", "State": "active", "NetworkInterfaceId": "eni-primary"}]}
        self.assertEqual(controller.classify_route(primary, "10.20.1.4/32", "eni-primary", "eni-backup"), "primary")
        primary["Routes"][0]["State"] = "blackhole"
        self.assertEqual(controller.classify_route(primary, "10.20.1.4/32", "eni-primary", "eni-backup"), "other")
        primary["Routes"][0]["State"] = "active"
        primary["Routes"][0]["NetworkInterfaceId"] = "eni-foreign"
        self.assertEqual(controller.classify_route(primary, "10.20.1.4/32", "eni-primary", "eni-backup"), "other")

    def test_failed_or_inconclusive_remote_execution_is_unknown(self):
        self.assertTrue(hasattr(controller, "parse_remote_health"), "Remote health parser must exist")
        self.assertEqual(controller.parse_remote_health("Success", "HEALTHY\n"), "healthy")
        self.assertEqual(controller.parse_remote_health("Success", "UNHEALTHY\n"), "unhealthy")
        self.assertEqual(controller.parse_remote_health("Failed", "UNHEALTHY\n"), "unknown")
        self.assertEqual(controller.parse_remote_health("Success", "unexpected"), "unknown")

    def test_health_probe_suppresses_iptables_output(self):
        cloud = controller.AWSCloud("us-east-1", "rtb-1234", "10.20.1.4/32", "i-1234", "eni-1234", "eni-5678", "tangama-flex-261104.azurewebsites.net")
        self.assertIn("-j MASQUERADE >/dev/null 2>&1", cloud.health_command())

    def test_aws_success_with_empty_output_is_not_an_error(self):
        self.assertTrue(hasattr(controller, "parse_aws_json"), "AWS response parser must exist")
        self.assertEqual(controller.parse_aws_json(""), {})
        self.assertEqual(controller.parse_aws_json('{"ok":true}'), {"ok": True})
        with self.assertRaises(json.JSONDecodeError):
            controller.parse_aws_json("not-json")

    def test_systemd_unit_uses_validated_ids_and_no_credentials(self):
        self.assertTrue(hasattr(controller, "render_systemd_service"), "Rebuild service renderer must exist")
        cloud = controller.AWSCloud("us-east-1", "rtb-1234", "10.20.1.4/32", "i-1234", "eni-1234", "eni-5678", "tangama-flex-261104.azurewebsites.net")
        unit = controller.render_systemd_service(cloud)
        self.assertIn("--primary-instance i-1234", unit)
        self.assertIn("--backup-eni eni-5678", unit)
        self.assertIn("flock -n", unit)
        self.assertNotIn("secret", unit.lower())
        with self.assertRaises(ValueError):
            controller.AWSCloud("us-east-1", "rtb-1234", "10.20.1.4/32", "i-1234", "eni-1234", "eni-5678", "unsafe;command")

    def test_service_can_be_rendered_without_contacting_aws(self):
        import sys
        result = subprocess.run([sys.executable, str(PATH), "--region", "us-east-1", "--table", "rtb-1234",
                                 "--destination", "10.20.1.4/32", "--primary-instance", "i-1234",
                                 "--primary-eni", "eni-1234", "--backup-eni", "eni-5678",
                                 "--hostname", "tangama-flex-261104.azurewebsites.net", "--render-service"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--backup-eni eni-5678", result.stdout)

    def test_preferred_service_renders_the_recovery_flag(self):
        cloud = controller.AWSCloud("us-east-1", "rtb-1234", "10.20.1.4/32", "i-1234", "eni-1234", "eni-5678", "tangama-flex-261104.azurewebsites.net")
        self.assertIn("--prefer-self", controller.render_systemd_service(cloud, prefer_self=True))
        self.assertNotIn("--prefer-self", controller.render_systemd_service(cloud, prefer_self=False))

    def test_installer_preflight_requires_known_route_and_both_healthy(self):
        self.assertTrue(hasattr(controller, "installation_preflight"), "Installer preflight must exist")
        class Cloud:
            def current_route(self): return "primary"
            def primary_health(self): return "healthy"
            def backup_health(self): return "healthy"
        cloud = Cloud()
        self.assertTrue(controller.installation_preflight(cloud))
        cloud.backup_health = lambda: "unknown"
        self.assertFalse(controller.installation_preflight(cloud))
        cloud.backup_health = lambda: "healthy"
        cloud.current_route = lambda: "backup"
        self.assertTrue(controller.installation_preflight(cloud))
        cloud.current_route = lambda: "other"
        self.assertFalse(controller.installation_preflight(cloud))

    def test_installer_refuses_missing_configuration(self):
        installer = PATH.with_name("install_tailscale_failover.sh")
        self.assertTrue(installer.exists(), "Reconstruction installer must exist")
        bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
        result = subprocess.run([bash, str(installer), "--apply"], capture_output=True, text=True,
                                env={"PATH": os.environ.get("PATH", "")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EXPECTED_AWS_ACCOUNT_ID", result.stderr)

    def test_installer_refuses_invalid_preference(self):
        installer = PATH.with_name("install_tailscale_failover.sh")
        bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
        env = {"PATH": os.environ.get("PATH", ""), "EXPECTED_AWS_ACCOUNT_ID": "654654388734", "AWS_REGION": "us-east-1",
               "ROUTE_TABLE_ID": "rtb-1234", "WMS_PRIVATE_IP": "10.20.1.4", "PRIMARY_INSTANCE_ID": "i-1234",
               "PRIMARY_ENI": "eni-1234", "BACKUP_ENI": "eni-5678", "WMS_HOSTNAME": "tangama-flex-261104.azurewebsites.net",
               "PREFER_SELF": "maybe"}
        result = subprocess.run([bash, str(installer), "--apply"], capture_output=True, text=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PREFER_SELF", result.stderr)

    def test_installer_rejects_ambiguous_nat_flag_before_host_changes(self):
        installer = PATH.with_name('install_tailscale_failover.sh')
        bash = r'C:\Program Files\Git\bin\bash.exe' if os.name == 'nt' else 'bash'
        env = {'PATH': os.environ.get('PATH', ''), 'EXPECTED_AWS_ACCOUNT_ID': '654654388734', 'AWS_REGION': 'us-east-1',
               'ROUTE_TABLE_ID': 'rtb-1234', 'WMS_PRIVATE_IP': '10.20.1.4', 'PRIMARY_INSTANCE_ID': 'i-1234',
               'PRIMARY_ENI': 'eni-1234', 'BACKUP_ENI': 'eni-5678', 'WMS_HOSTNAME': 'example.azurewebsites.net',
               'INSTALL_SCOPED_NAT': 'yes'}
        result = subprocess.run([bash, str(installer), '--apply'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('INSTALL_SCOPED_NAT', result.stderr)

    def test_preferred_router_returns_only_after_ten_healthy_observations(self):
        self.assertTrue(hasattr(controller, "run_ha_cycle"), "Bidirectional controller must exist")
        class Cloud:
            route = "primary"
            switches = 0
            def current_route(self): return self.route
            def primary_health(self): return "healthy"
            def backup_health(self): return "healthy"
            def switch_to_backup(self):
                self.switches += 1
                self.route = "backup"
        cloud = Cloud()
        state = {"failures": 0, "recoveries": 0}
        for n in range(9):
            state, reason = controller.run_ha_cycle(cloud, state, prefer_self=True)
            self.assertEqual((state["recoveries"], reason), (n + 1, None))
        state, reason = controller.run_ha_cycle(cloud, state, prefer_self=True)
        self.assertEqual((cloud.switches, reason), (1, "preferred_recovery"))

    def test_no_preferred_return_when_either_router_is_unknown(self):
        self.assertTrue(hasattr(controller, "run_ha_cycle"), "Bidirectional controller must exist")
        class Cloud:
            def current_route(self): return "primary"
            def primary_health(self): return "healthy"
            def backup_health(self): return "unknown"
            def switch_to_backup(self): self.fail("must not switch")
        state, reason = controller.run_ha_cycle(Cloud(), {"failures": 0, "recoveries": 9}, prefer_self=True)
        self.assertEqual((state["recoveries"], reason), (0, None))

    def test_changed_route_resets_the_failure_streak(self):
        class Cloud:
            def current_route(self): return "primary"
            def primary_health(self): return "unhealthy"
            def backup_health(self): return "healthy"
            def switch_to_backup(self): raise RuntimeError("route changed")
        state, reason = controller.run_ha_cycle(Cloud(), {"failures": 2}, prefer_self=True)
        self.assertEqual((state, reason), ({"failures": 0, "recoveries": 0}, None))

    def test_reverse_controller_takes_route_if_active_peer_fails(self):
        self.assertTrue(hasattr(controller, "run_ha_cycle"), "Bidirectional controller must exist")
        class Cloud:
            route = "primary"
            def current_route(self): return self.route
            def primary_health(self): return "unhealthy"
            def backup_health(self): return "healthy"
            def switch_to_backup(self): self.route = "backup"
        cloud = Cloud()
        state = {"failures": 0, "recoveries": 0}
        for _ in range(3): state, reason = controller.run_ha_cycle(cloud, state, prefer_self=True)
        self.assertEqual((cloud.route, reason), ("backup", "peer_failure"))


if __name__ == "__main__":
    unittest.main()
