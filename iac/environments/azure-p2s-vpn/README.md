# Azure Point-to-Site fallback for AWS application hosts

This isolated Terraform root is an **experimental fallback**, not the AWS–Azure
Site-to-Site design. It provisions an Azure RouteBased `VpnGw1AZ` gateway and
accepts OpenVPN certificate clients from the AWS application instances. It
does not attach a VPN gateway to the AWS VPC or provide VPC-wide routing, so it
must not be presented as an equivalent replacement for the course's S2S/BGP
criterion. The managed S2S root remains `../aws-azure-vpn`; AWS Academy
currently returns an explicit deny for `ec2:CreateCustomerGateway`.

The configuration references the existing `vnet-tangama-private` and its
`GatewaySubnet`. The client pool `172.31.250.0/24` is separate from AWS
`10.10.0.0/16` and Azure `10.20.0.0/16`. The gateway is billable while
provisioned, so the default `deployment_approved=false` cost gate must remain
closed until the temporary test window is ready.

## Validation

```powershell
terraform init
terraform fmt -check
terraform validate
terraform test
```

The mock tests cover the cost gate and the OpenVPN/certificate profile. A live
plan must use a valid public root certificate generated for the test; the
private root key and client PFX must stay out of Git, Terraform outputs, logs,
and command history. No certificate is included here.

## End-to-end requirements before apply

1. Generate and securely retain a root signing certificate; issue a client
   certificate for each EC2 instance. Store client PFX/password in an approved
   secret store and retrieve them only through the existing EC2 role.
2. Confirm the private Flex Function, its Private Endpoint, and private DNS
   record are deployed before claiming the WMS is private.
3. P2S clients need a route to the Azure VNet and private-endpoint DNS
   resolution. Azure's platform DNS address `168.63.129.16` cannot be queried
   directly by P2S clients for Private DNS zones; use a supported DNS forwarder
   or a documented, reconciled host mapping. See Microsoft's
   [P2S DNS troubleshooting guidance](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-troubleshoot-vpn-point-to-site-connection-problems)
   and [Function private-endpoint DNS guidance](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options).
4. Install/configure OpenVPN on the EC2 hosts through SSM, verify the VPN
   session and HTTPS request to the Function's private endpoint from each
   instance, then test reconnect/instance replacement.
5. After evidence capture, destroy this Terraform root and verify that the
   gateway and public IP are gone. Preserve only redacted evidence and the
   reproducible configuration.

The current root has no backend configured and has **not** been applied. Do not
run `terraform apply` until state storage, valid certificate handling, private
DNS, and the temporary cost window are all reviewed.
