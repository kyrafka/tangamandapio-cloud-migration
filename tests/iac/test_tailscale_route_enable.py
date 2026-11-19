"""Route enablement must wait for router readiness and roll back failed probes."""
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "iac/cloudformation/enable_tailscale_ha_route.sh"


class RouteEnablementTests(unittest.TestCase):
    def test_enablement_checks_account_and_both_router_health_before_cfn_route(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_AWS_ACCOUNT_ID", text)
        self.assertIn("tangamandapio-aws-azure-tailscale-ha", text)
        self.assertIn('"ready":true', text)
        self.assertLess(text.index('"ready":true'), text.index("EnablePrivateWmsRoute,ParameterValue=true"))

    def test_failed_application_private_probe_disables_the_route_again(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--resolve", text)
        self.assertIn("private_function_http=200_private_ip=10.20.1.4", text)
        self.assertIn("10.20.1.4", text)
        self.assertIn("EnablePrivateWmsRoute,ParameterValue=false", text)
        self.assertIn("curl", text)


if __name__ == "__main__":
    unittest.main()
