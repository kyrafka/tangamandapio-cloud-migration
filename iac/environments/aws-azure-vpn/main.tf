resource "terraform_data" "vpn_cost_gate" {
  input = var.deployment_approved

  lifecycle {
    precondition {
      condition     = var.deployment_approved
      error_message = "La VPN AWS–Azure tiene cargos recurrentes. Revise el costo y el saldo del laboratorio, y solo entonces establezca deployment_approved=true."
    }
  }
}

resource "azurerm_resource_group" "network" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags

  # Every Azure resource, including billable Public IPs, depends transitively
  # on this gate. An unapproved plan cannot partially create billable pieces.
  depends_on = [terraform_data.vpn_cost_gate]
}

resource "azurerm_virtual_network" "network" {
  name                = var.vnet_name
  address_space       = [var.azure_vnet_cidr]
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name
  tags                = var.tags

}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  resource_group_name  = azurerm_resource_group.network.name
  virtual_network_name = azurerm_virtual_network.network.name
  address_prefixes     = [var.gateway_subnet_cidr]
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

# Flex Consumption needs its own delegated integration subnet. Keep it
# separate from GatewaySubnet and the Private Endpoint subnet; Azure Functions
# consumes it for outbound VNet routing to the AWS VPN and private services.
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

resource "azurerm_public_ip" "gateway" {
  for_each            = toset(["a", "b"])
  name                = "pip-tangama-vpn-${each.key}"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_virtual_network_gateway" "network" {
  name                = "vng-tangama-aws"
  location            = azurerm_resource_group.network.location
  resource_group_name = azurerm_resource_group.network.name
  type                = "Vpn"
  vpn_type            = "RouteBased"
  active_active       = true
  enable_bgp          = true
  sku                 = var.gateway_sku
  generation          = "Generation1"
  tags                = var.tags

  ip_configuration {
    name                          = "active-active-a"
    public_ip_address_id          = azurerm_public_ip.gateway["a"].id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway.id
  }

  ip_configuration {
    name                          = "active-active-b"
    public_ip_address_id          = azurerm_public_ip.gateway["b"].id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gateway.id
  }

  bgp_settings {
    asn = var.azure_bgp_asn

    peering_addresses {
      ip_configuration_name = "active-active-a"
      apipa_addresses       = ["169.254.21.2", "169.254.22.2"]
    }

    peering_addresses {
      ip_configuration_name = "active-active-b"
      apipa_addresses       = ["169.254.21.6", "169.254.22.6"]
    }
  }

  # Create every subnet before the VPN gateway. Azure's Network provider
  # rejects concurrent subnet writes while the gateway is Updating; this
  # ordering also ensures the gateway is deleted before any VNet subnet.
  depends_on = [
    azurerm_subnet.gateway,
    azurerm_subnet.workloads,
    azurerm_subnet.private_endpoints,
    azurerm_subnet.flex_integration,
  ]
}
