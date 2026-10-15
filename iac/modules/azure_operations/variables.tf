variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "create_resource_group" {
  type        = bool
  default     = false
  description = "Crea el Resource Group solo cuando no exista. Por defecto se reutiliza uno existente."
}
variable "storage_account_name" { type = string }
variable "key_vault_name" { type = string }
variable "name_prefix" { type = string }
variable "tags" { type = map(string) }
variable "function_app_name" {
  type        = string
  default     = null
  description = "Nombre globalmente único opcional de la Function App; por defecto usa <name_prefix>-wms-fn."
}

variable "function_package_path" {
  type        = string
  description = "Ruta absoluta al ZIP inmutable de Azure Function, con SHA-256 en el nombre."

  validation {
    condition     = fileexists(var.function_package_path) && can(regex("azure_function_package-[a-f0-9]{64}\\.zip$", var.function_package_path))
    error_message = "function_package_path debe ser un ZIP existente azure_function_package-<SHA256>.zip. Genérelo con iac/scripts/package_azure_function.ps1 antes de aplicar Terraform."
  }
}

variable "alert_email_receivers" {
  description = "Destinatarios optativos para notificaciones de Action Group."
  type        = list(string)
  default     = []
  sensitive   = true

  validation {
    condition = length(distinct(var.alert_email_receivers)) == length(var.alert_email_receivers) && alltrue([
      for address in var.alert_email_receivers : address == trimspace(address) && can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", address))
    ])
    error_message = "Los destinatarios deben ser correos únicos y válidos, sin espacios."
  }
}

variable "allowed_event_sources" {
  description = "Productores autorizados para el contrato de eventos outbox AWS→Azure."
  type        = set(string)
  default     = ["aws-order-core", "aws-wms-demo-console", "tangamandapio-erp"]

  validation {
    condition = length(var.allowed_event_sources) > 0 && alltrue([
      for source in var.allowed_event_sources : can(regex("^[a-z0-9][a-z0-9-]{1,63}$", source))
    ])
    error_message = "Cada source debe ser un identificador de 2-64 caracteres en minúscula, números o guiones."
  }
}
