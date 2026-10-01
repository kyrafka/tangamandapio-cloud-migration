output "resource_group_name" {
  value = local.operations_resource_group_name
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "function_default_hostname" {
  value = azurerm_linux_function_app.wms.default_hostname
}

output "function_principal_id" {
  value = azurerm_linux_function_app.wms.identity[0].principal_id
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.operations.id
}
