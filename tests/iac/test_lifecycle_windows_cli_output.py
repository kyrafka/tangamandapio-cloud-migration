import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = ROOT / "iac" / "cloudformation" / "lifecycle.sh"
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def bash_executable():
    if os.name == "nt" and GIT_BASH.is_file():
        return str(GIT_BASH)
    return shutil.which("bash") or "bash"


def bash_path(path):
    path = Path(path)
    if os.name == "nt" and path.drive:
        return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
    return str(path)


class LifecycleWindowsCliOutputTests(unittest.TestCase):
    def test_vpn_route_stage_passes_project_resources_to_guarded_helper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shutil.copy(LIFECYCLE, root / 'lifecycle.sh')
            fake = root / 'aws-cli'
            fake.write_text('#!/usr/bin/env bash\ncase "$*" in\n*sts*) echo 654654388734;;\n*describe-stack-resource*) echo vpc-1234;;\n*) exit 90;;\nesac\n', encoding='utf8')
            fake.chmod(0o755)
            helper = root / 'python-cli'
            helper.write_text('#!/usr/bin/env bash\nprintf "ROUTE_ARGS=%s\\n" "$*"\n', encoding='utf8')
            helper.chmod(0o755)
            env = dict(os.environ, AWS_CLI=bash_path(fake), TANGAMA_PYTHON=bash_path(helper), EXPECTED_AWS_ACCOUNT_ID='654654388734', STACK_NAME='tangamandapio-live-20261104', AWS_REGION='us-east-1', ROUTE_TABLE_ID='rtb-1234', ROUTER_ENI='eni-1234', WMS_PRIVATE_IP='10.20.1.4')
            result = subprocess.run([bash_executable(), str(root / 'lifecycle.sh'), 'vpn-route'], env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('--table rtb-1234 --eni eni-1234 --destination 10.20.1.4 --apply', result.stdout)

    def test_dns_stage_can_be_resumed_without_rebuilding_portal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shutil.copy(LIFECYCLE, root / 'lifecycle.sh')
            (root / 'rebuild-private-wms-dns.sh').write_text('#!/usr/bin/env bash\necho "DNS_STAGE=$VPC_ID:$1"\n', encoding='utf8')
            fake = root / 'aws-cli'
            fake.write_text('#!/usr/bin/env bash\ncase "$*" in\n*sts*) echo 654654388734;;\n*describe-stack-resource*) echo vpc-1234;;\n*) echo UNEXPECTED >&2; exit 90;;\nesac\n', encoding='utf8')
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=bash_path(fake), EXPECTED_AWS_ACCOUNT_ID='654654388734', STACK_NAME='tangamandapio-live-20261104', AWS_REGION='us-east-1', WMS_HOSTNAME='tangama-flex-261104.azurewebsites.net', WMS_PRIVATE_IP='10.20.1.4')
            result = subprocess.run([bash_executable(), str(root / 'lifecycle.sh'), 'dns'], env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('DNS_STAGE=vpc-1234:--ensure', result.stdout)
            self.assertNotIn('UNEXPECTED', result.stderr)

    def test_private_dns_stage_runs_after_rebuild_and_receives_stack_vpc(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shutil.copy(LIFECYCLE, root / 'lifecycle.sh')
            (root / 'rebuild.sh').write_text('#!/usr/bin/env bash\necho REBUILT\n', encoding='utf8')
            (root / 'rebuild-private-wms-dns.sh').write_text('#!/usr/bin/env bash\necho "DNS_STAGE=$VPC_ID:$WMS_HOSTNAME:$WMS_PRIVATE_IP:$1"\n', encoding='utf8')
            fake = root / 'aws-cli'
            fake.write_text('#!/usr/bin/env bash\ncase "$*" in\n*sts*) echo 654654388734;;\n*describe-stack-resource*) echo vpc-1234;;\n*) exit 90;;\nesac\n', encoding='utf8')
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=bash_path(fake), EXPECTED_AWS_ACCOUNT_ID='654654388734', STACK_NAME='tangamandapio-live-20261104', AWS_REGION='us-east-1', AZURE_FULFILLMENT_URL='https://tangama-flex-261104.azurewebsites.net', AZURE_FUNCTION_KEY_SECRET='tangamandapio/azure/function-key', ALLOW_EMPTY_DATABASE='true', ENABLE_PRIVATE_WMS_DNS='true', WMS_HOSTNAME='tangama-flex-261104.azurewebsites.net', WMS_PRIVATE_IP='10.20.1.4')
            result = subprocess.run([bash_executable(), str(root / 'lifecycle.sh'), 'up'], input='CREATE tangamandapio-live-20261104\n', env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertLess(result.stdout.index('REBUILT'), result.stdout.index('DNS_STAGE='))
            self.assertIn('DNS_STAGE=vpc-1234:tangama-flex-261104.azurewebsites.net:10.20.1.4:--ensure', result.stdout)

    def test_private_dns_stage_refuses_missing_endpoint_before_rebuild(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake = Path(temp_dir) / 'aws-cli'
            fake.write_text('#!/usr/bin/env bash\necho 654654388734\n', encoding='utf8')
            fake.chmod(0o755)
            env = dict(os.environ, AWS_CLI=bash_path(fake), EXPECTED_AWS_ACCOUNT_ID='654654388734', STACK_NAME='tangamandapio-live-20261104', AWS_REGION='us-east-1', AZURE_FULFILLMENT_URL='https://example.azurewebsites.net', AZURE_FUNCTION_KEY_SECRET='tangamandapio/azure/function-key', ALLOW_EMPTY_DATABASE='true', ENABLE_PRIVATE_WMS_DNS='true', WMS_HOSTNAME='', WMS_PRIVATE_IP='')
            result = subprocess.run([bash_executable(), str(LIFECYCLE), 'up'], input='', env=env, capture_output=True, text=True, encoding='utf8', errors='replace')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('WMS_HOSTNAME', result.stderr)

    def test_strips_windows_cli_carriage_return_before_account_guard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_cli = Path(temp_dir) / "aws-cli"
            fake_cli.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1 $2\" == \"sts get-caller-identity\" ]]; then\n"
                "  printf '654654388734\\r\\n'\n"
                "  exit 0\n"
                "fi\n"
                "exit 99\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "AWS_CLI": str(fake_cli),
                    "EXPECTED_AWS_ACCOUNT_ID": "654654388734",
                    "STACK_NAME": "tangamandapio-live-20261031",
                    "AWS_REGION": "us-east-1",
                    "AZURE_FULFILLMENT_URL": "https://example.azurewebsites.net",
                    "AZURE_FUNCTION_KEY_SECRET": "tangamandapio/azure/function-key",
                    "RDS_SNAPSHOT_IDENTIFIER": "snapshot-demo",
                }
            )
            if os.name == "nt":
                environment["AWS_CLI"] = bash_path(fake_cli)
            result = subprocess.run(
                [bash_executable(), str(LIFECYCLE), "up"],
                cwd=ROOT,
                input="NO\n",
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                check=False,
            )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("confirmación incorrecta", result.stderr)
        self.assertIn("no despliega VPN privada operativa ni región secundaria", result.stdout)
        self.assertIn("Azure se opera con su lifecycle Terraform independiente", result.stdout)
        self.assertNotIn("otra cuenta", result.stderr)


if __name__ == "__main__":
    unittest.main()
