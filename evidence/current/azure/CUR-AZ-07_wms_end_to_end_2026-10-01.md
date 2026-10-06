# CUR-AZ-07 — Flujo WMS end to end verificado

| Campo | Resultado real |
|---|---|
| Fecha | 01/10/2026 |
| Región | West US |
| Prueba de disponibilidad | `GET /api/health` autenticado: HTTP `200`, `status=ok` |
| Evento sintético | `POST /api/fulfillment/events` con `event_id=evt-20261001-e2e-001` |
| Primera invocación | HTTP `202`, estado `queued` |
| Persistencia | Blob privado `fulfillment-events/evt-20261001-e2e-001.json` existe; tamaño observado: 430 bytes |
| Cola | `fulfillment-events` contiene el mensaje del evento; expiración configurada a siete días |
| Integración de referencia | Un pedido del núcleo API ejecutado localmente devolvió HTTP `201`; su outbox entregó el evento al WMS (`delivered`). No se presenta como prueba desde el ALB AWS temporal. |
| Seguridad | Claves Function usadas solo en memoria del cliente de prueba; no se guardan ni se muestran |

La verificación de Blob y Queue por identidad del estudiante devolvió denegación de plano de datos. Para comprobar el resultado sin exponer la clave, Azure CLI consultó temporalmente la clave de cuenta mediante plano de control autorizado. La Function ejecuta su operación normal con Managed Identity/RBAC.
