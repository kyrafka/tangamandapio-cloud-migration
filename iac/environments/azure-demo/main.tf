locals {
  tags = {
    Project            = "Tangamandapio-Cloud"
    Environment        = "academic-demo"
    Owner              = "academic-team"
    ManagedBy          = "Terraform"
    DataClassification = "Synthetic"
    CostControl        = "destroy-after-test"
  }
}

module "azure_operations" {
  source = "../../modules/azure_operations"

  location              = var.location
  resource_group_name   = var.resource_group_name
  create_resource_group = var.create_resource_group
  storage_account_name  = var.storage_account_name
  key_vault_name        = var.key_vault_name
  name_prefix           = var.name_prefix
  tags                  = local.tags
}
