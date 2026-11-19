"""Exercise production CloudFormation resources and the existing Terraform network module in Moto."""

import json
import os
from pathlib import Path
from shutil import copytree
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
import yaml

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "http://127.0.0.1:5000"
REGION = "us-east-2"


def local_client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, region_name=REGION,
                        aws_access_key_id="test", aws_secret_access_key="test")


class CloudFormationLoader(yaml.SafeLoader):
    pass


def intrinsic(loader, tag, node):
    name = tag if tag in {"Ref", "Condition"} else f"Fn::{tag}"
    if isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node, deep=True)
    else:
        value = loader.construct_scalar(node)
        if tag == "GetAtt":
            value = value.split(".", 1)
    return {name: value}


CloudFormationLoader.add_multi_constructor("!", intrinsic)


def describe_network(vpc_id):
    ec2 = local_client("ec2")
    filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
    subnets = ec2.describe_subnets(Filters=filters)["Subnets"]
    routing = ec2.describe_route_tables(Filters=filters)["RouteTables"]
    assert len(subnets) == 6
    assert len({subnet["AvailabilityZone"] for subnet in subnets}) == 2
    public_ips = sum(bool(subnet["MapPublicIpOnLaunch"]) for subnet in subnets)
    assert sum({tag["Key"]: tag["Value"] for tag in subnet.get("Tags", [])}.get("Tier") == "public"
               for subnet in subnets) == 2
    associations = sum(bool(association.get("SubnetId")) for table in routing for association in table["Associations"])
    internet = any(route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get("GatewayId", "").startswith("igw-")
                   for table in routing for route in table["Routes"])
    return {"subnets": len(subnets), "zones": 2, "explicit_route_associations": associations, "internet_route": internet,
            "auto_assign_public_ip_observed": public_ips}


def observed_bucket_feature(read, missing_code):
    try:
        return read()
    except ClientError as error:
        if error.response["Error"]["Code"] != missing_code:
            raise
        return None


def cloudformation(name):
    source = (ROOT / "cloudformation/aws-lab.yaml").read_text(encoding="utf-8")
    definition = yaml.load(source, Loader=CloudFormationLoader)
    # This slice preserves the actual resource declarations, mappings and references.
    types = {"AWS::EC2::VPC", "AWS::EC2::InternetGateway", "AWS::EC2::VPCGatewayAttachment",
             "AWS::EC2::Subnet", "AWS::EC2::RouteTable", "AWS::EC2::Route",
             "AWS::EC2::SubnetRouteTableAssociation", "AWS::S3::Bucket", "AWS::S3::BucketPolicy"}
    resources = {key: value for key, value in definition["Resources"].items() if value["Type"] in types}
    resources = {key: value for key, value in resources.items()
                 if not value.get("Condition") and "NatGatewayId" not in value["Properties"]}
    smoke = {"Parameters": {"ProjectName": definition["Parameters"]["ProjectName"]},
             "Mappings": definition["Mappings"], "Resources": resources}
    client = local_client("cloudformation")
    stack = client.create_stack(StackName=name, TemplateBody=json.dumps(smoke),
                                Parameters=[{"ParameterKey": "ProjectName", "ParameterValue": name}])["StackId"]
    report = {}
    try:
        client.get_waiter("stack_create_complete").wait(StackName=stack, WaiterConfig={"Delay": 1, "MaxAttempts": 30})
        physical = {entry["LogicalResourceId"]: entry["PhysicalResourceId"]
                    for entry in client.list_stack_resources(StackName=stack)["StackResourceSummaries"]}
        policies = {key for key, value in resources.items() if value["Type"] == "AWS::S3::BucketPolicy"}
        assert set(physical) - {""} == set(resources) - policies
        network = describe_network(physical["VPC"])
        s3 = local_client("s3")
        bucket = physical["AssetBucket"]
        encryption = s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]["Rules"][0]
        assert encryption["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
        access = observed_bucket_feature(lambda: s3.get_public_access_block(Bucket=bucket), "NoSuchPublicAccessBlockConfiguration")
        lifecycle = observed_bucket_feature(lambda: s3.get_bucket_lifecycle_configuration(Bucket=bucket), "NoSuchLifecycleConfiguration")
        retention = next((rule["Expiration"]["Days"] for rule in (lifecycle or {}).get("Rules", [])
                          if rule["ID"] == "ExpireManualPostgresCheckpoints"), None)
        applied_policies = []
        for policy in sorted(policies):
            attached_bucket = physical[resources[policy]["Properties"]["Bucket"]["Ref"]]
            current = observed_bucket_feature(lambda: s3.get_bucket_policy(Bucket=attached_bucket), "NoSuchBucketPolicy")
            if current and json.loads(current["Policy"])["Statement"]:
                applied_policies.append(policy)
        report = {"declared_resources": sorted(resources), "identified_resources": sorted(key for key in physical if key),
                  "bucket_policies_observed": applied_policies, "network": network, "bucket_encryption": "AES256",
                  "block_public_access_observed": all(access["PublicAccessBlockConfiguration"].values()) if access else None,
                  "manual_backup_retention_days_observed": retention, "created": True}
    finally:
        try:
            client.delete_stack(StackName=stack)
            client.get_waiter("stack_delete_complete").wait(StackName=stack, WaiterConfig={"Delay": 1, "MaxAttempts": 30})
            report["deleted"] = True
        except ClientError as error:
            if error.response["Error"]["Code"] != "DependencyViolation":
                raise
            report.update(deleted=False, emulator_delete_error="DependencyViolation")
    return report


def terraform(name):
    with TemporaryDirectory(prefix="tangama-iac-") as directory:
        scratch = Path(directory)
        target = scratch / "local-emulator/terraform"
        copytree(ROOT / "local-emulator/terraform", target, ignore=lambda _path, entries: [name for name in entries if name.startswith(".")])
        copytree(ROOT / "modules/aws_network", scratch / "modules/aws_network")
        environment = {key: value for key, value in os.environ.items() if not key.startswith(("AWS_", "TF_"))}
        environment.update(TF_IN_AUTOMATION="1", AWS_EC2_METADATA_DISABLED="true", TF_VAR_test_name=name)

        def run(*args):
            process = subprocess.run(["terraform", f"-chdir={target}", *args, "-no-color"], env=environment,
                                     text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=240)
            if process.returncode:
                raise RuntimeError(f"Terraform {args[0]} failed\n{process.stdout}\n{process.stderr}")

        run("init")
        run("validate")
        try:
            run("apply", "-auto-approve", "-input=false")
            state = json.loads((target / "terraform.tfstate").read_text(encoding="utf-8"))
            entries = [resource for resource in state["resources"] if resource["mode"] == "managed"]
            vpc = next(resource for resource in entries if resource["type"] == "aws_vpc")["instances"][0]["attributes"]["id"]
            provider = (target / ".terraform.lock.hcl").read_text(encoding="utf-8")
            version = next(line.split('"')[1] for line in provider.splitlines() if line.strip().startswith("version "))
            network = describe_network(vpc)
            assert network["auto_assign_public_ip_observed"] == 2
            assert network["explicit_route_associations"] == 6 and network["internet_route"]
            report = {"aws_provider_version": version, "managed_resource_count": sum(len(resource["instances"]) for resource in entries),
                      "network": network, "created": True}
        finally:
            run("destroy", "-auto-approve", "-input=false")
        remaining = local_client("ec2").describe_vpcs(Filters=[{"Name": "tag:EmulatorRun", "Values": [name]}])["Vpcs"]
        assert not remaining
        return {**report, "deleted": True}


def scaling(name):
    sys.path.insert(0, str(ROOT.parent / "app/aws_release/current"))
    from admin_cloud_tools import RESTORE_ACTION, hold_scaling_capacity, read_scaling_group

    client = local_client("autoscaling")
    client.create_launch_configuration(LaunchConfigurationName=name, ImageId="ami-0123456789abcdef0",
                                       InstanceType="t3.micro")
    results = []
    try:
        for target in (3, 4, 5):
            group = f"{name}-{target}"
            client.create_auto_scaling_group(AutoScalingGroupName=group, LaunchConfigurationName=name,
                                             MinSize=2, MaxSize=5, DesiredCapacity=2, AvailabilityZones=["us-east-2a"])
            try:
                hold_scaling_capacity(client, group, target)
                current = read_scaling_group(client, group)
                actions = client.describe_scheduled_actions(AutoScalingGroupName=group,
                                                            ScheduledActionNames=[RESTORE_ACTION])["ScheduledUpdateGroupActions"]
                restore = actions[0]
                assert current["desired"] == current["minimum"] == target
                assert restore["MinSize"] == restore["DesiredCapacity"] == 2
                results.append({"requested": target, "desired_observed": current["desired"], "restore_minimum": restore["MinSize"],
                                "restore_desired": restore["DesiredCapacity"]})
            finally:
                client.delete_auto_scaling_group(AutoScalingGroupName=group, ForceDelete=True)
    finally:
        client.delete_launch_configuration(LaunchConfigurationName=name)
    return {"cases": results, "automatic_execution_observed": False}


if __name__ == "__main__":
    run_id = uuid4().hex[:8]
    report = {"endpoint": ENDPOINT, "cloudformation": cloudformation(f"iac-cfn-{run_id}"),
              "terraform": terraform(f"iac-tf-{run_id}"), "scaling": scaling(f"iac-asg-{run_id}")}
    rendered = json.dumps(report, indent=2) + "\n"
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(rendered, encoding="utf-8")
    print(rendered)
