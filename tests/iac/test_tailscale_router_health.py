"""Health endpoint checks required before the standby may take the route."""
import importlib.util
from pathlib import Path
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
