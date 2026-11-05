import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RebuildBackupRetentionTests(unittest.TestCase):
    def test_rebuild_default_matches_cloudformation_retention(self):
        template = (ROOT / "iac/cloudformation/aws-lab.yaml").read_text(encoding="utf-8")
        rebuild = (ROOT / "iac/cloudformation/rebuild.sh").read_text(encoding="utf-8")

        template_match = re.search(
            r"(?ms)^  DatabaseBackupRetentionDays:\s*\n\s+Type: Number\s*\n\s+Default: (\d+)",
            template,
        )
        script_match = re.search(
            r"DatabaseBackupRetentionDays,ParameterValue=\$\{DATABASE_BACKUP_RETENTION_DAYS:-([0-9]+)\}",
            rebuild,
        )

        self.assertIsNotNone(template_match, "CloudFormation retention default is missing")
        self.assertIsNotNone(script_match, "rebuild.sh retention default is missing")
        self.assertEqual(
            script_match.group(1),
            template_match.group(1),
            "rebuild.sh must not silently override the template backup retention",
        )


if __name__ == "__main__":
    unittest.main()
