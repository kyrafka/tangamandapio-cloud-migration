terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tangamandapio-tfstate-wus"
    storage_account_name = "sttangamatfstate261014"
    container_name       = "tfstate"
    key                  = "azure-p2s-vpn.tfstate"
    use_azuread_auth     = true
    use_cli              = true
  }
}
