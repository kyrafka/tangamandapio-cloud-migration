mock_provider "azurerm" {}

run "blocks_billable_gateway_without_approval" {
  command = plan

  variables {
    subscription_id              = "00000000-0000-0000-0000-000000000000"
    root_certificate_public_data = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    deployment_approved          = false
  }

  expect_failures = [
    terraform_data.p2s_cost_gate,
  ]
}

run "plans_client_openvpn_into_existing_gateway_subnet" {
  command = plan

  override_data {
    target = data.azurerm_resource_group.network
    values = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangama-private-network"
      name     = "rg-tangama-private-network"
      location = "westus"
    }
  }

  override_data {
    target = data.azurerm_virtual_network.network
    values = {
      id                  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private"
      name                = "vnet-tangama-private"
      resource_group_name = "rg-tangama-private-network"
      location            = "westus"
    }
  }

  override_data {
    target = data.azurerm_subnet.gateway
    values = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private/subnets/GatewaySubnet"
    }
  }

  variables {
    subscription_id              = "00000000-0000-0000-0000-000000000000"
    root_certificate_public_data = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    deployment_approved          = true
  }

  assert {
    condition     = azurerm_virtual_network_gateway.p2s.vpn_type == "RouteBased" && azurerm_virtual_network_gateway.p2s.sku == "VpnGw1AZ"
    error_message = "El gateway P2S debe usar VPN route-based y la SKU AZ admitida."
  }

  assert {
    condition     = toset(azurerm_virtual_network_gateway.p2s.vpn_client_configuration[0].vpn_client_protocols) == toset(["OpenVPN"])
    error_message = "El perfil de cliente debe usar OpenVPN para las instancias Linux de AWS."
  }

  assert {
    condition     = toset(azurerm_virtual_network_gateway.p2s.vpn_client_configuration[0].vpn_auth_types) == toset(["Certificate"])
    error_message = "La conexión debe requerir certificado cliente."
  }

  assert {
    condition     = toset(azurerm_virtual_network_gateway.p2s.vpn_client_configuration[0].address_space) == toset(["172.31.250.0/24"])
    error_message = "El pool P2S debe permanecer separado de los CIDR de AWS y Azure."
  }

  assert {
    condition     = azurerm_virtual_network_gateway.p2s.ip_configuration[0].subnet_id == data.azurerm_subnet.gateway.id
    error_message = "El gateway debe usar la GatewaySubnet existente."
  }
}
