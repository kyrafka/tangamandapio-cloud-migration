output "resource_group_name" {
  value = azurerm_resource_group.network.name
}

output "virtual_network_name" {
  value = azurerm_virtual_network.network.name
}

output "virtual_network_gateway_name" {
  value = azurerm_virtual_network_gateway.network.name
}

output "azure_gateway_public_ips" {
  description = "Two Azure active-active VPN gateway public IPs; pass these to the AWS VPN CloudFormation stack."
  value       = { for key, pip in azurerm_public_ip.gateway : key => pip.ip_address }
}

output "azure_gateway_bgp_asn" {
  value = var.azure_bgp_asn
}

output "azure_vnet_cidr" {
  value = var.azure_vnet_cidr
}

output "workload_subnet_id" {
  value = azurerm_subnet.workloads.id
}

output "private_endpoint_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "flex_integration_subnet_id" {
  description = "Dedicated /27 subnet for a future Flex Consumption Function App; no Function is deployed by this network stack."
  value       = azurerm_subnet.flex_integration.id
}

output "flex_integration_subnet_cidr" {
  value = one(azurerm_subnet.flex_integration.address_prefixes)
}
