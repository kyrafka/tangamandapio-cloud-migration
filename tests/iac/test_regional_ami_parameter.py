import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RegionalAmiParameterTests(unittest.TestCase):
    def test_cloudformation_uses_region_scoped_amazon_linux_parameter(self):
        template = (ROOT / "iac/cloudformation/aws-lab.yaml").read_text(encoding="utf-8")

        self.assertIn(
            "Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
            template,
            "The AMI must be resolved from the deployment region, not hard-coded.",
        )
        self.assertIn(
            "Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",
            template,
        )
        self.assertNotIn("ami-097855b862d5b1eb2", template)


if __name__ == "__main__":
    unittest.main()
