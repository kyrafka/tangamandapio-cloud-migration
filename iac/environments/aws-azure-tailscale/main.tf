locals {
  expected_account_id = "481056890449"
}

resource "terraform_data" "deployment_guard" {
  input = {
    approved = var.deployment_approved
    account  = data.aws_caller_identity.current.account_id
  }

  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == local.expected_account_id
      error_message = "Este entorno está fijado a la cuenta AWS 481056890449; no despliegues routers en otra cuenta."
    }
  }
}

resource "aws_cloudformation_stack" "router_pair" {
  count = var.deployment_approved ? 1 : 0

  name          = var.stack_name
  template_body = file("${path.module}/../../cloudformation/aws-azure-tailscale-ha.yaml")
  capabilities  = ["CAPABILITY_NAMED_IAM"]
  on_failure    = "ROLLBACK"

  parameters = {
    VpcId                 = var.vpc_id
    AppSubnetA            = var.app_subnet_a
    AppSubnetB            = var.app_subnet_b
    AppRouteTableId       = var.app_route_table_id
    AssetBucketName       = var.asset_bucket_name
    RouterArtifactKey     = var.router_artifact_key
    RouterArtifactSha256  = var.router_artifact_sha256
    EnablePrivateWmsRoute = var.enable_private_wms_route ? "true" : "false"
  }

  tags = {
    Project   = "Tangamandapio"
    ManagedBy = "Terraform+CloudFormation"
  }

  timeouts {
    create = "45m"
    update = "45m"
    delete = "20m"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [terraform_data.deployment_guard]
}
