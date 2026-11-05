"""Ensure the optional DNS stack is private and scoped to one WMS name."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import yaml

PATH = Path(__file__).resolve().parents[2] / "iac/cloudformation/aws-private-wms-dns.yaml"


class Loader(yaml.SafeLoader):
    pass


Loader.add_multi_constructor("!", lambda loader, suffix, node: loader.construct_scalar(node))


class PrivateDnsTemplateTests(unittest.TestCase):
    def test_ensure_reuses_exact_existing_private_zone_without_deploying(self):
        result = self._run_ensure('[{"Name":"tangama-flex-261104.azurewebsites.net.","Type":"A","TTL":60,"ResourceRecords":[{"Value":"10.20.1.4"}]}]')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('verificados', result.stdout)
        self.assertNotIn('UNEXPECTED_DEPLOY', result.stdout)

    def test_ensure_rejects_mismatched_record_without_deploying(self):
        result = self._run_ensure('[{"Name":"tangama-flex-261104.azurewebsites.net.","Type":"A","TTL":60,"ResourceRecords":[{"Value":"10.20.1.9"}]}]')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('UNEXPECTED_DEPLOY', result.stdout)

    def _run_ensure(self, records):
        bash = r'C:\Program Files\Git\bin\bash.exe' if os.name == 'nt' else 'bash'
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'fake-aws'
            fake.write_text('#!/usr/bin/env bash\ncase "$*" in\n*sts*) echo 654654388734;;\n*describe-stacks*) echo "does not exist" >&2; exit 1;;\n*list-hosted-zones-by-name*) echo Z123;;\n*get-hosted-zone*) echo 1;;\n*list-resource-record-sets*) printf \'%s\\n\' \'%s\';;\n*deploy*) echo UNEXPECTED_DEPLOY;;\n*) exit 9;;\nesac\n' % ('%s', records), encoding='utf-8')
            fake.chmod(0o755)
            env = dict(os.environ, EXPECTED_AWS_ACCOUNT_ID='654654388734', AWS_REGION='us-east-1', VPC_ID='vpc-1234', WMS_HOSTNAME='tangama-flex-261104.azurewebsites.net', WMS_PRIVATE_IP='10.20.1.4', TANGAMA_PYTHON=sys.executable.replace('\\', '/'), AWS_CLI=str(fake).replace('\\', '/'))
            return subprocess.run([bash, str(PATH.with_name('rebuild-private-wms-dns.sh')), '--ensure'], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    def test_zone_is_private_and_contains_only_the_wms_record(self):
        self.assertTrue(PATH.exists(), "Private DNS template must exist")
        template = yaml.load(PATH.read_text(encoding="utf-8"), Loader=Loader)
        resources = template["Resources"]
        zones = [r for r in resources.values() if r["Type"] == "AWS::Route53::HostedZone"]
        records = [r for r in resources.values() if r["Type"] == "AWS::Route53::RecordSet"]
        self.assertEqual(len(zones), 1)
        self.assertTrue(zones[0]["Properties"].get("VPCs"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["Properties"]["Type"], "A")
        self.assertEqual(records[0]["Properties"]["Name"], "WmsHostname")
        self.assertEqual(records[0]["Properties"]["ResourceRecords"], ["WmsPrivateIp"])

    def test_rebuild_helper_refuses_missing_account_before_any_changes(self):
        helper = PATH.with_name("rebuild-private-wms-dns.sh")
        self.assertTrue(helper.exists(), "Private DNS rebuild helper must exist")
        bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
        result = subprocess.run([bash, str(helper), "--apply"], capture_output=True, text=True,
                                env={"PATH": os.environ.get("PATH", "")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EXPECTED_AWS_ACCOUNT_ID", result.stderr)

    def test_rebuild_helper_refuses_invalid_python_override(self):
        helper = PATH.with_name("rebuild-private-wms-dns.sh")
        bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
        env = {"PATH": os.environ.get("PATH", ""), "EXPECTED_AWS_ACCOUNT_ID": "654654388734",
               "AWS_REGION": "us-east-1", "VPC_ID": "vpc-1234",
               "WMS_HOSTNAME": "tangama-flex-261104.azurewebsites.net", "WMS_PRIVATE_IP": "10.20.1.4",
               "TANGAMA_PYTHON": "does-not-exist-tangamandapio"}
        result = subprocess.run([bash, str(helper), "--apply"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TANGAMA_PYTHON", result.stderr)

    def test_rebuild_helper_never_updates_an_existing_stack(self):
        helper = PATH.with_name("rebuild-private-wms-dns.sh")
        bash = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake-aws"
            fake.write_text("#!/usr/bin/env bash\ncase \"$*\" in\n*sts*) echo 654654388734;;\n*list-hosted-zones*) echo None;;\n*describe-stacks*) echo CREATE_COMPLETE;;\n*deploy*) echo UNEXPECTED_DEPLOY;;\n*) exit 9;;\nesac\n", encoding="utf-8")
            fake.chmod(0o755)
            env = {"PATH": os.environ.get("PATH", ""), "EXPECTED_AWS_ACCOUNT_ID": "654654388734",
                   "AWS_REGION": "us-east-1", "VPC_ID": "vpc-1234",
                   "WMS_HOSTNAME": "tangama-flex-261104.azurewebsites.net", "WMS_PRIVATE_IP": "10.20.1.4",
                   "TANGAMA_PYTHON": sys.executable.replace("\\", "/"), "AWS_CLI": str(fake).replace("\\", "/")}
            result = subprocess.run([bash, str(helper), "--apply"], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("UNEXPECTED_DEPLOY", result.stdout)
            self.assertIn("stack", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
