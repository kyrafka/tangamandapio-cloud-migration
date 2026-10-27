# Validación cloud AWS–Azure — 27/10/2026

**Corte:** 2026-10-27 20:00 UTC. Región AWS `us-east-1`. No se incluyen credenciales ni valores secretos.

## AWS

- CloudFormation `tangamandapio-live-20261026`: `UPDATE_COMPLETE`; detección de drift: `IN_SYNC`, cero recursos desviados.
- Release activo: `20261027-rds-connection-pool-v26-python312`, SHA-256 `61b36692a2754e5e47515a1af2a5742a15ff8c6c278225d1294e6288e841e53b`. El artefacto local y el objeto privado de S3 corresponden a 304,812 bytes; el objeto usa cifrado de servidor AES256.
- Auto Scaling Group: mínimo/deseado 2, máximo 5. Hay dos instancias en servicio con Launch Template versión 3; confirmé por SSM que ambas sirven `20261027-rds-connection-pool-v26-python312`, responden `/health=200` local y sus destinos del ALB están `healthy`. La rotación llegó temporalmente a tres/cuatro instancias para conservar capacidad. Eso no demuestra escalado automático 2→3 por demanda.
- Dominio `https://tangamandapio.kendellnm.me`: certificado ACM `ISSUED`; `/`, `/health` y `/ready` respondieron HTTP 200 por HTTPS.
- Smoke de solo lectura contra `/ready`, preservando SNI/certificado y conectando directamente al origen ALB: 40 solicitudes, 8 concurrentes, 40 HTTP 200, p95 441.8 ms. La métrica RDS `DatabaseConnections` tuvo máximos de 8 en las muestras de 1 minuto consultadas para los 15 minutos previos. Esto valida un smoke ligero; no es carga transaccional ni capacidad para 3,000 usuarios.
- El proxy Cloudflare devolvió HTTP 403 al cliente Python automatizado; solicitudes con el cliente PowerShell y la ruta directa al ALB funcionaron. No se cambió la configuración de Cloudflare.
- RDS PostgreSQL: `available`, Multi-AZ, cifrada, sin acceso público, retención automática de siete días.
- AWS WAF: habilitado y asociado al ALB.
- Pruebas locales focalizadas de conexiones RDS y autenticación de secreto: **9 aprobadas**. `validate-template` pasó.

## Azure

- Function App `tangama-wms-261008`: `Running`, `httpsOnly=true`; `https://tangama-wms-261008.azurewebsites.net/api/health` respondió 200.
- La Function conserva acceso de red público y no tiene integración privada con la VNet. La consulta de gateways de `rg-tangama-private-network` no devolvió gateways.

## Pendientes y límites

- No hay túnel privado entre AWS y Azure. AWS Academy denegó la creación del Customer Gateway; no se desplegó un sustituto overlay.
- No están desplegados SQS + Lambda + DLQ, identidad Entra ID/SSO/MFA ni respaldo cruzado AWS–Azure con restauración demostrada.
- El escalado por carga 2→3 y una carga sostenida de 3,000 usuarios no se han demostrado. El pool reduce conexiones repetidas y limita conexiones por proceso; falta una prueba de carga medida antes de afirmar capacidad.
- El ledger WMS conserva inventario sintético. El estado de la Function valida disponibilidad, no una conexión a un WMS empresarial externo.
