output "router_stack_id" {
  value       = try(aws_cloudformation_stack.router_pair[0].id, null)
  description = "ID de la pila CloudFormation creada dentro del estado Terraform."
}

output "router_stack_outputs" {
  value       = try(aws_cloudformation_stack.router_pair[0].outputs, {})
  description = "IPs privadas, tabla app y EC2 del par de routers."
}
