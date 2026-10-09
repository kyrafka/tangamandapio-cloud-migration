# Terraform `demo` — red AWS aislada

Este entorno gestiona únicamente una VPC nueva con seis subredes, tablas de rutas e Internet Gateway mediante `modules/aws_network`. No incluye el ALB, Auto Scaling, aplicación, RDS, S3, WAF ni observabilidad del stack actual; esos recursos pertenecen a CloudFormation.

La validación y el formato pasan, pero no existe un Terraform state aquí. No ejecutar `terraform apply` sobre la cuenta del laboratorio como método para actualizar el stack: crearía una segunda VPC con CIDR `10.10.0.0/16` y recursos/costos duplicados. CloudFormation sigue siendo la fuente de verdad AWS.

Comprobaciones locales seguras:

```powershell
terraform fmt -check -recursive
terraform validate
```

Antes de cualquier despliegue independiente se necesita un backend/state nuevo y aislado, nombres/tags propios, revisar el plan y presupuesto y acordar cómo limpiar únicamente ese entorno.
