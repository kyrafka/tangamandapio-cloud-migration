import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / "iac" / "cloudformation" / "aws-lab.yaml").read_text(encoding="utf-8")
DEPLOY = (ROOT / "iac" / "cloudformation" / "deploy.sh").read_text(encoding="utf-8")
REBUILD = (ROOT / "iac" / "cloudformation" / "rebuild.sh").read_text(encoding="utf-8")


class HighAvailabilityAndWafTemplateTests(unittest.TestCase):
    def test_rebuild_defaults_keep_multiaz_waf_and_association_enabled(self):
        self.assertRegex(TEMPLATE, r"DatabaseMultiAZ:\s*\n\s+Type: String\s*\n\s+Default: 'true'")
        self.assertRegex(TEMPLATE, r"EnableWaf:\s*\n\s+Type: String\s*\n\s+Default: 'true'")
        self.assertRegex(TEMPLATE, r"ManageWafAssociation:\s*\n\s+Type: String\s*\n\s+Default: 'true'")
        self.assertIn("MultiAZ: !If [UseDatabaseMultiAZ, true, false]", TEMPLATE)
        self.assertIn("Condition: UseManagedWafAssociation", TEMPLATE)

    def test_waf_rate_limit_is_configurable_and_default_supports_the_load_profile(self):
        self.assertRegex(TEMPLATE, r"WafRateLimitPerIp:\s*\n\s+Type: Number\s*\n\s+Default: 30000")
        self.assertIn("Limit: !Ref WafRateLimitPerIp", TEMPLATE)
        self.assertIn("WAF_RATE_LIMIT_PER_IP", DEPLOY)
        self.assertIn("WAF_RATE_LIMIT_PER_IP:-30000", REBUILD)

    def test_rebuild_and_deploy_scripts_make_cloudformation_the_source_of_truth(self):
        self.assertIn('"ParameterKey=DatabaseMultiAZ,ParameterValue=${DATABASE_MULTI_AZ:-true}"', REBUILD)
        self.assertIn('"ParameterKey=EnableWaf,ParameterValue=${ENABLE_WAF:-true}"', REBUILD)
        self.assertIn('"ParameterKey=ManageWafAssociation,ParameterValue=${MANAGE_WAF_ASSOCIATION:-true}"', REBUILD)
        self.assertIn('"ParameterKey=WafRateLimitPerIp,ParameterValue=${WAF_RATE_LIMIT_PER_IP:-30000}"', REBUILD)
        self.assertIn("ParameterKey=$key,ParameterValue=$WAF_RATE_LIMIT_PER_IP", DEPLOY)

    def test_application_workers_support_io_concurrency(self):
        self.assertRegex(TEMPLATE, r"gunicorn[^\n]+--workers 2 --threads 4")


if __name__ == "__main__":
    unittest.main()
