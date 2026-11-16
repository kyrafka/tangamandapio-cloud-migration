variable "aws_region" {
  description = "Región AWS del entorno actual."
  type        = string
  default     = "us-east-2"
}

variable "stack_name" {
  type    = string
  default = "tangamandapio-aws-azure-tailscale-ha"
}

variable "deployment_approved" {
  description = "Interruptor deliberado porque dos EC2 y sus volúmenes generan consumo."
  type        = bool
  default     = false
}

variable "enable_private_wms_route" {
  description = "Debe seguir false hasta que las dos sondas Tailscale estén sanas."
  type        = bool
  default     = false
}

variable "vpc_id" {
  type    = string
  default = "vpc-0a4fc4c2a6b503338"
}

variable "app_subnet_a" {
  type    = string
  default = "subnet-08f8437d6d225e630"
}

variable "app_subnet_b" {
  type    = string
  default = "subnet-0e5572cb61b5d4697"
}

variable "app_route_table_id" {
  type    = string
  default = "rtb-0cb5b4e9fd67db03e"
}

variable "asset_bucket_name" {
  type    = string
  default = "tangamandapio-481056890449-us-east-2"
}

variable "router_artifact_key" {
  description = "Clave S3 devuelta por deploy_tailscale_ha.sh después de cargar el paquete versionado por SHA-256."
  type        = string
}

variable "router_artifact_sha256" {
  description = "SHA-256 del paquete subido al bucket privado de activos."
  type        = string

  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.router_artifact_sha256))
    error_message = "Indica el SHA-256 completo de 64 caracteres del paquete de routers."
  }
}
