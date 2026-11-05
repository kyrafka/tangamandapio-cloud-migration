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
    key                  = "azure-tailscale-pilot.tfstate"
    use_azuread_auth     = true
    use_cli              = true
  }
}
