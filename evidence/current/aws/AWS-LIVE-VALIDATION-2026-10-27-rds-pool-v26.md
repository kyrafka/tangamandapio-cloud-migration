# Validación cloud AWS–Azure — 27/10/2026

## Revalidación posterior — 27/10/2026, 20:19–20:23 UTC

- Se sustituyó el perfil AWS local `default` por el token temporal entregado
  por el usuario; `aws sts get-caller-identity` respondió correctamente en la
  cuenta Academy `654654388734`. El token no se guardó en el repositorio ni en
  esta evidencia.
- CloudFormation `tangamandapio-live-20261026` permanece `UPDATE_COMPLETE`
  (última actualización informada: 19:39 UTC). El ALB está activo; sus dos
  destinos están `healthy`. ASG: mínimo 2, deseado 2 y máximo 5. RDS está
  `available`, cifrada, Multi-AZ y con siete días de retención. La plantilla
  mantiene WAF asociado al ALB. El dominio
  `https://tangamandapio.kendellnm.me/health` respondió HTTP 200.
- El portal de AWS Academy mostró el laboratorio listo y consumo de `$4.70` de
  `$50` en la observación. No se aplicaron cambios de infraestructura durante
  esta comprobación.
- La suscripción `Azure for Students` está `Enabled`. La Function
  `tangama-wms-261008` permanece `Running`/HTTPS-only en plan Y1; su endpoint
  `/api/health` respondió HTTP 200. No tiene integración con VNet.
- Azure sí contiene `vnet-tangama-private` en `rg-tangama-private-network`, con
  espacio `10.20.0.0/16`, `GatewaySubnet` y subredes para workloads, endpoints
  privados y Functions Flex. La consulta de suscripción no encontró recursos
  `virtualNetworkGateways`, conexiones VPN, private endpoints ni integración
  VNet de la Function. Por tanto, la VNet existe, pero todavía no es una ruta
  privada AWS–Azure.
- AWS no devuelve colas SQS ni funciones Lambda con el prefijo del proyecto.
  `iam:GetRole` y `iam:ListAttachedRolePolicies` sobre
  `RoleForLambdaModLabRole` devuelven `AccessDenied` explícito; el corte
  anterior registró `implicitDeny` para crear/pasar un rol de ejecución. No se
  usó `LabRole`.
- La política de escalado del ASG apunta a CPU promedio del grupo de 60%. El
  estado sigue 2/2 y esta revalidación no ejecutó carga: el smoke de `/health`
  previo no demuestra escalado 2→3 ni capacidad para 3,000 usuarios.

**Corte base:** 2026-10-27 20:03 UTC. **Revalidación adicional:** 20:08–20:14 UTC. Región AWS `us-east-1`. No se incluyen credenciales ni valores secretos.

## Revalidación adicional — 27/10/2026, 20:08–20:14 UTC

- El token temporal del laboratorio autenticó por STS en la cuenta AWS Academy
  correcta. CloudFormation terminó una detección nueva: `IN_SYNC`, cero
  recursos desviados, 20:11:45 UTC. No se aplicó ni modificó infraestructura.
- Stack `tangamandapio-live-20261026`: `UPDATE_COMPLETE`; ASG mínimo/deseado 2,
  máximo 5; dos EC2 `InService` y dos destinos ALB `healthy`. RDS disponible,
  Multi-AZ, cifrada, privada y con siete días de retención. AWS WAF asociado al
  ALB con reglas administradas Common, Bad Inputs, SQL Injection y Rate Limit.
- El dominio público `https://tangamandapio.kendellnm.me/health` devolvió 200 a
  través de Cloudflare. Un canario XSS inocuo contra la portada devolvió 403
  desde el origen ALB con TLS/SNI del dominio.
- Azure Function `https://tangama-wms-261008.azurewebsites.net/api/health`
  devolvió 200. Sigue en plan Y1/Dynamic Consumption, red pública habilitada,
  sin integración VNet. El grupo de recursos esperado para la red privada no
  existe en la suscripción activa.
- PT-PERF-01, lectura de `/health` directa al ALB con TLS válido: 500/500 HTTP
  200, concurrencia 20, duración 11.163 s, p95 547.78 ms, máximo 859.61 ms,
  cero errores. Es un smoke de salud de solo lectura, no tráfico transaccional.
  El ASG quedó en 2; no se cruzó el objetivo de CPU del 60%, por lo que **no
  demuestra el escalado automático 2→3 ni capacidad para 3,000 usuarios**.
- En muestras CloudWatch de 20:05–20:12 UTC, RDS llegó a un máximo de cuatro
  conexiones y 7.66% de CPU; la CPU máxima reportada del ASG fue 4.05%, por
  debajo del objetivo de 60%. Esto no reproduce la saturación transaccional
  histórica de RDS ni permite atribuirle una resolución completa.
- La simulación IAM volvió a indicar `implicitDeny` para `iam:CreateRole` y
  `iam:PassRole`, aunque `lambda:CreateFunction` y creación/configuración de
  SQS figuran permitidas. No existen colas ni funciones del proyecto. No se usó
  `LabRole` para evitar una ejecución con permisos amplios.
- Suite del release: 24/24 aprobadas; además, las cinco pruebas de
  autenticación del secreto RDS pasaron. Las cuatro pruebas del pool forman
  parte de las 24. Se ajustó solo el fixture ERP para desactivar la rotación
  inicial en esos escenarios de permisos/correo; producción conserva el cambio
  obligatorio de clave inicial.
- La puerta integral `tests/run_local_quality.ps1 -ValidateTerraform` no pudo
  iniciar porque este worktree no contiene `app/.venv`; no es un fallo de una
  prueba. No se modificó producción ni se desplegaron cambios por esta
  revalidación.

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

## Prerrequisitos para los siguientes cambios

- Simulación IAM de solo lectura para el rol del laboratorio: `iam:CreateRole` y `iam:PassRole` dan `implicitDeny`; las acciones de crear/actualizar Lambda y crear/configurar SQS figuran como permitidas. No hay funciones ni colas Tangamandapio en la cuenta. No se usó `LabRole` porque no sería un permiso de ejecución acotado; falta que el laboratorio permita crear y pasar un rol mínimo.
- La Function está en el plan Y1/Dynamic Consumption, con red pública habilitada, sin integración VNet y sin gateway de red. Microsoft documenta que el plan Consumption no admite Private Endpoint ni integración de salida a VNet; para entrada privada se requiere Flex Consumption, Elastic Premium o Dedicated, además de Private Endpoint y conectividad privada desde AWS ([documentación oficial de red de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)).

## Pendientes y límites

- No hay túnel privado entre AWS y Azure. AWS Academy denegó la creación del Customer Gateway; no se desplegó un sustituto overlay.
- No están desplegados SQS + Lambda + DLQ, identidad Entra ID/SSO/MFA ni respaldo cruzado AWS–Azure con restauración demostrada.
- El escalado por carga 2→3 y una carga sostenida de 3,000 usuarios no se han demostrado. El pool reduce conexiones repetidas y limita conexiones por proceso; falta una prueba de carga medida antes de afirmar capacidad.
- El ledger WMS conserva inventario sintético. El estado de la Function valida disponibilidad, no una conexión a un WMS empresarial externo.
