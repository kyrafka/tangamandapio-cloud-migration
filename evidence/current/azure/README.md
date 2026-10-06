# Evidencias históricas Azure

**Fecha de corte:** 05/10/2026
**Dominio:** operación WMS asíncrona de Tangamandapio S.A.C.  
**Región temporal:** West US
**Estado actual:** ciclo destruido; no existe un Resource Group activo de Tangamandapio.

| ID | Qué demuestra | Resultado | Uso en el entregable |
|---|---|---|---|
| CUR-AZ-01 | Terraform creó el vertical WMS temporal | 12 recursos creados en `rg-tangamandapio-e2e-wus` | Sí, como evidencia de infraestructura |
| CUR-AZ-02 | Diagnóstico de empaquetado corregido | El runtime sólo indexó correctamente después de terminar el build remoto y publicar un único modelo compatible | No usar como evidencia de logro; sí en bitácora técnica |
| CUR-AZ-03 | Plan de eliminación | Ejecutado y sustituido por `CUR-AZ-08` | Bitácora, no prueba principal |
| CUR-AZ-05 | Inventario Azure CLI del ciclo temporal | Function Linux `Running`, Storage, Key Vault, Monitor y plan Consumption | Evidencia histórica de infraestructura |
| CUR-AZ-06 | Health WMS autenticado | HTTP `200`, `status=ok`; CORS limitado al portal | Sí, evidencia visual de funcionamiento parcial |
| CUR-AZ-07 | Flujo WMS extremo a extremo | Health `200`; fulfillment `202`; Blob (430 bytes) y Queue verificados; núcleo API local `201` y outbox `delivered` | Sí, evidencia visual de funcionamiento completo |
| CUR-AZ-08 | Cierre Azure | Grupos temporales eliminados; consulta final sin grupos | Evidencia de control de costos |

No se guarda ningún secreto, clave de Function, URL firmada, identificador de cuenta ni dato personal. Las imágenes `CUR-AZ-05`, `CUR-AZ-06` y `CUR-AZ-07` son registros visuales de consultas autenticadas de Azure CLI, no capturas del portal. Las capturas de portal deben archivarse y anonimizarse antes de incorporarlas al Entregable 1; ningún registro de esta carpeta debe presentarse como inventario activo.
