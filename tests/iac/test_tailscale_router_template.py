"""Safety checks for the AWS Tailscale pilot before any route is enabled."""
from pathlib import Path
import unittest
import yaml

TEMPLATE = Path(__file__).resolve().parents[2] / "iac/cloudformation/aws-tailscale-pilot.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _intrinsic(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


CloudFormationLoader.add_multi_constructor("!", _intrinsic)


class TailscalePilotSafetyTests(unittest.TestCase):
    def test_pilot_is_isolated_and_does_not_change_application_routes(self):
        template = yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=CloudFormationLoader)
        resources = template["Resources"]
        types = [resource["Type"] for resource in resources.values()]
        self.assertEqual(types.count("AWS::EC2::Instance"), 1)
        self.assertNotIn("AWS::EC2::Route", types)
        self.assertNotIn("AWS::Route53::RecordSet", types)
        instance = next(resource for resource in resources.values() if resource["Type"] == "AWS::EC2::Instance")
        self.assertFalse(instance["Properties"]["SourceDestCheck"])
        group = next(resource for resource in resources.values() if resource["Type"] == "AWS::EC2::SecurityGroup")
        self.assertFalse(group["Properties"].get("SecurityGroupIngress"))

    def test_no_authentication_secret_is_stored_in_template(self):
        text = TEMPLATE.read_text(encoding="utf-8").lower()
        self.assertNotIn("tskey-auth-", text)
        self.assertNotIn("--authkey", text)


if __name__ == "__main__":
    unittest.main()
