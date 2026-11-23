output "resource_group_name" {
  value = local.operations_resource_group_name
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "function_default_hostname" {
  value = var.deploy_legacy_consumption ? azurerm_linux_function_app.wms[0].default_hostname : null
}

output "function_principal_id" {
  value = var.deploy_legacy_consumption ? azurerm_linux_function_app.wms[0].identity[0].principal_id : null
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.operations.id
}
