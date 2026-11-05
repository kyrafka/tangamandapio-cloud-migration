import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'iac/scripts/enrol_tailscale_router.py'


def load():
    spec = importlib.util.spec_from_file_location('enrol_router', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EnrollmentTests(unittest.TestCase):
    def test_aws_registration_uses_file_reference_and_scoped_tag(self):
        mod = load()
        cmd = mod.build_command('aws', '/run/credentials/one-use-key', 'tangamandapio-aws-primary')
        self.assertIn('--auth-key=file:/run/credentials/one-use-key', cmd)
        self.assertIn('--advertise-tags=tag:tangama-aws-router', cmd)
        self.assertNotIn('--advertise-routes=10.20.1.0/24', cmd)
        self.assertNotIn('--force-reauth', cmd)

    def test_azure_registration_advertises_only_wms_subnet(self):
        mod = load()
        cmd = mod.build_command('azure', '/run/credentials/one-use-key', 'tangamandapio-azure-primary')
        self.assertIn('--advertise-routes=10.20.1.0/24', cmd)
        self.assertIn('--advertise-tags=tag:tangama-azure-router', cmd)
        self.assertNotIn('--advertise-exit-node', cmd)

    def test_refuses_unrelated_host_and_unsafe_secret_path(self):
        mod = load()
        with self.assertRaises(ValueError):
            mod.build_command('aws', '/run/credentials/key', 'unrelated-router')
        with self.assertRaises(ValueError):
            mod.build_command('azure', 'relative-key', 'tangamandapio-azure-primary')

    def test_refuses_to_replace_existing_identity(self):
        mod = load()
        self.assertFalse(mod.may_enrol({'BackendState': 'Running'}))
        self.assertTrue(mod.may_enrol({'BackendState': 'NeedsLogin'}))
        self.assertFalse(mod.may_enrol({'BackendState': 'Starting'}))
