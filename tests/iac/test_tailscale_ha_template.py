"""Security and fail-closed checks for the deployable AWS router pair."""
from pathlib import Path
import unittest

import yaml


TEMPLATE = Path(__file__).resolve().parents[2] / "iac/cloudformation/aws-azure-tailscale-ha.yaml"


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _intrinsic(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return {"Fn::" + suffix: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {"Fn::" + suffix: loader.construct_sequence(node)}
    return {"Fn::" + suffix: loader.construct_mapping(node)}


CloudFormationLoader.add_multi_constructor("!", _intrinsic)


class TailscaleHaTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=CloudFormationLoader)
        cls.resources = cls.template["Resources"]

    def test_template_creates_two_hardened_private_router_instances(self):
        instances = [r for r in self.resources.values() if r["Type"] == "AWS::EC2::Instance"]
        self.assertEqual(len(instances), 2)
        for resource in instances:
            props = resource["Properties"]
            self.assertFalse(props["SourceDestCheck"])
            metadata = props["MetadataOptions"]
            self.assertEqual(metadata["HttpTokens"], "required")
            self.assertNotIn("AssociatePublicIpAddress", props)
            root = props["BlockDeviceMappings"][0]["Ebs"]
            self.assertTrue(root["Encrypted"])
            self.assertEqual(root["VolumeType"], "gp3")

    def test_router_security_group_has_no_internet_ingress(self):
        groups = [r["Properties"] for r in self.resources.values()
                  if r["Type"] == "AWS::EC2::SecurityGroup"]
        self.assertEqual(len(groups), 1)
        ingress = groups[0].get("SecurityGroupIngress", [])
        self.assertFalse(ingress, "Ingress rules live separately to avoid a CloudFormation dependency cycle")
        ingress_resources = [r["Properties"] for r in self.resources.values()
                             if r["Type"] == "AWS::EC2::SecurityGroupIngress"]
        self.assertEqual(len(ingress_resources), 2)
        self.assertTrue(all(rule["GroupId"] == {"Fn::Ref": "RouterSecurityGroup"}
                            for rule in ingress_resources))
        self.assertTrue(all(rule.get("CidrIp") != "0.0.0.0/0" and
                            rule.get("CidrIpv6") != "::/0" for rule in ingress_resources))
        self.assertTrue(any(rule.get("CidrIp") == {"Fn::Ref": "AppCidr"}
                            for rule in ingress_resources))
        self.assertTrue(any(rule.get("SourceSecurityGroupId") == {"Fn::Ref": "RouterSecurityGroup"}
                            for rule in ingress_resources))

    def test_private_wms_route_is_opt_in_and_targets_only_the_primary_router(self):
        route_resources = [r for r in self.resources.values() if r["Type"] == "AWS::EC2::Route"]
        self.assertEqual(len(route_resources), 1)
        route = route_resources[0]
        self.assertEqual(route["Condition"], "EnablePrivateWmsRoute")
        self.assertEqual(route["Properties"]["DestinationCidrBlock"], "10.20.1.4/32")
        self.assertEqual(route["Properties"]["NetworkInterfaceId"], {"Fn::GetAtt": "PrimaryRouter.PrimaryNetworkInterfaceId"})
        condition = self.template["Conditions"]["EnablePrivateWmsRoute"]
        self.assertEqual(condition, {"Fn::Equals": [{"Fn::Ref": "EnablePrivateWmsRoute"}, "true"]})
        self.assertEqual(self.template["Parameters"]["EnablePrivateWmsRoute"]["Default"], "false")

    def test_role_scopes_secret_reads_and_route_replacement(self):
        role = next(r["Properties"] for r in self.resources.values() if r["Type"] == "AWS::IAM::Role")
        inline = role["Policies"]
        document = str(inline)
        self.assertIn("secretsmanager:GetSecretValue", document)
        self.assertIn("PrimaryAuthKeySecretName", document)
        self.assertIn("BackupAuthKeySecretName", document)
        self.assertEqual(self.template["Parameters"]["PrimaryAuthKeySecretName"]["Default"],
                         "tangamandapio/tailscale/aws-pilot")
        self.assertEqual(self.template["Parameters"]["BackupAuthKeySecretName"]["Default"],
                         "tangamandapio/tailscale/aws-backup")
        self.assertIn("ec2:ReplaceRoute", document)
        self.assertIn("AppRouteTableId", document)

    def test_no_auth_key_material_is_embedded_in_template(self):
        text = TEMPLATE.read_text(encoding="utf-8").lower()
        self.assertNotIn("tskey-auth-", text)
        self.assertNotRegex(text, r"--auth-key\s+[a-z0-9]{20,}")

    def test_deployer_validates_both_auth_secrets_before_uploading_or_creating_ec2(self):
        script = (TEMPLATE.parent / "deploy_tailscale_ha.sh").read_text(encoding="utf-8")
        self.assertIn("secretsmanager get-secret-value", script)
        self.assertIn("^tskey-auth-[A-Za-z0-9_-]{20,}$", script)
        self.assertLess(script.index("^tskey-auth-"), script.index('aws s3 cp "$BUNDLE"'))


if __name__ == "__main__":
    unittest.main()
