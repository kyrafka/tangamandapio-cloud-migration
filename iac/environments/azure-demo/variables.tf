variable "location" {
  type        = string
  description = "Región aprobada para el laboratorio Azure."
  default     = "eastus"
}

variable "resource_group_name" {
  type        = string
  description = "Grupo de recursos temporal del despliegue verificable."
  default     = "rg-tangamandapio-ops-demo"
}

variable "create_resource_group" {
  type        = bool
  description = "Crea el Resource Group para una región permitida cuando no se reutiliza uno existente."
  default     = false
}

variable "storage_account_name" {
  type        = string
  description = "Nombre globalmente único, 3-24 caracteres alfanuméricos en minúscula."
}

variable "key_vault_name" {
  type        = string
  description = "Nombre globalmente único del Key Vault, 3-24 caracteres alfanuméricos o guiones."
}

variable "name_prefix" {
  type        = string
  description = "Prefijo corto para recursos Azure."
  default     = "tangama"
}

variable "function_package_path" {
  type        = string
  description = "Ruta al ZIP de Function generado localmente antes del apply."
}
