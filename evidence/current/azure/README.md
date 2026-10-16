# Evidencias Azure

**Revalidación viva — 16/10/2026, 05:44–05:58 UTC:** suscripción `Azure for
Students` `Enabled`; grupo de reconstrucción `Succeeded`; Function
`tangama-wms-261008` `Running`/HTTPS-only y siete funciones indexadas. Health
200 con TLS válido. El plan Terraform con el backend remoto terminó `No
changes` sin `apply`. El E2E local→Azure procesó venta/reposición sintéticas,
restauró el ledger ficticio y dejó poison count cero; no fue tráfico desde
EC2/RDS. La evidencia conjunta incluye el incidente del portal AWS:
[`CLOUD-REVALIDATION-2026-10-16-0547UTC.md`](../CLOUD-REVALIDATION-2026-10-16-0547UTC.md).

**E2E compensado ERP local→Azure — 16/10/2026, 05:37 UTC:** tras desplegar la
sonda GET/HEAD, el release local procesó una venta y una recepción; el saldo
ficticio regresó a su línea base. Guards 401/400 y poison count cero antes y
después. Application Insights reportó dos ejecuciones correctas del worker,
cero fallidas en la ventana agregada de 20 minutos. No fue tráfico de EC2/RDS. Véase
[`AZURE-ERP-E2E-2026-10-16-0537UTC.md`](AZURE-ERP-E2E-2026-10-16-0537UTC.md).

**Revalidación Function + Application Insights — 16/10/2026, 01:24 UTC:** el
smoke ERP local→Azure pasó a las 01:20 con compensación del saldo demo. La
consulta de 10 minutos mostró dos `202`, dos workers exitosos, el `400` de
guarda esperado y cero fallidas. Detalle en
[`AZURE-APPINSIGHTS-REVALIDACION-2026-10-16-0124UTC.md`](AZURE-APPINSIGHTS-REVALIDACION-2026-10-16-0124UTC.md).
La lectura de las 01:25 confirmó además las dos reglas habilitadas, el Action
Group activo y sus dos receptores, sin revelar direcciones ni enviar alertas.

**Prueba viva ERP→Azure compensada — 15/10/2026:** el release local con SQLite
efímera recorrió la venta y recepción sintéticas contra la Function desplegada;
Azure procesó ambos eventos y el ledger demo regresó a la línea base. Pasaron
los guardas de ingreso y la comprobación de poison queue solo por metadatos.
No fue tráfico originado desde EC2. Véase
[`AZURE-LIVE-ERP-SMOKE-2026-10-15.md`](AZURE-LIVE-ERP-SMOKE-2026-10-15.md).

**Application Insights y ejecución del trigger — 15/10/2026, 00:49 UTC:**
Function `tangama-wms-261008` `Running`/HTTPS-only; health HTTP 200. La consulta
de 24 horas reportó 17 solicitudes y cero fallidas, incluidas dos ejecuciones
exitosas de `process_fulfillment_message` y dos de
`receive_fulfillment_event`. Es telemetría agregada sin payload; no prueba por
sí sola alertas entregadas ni WMS comercial. Ver
[`AZURE-MONITOR-INVOCACIONES-2026-10-15.md`](AZURE-MONITOR-INVOCACIONES-2026-10-15.md).

**E2E y seguridad de ingreso — 14/10/2026, 07:43–07:49 America/Chicago:**
el smoke live del portal local verificó 401 sin Function key, 400 para fuente
no permitida y ausencia de persistencia del ID rechazado. Después procesó venta
y recepción compensatoria; stock del ledger demo volvió a la línea base.
Application Insights mostró seis respuestas 202, un 400 de validación y seis
workers `resultCode=0` para tres corridas recientes. Poison count cero antes y
después, sin leer payloads. No fue tráfico de EC2 ni una prueba de VPN; los
eventos válidos sintéticos quedan en auditoría. Detalle en
[`AZURE-ERP-E2E-2026-10-14.md`](AZURE-ERP-E2E-2026-10-14.md).

**E2E compensado — 14/10/2026, 07:29 America/Chicago:** el portal local, con
SQLite efímera, envió una venta y una recepción compensatoria; la Azure
Function procesó ambos eventos y el ledger ficticio volvió a su línea base.
Application Insights mostró cuatro solicitudes HTTP 202 y cuatro workers con
`resultCode=0` para dos corridas recientes. El poison count fue cero antes y
después, solo por metadatos. No es tráfico originado desde EC2 ni conexión
privada AWS–Azure; dos eventos sintéticos permanecen en auditoría. Detalle en
[`AZURE-ERP-E2E-2026-10-14.md`](AZURE-ERP-E2E-2026-10-14.md).

**Revalidación viva — 14/10/2026, 00:51 America/Chicago:** la Function
`tangama-wms-261008` está `Running`, `httpsOnly=true`, Linux/West US; health
200. Application Insights conserva dos solicitudes de
`process_fulfillment_message`, ambas `resultCode=0` y ninguna fallida. Esta es
telemetría agregada sin payload; no es una captura del portal ni demuestra un
WMS comercial. Véase el [corte cloud del 14/10](../CLOUD-REVALIDATION-2026-10-14.md).

**Fecha del antecedente:** 05/10/2026
**Dominio:** operación WMS asíncrona de Tangamandapio S.A.C.  
**Región temporal:** West US
**Historial:** los ciclos identificados como `261001evid766` y `261001r2` se
cerraron. El portal de Azure mostró un ciclo posterior con la Function App
`tangama-wms-fn` en ejecución el 08/10/2026; la nota visual está en
[`../REVISION_CHROME_2026-10-08.md`](../REVISION_CHROME_2026-10-08.md). No se
confundirá el cierre de los grupos antiguos con el estado de este recurso
posterior.

**Revalidación viva — 13/10/2026, 23:09 America/Chicago:** el grupo activo es
`rg-tangamandapio-rebuild-wus`, Function `tangama-wms-261008` (`Running`,
HTTPS-only), hash publicado `6eea3b6a…`, health 200 y E2E compensado venta/
recepción aprobado. Un Terraform plan reciente contra el state local y el ZIP
con ese hash terminó `No changes` (exit 0). No se aplicó nada en ese plan. La
revalidación completa y sus límites están en
[`../CLOUD-REVALIDATION-2026-10-13.md`](../CLOUD-REVALIDATION-2026-10-13.md).

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
