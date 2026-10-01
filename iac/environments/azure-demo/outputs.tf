output "resource_group_name" {
  value = module.azure_operations.resource_group_name
}

output "function_hostname" {
  value = module.azure_operations.function_default_hostname
}

output "storage_account_name" {
  value = module.azure_operations.storage_account_name
}
