import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2]
TEMPLATE = WORKSPACE / "iac" / "cloudformation" / "aws-lab.yaml"
DEPLOY = WORKSPACE / "iac" / "cloudformation" / "deploy.sh"
REBUILD = WORKSPACE / "iac" / "cloudformation" / "rebuild.sh"


class AwsRootVolumeEncryptionTests(unittest.TestCase):
    def test_root_disk_encryption_cannot_be_disabled_by_a_lab_override(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("Encrypted: true", template)
        self.assertNotIn("EncryptRootVolume:", template)

    def test_cloudformation_deployment_paths_have_no_unencrypted_override(self):
        deploy = DEPLOY.read_text(encoding="utf-8")
        rebuild = REBUILD.read_text(encoding="utf-8")

        self.assertNotIn("ENCRYPT_ROOT_VOLUME", deploy)
        self.assertNotIn("ENCRYPT_ROOT_VOLUME", rebuild)


if __name__ == "__main__":
    unittest.main()
