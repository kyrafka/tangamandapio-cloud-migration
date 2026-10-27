output "gateway_id" {
  description = "Resource ID of the Azure Point-to-Site VPN Gateway."
  value       = azurerm_virtual_network_gateway.p2s.id
}

output "gateway_public_ip" {
  description = "Static public endpoint used by AWS OpenVPN clients."
  value       = azurerm_public_ip.p2s.ip_address
}

output "client_address_pool" {
  description = "Private address pool assigned to connected AWS client instances."
  value       = var.client_address_pool
}
