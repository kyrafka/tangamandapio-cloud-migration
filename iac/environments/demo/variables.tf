variable "project_name" {
  description = "Nombre corto utilizado para etiquetar los recursos."
  type        = string
  default     = "tangamandapio-cloud"
}

variable "environment" {
  description = "Nombre del entorno."
  type        = string
  default     = "demo"
}

variable "owner" {
  description = "Equipo responsable. No incluir correos ni datos sensibles."
  type        = string
  default     = "grupo-pendiente"
}

variable "aws_region" {
  description = "Región AWS habilitada en la cuenta académica."
  type        = string
  default     = "us-east-1"
}

variable "aws_vpc_cidr" {
  description = "CIDR principal de AWS."
  type        = string
  default     = "10.10.0.0/16"
}

variable "enable_azure" {
  description = "Crea el componente Azure solo con presupuesto y región confirmados."
  type        = bool
  default     = false
}

variable "azure_location" {
  description = "Región Azure que se validará en la suscripción antes de aplicar."
  type        = string
  default     = "eastus"
}

variable "azure_resource_group_name" {
  description = "Grupo de recursos de Azure."
  type        = string
  default     = "rg-tangamandapio-demo"
}

variable "azure_storage_account_name" {
  description = "Nombre globalmente único y en minúsculas para Storage Account. Requerido solo con enable_azure=true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_azure || can(regex("^[a-z0-9]{3,24}$", var.azure_storage_account_name))
    error_message = "Con Azure habilitado, el nombre debe tener 3-24 caracteres alfanuméricos en minúsculas."
  }
}
