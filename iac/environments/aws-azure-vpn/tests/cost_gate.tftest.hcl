mock_provider "azurerm" {}

run "rejects_plan_without_cost_approval" {
  command = plan

  variables {
    deployment_approved = false
  }

  expect_failures = [
    terraform_data.vpn_cost_gate,
  ]
}

run "plans_active_active_gateway_after_approval" {
  command = plan

  variables {
    deployment_approved = true
  }

  assert {
    condition     = azurerm_virtual_network_gateway.network.active_active && azurerm_virtual_network_gateway.network.enable_bgp
    error_message = "El diseño aprobado debe conservar BGP y gateway activo-activo."
  }

  assert {
    condition     = azurerm_virtual_network_gateway.network.sku == "VpnGw1AZ"
    error_message = "Las nuevas implementaciones usan la SKU zonal admitida por Azure."
  }

  assert {
    condition = (one(azurerm_subnet.flex_integration.address_prefixes) == "10.20.2.0/27" &&
      azurerm_subnet.flex_integration.delegation[0].service_delegation[0].name == "Microsoft.App/environments"
    )
    error_message = "Flex Consumption debe usar su subred /27 dedicada con delegación Microsoft.App/environments."
  }
}
