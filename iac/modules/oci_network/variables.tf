variable "compartment_id" {
  description = "OCID del compartment OCI."
  type        = string
}

variable "name_prefix" {
  description = "Prefijo legible para recursos."
  type        = string
}

variable "vcn_cidr" {
  description = "CIDR de la VCN."
  type        = string
}

variable "freeform_tags" {
  description = "Etiquetas comunes."
  type        = map(string)
  default     = {}
}
