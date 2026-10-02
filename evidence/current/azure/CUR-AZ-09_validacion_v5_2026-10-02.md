# CUR-AZ-09 — Validación funcional real del WMS Azure

- Fecha: 02/10/2026
- Entorno: Azure for Students, West US
- Grupo de recursos: `rg-tangamandapio-261001r2-wus`
- Servicio principal: Azure Function `tangama261001r2-wms-fn`

## Plataforma vigente

El despliegue fue aplicado con Terraform. La Function consume un paquete ZIP
privado desde Blob Storage mediante `WEBSITE_RUN_FROM_PACKAGE` y un SAS de solo
lectura temporal. El código usa identidad administrada para escribir en el
contenedor privado de evidencia y publicar en Azure Queue Storage. Se mantienen
Application Insights, Log Analytics, Key Vault con RBAC y las asignaciones de
roles de Blob/Queue para la identidad de la Function.

## Resultados de prueba

| Prueba | Resultado real |
| --- | --- |
| Inventario de Function App con Azure CLI | `Fulfillment` y `HttpHealth` registrados |
| `GET /api/health` | HTTP **200** con `status=ok` y `service=tangamandapio-wms` |
| Primer `POST /api/fulfillment/events` con `event_id=evt-20261002-r2` | HTTP **202** y estado `queued` |
| Reintento idéntico del mismo evento | HTTP **200** y estado `duplicate` |

La segunda respuesta confirma idempotencia: el Blob se crea con `If-None-Match: *`,
por lo que un reintento no sobrescribe la evidencia ni vuelve a encolar el pedido.

## Captura visual pendiente

Para evidencia visual, capturar en el portal la Function en estado **En ejecución**
y la lista de funciones `HttpHealth` y `Fulfillment`; en Cloud Shell o CLI mostrar
las respuestas HTTP 200, 202 y 200 sin exponer la clave de función.
