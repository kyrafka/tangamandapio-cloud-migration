data "azurerm_resource_group" "operations" {
  name = var.resource_group_name
}

data "azurerm_resource_group" "network" {
  name = var.network_resource_group_name
}

data "azurerm_virtual_network" "network" {
  name                = var.virtual_network_name
  resource_group_name = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "flex_integration" {
  name                 = var.flex_integration_subnet_name
  virtual_network_name = data.azurerm_virtual_network.network.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azurerm_subnet" "private_endpoints" {
  name                 = var.private_endpoint_subnet_name
  virtual_network_name = data.azurerm_virtual_network.network.name
  resource_group_name  = data.azurerm_resource_group.network.name
}

data "azurerm_storage_account" "operations" {
  name                = var.storage_account_name
  resource_group_name = data.azurerm_resource_group.operations.name
}

data "azurerm_application_insights" "wms" {
  name                = var.application_insights_name
  resource_group_name = data.azurerm_resource_group.operations.name
}

locals {
  flex_deployment_container_endpoint = "${data.azurerm_storage_account.operations.primary_blob_endpoint}${var.deployment_container_name}"

  function_app_settings = {
    FUNCTIONS_EXTENSION_VERSION               = "~4"
    AzureWebJobsStorage__accountName          = data.azurerm_storage_account.operations.name
    AzureWebJobsStorage__credential           = "managedidentity"
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING = "Authorization=AAD"
    WMS_QUEUE_NAME                            = var.fulfillment_queue_name
    WMS_POISON_QUEUE_NAME                     = var.poison_queue_name
    EVIDENCE_CONTAINER                        = var.events_container_name
    AZURE_BLOB_ACCOUNT_URL                    = "https://${data.azurerm_storage_account.operations.name}.blob.core.windows.net"
    AZURE_QUEUE_ACCOUNT_URL                   = "https://${data.azurerm_storage_account.operations.name}.queue.core.windows.net"
    EVENT_SCHEMA_VERSION                      = "1.0"
    ALLOWED_EVENT_SOURCES                     = join(",", sort(tolist(var.allowed_event_sources)))
  }

  storage_container_scope = "${data.azurerm_storage_account.operations.id}/blobServices/default/containers"
  queue_scope             = "${data.azurerm_storage_account.operations.id}/queueServices/default/queues"
}

# Every billable Azure resource below depends on this explicit cost and
# migration gate. Temporary public bootstrap requires a separate acknowledgement.
resource "terraform_data" "flex_cost_gate" {
  input = {
    deployment_approved             = var.deployment_approved
    bootstrap_public_access_enabled = var.bootstrap_public_access_enabled
  }

  lifecycle {
    precondition {
      condition     = var.deployment_approved
      error_message = "No se despliega Flex ni recursos de red sin revisar costo, presupuesto Azure y plan blue-green."
    }

    precondition {
      condition     = !var.bootstrap_public_access_enabled || var.bootstrap_public_access_acknowledged
      error_message = "El acceso público temporal requiere bootstrap_public_access_acknowledged=true y debe cerrarse después del smoke privado."
    }
  }
}

resource "azurerm_storage_container" "flex_deployments" {
  name                  = var.deployment_container_name
  storage_account_id    = data.azurerm_storage_account.operations.id
  container_access_type = "private"
  depends_on            = [terraform_data.flex_cost_gate]
}

resource "azurerm_service_plan" "flex" {
  name                = "${var.function_app_name}-plan"
  resource_group_name = data.azurerm_resource_group.operations.name
  location            = data.azurerm_resource_group.operations.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = var.tags

  depends_on = [terraform_data.flex_cost_gate]
}

resource "azurerm_function_app_flex_consumption" "wms" {
  name                = var.function_app_name
  resource_group_name = data.azurerm_resource_group.operations.name
  location            = data.azurerm_resource_group.operations.location
  service_plan_id     = azurerm_service_plan.flex.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = local.flex_deployment_container_endpoint
  storage_authentication_type = "SystemAssignedIdentity"
  runtime_name                = "python"
  runtime_version             = "3.11"
  maximum_instance_count      = var.maximum_instance_count
  instance_memory_in_mb       = var.instance_memory_in_mb

  https_only                                     = true
  public_network_access_enabled                  = var.bootstrap_public_access_enabled
  webdeploy_publish_basic_authentication_enabled = false
  virtual_network_subnet_id                      = data.azurerm_subnet.flex_integration.id
  tags                                           = var.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = data.azurerm_application_insights.wms.connection_string
    minimum_tls_version                    = "1.2"
  }

  app_settings = local.function_app_settings

  depends_on = [terraform_data.flex_cost_gate]
}

resource "azurerm_role_assignment" "flex_host_blob" {
  scope                = data.azurerm_storage_account.operations.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_function_app_flex_consumption.wms.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "flex_host_queue" {
  scope                = data.azurerm_storage_account.operations.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.wms.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "flex_deployment_blob" {
  scope                = "${local.storage_container_scope}/${var.deployment_container_name}"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.wms.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "flex_events_blob" {
  scope                = "${local.storage_container_scope}/${var.events_container_name}"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.wms.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "flex_app_insights" {
  scope                = data.azurerm_application_insights.wms.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azurerm_function_app_flex_consumption.wms.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_private_dns_zone" "function" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = data.azurerm_resource_group.network.name
  tags                = var.tags

  depends_on = [terraform_data.flex_cost_gate]
}

resource "azurerm_private_dns_zone_virtual_network_link" "function" {
  name                  = "${var.function_app_name}-dns-link"
  resource_group_name   = data.azurerm_resource_group.network.name
  private_dns_zone_name = azurerm_private_dns_zone.function.name
  virtual_network_id    = data.azurerm_virtual_network.network.id
  registration_enabled  = false
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "function" {
  name                = "${var.function_app_name}-pe"
  location            = data.azurerm_resource_group.network.location
  resource_group_name = data.azurerm_resource_group.network.name
  subnet_id           = data.azurerm_subnet.private_endpoints.id
  tags                = var.tags

  private_service_connection {
    name                           = "${var.function_app_name}-private-link"
    private_connection_resource_id = azurerm_function_app_flex_consumption.wms.id
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "function-private-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.function.id]
  }

  depends_on = [
    terraform_data.flex_cost_gate,
    azurerm_private_dns_zone_virtual_network_link.function,
  ]
}
