"""Never allow the generic destroy to orphan the private VPN."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASH = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"


class VpnCleanupGuardTests(unittest.TestCase):
    def test_active_vpn_stack_stops_destroy_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "aws"
            fake.write_text("#!/usr/bin/env bash\ncase \"$*\" in\n*sts*) echo 654654388734;;\n*describe-stacks*tangamandapio-tailscale-pilot*) echo CREATE_COMPLETE;;\n*) echo UNEXPECTED_MUTATION >&2; exit 9;;\nesac\n", encoding="utf8")
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=str(fake).replace('\\', '/'), EXPECTED_AWS_ACCOUNT_ID="654654388734", STACK_NAME="tangamandapio-live-20261104", CONFIRM_DELETE_DATA="true", PURGE_PROJECT_RESOURCES="true", CONFIRM_STACK_NAME="tangamandapio-live-20261104")
            result = subprocess.run([BASH, str(ROOT / "iac/cloudformation/destroy.sh")], env=env, capture_output=True, text=True, encoding="utf8", errors="replace")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("VPN", result.stderr)
            self.assertNotIn("UNEXPECTED_MUTATION", result.stderr)

    def test_uncertain_vpn_inventory_stops_destroy(self):
        # No API denial may be mistaken for a missing stack.
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "aws"
            fake.write_text("#!/usr/bin/env bash\ncase \"$*\" in\n*sts*) echo 654654388734;;\n*) echo AccessDenied >&2; exit 254;;\nesac\n", encoding="utf8")
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=str(fake).replace('\\', '/'), EXPECTED_AWS_ACCOUNT_ID="654654388734", STACK_NAME="tangamandapio-live-20261104", CONFIRM_DELETE_DATA="true", PURGE_PROJECT_RESOURCES="true", CONFIRM_STACK_NAME="tangamandapio-live-20261104")
            result = subprocess.run([BASH, str(ROOT / "iac/cloudformation/destroy.sh")], env=env, capture_output=True, text=True, encoding="utf8", errors="replace")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("comprobar", result.stderr)

    def test_associated_private_dns_stops_destroy_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'aws'
            fake.write_text('#!/usr/bin/env bash\ncase "$*" in\n*sts*) echo 654654388734;;\n*describe-stacks*tangamandapio-tailscale-pilot*) echo "does not exist" >&2; exit 1;;\n*describe-stack-resource*) echo vpc-1234;;\n*list-hosted-zones-by-vpc*) echo Z12345;;\n*) echo UNEXPECTED_MUTATION >&2; exit 9;;\nesac\n', encoding='utf8')
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=str(fake).replace('\\', '/'), EXPECTED_AWS_ACCOUNT_ID='654654388734', STACK_NAME='tangamandapio-live-20261104', CONFIRM_DELETE_DATA='true', PURGE_PROJECT_RESOURCES='true', CONFIRM_STACK_NAME='tangamandapio-live-20261104')
            result = subprocess.run([BASH, str(ROOT / 'iac/cloudformation/destroy.sh')], env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('zonas DNS privadas', result.stderr)
            self.assertNotIn('UNEXPECTED_MUTATION', result.stderr)
