output "vpc_id" {
  description = "ID de la VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "CIDR efectivo de la VPC."
  value       = aws_vpc.this.cidr_block
}

output "internet_gateway_id" {
  description = "ID del Internet Gateway."
  value       = aws_internet_gateway.this.id
}

output "public_subnet_ids" {
  description = "IDs de subredes públicas ordenadas por zona lógica."
  value       = [aws_subnet.this["public_a"].id, aws_subnet.this["public_b"].id]
}

output "app_subnet_ids" {
  description = "IDs de subredes privadas de aplicación."
  value       = [aws_subnet.this["app_a"].id, aws_subnet.this["app_b"].id]
}

output "db_subnet_ids" {
  description = "IDs de subredes privadas de datos."
  value       = [aws_subnet.this["db_a"].id, aws_subnet.this["db_b"].id]
}

output "public_route_table_id" {
  description = "ID de la tabla pública."
  value       = aws_route_table.public.id
}

output "app_route_table_id" {
  description = "ID de la tabla de aplicación."
  value       = aws_route_table.app.id
}

