terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.79.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-tangamandapio-tfstate-wus"
    storage_account_name = "sttangamatfstate261014"
    container_name       = "tfstate"
    key                  = "azure-tailscale-backup.tfstate"
    use_azuread_auth     = true
    use_cli              = true
  }
}

variable "subscription_id" { type = string }
variable "ssh_public_key" { type = string }

module "backup" {
  source          = "../azure-tailscale-pilot"
  subscription_id = var.subscription_id
  ssh_public_key  = var.ssh_public_key
  name_suffix     = "backup"
}

output "router_name" { value = module.backup.router_name }
output "router_private_ip" { value = module.backup.router_private_ip }
