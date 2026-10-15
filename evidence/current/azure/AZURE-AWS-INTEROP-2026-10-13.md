# Reconciliación AWS–Azure y prueba E2E — 13/10/2026

## Revalidación de servicios — 15:15 America/Chicago

AWS STS autenticó; el stack del portal está `UPDATE_COMPLETE` y RDS
`available`, privado, Single-AZ, con un día de backup. En Azure, la Function
WMS sigue `Running`, HTTPS-only y con acceso público; `/api/health` devolvió
HTTP 200 (`status=ok`). Azure no lista una VNet y Tailscale continúa offline,
por lo que no hay conectividad privada probada ni evidencia de que esta lectura
procesara eventos. No se alteraron recursos.

## Confirmación funcional complementaria — aproximadamente 15:18

El smoke Azure ERP→outbox→Queue/Function volvió a pasar desde el release
ejecutado localmente: venta `demo_fulfillment_completed`, compensación
`demo_restock_completed`, saldo ficticio **24 → 23 → 24**. Los IDs y detalles
están en [la evidencia E2E](AZURE-ERP-E2E-2026-10-13.md). Esto complementa, no
reemplaza, el E2E de las 02:32 ejecutado desde el artefacto AWS desplegado en
EC2, que sí confirmó el flujo de aplicación AWS→Azure por HTTPS público. En
ninguno de los dos casos se probó conectividad privada; queda aplazada hasta el
cierre del VPN.

## Salud final — aproximadamente 15:28

AWS siguió `UPDATE_COMPLETE`; el target group mostró 2/2 destinos `healthy`,
`/health` devolvió HTTP 200 con base `ok` y `/ready` HTTP 200. Azure
`/api/health` devolvió HTTP 200 (`ok`). Fueron consultas de solo lectura; el
último detalle de RDS es el corte 15:15 de arriba. La aplicación está levantada
en ambas nubes, pero la red privada sigue sin existir.

## Alternativa Tailscale revisada — 14:53 America/Chicago

Se verificó de solo lectura que AWS STS autentica y existe la VPC `10.10.0.0/16`;
Azure CLI selecciona una suscripción, pero no lista ninguna VNet. El servicio
Tailscale local está instalado/activo, aunque el cliente reporta `NoState` y
offline. No hay nodos AWS/Azure enrutadores ni rutas de tailnet demostradas.
Se añadió un preflight y un diseño local para evaluar un piloto, sin crear
recursos. El resultado continúa siendo **sin túnel privado** y no cambia la
autoevaluación provisional.

## Intento de VPN temporal y limpieza — 14:46 America/Chicago

- AWS STS aceptó las credenciales temporales del perfil local `default`. El
  preflight de solo lectura validó la VPC `10.10.0.0/16`, la tabla de rutas de
  aplicación y que el stack de VPN no existía.
- Terraform creó los 10 recursos de prueba dentro del grupo dedicado
  `rg-tangama-private-network`. El gateway Azure `VpnGw1AZ` llegó a
  `Succeeded`, activo-activo y con BGP. Durante la creación, Azure retrasó la
  subred delegada mientras el gateway estaba `Updating`; Terraform recibió
  errores reintentables y terminó correctamente cuando el gateway quedó listo.
- AWS CloudFormation rechazó `ec2:CreateCustomerGateway` por una denegación
  explícita de la SCP de la organización. No se pudo crear ninguna conexión
  IPsec ni probar túneles, BGP, rutas privadas o tráfico entre redes. El stack
  quedó `ROLLBACK_COMPLETE`, todos sus recursos figuran `DELETE_COMPLETE` y se
  eliminó el registro del stack.
- Para cortar el costo recurrente autorizado solo para la prueba, Terraform
  destruyó los 10 recursos Azure. `rg-tangama-private-network` devuelve
  inexistente y `terraform state list` quedó vacío. La Function y el grupo
  Azure del WMS, así como el stack del portal AWS, no se eliminaron.
- Se corrigió la plantilla VPN: las reglas de parámetros ya no usan
  `!Condition` dentro del bloque CloudFormation `Rules`, y
  `aws cloudformation validate-template` pasó. Terraform ahora ordena la
  creación de todos los subnets antes del gateway para evitar escrituras
  concurrentes al plano de red; `fmt -check` y `validate` pasaron. Esto deja la
  IaC corregida, pero **no** elimina el bloqueo de política ni constituye una
  conexión multinube implementada.
- Verificación posterior: el portal siguió `UPDATE_COMPLETE`; `/health` y
  `/ready` devolvieron HTTP 200, PostgreSQL `ok` y ambos destinos del ALB
  `healthy`. No se registraron credenciales ni secretos en este documento.

## Resultado — 02:32 America/Chicago

Se identificó y corrigió la causa del `401` visto a la 01:23: el secreto
`tangamandapio/azure/function-key` en AWS Secrets Manager no coincidía con la
clave host vigente de la Function App. Se obtuvo la clave con ARM en memoria,
se verificó primero contra `GET /api/wms/inventory` (HTTP 200) y se escribió
una nueva versión del secreto. Su valor no se registró ni se mostró.

Como la plantilla AWS lee el secreto durante el arranque, se reemplazaron las
EC2 gradualmente, una por una. AWS Academy denegó `StartInstanceRefresh` por una
política organizacional; la terminación controlada con capacidad deseada
constante sí fue permitida. Tras cada nodo se esperó drenaje completo antes de
continuar. Los procesos nuevos de ambas instancias consultaron Azure con la
clave cargada desde su configuración y recibieron HTTP 200; ambas respuestas
identificaron `demo-inventory-ledger` y 3 artículos.

## Recorrido desde el artefacto AWS desplegado

En una EC2 se ejecutó el `app.py` publicado en `/opt/tangamandapio` con una
base SQLite temporal, eliminada al terminar; no se crearon pedidos ni socios en
RDS. La prueba recorrió el outbox y la API ERP de ese artefacto contra la
Function/Queue/Blob de Azure:

1. La orden sintética se guardó en el outbox local y se despachó (`delivered`,
   upstream `queued`). Azure la procesó como `demo_fulfillment_completed`.
2. Se creó la recepción compensatoria; Azure la procesó como
   `demo_restock_completed`.
3. El stock ficticio de `SKU-ARROZ-001` volvió al valor inicial: **24 → 23 → 24**.
4. El portal temporal reconcilió ambos resultados (`completed_demo` y
   `received_demo`).

IDs de correlación: venta `evt-27367b8f25374ac189ba74479f5c214f`; recepción
`evt-9d16f4138e9a4b8b927107fbf8cf614e`. Azure conserva los blobs sintéticos
como auditoría; la prueba no representa stock comercial ni un WMS real.

## Comprobaciones finales y límites

- CloudFormation `UPDATE_COMPLETE`, última detección `IN_SYNC`; ASG deseado 2,
  2/2 `InService`/`Healthy`; target group 2 sanos, 0 drenando y 0 no sanos.
- ALB `/health`: `status=ok`, `database=ok`. RDS disponible, cifrado, privado,
  Single-AZ, retención de backup de 1 día.
- La Function Azure permanece en endpoint público HTTPS; no se desplegó VNet/VPN
  privada. La prueba acredita integración HTTPS autenticada, no conectividad
  privada multinube.
- El endpoint de inventario del portal en la sesión del admin de producción
  respondió HTTP 428 `password_change_required`. Se respetó la política y no se
  omitió ni cambió la contraseña; por eso la prueba E2E usó login temporal y
  SQLite aislada dentro de EC2.
- La instancia real de RDS, el admin de producción, los roles en navegador,
  dominio/HTTPS del ALB, voz y recuperación RDS con RTO/RPO siguen sin cerrarse.
