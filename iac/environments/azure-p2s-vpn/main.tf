data "azurerm_resource_group" "network" {
  name = var.resource_group_name
}

data "azurerm_virtual_network" "network" {
  name                = var.virtual_network_name
  resource_group_name = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "gateway" {
  name                 = var.gateway_subnet_name
  virtual_network_name = data.azurerm_virtual_network.network.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

resource "terraform_data" "p2s_cost_gate" {
  input = var.deployment_approved

  lifecycle {
    precondition {
      condition     = var.deployment_approved
      error_message = "Azure VPN Gateway genera cargos horarios; revise el saldo y apruebe explícitamente antes de desplegar."
    }
  }
}

resource "azurerm_public_ip" "p2s" {
  name                = "pip-tangama-aws-p2s"
  location            = data.azurerm_resource_group.network.location
  resource_group_name = data.azurerm_resource_group.network.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags

  depends_on = [terraform_data.p2s_cost_gate]
}

resource "azurerm_virtual_network_gateway" "p2s" {
  name                = "vng-tangama-aws-p2s"
  location            = data.azurerm_resource_group.network.location
  resource_group_name = data.azurerm_resource_group.network.name
  type                = "Vpn"
  vpn_type            = "RouteBased"
  active_active       = false
  bgp_enabled         = false
  sku                 = var.gateway_sku
  generation          = "Generation1"
  tags                = var.tags

  ip_configuration {
    name                          = "vnetGatewayConfig"
    public_ip_address_id          = azurerm_public_ip.p2s.id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = data.azurerm_subnet.gateway.id
  }

  vpn_client_configuration {
    address_space        = [var.client_address_pool]
    vpn_client_protocols = ["OpenVPN"]
    vpn_auth_types       = ["Certificate"]

    root_certificate {
      name             = var.root_certificate_name
      public_cert_data = var.root_certificate_public_data
    }
  }

  depends_on = [terraform_data.p2s_cost_gate]
}
