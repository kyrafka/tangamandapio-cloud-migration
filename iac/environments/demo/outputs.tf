output "aws_vpc_id" {
  description = "ID de la VPC principal."
  value       = module.aws_network.vpc_id
}

output "aws_public_subnet_ids" {
  description = "Subredes públicas para ALB y gateways."
  value       = module.aws_network.public_subnet_ids
}

output "aws_app_subnet_ids" {
  description = "Subredes privadas de aplicación."
  value       = module.aws_network.app_subnet_ids
}

output "aws_db_subnet_ids" {
  description = "Subredes privadas de datos."
  value       = module.aws_network.db_subnet_ids
}

output "azure_resource_group" {
  description = "Grupo de recursos Azure cuando está habilitado."
  value       = var.enable_azure ? module.azure_operations[0].resource_group_name : null
}

output "azure_function_hostname" {
  description = "Hostname de la Function App Azure cuando está habilitada."
  value       = var.enable_azure ? module.azure_operations[0].function_default_hostname : null
}

output "azure_storage_account" {
  description = "Cuenta de almacenamiento Azure cuando está habilitada."
  value       = var.enable_azure ? module.azure_operations[0].storage_account_name : null
}
