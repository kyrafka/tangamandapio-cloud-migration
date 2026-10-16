# Revalidación viva AWS–Azure — 16/10/2026, 07:59–08:08 UTC

## Estado de infraestructura

- AWS STS aceptó el perfil temporal `default` en la cuenta académica
  `841113066612`. CloudFormation `tangamandapio-live-20261013` está
  `UPDATE_COMPLETE`; una detección iniciada a las 07:59:34 terminó
  `IN_SYNC`, con cero recursos desviados.
- El ASG mantiene mínimo/deseado 2 y máximo 5. Las dos instancias están
  `InService`/`Healthy`; ambos destinos del ALB están `healthy`. Los dos
  volúmenes raíz son gp3 de 8 GiB y están cifrados. Esto resuelve la duda
  anterior sobre si hacía falta permitir un volumen raíz sin cifrar: no.
- RDS `tangamandapio-postgres` está `available` y cifrado; sigue Single-AZ,
  `db.t3.micro` y con retención de backup de un día. No se probó failover en
  este corte.
- A las 08:08 el dominio `https://tangamandapio.kendellnm.me/health` devolvió
  `200`; HTTP redirigió a HTTPS con `301`. La respuesta HTTPS incluye HSTS.
- La suscripción Azure for Students está `Enabled`; la Function
  `tangama-wms-261008` está `Running` y `HTTPS-only`. El health HTTPS devolvió
  `{"status":"ok","service":"tangamandapio-wms"}`. Application Insights
  `tangama-wms-ai` está `Succeeded`; las alertas métricas de 5xx y latencia
  están habilitadas.
- Terraform Azure ejecutó `plan -refresh-only` con
  `rebuild.tfvars.example`: `No changes`; después, un plan normal con ese
  archivo y `alert-recipients.local.tfvars` protegido también terminó
  `No changes`. No se guardó plan ni se ejecutó `apply`. El intento inicial
  sin `-var-file` se detuvo por variables requeridas faltantes y no cambió
  recursos. El plan no imprimió los receptores de alerta.

## Pruebas funcionales desplegadas

### ERP → AWS/RDS/outbox → Azure Queue/Function

El modo `full` del smoke desplegado terminó `LIVE_E2E_PASSED` por el origen
ALB HTTPS:

- Salud RDS `ok`; importación de catálogo sintético aprobada.
- Venta `completed_demo` y compra/recepción `received_demo` completadas.
- Dos eventos outbox entregados. El ledger ficticio del SKU de QA quedó
  exactamente en su línea base: 10 → 10.
- Autorización API: Comercial recibió 200 para ventas y 403 para WMS, outbox y
  administración; Operaciones recibió 200 para WMS/outbox y 403 para ventas y
  administración.
- 24/24 lecturas autenticadas HTTP 200 con concurrencia 6; p95 240.44 ms.

Application Insights permite ahora correlacionar los resultados por `event_id`
con la invocación del worker (`operation_Id` coincidente):

| Evento sintético | Resultado del ledger demo | Worker | `resultCode` | Duración |
|---|---|---:|---:|---:|
| `evt-68a03f029c614589ba59f8e864a55638` | `demo_fulfillment_completed` | Éxito | 0 | 240.04 ms |
| `evt-d8370a2acb464f08922b00e1af83699f` | `demo_restock_completed` | Éxito | 0 | 327.06 ms |

### Administración, Finanzas y correo

- Smoke Admin de solo lectura: `LIVE_ADMIN_READONLY_SMOKE_PASSED`; outbox
  paginado 57/57 entregado, cero pendientes; 24/24 lecturas HTTP 200, p95
  243.2 ms; matriz de permisos 200/403 conforme.
- Smoke Admin de módulos: `LIVE_ADMIN_MODULE_SMOKE_PASSED`; cuenta de QA por
  S/ 0.05 quedó `paid`; correo sintético apareció en Enviados y Bandeja y se
  marcó leído. El transporte confirmó `portal_only`, sin SMTP externo.
- Azure poison queue informó conteo aproximado 0 y `payloads_exposed=false`;
  no se leyó ni manipuló mensaje poison. Dos suscripciones SNS están
  confirmadas; esta prueba no disparó una alarma nueva.

Estas pruebas conservan transacciones sintéticas en RDS y eventos de auditoría
en Azure; no realizan pagos externos ni cambian inventario físico. El WMS sigue
siendo el ledger académico ficticio, pero la venta, reposición, entrega y
conciliación del flujo demo sí se ejecutaron en los servicios desplegados.

## Criterios todavía abiertos o no demostrados

- La automatización visual de Chrome se detuvo porque el control no pudo
  identificar con suficiente confianza la URL activa. Por ello este corte no
  afirma recorrido visual por cada rol ni prueba visual de CSV.
- WebRTC audio/video entre dos navegadores sigue sin prueba bidireccional
  reciente.
- No se indujo una falla transitoria en el outbox desplegado; recuperación y
  backoff están cubiertos por pruebas aisladas/mocks, no por un fallo live.
- RDS continúa Single-AZ con un día de retención. Restore aislado previo
  (RTO observado 289 s, RPO observado ≤10 s) es histórico; no se repitió ni se
  probó failover.
- No hay ruta privada AWS–Azure; AWS Academy denegó históricamente
  `CreateCustomerGateway` por SCP y Azure no tiene VNet para esta integración.
- No se midió carga sostenida ni escalado 2↔3; 3,000 usuarios externos es un
  objetivo de diseño, no una capacidad demostrada. El ensayo de 24 lecturas no
  es un benchmark de capacidad.
- WAF no está desplegado. El intento previo de 300 solicitudes vía Cloudflare
  recibió 403/1010 antes de llegar a la aplicación; no se desactivó ni eludió
  la protección.
- El coste Azure no quedó atribuido con una cifra fiable en este corte.

No se aplicó ni reinició infraestructura. Se ejecutó una detección de drift,
consultas de solo lectura y los dos smokes funcionales descritos arriba.
