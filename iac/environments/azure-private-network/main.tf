locals {
  project_tags = {
    Project     = "Tangamandapio-Cloud"
    Environment = "academic-demo"
    ManagedBy   = "Terraform"
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "network" {
  name     = "rg-tangama-private-network"
  location = "westus"
  tags     = local.project_tags
}

resource "azurerm_virtual_network" "network" {
  name                = "vnet-tangama-private"
  address_space       = ["10.20.0.0/16"]
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name
  tags                = local.project_tags
}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.network.name
  address_prefixes     = ["10.20.255.0/27"]
}

resource "azurerm_subnet" "workloads" {
  name                 = "snet-private-workloads"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.network.name
  address_prefixes     = ["10.20.0.0/24"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "snet-private-endpoints"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.network.name
  address_prefixes     = ["10.20.1.0/24"]
}

resource "azurerm_subnet" "flex_integration" {
  name                 = "snet-flex-functions"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.network.name
  address_prefixes     = ["10.20.2.0/27"]

  delegation {
    name = "flex-consumption"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_key_vault" "vpn_pki" {
  name                       = "kv-tangama-vpn-261104"
  location                   = azurerm_resource_group.network.location
  resource_group_name        = azurerm_resource_group.network.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.project_tags
}

resource "azurerm_role_assignment" "vpn_pki_operator" {
  scope                = azurerm_key_vault.vpn_pki.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

output "resource_group_name" {
  value = azurerm_resource_group.network.name
}

output "virtual_network_name" {
  value = azurerm_virtual_network.network.name
}

output "private_endpoint_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "flex_integration_subnet_id" {
  value = azurerm_subnet.flex_integration.id
}

output "vpn_pki_vault_name" {
  value = azurerm_key_vault.vpn_pki.name
}
