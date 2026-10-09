# Evidencias Azure

**Fecha del antecedente:** 05/10/2026
**Dominio:** operación WMS asíncrona de Tangamandapio S.A.C.  
**Región temporal:** West US
**Historial:** los ciclos identificados como `261001evid766` y `261001r2` se
cerraron. El portal de Azure mostró un ciclo posterior con la Function App
`tangama-wms-fn` en ejecución el 08/10/2026; la nota visual está en
[`../REVISION_CHROME_2026-10-08.md`](../REVISION_CHROME_2026-10-08.md). No se
confundirá el cierre de los grupos antiguos con el estado de este recurso
posterior.

| ID | Qué demuestra | Resultado | Uso en el entregable |
|---|---|---|---|
| CUR-AZ-01 | Terraform creó el vertical WMS temporal | 12 recursos creados en `rg-tangamandapio-e2e-wus` | Sí, como evidencia de infraestructura |
| CUR-AZ-02 | Diagnóstico de empaquetado corregido | El runtime sólo indexó correctamente después de terminar el build remoto y publicar un único modelo compatible | No usar como evidencia de logro; sí en bitácora técnica |
| CUR-AZ-03 | Plan de eliminación | Ejecutado y sustituido por `CUR-AZ-08` | Bitácora, no prueba principal |
| CUR-AZ-05 | Inventario Azure CLI del ciclo temporal | Function Linux `Running`, Storage, Key Vault, Monitor y plan Consumption | Evidencia histórica de infraestructura |
| CUR-AZ-06 | Health WMS autenticado | HTTP `200`, `status=ok`; CORS limitado al portal | Tarjeta derivada de respuesta CLI real; no es captura cruda |
| CUR-AZ-07 | Flujo WMS extremo a extremo | Health `200`; fulfillment `202`; Blob (430 bytes) y Queue verificados; núcleo API local `201` y outbox `delivered` | Tarjeta derivada de prueba real; no es captura cruda |
| CUR-AZ-08 | Cierre Azure | Grupos temporales eliminados; consulta final sin grupos | Evidencia de control de costos |

No se guarda ningún secreto, clave de Function, URL firmada, identificador de cuenta ni dato personal. Las imágenes históricas `CUR-AZ-05` a `CUR-AZ-08` son tarjetas visuales de resultados Azure CLI, no capturas crudas del portal/terminal. No deben presentarse como inventario activo; el estado posterior observado se delimita en la bitácora Chrome del 08/10.

`AZ-PORTAL-01` es una captura directa del portal del ciclo antiguo. En el
registro [`LIVE_PORTAL_2026-10-01.md`](LIVE_PORTAL_2026-10-01.md), las vistas
02–04 se describieron, pero sus PNG no están archivados. Las imágenes
`CUR-AZ-05` a `CUR-AZ-08` son tarjetas visuales resumidas de las ejecuciones CLI,
no capturas de pantalla del terminal. Para el estado visual posterior de
`tangama-wms-fn`, falta archivar el PNG anonimizado sugerido en
[`../CAPTURAS_PENDIENTES.md`](../CAPTURAS_PENDIENTES.md); la revisión de Chrome
no guardó ningún binario nuevo en esta carpeta.
