output "vcn_id" {
  description = "OCID de la VCN."
  value       = oci_core_vcn.this.id
}

output "internet_gateway_id" {
  description = "OCID del Internet Gateway."
  value       = oci_core_internet_gateway.this.id
}

output "nat_gateway_id" {
  description = "OCID del NAT Gateway."
  value       = oci_core_nat_gateway.this.id
}

output "public_subnet_id" {
  description = "OCID de la subred pública."
  value       = oci_core_subnet.public.id
}

output "private_subnet_id" {
  description = "OCID de la subred privada."
  value       = oci_core_subnet.private.id
}

output "vpn_nsg_id" {
  description = "OCID del NSG para el gateway de integración."
  value       = oci_core_network_security_group.vpn.id
}

output "app_nsg_id" {
  description = "OCID del NSG para el servicio privado."
  value       = oci_core_network_security_group.app.id
}
