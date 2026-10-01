# CUR-AZ-01 — Terraform apply del vertical WMS

| Campo | Registro |
|---|---|
| Fecha | 30/09/2026 |
| Nube y región | Azure for Students, West US |
| IaC | `iac/environments/azure-demo` y `iac/modules/azure_operations` |
| Validación local | `terraform fmt -recursive` y `terraform validate` aprobados |
| Resultado de apply | 12 recursos creados, 0 modificados, 0 destruidos |
| Componentes | Resource Group, Storage Account, Blob privado, Queue, Key Vault, plan Consumption, Function App, Log Analytics, Application Insights y tres roles RBAC |
| Protección | TLS 1.2, Blob no público, soft delete, Managed Identity y RBAC |
| Estado de limpieza | Pendiente de destruir el grupo temporal y verificar inventario cero |

## Límite de esta evidencia

Demuestra creación de infraestructura, no funcionamiento del evento WMS. La prueba de Blob/Queue depende de la corrección documentada en `CUR-AZ-02`.
