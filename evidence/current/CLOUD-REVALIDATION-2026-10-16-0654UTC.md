# Revalidación de nube y pruebas integradas — 16/10/2026, 06:39–06:54 UTC

## Resultado

El token temporal AWS autenticó por STS en la cuenta `841113066612` (rol
`voclabs`). No se copió el token a esta evidencia. El portal recuperó servicio
con EBS cifrado; no se modificó CloudFormation, no se desactivó cifrado y no se
aplicó Terraform.

## AWS

- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; ALB `active`.
- `detect-stack-drift` completó con `IN_SYNC` a las 06:53:38 UTC.
- ASG `tangamandapio-asg`: mínimo/deseado 2, máximo 5; dos EC2
  `InService`/`Healthy` (`i-04b97f0ae7a9eddb5`, `i-0d4f01a1588a857bc`) y dos
  destinos `healthy` al corte. Instancias anteriores estaban en drenaje o
  terminación; el ASG las reemplazó.
- El mismo Launch Template v18 lanzó instancias con volúmenes raíz EBS
  cifrados usando `alias/aws/ebs`. Se conserva el requisito de cifrado.
- `https://tangamandapio.kendellnm.me/health`: HTTP 200 a las 06:53:42 UTC.
- `admin-modules` pasó en modo sintético vía SSM desde una instancia sana al
  origen HTTPS del portal: Finanzas aceptó un documento de 0.05, lo liquidó
  como `paid` y confirmó persistencia; el correo se envió/leyó en la bandeja
  interna `portal_only`, sin SMTP externo; Azure reportó `fulfillment-events-
  poison` count 0 y `payloads_exposed=false`.
- El E2E AWS→Azure completo pasó: productos/catálogo, venta y recepción
  compensatoria, stock ficticio regresó 10→10, dos eventos outbox entregados,
  autorizaciones de Comercial/Operaciones 200/403 como esperado y 24/24 GET
  autenticados 200 (concurrencia 6, p95 346.89 ms). No es prueba sostenida ni
  valida capacidad para 3,000 usuarios.
- CloudTrail registró `StopInstances` sobre dos instancias antiguas a las
  06:45:43–06:45:44 UTC por el rol administrado del laboratorio
  `vocareum/resource`. Un comando SSM dirigido a una de ellas no llegó a
  comenzar (`ExecutionStartDateTime=null`); se canceló, sin efectos de prueba,
  y el smoke se ejecutó una vez en la instancia sana.

## Azure

- Azure CLI confirmó suscripción `Enabled` y Function
  `tangama-wms-261008` `Running`, `httpsOnly=true`, región West US.
- `https://tangama-wms-261008.azurewebsites.net/api/health`: HTTP 200,
  respuesta `{"status":"ok","service":"tangamandapio-wms"}`.
- El procesamiento representa un ledger de inventario sintético; no está
  conectado a un WMS comercial ni a stock físico.

## Alcance y pendientes

### Reconsulta a las 07:03 UTC

Después de la terminación de las instancias detenidas por el rol del laboratorio,
el ASG quedó exactamente en su deseado de 2: ambas instancias están
`InService`/`Healthy`, y sus dos destinos aparecen `healthy`. El health público
del portal AWS y el de Azure Function devolvieron HTTP 200. No se realizaron
cambios cloud en esta reconsulta.

La red privada/VPN AWS–Azure sigue sin desplegarse. Faltan carga sostenida y
medición de escalado, revisión visual autenticada completa, comprobación de
WebRTC entre dos navegadores y prueba de failover Multi-AZ. Esta pasada confirma
salud, integración y módulos mencionados, pero no cierra esos criterios.
