import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / 'iac/scripts/prepare_tailscale_policy.py'


def load():
    spec = importlib.util.spec_from_file_location('policy_prepare', PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PolicyPrepareTests(unittest.TestCase):
    def test_preserves_existing_rules_and_is_idempotent(self):
        mod = load()
        existing = {'tagOwners': {'tag:other': ['alice@example.com']}, 'grants': [{'src': ['tag:other'], 'dst': ['100.1.2.3'], 'ip': ['tcp:80']}], 'autoApprovers': {'routes': {'10.30.0.0/16': ['tag:other']}}}
        result = mod.prepare(existing)
        self.assertEqual(result['tagOwners']['tag:other'], ['alice@example.com'])
        self.assertIn(existing['grants'][0], result['grants'])
        self.assertEqual(result['autoApprovers']['routes']['10.30.0.0/16'], ['tag:other'])
        self.assertIn('tag:tangama-azure-router', result['autoApprovers']['routes']['10.20.1.0/24'])
        self.assertIn({'src': ['tag:tangama-aws-router'], 'dst': ['10.20.1.4/32'], 'ip': ['tcp:443']}, result['grants'])
        self.assertEqual(result, mod.prepare(result))
        self.assertNotIn('tag:tangama-aws-router', existing['tagOwners'])

    def test_refuses_conflicting_existing_tag_owners(self):
        mod = load()
        with self.assertRaises(ValueError):
            mod.prepare({'tagOwners': {'tag:tangama-aws-router': ['group:other']}})

    def test_refuses_malformed_policy(self):
        mod = load()
        with self.assertRaises(ValueError):
            mod.prepare({'grants': 'unexpected'})
