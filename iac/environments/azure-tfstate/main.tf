terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}

  # Use Microsoft Entra ID for container operations; shared keys are disabled.
  storage_use_azuread = true
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "state" {
  name     = "rg-tangamandapio-tfstate-wus"
  location = "westus"

  tags = {
    Project            = "Tangamandapio-Cloud"
    Environment        = "academic-demo"
    ManagedBy          = "Terraform"
    Purpose            = "Terraform state backend bootstrap"
    DataClassification = "Sensitive"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_account" "state" {
  name                             = "sttangamatfstate261014"
  resource_group_name              = azurerm_resource_group.state.name
  location                         = azurerm_resource_group.state.location
  account_tier                     = "Standard"
  account_replication_type         = "LRS"
  account_kind                     = "StorageV2"
  min_tls_version                  = "TLS1_2"
  https_traffic_only_enabled       = true
  allow_nested_items_to_be_public  = false
  shared_access_key_enabled        = false
  public_network_access_enabled    = true
  default_to_oauth_authentication  = true
  local_user_enabled               = false
  cross_tenant_replication_enabled = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  tags = {
    Project            = "Tangamandapio-Cloud"
    Environment        = "academic-demo"
    ManagedBy          = "Terraform"
    Purpose            = "Terraform state backend"
    DataClassification = "Sensitive"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_role_assignment" "backend_writer" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_storage_container" "state" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.state.name
  container_access_type = "private"

  depends_on = [azurerm_role_assignment.backend_writer]

  lifecycle {
    prevent_destroy = true
  }
}
