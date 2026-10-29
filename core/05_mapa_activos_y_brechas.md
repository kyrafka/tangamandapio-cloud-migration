# Mapa de activos y brechas — 29/10/2026

Este mapa resume qué artefactos y servicios forman la solución, separando la existencia de código de un despliegue vivo. La última consulta del portal público respondió 503; por ese motivo, el estado histórico no se presenta como disponibilidad actual.

## Activos del proyecto

| Dominio | Activos | Alcance y estado |
|---|---|---|
| Portal/ERP | React/Vite, Flask, PostgreSQL en AWS y SQLite para QA local; módulos B2B, ventas, compras, finanzas operativas, maestros, permisos y correo interno. | La aplicación publicada respondió 503. ERP/roles se probaron localmente; no equivale a QA de todos los roles en producción. El buzón no es SMTP corporativo. |
| Integración WMS | Azure Functions Y1/Flex, Blob y Queue; procesamiento idempotente de eventos. | Funciona con datos sintéticos. La Function Flex es privada; la respuesta 403 desde Internet es esperada y no valida la VPN. |
| Capa AWS | CloudFormation del portal; ALB, WAF, ASG/EC2, RDS, S3, Secrets Manager, CloudWatch/SNS según último inventario documentado. | Último corte del 27/10; AWS STS autenticó el 29/10, pero una política explícita denegó consultas de inventario. Estado vivo desconocido. |
| Capa Azure | Functions, Storage, Key Vault, App Insights, Log Analytics, alertas, VNet, Private Endpoint, DNS privado y P2S Gateway. | CLI Azure inventarió estos recursos. El gateway provisionado no basta para afirmar que la sesión está conectada. |
| Interconexión | P2S Azure OpenVPN mediante un router EC2 y rutas limitadas al WMS privado. | Recorrido de salud HTTPS 200 reportado el 29/10; no es AWS Site-to-Site/BGP y no se revalidó hoy desde AWS. |
| Recuperación | Script para copiar/restaurar un fixture sintético S3→Blob, hash coincidente. | No respalda ni restaura RDS. Falta una copia de PostgreSQL entre nubes y una restauración SQL aislada. |
| IaC | CloudFormation AWS y múltiples roots Terraform Azure; estado Terraform remoto. | Hay código para reconstruir infraestructura, pero no se ha probado una reconstrucción de punta a punta desde una cuenta vacía. |

## Brechas priorizadas

1. **P0 — recuperar el servicio y el inventario.** Investigar el 503 y conseguir permisos de solo lectura AWS; comparar CloudFormation con los recursos reales antes de modificar.
2. **P1 — backup real multinube.** Exportación PostgreSQL cifrada a Azure Blob, retención definida y restauración en un entorno aislado con integridad SQL y RPO/RTO medidos.
3. **P1 — interconexión durable.** La ruta P2S + router EC2 es un piloto con puntos únicos de falla. Si la rúbrica pide S2S administrada, habilitarla en una cuenta autorizada o acordar formalmente la alternativa.
4. **P1 — eventos AWS.** SQS + DLQ + Lambda con permisos mínimos solo si la política lo permite o el criterio la exige; Azure Functions cubre el lado Azure.
5. **P1 — capacidad.** Diagnosticar RDS, luego probar carga gradual y guardar evidencia de escalado automático 2→3. No afirmar capacidad de 3,000 concurrentes con pruebas menores.
6. **P2 — identidad y auditoría.** Entra ID/OIDC con MFA administrativo, mapeo de grupos a roles y trazabilidad consistente.
7. **P2 — experiencia del portal.** Corregir disponibilidad pública y después repetir una pasada autenticada por cada rol; A/V WebRTC sigue siendo una prueba separada de dos sesiones.

## Fuentes vigentes

- [Estado general](../README.md)
- [Mapa de CloudFormation y Terraform](../iac/README.md)
- [Runbook AWS](01_aws_ejecucion.md)
- [Runbook Azure](02_azure_ejecucion.md)
- [Matriz de criterios](04_matriz_rubrica.md)
