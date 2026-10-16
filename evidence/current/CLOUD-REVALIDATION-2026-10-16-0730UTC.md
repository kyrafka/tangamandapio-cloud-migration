# Revalidación AWS–Azure — 16/10/2026 07:23–07:40 UTC

## Resultado

- AWS STS aceptó el perfil `default`. CloudFormation está `UPDATE_COMPLETE`;
  el último drift detection fresco terminó `IN_SYNC` con cero recursos.
- ASG: 2/2 instancias `InService` y `Healthy`; ambos destinos del ALB
  `healthy`. RDS está disponible, cifrado, Single-AZ, con retención de backup
  de un día.
- Portal `https://tangamandapio.kendellnm.me/health` y Azure Function
  `https://tangama-wms-261008.azurewebsites.net/api/health` respondieron HTTP
  200. Azure informa `Running` y HTTPS-only. Terraform Azure `-refresh-only`
  previo: `No changes`; no se aplicó infraestructura.

## Prueba E2E desplegada — 07:28 UTC

Se ejecutó una vez el modo `full` por SSM en una instancia sana, con destino
loopback al portal desplegado. El test usa únicamente el inventario sintético
marcado por el servicio y crea una venta y compra de prueba; conserva los
registros transaccionales como evidencia y compensa la unidad vendida con la
recepción sintética.

- Resultado: `LIVE_E2E_PASSED`; salud de base de datos `ok`.
- Venta: `completed_demo`. Compra/recepción: `received_demo`.
- Dos eventos outbox procesados y entregados por Azure.
- SKU QA: saldo ficticio antes/después **10 → 10**.
- Matriz de acceso repetida: Comercial obtiene 200 en ventas y 403 en
  inventario, outbox y administración; Operaciones obtiene 200 en inventario y
  outbox y 403 en ventas y administración.
- Lecturas autenticadas concurrentes: 24/24 HTTP 200, concurrencia 6,
  p95 370.65 ms.

## Verificación posterior — 07:29 UTC

El smoke Admin de solo lectura terminó `LIVE_ADMIN_READONLY_SMOKE_PASSED`:

- Dashboard/outbox: 55 de 55 eventos reconciliados como entregados, cero
  pendientes; 1 de 1 pedido visible coincide con la lista completa permitida.
- La matriz de permisos volvió a arrojar las respuestas esperadas 200/403.
- Lecturas autenticadas: 24/24 HTTP 200, concurrencia 6, p95 511.97 ms.
- SNS: dos suscripciones confirmadas, cero pendientes. Este chequeo no disparó
  una alarma ni demuestra entrega de una alerta nueva.
- Application Insights (ventana agregada de 20 min): dos recepciones de evento
  HTTP 202 y dos ejecuciones de `process_fulfillment_message` con `resultCode=0`
  y éxito. El conteo coincide con el E2E, pero la consulta no correlacionó
  cada ejecución con su `event_id`.

## Smoke adicional por ALB — 07:39 UTC

La prueba Admin de solo lectura se repitió desde el equipo local usando el
destino `alb-origin-https`: conectó al ALB directamente, manteniendo el
hostname/SNI y la validación TLS normales. No se cambió Cloudflare. Resultado:
24/24 lecturas HTTP 200, concurrencia 6, p95 599.37 ms; 55/55 eventos
entregados y cero pendientes. Es un smoke corto del origen, no carga sostenida.

Estos smokes miden operaciones cortas de lectura, no carga sostenida ni la
capacidad para 3,000 usuarios. Un intento independiente de 300 solicitudes al
dominio atravesando Cloudflare había recibido 403/1010 antes de llegar a la
aplicación; no se modificó ni eludió la protección.

## Criterios todavía abiertos

- Fallo controlado y recuperación/reintento del outbox con correlación, sin
  manipular una poison message existente.
- Red privada AWS–Azure; AWS Academy denegó `CreateCustomerGateway` por SCP.
- RDS Single-AZ y backup de un día: restore aislado pasó históricamente, pero
  failover Multi-AZ no fue probado.
- WAF administrado no desplegado.
- Carga sostenida y observación del escalado 2↔3 con un cliente autorizado por
  Cloudflare; aún no se demuestra capacidad de 3,000 usuarios.
- Prueba visual con sesiones Comercial y Operaciones, CSV e interacción
  WebRTC audio/video en dos navegadores.
- Correlación de una invocación Azure por ID con la alerta entregada y costo
  Azure atribuible por proyecto.

No se reinició ni cambió infraestructura, usuarios, credenciales o políticas.
