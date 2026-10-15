mock_provider "azurerm" {}

run "refuses_billable_plan_without_cost_approval" {
  command = plan

  variables {
    subscription_id     = "00000000-0000-0000-0000-000000000000"
    deployment_approved = false
  }

  expect_failures = [
    terraform_data.flex_cost_gate,
  ]
}

run "plans_private_by_default_with_required_networking" {
  command = plan

  override_data {
    target = data.azurerm_resource_group.operations
    values = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangamandapio-rebuild-wus"
      name     = "rg-tangamandapio-rebuild-wus"
      location = "westus"
    }
  }

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
    target = data.azurerm_subnet.flex_integration
    values = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private/subnets/snet-flex-functions"
    }
  }

  override_data {
    target = data.azurerm_subnet.private_endpoints
    values = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private/subnets/snet-private-endpoints"
    }
  }

  override_data {
    target = data.azurerm_storage_account.operations
    values = {
      id                    = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangamandapio-rebuild-wus/providers/Microsoft.Storage/storageAccounts/sttangama261008r"
      name                  = "sttangama261008r"
      primary_blob_endpoint = "https://sttangama261008r.blob.core.windows.net/"
    }
  }

  override_data {
    target = data.azurerm_application_insights.wms
    values = {
      id                = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-tangamandapio-rebuild-wus/providers/Microsoft.Insights/components/tangama-wms-ai"
      connection_string = "InstrumentationKey=00000000-0000-0000-0000-000000000000;IngestionEndpoint=https://westus-0.in.applicationinsights.azure.com/"
    }
  }

  variables {
    subscription_id     = "00000000-0000-0000-0000-000000000000"
    deployment_approved = true
  }

  assert {
    condition     = azurerm_function_app_flex_consumption.wms.public_network_access_enabled == false
    error_message = "El estado final predeterminado debe bloquear el acceso público al WMS Flex."
  }

  assert {
    condition     = azurerm_function_app_flex_consumption.wms.virtual_network_subnet_id == data.azurerm_subnet.flex_integration.id
    error_message = "La Function debe integrarse a la subnet Flex dedicada."
  }

  assert {
    condition     = length(azurerm_private_endpoint.function.private_service_connection[0].subresource_names) == 1 && contains(azurerm_private_endpoint.function.private_service_connection[0].subresource_names, "sites")
    error_message = "El endpoint privado debe apuntar al subrecurso sites de la Function."
  }

  assert {
    condition     = azurerm_function_app_flex_consumption.wms.storage_authentication_type == "SystemAssignedIdentity"
    error_message = "La Function debe autenticar el storage de deployment con identidad administrada."
  }

  assert {
    condition     = startswith(azurerm_function_app_flex_consumption.wms.storage_container_endpoint, "https://sttangama261008r.blob.core.windows.net/")
    error_message = "Flex requiere el endpoint HTTPS del contenedor de paquetes, no un ID ARM."
  }
}

run "requires_acknowledgement_for_public_bootstrap" {
  command = plan

  variables {
    subscription_id                      = "00000000-0000-0000-0000-000000000000"
    deployment_approved                  = true
    bootstrap_public_access_enabled      = true
    bootstrap_public_access_acknowledged = false
  }

  expect_failures = [
    terraform_data.flex_cost_gate,
  ]
}
