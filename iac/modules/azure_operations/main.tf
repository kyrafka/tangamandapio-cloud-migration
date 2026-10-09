data "azurerm_resource_group" "existing" {
  count = var.create_resource_group ? 0 : 1
  name  = var.resource_group_name
}

resource "azurerm_resource_group" "this" {
  count    = var.create_resource_group ? 1 : 0
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

data "azurerm_client_config" "current" {}

locals {
  operations_resource_group_name = var.create_resource_group ? azurerm_resource_group.this[0].name : data.azurerm_resource_group.existing[0].name
  operations_location            = var.create_resource_group ? azurerm_resource_group.this[0].location : data.azurerm_resource_group.existing[0].location
}

resource "azurerm_log_analytics_workspace" "operations" {
  name                = "${var.name_prefix}-ops-law"
  location            = local.operations_location
  resource_group_name = local.operations_resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "wms" {
  name                = "${var.name_prefix}-wms-ai"
  location            = local.operations_location
  resource_group_name = local.operations_resource_group_name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.operations.id
  tags                = var.tags
}

resource "azurerm_storage_account" "this" {
  name                            = var.storage_account_name
  resource_group_name             = local.operations_resource_group_name
  location                        = local.operations_location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true
  tags                            = var.tags

  blob_properties {
    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_container" "evidence" {
  name                  = "fulfillment-events"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

resource "azurerm_storage_queue" "fulfillment" {
  name                 = "fulfillment-events"
  storage_account_name = azurerm_storage_account.this.name
}

resource "azurerm_key_vault" "operations" {
  name                          = var.key_vault_name
  location                      = local.operations_location
  resource_group_name           = local.operations_resource_group_name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  public_network_access_enabled = true
  tags                          = var.tags

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

resource "azurerm_service_plan" "function" {
  name                = "${var.name_prefix}-wms-plan"
  resource_group_name = local.operations_resource_group_name
  location            = local.operations_location
  os_type             = "Linux"
  sku_name            = "Y1"
  tags                = var.tags
}

resource "azurerm_linux_function_app" "wms" {
  name                       = "${var.name_prefix}-wms-fn"
  resource_group_name        = local.operations_resource_group_name
  location                   = local.operations_location
  service_plan_id            = azurerm_service_plan.function.id
  storage_account_name       = azurerm_storage_account.this.name
  storage_account_access_key = azurerm_storage_account.this.primary_access_key
  zip_deploy_file            = var.function_package_path
  https_only                 = true
  tags                       = var.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
    minimum_tls_version = "1.2"
    ftps_state          = "Disabled"

    # Permite la prueba integrada del Portal de Azure sin abrir el endpoint
    # a orígenes arbitrarios. El acceso productivo se restringe además por
    # autenticación, firma del evento y la IP de egreso de AWS.
    cors {
      allowed_origins = ["https://portal.azure.com"]
    }
  }

  app_settings = {
    "FUNCTIONS_EXTENSION_VERSION" = "~4"
    "FUNCTIONS_WORKER_RUNTIME"    = "python"
    # Required host storage.  The Function runtime uses it internally for
    # trigger metadata and leases; it is distinct from the application Blob
    # and Queue clients, which authenticate with managed identity.
    "AzureWebJobsStorage"      = azurerm_storage_account.this.primary_connection_string
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
    # El proveedor realiza Zip Deploy desde el artefacto generado localmente.
    # Así no se versionan ZIPs ni SAS con caducidad fija en Terraform.
    "DEPLOYMENT_PACKAGE_SHA256"             = filesha256(var.function_package_path)
    "SCM_DO_BUILD_DURING_DEPLOYMENT"        = "false"
    "ENABLE_ORYX_BUILD"                     = "false"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.wms.connection_string
    "WMS_QUEUE_NAME"                        = azurerm_storage_queue.fulfillment.name
    "EVIDENCE_CONTAINER"                    = azurerm_storage_container.evidence.name
    "AZURE_BLOB_ACCOUNT_URL"                = "https://${azurerm_storage_account.this.name}.blob.core.windows.net"
    "AZURE_QUEUE_ACCOUNT_URL"               = "https://${azurerm_storage_account.this.name}.queue.core.windows.net"
    "EVENT_SCHEMA_VERSION"                  = "1.0"
    "WEBSITE_ENABLE_SYNC_UPDATE_SITE"       = "true"
  }
}

resource "azurerm_role_assignment" "function_blob" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_queue" {
  scope                = azurerm_storage_account.this.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_secrets" {
  scope                = azurerm_key_vault.operations.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}
