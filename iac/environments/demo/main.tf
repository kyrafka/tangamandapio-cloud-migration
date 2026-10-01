module "aws_network" {
  source = "../../modules/aws_network"

  name_prefix = local.name_prefix
  vpc_cidr    = var.aws_vpc_cidr
  tags        = local.common_tags
}

# Mantener false hasta confirmar región, presupuesto y nombre único de Storage Account.
module "azure_operations" {
  count  = var.enable_azure ? 1 : 0
  source = "../../modules/azure_operations"

  location             = var.azure_location
  resource_group_name  = var.azure_resource_group_name
  storage_account_name = var.azure_storage_account_name
  name_prefix          = local.name_prefix
  tags                 = local.common_tags
}
