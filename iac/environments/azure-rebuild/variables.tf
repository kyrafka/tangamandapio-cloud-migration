variable "location" {
  description = "Región del entorno WMS de demostración."
  type        = string
  default     = "westus"
}

variable "resource_group_name" {
  description = "Grupo de recursos que se recrea desde cero."
  type        = string
  default     = "rg-tangamandapio-rebuild-wus"
}

variable "storage_account_name" {
  description = "Nombre globalmente único; cambia el sufijo si Azure lo reporta ocupado."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Storage Account requiere de 3 a 24 caracteres en minúscula o números."
  }
}

variable "key_vault_name" {
  description = "Nombre globalmente único nuevo para evitar el soft-delete del Key Vault anterior."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9-]{1,22}[A-Za-z0-9]$", var.key_vault_name)) && !strcontains(var.key_vault_name, "--")
    error_message = "Key Vault requiere de 3 a 24 caracteres, iniciar con letra y no usar guiones consecutivos."
  }
}

variable "function_app_name" {
  description = "Nombre globalmente único de la Function App nueva."
  type        = string
}

variable "alert_email_receivers" {
  description = "Destinatarios explícitos de alertas operativas; manténgalos fuera del repositorio."
  type        = list(string)
  default     = []
  sensitive   = true

  validation {
    condition = length(distinct(var.alert_email_receivers)) == length(var.alert_email_receivers) && alltrue([
      for address in var.alert_email_receivers : address == trimspace(address) && can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", address))
    ])
    error_message = "Los destinatarios deben ser correos únicos y válidos, sin espacios; no guarde direcciones personales en Git."
  }
}

variable "name_prefix" {
  description = "Prefijo para Log Analytics, Application Insights, plan y alertas."
  type        = string
  default     = "tangama"
}

variable "function_package_path" {
  description = "Ruta explícita al ZIP inmutable de la Function, generado desde app/azure_function."
  type        = string

  validation {
    condition     = fileexists(var.function_package_path) && can(regex("azure_function_package-[a-f0-9]{64}\\.zip$", var.function_package_path))
    error_message = "Indique un ZIP inmutable azure_function_package-<SHA256>.zip, generado con iac/scripts/package_azure_function.ps1."
  }
}
