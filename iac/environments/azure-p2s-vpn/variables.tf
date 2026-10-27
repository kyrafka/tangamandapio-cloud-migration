variable "subscription_id" {
  description = "Azure subscription ID from the active CLI context; never commit credentials."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "subscription_id debe ser un GUID de Azure válido."
  }
}

variable "resource_group_name" {
  description = "Existing resource group that owns the Azure private VNet."
  type        = string
  default     = "rg-tangama-private-network"
}

variable "virtual_network_name" {
  type    = string
  default = "vnet-tangama-private"
}

variable "gateway_subnet_name" {
  type    = string
  default = "GatewaySubnet"
}

variable "location" {
  description = "Must match the existing VNet location."
  type        = string
  default     = "westus"
}

variable "deployment_approved" {
  description = "Enables creation of the billable Azure VPN Gateway after cost review."
  type        = bool
  default     = false
}

variable "gateway_sku" {
  description = "Azure VPN Gateway SKU; AZ SKU is required by this student subscription."
  type        = string
  default     = "VpnGw1AZ"
}

variable "client_address_pool" {
  description = "Non-overlapping IPv4 pool assigned to AWS OpenVPN clients."
  type        = string
  default     = "172.31.250.0/24"
}

variable "root_certificate_name" {
  type    = string
  default = "tangamandapio-aws-p2s-root"
}

variable "root_certificate_public_data" {
  description = "Base64-encoded public root certificate data; no private key."
  type        = string

  validation {
    condition     = length(trimspace(var.root_certificate_public_data)) >= 100
    error_message = "Debe proporcionar el certificado raíz público en Base64."
  }
}

variable "tags" {
  type = map(string)
  default = {
    Project            = "Tangamandapio-Cloud"
    Environment        = "academic-demo"
    ManagedBy          = "Terraform"
    DataClassification = "Synthetic"
    CostControl        = "destroy-after-test"
  }
}
