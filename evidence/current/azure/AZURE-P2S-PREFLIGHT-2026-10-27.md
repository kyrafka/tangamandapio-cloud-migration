# Azure P2S preflight — 27/10/2026

## Current state

- AWS STS accepted the currently supplied Academy token for account
  `654654388734`; no credential values are recorded here.
- The Azure for Students subscription is enabled. The existing WMS Function
  `tangama-wms-261008` is running on `Y1`/Dynamic Consumption, has no VNet
  integration or Private Endpoint, and its HTTPS health endpoint returned
  HTTP 200.
- `vnet-tangama-private` exists in `rg-tangama-private-network` with CIDR
  `10.20.0.0/16` and `GatewaySubnet`. No Azure VPN Gateway, private endpoint, or
  Function VNet integration was found in the current query.
- The domain `https://tangamandapio.kendellnm.me/health` returned HTTP 200.
- AWS CloudFormation stack `tangamandapio-live-20261026` is
  `UPDATE_COMPLETE`. The ASG remains min 2 / desired 2 / max 5. Both EC2
  instances are SSM Online and outbound HTTPS returned HTTP 200. The
  `openvpn` executable was not found on either host.
- No project SQS queue or Lambda function exists. Current IAM simulation
  returns `explicitDeny` for `ec2:CreateCustomerGateway`, `implicitDeny` for
  `iam:CreateRole`/`iam:PassRole`, and `allowed` for SQS/Lambda create actions.
  The existing `LabRole` can read SSM parameters and Secrets Manager values.

## P2S Terraform validation

Root: `iac/environments/azure-p2s-vpn`.

- `terraform fmt -check`: passed.
- `terraform validate`: passed.
- `terraform test`: 2 passed, 0 failed. The tests cover the default cost gate
  and route-based OpenVPN/certificate configuration.
- A read-only plan successfully read the existing resource group, VNet and
  `GatewaySubnet`; it proposed 3 resources to add. The plan used a placeholder
  certificate value only to inspect provider planning and is **not suitable
  for apply**. No resources were created.

## Limits and next gate

Azure P2S can let each AWS application host act as an OpenVPN client into the
Azure VNet, but this is not VPC-to-VNet Site-to-Site connectivity and cannot
close that rubric criterion by itself. The WMS remains public until the
blue-green Flex Function and Private Endpoint/Private DNS are deployed. Before
an end-to-end test, prepare valid certificates without committing private keys,
choose a private DNS method for P2S clients, deploy the private Function, then
configure/test OpenVPN via SSM. The temporary gateway must be destroyed after
the approved test window.

No Azure or AWS resource was modified during this preflight.
