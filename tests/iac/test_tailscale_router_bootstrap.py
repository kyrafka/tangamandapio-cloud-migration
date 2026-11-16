"""Static security guarantees for the one-time router bootstrap."""
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "iac/scripts/bootstrap_tailscale_router.sh"


class RouterBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")
        cls.compact = " ".join(cls.text.split())

    def test_auth_key_is_read_from_secrets_manager_into_a_private_file(self):
        self.assertIn("secretsmanager get-secret-value", self.text)
        self.assertIn("--query SecretString", self.text)
        self.assertIn("--output text", self.text)
        self.assertIn("--auth-key=file:/run/tangamandapio/auth-key", self.text)
        self.assertIn("chmod 0600 /run/tangamandapio/auth-key", self.text)
        self.assertRegex(self.text, r"rm -f /run/tangamandapio/auth-key")

    def test_router_forwarding_is_scoped_to_application_to_private_function_https(self):
        self.assertIn("--source 10.10.10.0/23", self.text)
        self.assertIn('WMS_PRIVATE_IP="10.20.1.4"', self.text)
        nat = (SCRIPT.parent / "tailscale_nat.py").read_text(encoding="utf-8")
        self.assertIn("--dport 443", nat)
        self.assertIn("-o tailscale0 -j MASQUERADE", nat)

    def test_backup_service_uses_one_second_checks_and_does_not_start_on_primary(self):
        self.assertIn('if [[ "$ROUTER_ROLE" == backup ]]', self.text)
        self.assertIn("OnUnitActiveSec=500ms", self.text)
        self.assertIn("tailscale_ha_controller.py", self.text)

    def test_backup_interface_is_validated_only_after_it_is_read_from_imds(self):
        initial_validation = self.text.split('IMDS_TOKEN="$(curl', 1)[0]
        self.assertNotRegex(initial_validation, r'\[\[.*\$BACKUP_ENI.*\]\]')
        self.assertIn('BACKUP_ENI="$(curl', self.text)
        self.assertRegex(self.text, r'BACKUP_ENI" =~ \^eni-\[0-9a-f\]\{8,17\}\$.*PRIMARY_ENI')

    def test_auth_material_is_not_written_to_logs_or_command_history(self):
        self.assertNotIn("set -x", self.text)
        self.assertNotRegex(self.text, r"echo\s+\$AUTH_KEY")
        self.assertNotRegex(self.text, r"tskey-auth-[A-Za-z0-9_-]{20,}")


if __name__ == "__main__":
    unittest.main()
