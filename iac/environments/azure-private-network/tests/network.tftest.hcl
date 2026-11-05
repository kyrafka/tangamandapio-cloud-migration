mock_provider "azurerm" {}

run "plans_private_network_for_p2s_and_flex" {
  command = plan

  override_data {
    target = data.azurerm_client_config.current
    values = {
      tenant_id       = "00000000-0000-0000-0000-000000000001"
      object_id       = "00000000-0000-0000-0000-000000000002"
      subscription_id = "00000000-0000-0000-0000-000000000000"
      client_id       = "00000000-0000-0000-0000-000000000003"
    }
  }

  variables {
    subscription_id = "00000000-0000-0000-0000-000000000000"
  }

  assert {
    condition     = toset(azurerm_virtual_network.network.address_space) == toset(["10.20.0.0/16"])
    error_message = "La VNet debe usar el CIDR Azure sin solapar AWS."
  }

  assert {
    condition     = azurerm_subnet.gateway.name == "GatewaySubnet" && toset(azurerm_subnet.gateway.address_prefixes) == toset(["10.20.255.0/27"])
    error_message = "La subred del gateway debe quedar preparada para P2S."
  }

  assert {
    condition     = azurerm_subnet.private_endpoints.name == "snet-private-endpoints" && toset(azurerm_subnet.private_endpoints.address_prefixes) == toset(["10.20.1.0/24"])
    error_message = "El endpoint privado debe tener su propia subred."
  }

  assert {
    condition     = azurerm_subnet.flex_integration.name == "snet-flex-functions" && azurerm_subnet.flex_integration.delegation[0].service_delegation[0].name == "Microsoft.App/environments"
    error_message = "Flex requiere una subred dedicada y delegada."
  }

  assert {
    condition     = azurerm_key_vault.vpn_pki.rbac_authorization_enabled && azurerm_key_vault.vpn_pki.soft_delete_retention_days == 7
    error_message = "La CA VPN necesita un almacén dedicado con RBAC y retención."
  }

  assert {
    condition     = azurerm_role_assignment.vpn_pki_operator.role_definition_name == "Key Vault Secrets Officer" && azurerm_role_assignment.vpn_pki_operator.principal_id == data.azurerm_client_config.current.object_id
    error_message = "El operador de certificados debe tener el rol previsto."
  }
}
