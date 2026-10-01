# CUR-AZ-02 — Diagnóstico inicial de Functions y corrección de empaquetado

| Campo | Registro |
|---|---|
| Fecha | 30/09/2026 |
| Recurso | Azure Function App del vertical WMS temporal |
| Correcciones iniciales | Funciones explícitas `function.json` y configuración `AzureWebJobsStorage` |
| Descubrimiento del host | Registró `HttpHealth` y `HttpFulfillment` |
| Prueba | GET `/api/health` y POST `/api/fulfillment/events` con clave válida, sin registrar ni exponer la clave |
| Resultado inicial | HTTP 500; diagnóstico técnico previo a la corrección final |
| Blob y Queue | No acreditados; no existe prueba válida de mensaje ni objeto persistido |
| Corrección posterior | Se eliminó el paquete de dependencias compiladas en Windows y se publicó código fuente para compilación remota Linux. Se corrigió además el TTL de Azure Queue para enviarlo como segundos enteros. |
| Estado actual | `HttpHealth` autenticado respondió HTTP 200 el 01/10/2026. La prueba integral Blob/Queue de `HttpFulfillment` debe repetirse y quedar evidenciada antes de declararla aprobada. |

## Interpretación permitida

Esta evidencia conserva el diagnóstico y la corrección aplicada. No autoriza afirmar que el flujo WMS, la integración AWS-Azure, Blob ni Queue funcionan correctamente hasta repetir la prueba integral y registrar su evidencia.
