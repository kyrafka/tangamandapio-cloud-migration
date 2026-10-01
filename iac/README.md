# Infraestructura como código

CloudFormation conserva la evidencia histórica del piloto AWS. Terraform define de forma modular la red AWS y el vertical Azure de operaciones para el flujo AWS-Azure.

| Componente | Herramienta | Estado |
|---|---|---|
| VPC y piloto AWS | CloudFormation | Desplegado, probado y eliminado el 24/09/2026 |
| Red AWS modular | Terraform | Validación local prevista |
| Azure WMS | Terraform | Código preparado, deshabilitado por defecto |

El módulo Azure crea Resource Group, Storage Account privada, Blob Container, Queue y Function App Consumption. La Function no contiene todavía la lógica de recepción; esa fase exige una prueba real, evidencia de consola y destrucción posterior.

El directorio `modules/oci_network` se conserva solo como antecedente archivado y no forma parte del entorno activo ni del alcance AWS-Azure.
