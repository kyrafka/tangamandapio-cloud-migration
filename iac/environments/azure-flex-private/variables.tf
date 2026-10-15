variable "subscription_id" {
  description = "Azure subscription ID from the authenticated Azure CLI context; do not commit a tfvars file containing account data."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id debe ser un GUID de Azure válido."
  }
}

variable "location" {
  description = "Must match the VNet and existing WMS resources."
  type        = string
  default     = "westus"
}

variable "resource_group_name" {
  description = "Existing Azure operations resource group; this environment does not create or replace it."
  type        = string
  default     = "rg-tangamandapio-rebuild-wus"
}

variable "network_resource_group_name" {
  description = "Resource group created by iac/environments/aws-azure-vpn."
  type        = string
  default     = "rg-tangama-private-network"
}

variable "virtual_network_name" {
  type    = string
  default = "vnet-tangama-private"
}

variable "flex_integration_subnet_name" {
  type    = string
  default = "snet-flex-functions"
}

variable "private_endpoint_subnet_name" {
  type    = string
  default = "snet-private-endpoints"
}

variable "function_app_name" {
  description = "Blue-green Flex app name; must be globally unique and <=32 characters. Keep the current Y1 app until cutover is verified."
  type        = string
  default     = "tangama-wms-flex-261013"

  validation {
    condition     = length(var.function_app_name) <= 32 && can(regex("^[a-zA-Z0-9-]+$", var.function_app_name))
    error_message = "function_app_name debe ser globalmente único, alfanumérico con guiones y de máximo 32 caracteres."
  }
}

variable "storage_account_name" {
  description = "Existing private-project data account. The app uses managed identity; no storage key is placed in settings."
  type        = string
  default     = "sttangama261008r"
}

variable "deployment_container_name" {
  description = "Dedicated package container for this blue-green Function App."
  type        = string
  default     = "function-flex-deployments"
}

variable "application_insights_name" {
  type    = string
  default = "tangama-wms-ai"
}

variable "events_container_name" {
  type    = string
  default = "fulfillment-events"
}

variable "fulfillment_queue_name" {
  type    = string
  default = "fulfillment-events"
}

variable "poison_queue_name" {
  type    = string
  default = "fulfillment-events-poison"
}

variable "maximum_instance_count" {
  description = "Flex Consumption upper bound for the academic workload; adjust only with a reviewed cost/load profile."
  type        = number
  default     = 10

  validation {
    condition     = var.maximum_instance_count >= 1 && var.maximum_instance_count <= 20
    error_message = "El límite académico debe estar entre 1 y 20 instancias para controlar el costo."
  }
}

variable "instance_memory_in_mb" {
  type    = number
  default = 2048

  validation {
    condition     = contains([512, 2048, 4096], var.instance_memory_in_mb)
    error_message = "Flex Consumption admite tamaños de instancia 512, 2048 o 4096 MB."
  }
}

variable "deployment_approved" {
  description = "Must be true only after reviewing Azure costs, the student budget, and the blue-green plan."
  type        = bool
  default     = false
}

variable "bootstrap_public_access_enabled" {
  description = "Temporary first-deployment exception so Azure CLI can publish the package before private routing is available. Final state must be false."
  type        = bool
  default     = false
}

variable "bootstrap_public_access_acknowledged" {
  description = "Explicit acknowledgement required when the temporary public bootstrap endpoint is enabled."
  type        = bool
  default     = false
}

variable "allowed_event_sources" {
  type    = set(string)
  default = ["aws-order-core", "aws-wms-demo-console", "tangamandapio-erp"]

  validation {
    condition = length(var.allowed_event_sources) > 0 && alltrue([
      for source in var.allowed_event_sources : can(regex("^[a-z0-9][a-z0-9-]{1,63}$", source))
    ])
    error_message = "Cada source debe ser un identificador de 2-64 caracteres en minúscula, números o guiones."
  }
}

variable "tags" {
  type = map(string)
  default = {
    Project            = "Tangamandapio-Cloud"
    Environment        = "academic-demo"
    ManagedBy          = "Terraform"
    DataClassification = "Synthetic"
    CostControl        = "blue-green-review-required"
  }
}
