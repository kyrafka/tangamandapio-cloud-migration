variable "resource_group_name" {
  description = "Dedicated resource group for cross-cloud networking."
  type        = string
  default     = "rg-tangama-private-network"
}

variable "location" {
  description = "Azure region for the VPN gateway."
  type        = string
  default     = "westus"
}

variable "vnet_name" {
  description = "Azure virtual network name."
  type        = string
  default     = "vnet-tangama-private"
}

variable "azure_vnet_cidr" {
  description = "Azure address space; it must not overlap AWS or other connected networks."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = var.azure_vnet_cidr == "10.20.0.0/16"
    error_message = "Este entorno usa 10.20.0.0/16; cambie también las subredes y los peers BGP antes de usar otro prefijo."
  }
}

variable "gateway_subnet_cidr" {
  description = "Dedicated GatewaySubnet. Azure recommends at least /27 for VPN gateways."
  type        = string
  default     = "10.20.255.0/27"
}

variable "azure_bgp_asn" {
  description = "Azure VPN gateway ASN advertised to AWS."
  type        = number
  default     = 65515
}

variable "aws_vpc_cidr" {
  description = "AWS VPC prefix used for the route-based tunnel."
  type        = string
  default     = "10.10.0.0/16"

  validation {
    condition     = var.aws_vpc_cidr == "10.10.0.0/16"
    error_message = "La plantilla emparejada presupone la VPC actual 10.10.0.0/16; no cambie este valor sin actualizar las rutas AWS."
  }
}

variable "gateway_sku" {
  description = "Billable zone-aware Azure VPN gateway SKU. Review regional availability and cost before apply."
  type        = string
  default     = "VpnGw1AZ"

  validation {
    condition     = var.gateway_sku == "VpnGw1AZ"
    error_message = "Este entorno académico usa VpnGw1AZ; las SKU no zonales ya no admiten nuevas creaciones en la suscripción/región probada."
  }
}

variable "tags" {
  description = "Non-sensitive Azure resource tags."
  type        = map(string)
  default = {
    Project     = "Tangamandapio-Cloud"
    Environment = "academic-demo"
    ManagedBy   = "Terraform"
    CostControl = "destroy-after-test"
  }
}

variable "deployment_approved" {
  description = "Must be true only after reviewing the recurring VPN gateway cost and lab balance."
  type        = bool
  default     = false
}
