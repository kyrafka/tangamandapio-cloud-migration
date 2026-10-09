# Infraestructura como código — corte 08/10/2026

La referencia del inventario actual es [MAPA_ESTADO_ACTUAL_2026-10-08.md](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md). Separa recursos comprobados en las nubes del estado de Terraform; no ejecutar un `apply` basándose solo en que `validate` pase.

| Dominio | Fuente de verdad actual | Estado de despliegue |
|---|---|---|
| AWS productivo del laboratorio | CloudFormation: `cloudformation/aws-lab.yaml` y stack `tangamandapio-live-20261005` | Plantilla local idéntica a la viva, `UPDATE_COMPLETE`, drift `IN_SYNC`; cambio preparado únicamente mediante change set revisable. |
| Red AWS de ejemplo | Terraform: `environments/demo` → `modules/aws_network` | Formato y validación correctos; no tiene state y no administra el stack vivo. Un `apply` crearía una VPC adicional. |
| WMS de demostración Azure | Terraform: `environments/azure-demo` → `modules/azure_operations` | Código valida, pero el state local apunta a un Resource Group anterior y el plan requiere reconciliación/importación. No aplicar ni destruir sobre el grupo vivo. |

## Criterios de operación

- No administrar un mismo recurso con CloudFormation y Terraform.
- En AWS, revisar el change set y usar `APPLY_CHANGE_SET=true` más confirmación explícita para ejecutarlo. Por defecto, `deploy.sh` solo prepara el change set y conserva todos los parámetros actuales, incluso los `NoEcho`.
- En Azure, `terraform validate` es una comprobación de sintaxis, no prueba de que el state represente los recursos actuales. Respaldar y reconciliar el state antes de plan/apply.
- No subir archivos `terraform.tfstate`, `terraform.tfvars`, claves ni salidas con secretos.
- El inventario Azure actual es una demostración de despacho/inventario ficticio, no integración con un WMS/ERP real.
