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
  # Safeguard against accidental telemetry spikes in the student subscription.
  # This is a ceiling, not a substitute for filtering noisy telemetry.
  daily_quota_gb = 0.1
  tags           = var.tags
}

resource "azurerm_application_insights" "wms" {
  name                                  = "${var.name_prefix}-wms-ai"
  location                              = local.operations_location
  resource_group_name                   = local.operations_resource_group_name
  application_type                      = "web"
  workspace_id                          = azurerm_log_analytics_workspace.operations.id
  daily_data_cap_in_gb                  = 0.1
  daily_data_cap_notifications_disabled = true
  retention_in_days                     = 30
  sampling_percentage                   = 100
  tags                                  = var.tags
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

# Linux Consumption loads the Function from an external package URL. Keep the
# release private, immutable and addressable by digest; the app reads it via MI.
resource "azurerm_storage_container" "function_packages" {
  name                  = "function-packages"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

resource "azurerm_storage_blob" "function_package" {
  name                   = "function-${filesha256(var.function_package_path)}.zip"
  storage_account_name   = azurerm_storage_account.this.name
  storage_container_name = azurerm_storage_container.function_packages.name
  type                   = "Block"
  source                 = var.function_package_path
  content_type           = "application/zip"

  # Package names are content-addressed, so both releases can coexist while
  # the Function switches to the new URL. The previous Blob remains recoverable
  # through Storage soft delete if the rollout needs to be rolled back.
  lifecycle {
    create_before_destroy = true
  }
}

resource "azurerm_storage_queue" "fulfillment" {
  name                 = "fulfillment-events"
  storage_account_name = azurerm_storage_account.this.name
}

resource "azurerm_storage_queue" "fulfillment_poison" {
  name                 = "fulfillment-events-poison"
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
  name                                           = coalesce(var.function_app_name, "${var.name_prefix}-wms-fn")
  resource_group_name                            = local.operations_resource_group_name
  location                                       = local.operations_location
  service_plan_id                                = azurerm_service_plan.function.id
  storage_account_name                           = azurerm_storage_account.this.name
  storage_account_access_key                     = azurerm_storage_account.this.primary_access_key
  functions_extension_version                    = "~4"
  https_only                                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  tags                                           = var.tags

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.wms.connection_string

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
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "AzureWebJobsFeatureFlags" = "EnableWorkerIndexing"
    # The AzureRM Function resource derives FUNCTIONS_EXTENSION_VERSION,
    # AzureWebJobsStorage, and APPLICATIONINSIGHTS_CONNECTION_STRING from
    # its dedicated fields above and storage_account_access_key. Keeping them
    # here as well caused perpetual diffs because Azure exposes these settings
    # through its computed Function configuration rather than custom settings.
    # Linux Consumption requires the package URL. The immutable blob is private
    # and fetched with the system-assigned identity, not a long-lived SAS.
    "WEBSITE_RUN_FROM_PACKAGE"                     = azurerm_storage_blob.function_package.url
    "WEBSITE_RUN_FROM_PACKAGE_BLOB_MI_RESOURCE_ID" = "SystemAssigned"
    "DEPLOYMENT_PACKAGE_SHA256"                    = filesha256(var.function_package_path)
    "SCM_DO_BUILD_DURING_DEPLOYMENT"               = "false"
    "ENABLE_ORYX_BUILD"                            = "false"
    "WMS_QUEUE_NAME"                               = azurerm_storage_queue.fulfillment.name
    "WMS_POISON_QUEUE_NAME"                        = azurerm_storage_queue.fulfillment_poison.name
    "EVIDENCE_CONTAINER"                           = azurerm_storage_container.evidence.name
    "AZURE_BLOB_ACCOUNT_URL"                       = "https://${azurerm_storage_account.this.name}.blob.core.windows.net"
    "AZURE_QUEUE_ACCOUNT_URL"                      = "https://${azurerm_storage_account.this.name}.queue.core.windows.net"
    "EVENT_SCHEMA_VERSION"                         = "1.0"
    "ALLOWED_EVENT_SOURCES"                        = join(",", var.allowed_event_sources)
    "WEBSITE_ENABLE_SYNC_UPDATE_SITE"              = "true"
  }

}

resource "azurerm_role_assignment" "function_package_reader" {
  scope                = azurerm_storage_container.function_packages.resource_manager_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_blob" {
  scope                = azurerm_storage_container.evidence.resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_queue" {
  scope                = azurerm_storage_queue.fulfillment.resource_manager_id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_poison_queue_reader" {
  scope                = azurerm_storage_queue.fulfillment_poison.resource_manager_id
  role_definition_name = "Storage Queue Data Reader"
  principal_id         = azurerm_linux_function_app.wms.identity[0].principal_id
}

# Alertas que existen en el entorno Azure vigente. Se declaran aquí para que
# una recreación desde cero no pierda la señalización del WMS.
resource "azurerm_monitor_action_group" "operations" {
  name                = "${var.name_prefix}-ops-ag"
  resource_group_name = local.operations_resource_group_name
  short_name          = "tngops"
  enabled             = true
  location            = "global"
  tags                = var.tags

  dynamic "email_receiver" {
    # Iterate over public numeric indexes; the receiver addresses themselves
    # remain sensitive in plan output and diagnostics.
    for_each = range(nonsensitive(length(var.alert_email_receivers)))
    iterator = receiver

    content {
      name                    = "operations-email-${receiver.key + 1}"
      email_address           = var.alert_email_receivers[receiver.key]
      use_common_alert_schema = true
    }
  }
}

resource "azurerm_monitor_metric_alert" "function_http_5xx" {
  name                = "${var.name_prefix}-wms-fn-5xx"
  resource_group_name = local.operations_resource_group_name
  scopes              = [azurerm_linux_function_app.wms.id]
  description         = "La Function WMS devolvió errores HTTP 5xx."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  tags                = var.tags

  criteria {
    metric_namespace       = "Microsoft.Web/sites"
    metric_name            = "Http5xx"
    aggregation            = "Total"
    operator               = "GreaterThan"
    threshold              = 0
    skip_metric_validation = false
  }

  action {
    action_group_id = azurerm_monitor_action_group.operations.id
  }
}

resource "azurerm_monitor_metric_alert" "function_latency" {
  name                = "${var.name_prefix}-wms-fn-latency"
  resource_group_name = local.operations_resource_group_name
  scopes              = [azurerm_linux_function_app.wms.id]
  description         = "La latencia media de la Function WMS superó el umbral esperado."
  severity            = 3
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = var.tags

  criteria {
    metric_namespace       = "Microsoft.Web/sites"
    metric_name            = "HttpResponseTime"
    aggregation            = "Average"
    operator               = "GreaterThan"
    threshold              = 5
    skip_metric_validation = false
  }

  action {
    action_group_id = azurerm_monitor_action_group.operations.id
  }
}
