"""Terraform wraps the single CloudFormation owner with deployment safeguards."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2] / "iac/environments/aws-azure-tailscale"


class TailscaleTerraformStackTests(unittest.TestCase):
    def test_terraform_uses_same_cloudformation_stack_and_target_account(self):
        main = (ROOT / "main.tf").read_text(encoding="utf-8")
        versions = (ROOT / "versions.tf").read_text(encoding="utf-8")
        self.assertIn('resource "aws_cloudformation_stack" "router_pair"', main)
        self.assertIn('expected_account_id = "481056890449"', main)
        self.assertIn("aws-azure-tailscale-ha.yaml", main)
        self.assertIn('region = var.aws_region', versions)

    def test_terraform_defaults_to_no_deployment_and_protects_stack_from_destroy(self):
        main = (ROOT / "main.tf").read_text(encoding="utf-8")
        variables = (ROOT / "variables.tf").read_text(encoding="utf-8")
        self.assertIn("count = var.deployment_approved ? 1 : 0", main)
        self.assertIn("prevent_destroy = true", main)
        self.assertIn('default     = false', variables)
        self.assertIn("enable_private_wms_route ? \"true\" : \"false\"", main)

    def test_terraform_uses_secret_names_only(self):
        all_files = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.glob("*.tf"))
        self.assertNotIn("tskey-auth-", all_files)
        self.assertIn("router_artifact_sha256", all_files)

    def test_artifact_packaging_is_encrypted_and_content_addressed(self):
        script = ROOT.parents[1] / "cloudformation/package_tailscale_ha.sh"
        text = script.read_text(encoding="utf-8")
        self.assertIn("sha256sum", text)
        self.assertIn("--sse AES256", text)
        self.assertIn("EXPECTED_AWS_ACCOUNT_ID", text)


if __name__ == "__main__":
    unittest.main()
