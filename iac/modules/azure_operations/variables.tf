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
