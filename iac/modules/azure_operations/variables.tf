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

variable "function_package_path" {
  type        = string
  description = "Ruta absoluta al ZIP reproducible de Azure Function creado con iac/scripts/package_azure_function.ps1."

  validation {
    condition     = fileexists(var.function_package_path)
    error_message = "function_package_path debe apuntar a un ZIP existente. Genérelo con iac/scripts/package_azure_function.ps1 antes de aplicar Terraform."
  }
}
