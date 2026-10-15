import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2]
TEMPLATE = WORKSPACE / "iac" / "cloudformation" / "aws-lab.yaml"


class CloudWatchTemplateWiringTests(unittest.TestCase):
    def test_runtime_environment_contains_real_aws_resource_dimensions(self):
        template = TEMPLATE.read_text(encoding="utf-8")

        for expected in (
            '"CLOUDWATCH_REGION_NAME": "${AWS::Region}"',
            '"CLOUDWATCH_LOAD_BALANCER_FULL_NAME": "${AppLoadBalancer.LoadBalancerFullName}"',
            '"CLOUDWATCH_TARGET_GROUP_FULL_NAME": "${TargetGroup.TargetGroupFullName}"',
            '"CLOUDWATCH_RDS_INSTANCE_ID": "${Database}"',
            '"CLOUDWATCH_AUTO_SCALING_GROUP": "${ProjectName}-asg"',
        ):
            with self.subTest(setting=expected):
                self.assertIn(expected, template)

    def test_waf_dimensions_are_only_written_when_waf_is_enabled(self):
        template = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('if "${EnableWaf}" == "true":', template)
        self.assertIn('lines["CLOUDWATCH_WAF_WEB_ACL_NAME"] = "${ProjectName}-alb"', template)
        self.assertIn('lines["CLOUDWATCH_WAF_REGION"] = "${AWS::Region}"', template)


if __name__ == "__main__":
    unittest.main()
