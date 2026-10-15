output "function_app_name" {
  value = azurerm_function_app_flex_consumption.wms.name
}

output "function_hostname" {
  description = "Public Azure Functions hostname preserved for HTTPS host/SNI; AWS private DNS must map this exact name to the private endpoint IP."
  value       = "${var.function_app_name}.azurewebsites.net"
}

output "function_private_endpoint_ip" {
  value = azurerm_private_endpoint.function.private_service_connection[0].private_ip_address
}

output "function_private_dns_zone_id" {
  value = azurerm_private_dns_zone.function.id
}

output "flex_integration_subnet_id" {
  value = data.azurerm_subnet.flex_integration.id
}

output "public_access_enabled" {
  value       = azurerm_function_app_flex_consumption.wms.public_network_access_enabled
  description = "Must be false in the final state; true is only for the acknowledged package bootstrap stage."
}
