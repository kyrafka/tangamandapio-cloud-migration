"""Health endpoint checks required before the standby may take the route."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[2] / "iac/scripts/tailscale_router_health.py"
spec = importlib.util.spec_from_file_location("tailscale_router_health", PATH)
health = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = health
spec.loader.exec_module(health)


class RouterHealthTests(unittest.TestCase):
    def test_ready_requires_live_tailscale_and_private_function_health(self):
        self.assertTrue(health.is_ready("Running", 200))
        self.assertFalse(health.is_ready("NoState", 200))
        self.assertFalse(health.is_ready("Running", 403))
        self.assertFalse(health.is_ready("Running", None))

    def test_health_body_contains_only_component_status_and_no_secret_values(self):
        body = health.health_payload("Running", 200)
        self.assertEqual(body, {"ready": True, "tailscale": "Running", "private_wms_http": 200})
        self.assertNotIn("key", str(body).lower())

    def test_regular_health_polls_reuse_the_azure_result_but_detect_a_stopped_tunnel(self):
        server = health.HealthServer(("127.0.0.1", 0), health.Handler)
        server.wms_private_ip = "10.20.1.4"
        server.wms_hostname = "tangama-flex-261104.azurewebsites.net"
        with server, patch.object(health, "read_tailscale_state", side_effect=["Running", "Running", "Stopped"]), patch.object(health, "probe_private_wms", return_value=200) as probe:
            self.assertTrue(server.route_health()["ready"])
            self.assertTrue(server.route_health()["ready"])
            self.assertFalse(server.route_health()["ready"])
            probe.assert_called_once()

    def test_route_health_tolerates_one_transient_timeout_on_a_previously_healthy_path(self):
        server = health.HealthServer(("127.0.0.1", 0), health.Handler)
        server.wms_private_ip = "10.20.1.4"
        server.wms_hostname = "tangama-flex-261104.azurewebsites.net"
        with server, patch.object(health, "read_tailscale_state", return_value="Running"), patch.object(health, "probe_private_wms", side_effect=[200, TimeoutError(), TimeoutError()]):
            self.assertTrue(server.route_health()["ready"])
            server.next_probe = 0.0
            self.assertTrue(server.route_health()["ready"])
            server.next_probe = 0.0
            self.assertFalse(server.route_health()["ready"])


if __name__ == "__main__":
    unittest.main()
