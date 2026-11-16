import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / "iac" / "cloudformation" / "aws-lab.yaml").read_text(encoding="utf-8")
DEPLOY = (ROOT / "iac" / "cloudformation" / "deploy.sh").read_text(encoding="utf-8")
REBUILD = (ROOT / "iac" / "cloudformation" / "rebuild.sh").read_text(encoding="utf-8")


class HighAvailabilityAndWafTemplateTests(unittest.TestCase):
    def test_database_defaults_match_live_cost_controlled_baseline(self):
        self.assertRegex(TEMPLATE, r"DatabaseMultiAZ:\s*\n\s+Type: String\s*\n\s+Default: 'false'")
        self.assertRegex(TEMPLATE, r"DatabaseBackupRetentionDays:\s*\n\s+Type: Number\s*\n\s+Default: 1")
        self.assertIn("DATABASE_MULTI_AZ:-false", REBUILD)
        self.assertIn("DATABASE_BACKUP_RETENTION_DAYS:-1", REBUILD)

    def test_waf_and_association_remain_enabled_by_default(self):
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
        self.assertIn('"ParameterKey=DatabaseMultiAZ,ParameterValue=${DATABASE_MULTI_AZ:-false}"', REBUILD)
        self.assertIn('"ParameterKey=DatabaseBackupRetentionDays,ParameterValue=${DATABASE_BACKUP_RETENTION_DAYS:-1}"', REBUILD)
        self.assertIn('"ParameterKey=EnableWaf,ParameterValue=${ENABLE_WAF:-true}"', REBUILD)
        self.assertIn('"ParameterKey=ManageWafAssociation,ParameterValue=${MANAGE_WAF_ASSOCIATION:-true}"', REBUILD)
        self.assertIn('"ParameterKey=WafRateLimitPerIp,ParameterValue=${WAF_RATE_LIMIT_PER_IP:-30000}"', REBUILD)
        self.assertIn("ParameterKey=$key,ParameterValue=$WAF_RATE_LIMIT_PER_IP", DEPLOY)

    def test_application_workers_support_io_concurrency(self):
        self.assertRegex(TEMPLATE, r"gunicorn[^\n]+--workers 2 --threads 4")

    def test_rebuild_defaults_target_live_region_and_verified_release(self):
        self.assertIn('REGION="${AWS_REGION:-us-east-2}"', DEPLOY)
        self.assertIn('REGION="${AWS_REGION:-us-east-2}"', REBUILD)
        self.assertIn('if [[ "$REGION" == "us-east-1" ]]; then', REBUILD)
        self.assertIn("portal-b2b-20261105-password-change-optional-v29-python312-0c1b86e998a483764f7a80a1cec3e0f90d73c60d564f907fa1c8dc4e59a6152e.tar.gz", TEMPLATE)
        self.assertIn("Default: 20261105-password-change-optional-v29-python312", TEMPLATE)
        self.assertIn("Default: 0c1b86e998a483764f7a80a1cec3e0f90d73c60d564f907fa1c8dc4e59a6152e", TEMPLATE)


if __name__ == "__main__":
    unittest.main()
