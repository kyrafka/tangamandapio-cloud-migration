output "storage_account_name" {
  description = "Dedicated storage account for private Terraform state blobs."
  value       = azurerm_storage_account.state.name
}

output "container_name" {
  description = "Private container holding Terraform state."
  value       = azurerm_storage_container.state.name
}

output "state_backend_scope" {
  description = "Azure RBAC scope for the Terraform state container account."
  value       = azurerm_storage_account.state.id
}
