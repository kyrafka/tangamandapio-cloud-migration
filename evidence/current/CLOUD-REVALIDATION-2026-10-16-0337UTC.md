# Revalidación AWS–Azure y pruebas del portal — 16/10/2026, 03:37 UTC

## Infraestructura observada

- AWS STS autenticó en la cuenta Academy esperada y el rol `voclabs` desde el
  perfil local `default`. No se guardaron credenciales en el repositorio.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE` (última
  actualización 00:27:59 UTC). El ALB está activo, internet-facing; el listener
  443 usa ACM `ISSUED` para `tangamandapio.kendellnm.me`, y el listener 80
  redirige a HTTPS. El certificado ACM consultado vence el 30/04/2027.
- `https://tangamandapio.kendellnm.me/`, `/health` y `/ready`: HTTP 200 con
  verificación TLS correcta. La Function Azure `/api/health`: HTTP 200 con TLS
  correcto.
- ASG: 2/2 instancias `InService` y `Healthy`, deseadas 2, máximo 5. Target
  group: 2/2 destinos `healthy`.
- RDS PostgreSQL 18.3 está `available`, `db.t3.micro`, privada y cifrada; sigue
  **Single-AZ**, con retención de backup de **un día**.
- La detección fresca de CloudFormation terminó `IN_SYNC`, 0 recursos con drift.
  Sin embargo, la plantilla original guardada por el stack conserva defaults
  del artefacto v16; los parámetros efectivos del stack apuntan explícitamente
  a v18 y coinciden con la plantilla local. Un change set que preservaba todos
  los parámetros fue rechazado por AWS porque no había cambios efectivos. No se
  ejecutó ni quedó un change set pendiente; recursos y stack siguen intactos.

## Pruebas funcionales vivas

- El login Admin/Comercial/Operaciones, la matriz de permisos, la reconciliación
  del tablero y las suscripciones SNS pasaron por conexión directa al ALB con
  SNI y hostname del dominio y validación TLS normal. Comercial obtuvo 200 solo
  en ventas y 403 en WMS, outbox y administración; Operaciones obtuvo 200 en
  WMS/outbox y 403 en ventas y administración. Admin obtuvo sus rutas admin.
- El tablero reportó 1 pedido visible, 49 eventos entregados, 0 pendientes; la
  paginación concilió 49/49. SNS reportó 2 suscripciones confirmadas y 0
  pendientes; no se disparó una alarma en este smoke.
- E2E AWS → RDS/outbox → Azure pasó: catálogo sintético, venta
  `completed_demo`, recepción `received_demo`, ambos eventos entregados, ledger
  ficticio restaurado de 10 a 10. Las 24 lecturas autenticadas dieron 24/24
  HTTP 200, concurrencia 6, p95 287.75 ms. La prueba añade registros de venta,
  compra y auditoría sintéticos; no cambia stock neto.
- Smoke de módulos Admin pasó: gasto sintético de S/ 0.05 liquidado como
  `paid`; correo interno del portal enviado y leído (no SMTP externo); poison
  queue `ok`, conteo aproximado 0 y sin exponer mensajes.
- Se intentó una sola autenticación automatizada por el FQDN público. Cloudflare
  devolvió 403 antes de llegar a Flask (`cf-ray` `a4b3e39c3dc1379c-EZE`). El
  mismo flujo completo pasó directamente por TLS al ALB; esto aísla el fallo en
  la ruta automatizada del proxy, pero no demuestra la causa exacta ni justifica
  cambiar reglas de seguridad de Cloudflare.

## Validación local

`tests/run_local_quality.ps1 -ValidateTerraform` terminó
`QUALITY_GATE=APROBADA`: 213 pruebas Python, 14 Node, build Vite, auditorías de
dependencias sin vulnerabilidades conocidas, `cfn-lint`, Terraform `fmt`,
`init`/`validate` y pruebas mock de VPN/red privada. No se ejecutó `terraform
apply` ni hubo mutación de infraestructura.

## Costos observados y límites de atribución

- AWS Cost Explorer, cuenta Academy completa, del 01 al 15/10: uso bruto
  `US$26.0033000468`, créditos `−US$26.0033011861`, neto
  `−US$0.0000011393`. No es una medición exclusiva de Tangamandapio ni un
  pronóstico; la cuenta agrupa otros servicios del laboratorio.
- Azure for Students reportó 255 filas de consumo para el mismo periodo, pero
  `pretaxCost` fue `None` en las 255; no hubo moneda/importe numérico para sumar.

Por tanto, hay lectura parcial de gasto/créditos AWS, pero la reconciliación
multinube por proyecto y el monto Azure siguen pendientes.

El runner `run_public_portal_admin_readonly.ps1` tiene opt-in separado, verifica
la identidad Academy, admite la ruta pública o diagnóstico directo al ALB con
TLS, incluye la matriz de roles y no imprime secretos ni cuerpos HTTP. Las
pruebas unitarias del runner y de la clasificación segura del 403 pasaron. El
paquete del frontend no cambió en este ajuste. El código IaC local usa defaults
v18, pero la plantilla original almacenada en CloudFormation conserva defaults
v16; el release desplegado sigue siendo v18 por los parámetros actuales. Una
actualización que persista esos defaults requiere una actualización efectiva
de stack, no un change set vacío.

## Brechas vigentes

- El login automatizado del FQDN vía Cloudflare quedó bloqueado; falta una
  comprobación interactiva completa desde la interfaz real del navegador y
  revisar el evento de seguridad del proxy con quien administra Cloudflare.
- No hay conectividad privada AWS–Azure: AWS Academy denegó Customer Gateway
  por SCP y no hay VNet Azure. El E2E funciona sobre HTTPS público.
- RDS no es Multi-AZ, la retención es de un día y no se ha probado failover.
  El restore PT-DR-01 previo es evidencia histórica, no se repitió aquí.
- La carga es una sonda de 24 lecturas en una EC2; no prueba 3,000 usuarios,
  escalado del ASG bajo carga ni capacidad regional.
- WAF AWS no está desplegado; no se probaron WebRTC entre dos navegadores ni
  alarmas métricas disparadas/recuperadas en esta pasada.
- Falta reconciliar costos observados de ambas nubes y guardar capturas nuevas
  de inventario AWS y monitor/invocación Azure.

El WMS y la venta son funcionales como **datos sintéticos/ledger de demo**; no
representan existencias físicas. El correo es portal-only, y Finanzas cubre
operaciones demo, no contabilidad legal.
