# Evidencia real de portal Azure — 01/10/2026

## Alcance

Ejecución vigente del vertical WMS, conservada activa a pedido del estudiante para capturas antes de cualquier cierre.

| Dato | Valor |
|---|---|
| Grupo de recursos | `rg-tangamandapio-261001evid766-wus` |
| Región | West US |
| Function App | `tangama261001evid766-wms-fn` |
| Estado | En ejecución; Linux; runtime Functions v4 |
| Prueba sintética | `evt-20261001-portal-001` |

## Vistas registradas desde Azure Portal

Solo `AZ-PORTAL-01_inventario_2026-10-01.png` está archivada como captura
directa del portal. Las vistas `AZ-PORTAL-02` a `AZ-PORTAL-04` se describieron
en la bitácora, pero sus archivos PNG no están presentes en el repositorio; no
presentarlas como capturas adjuntas.

| ID propuesto | Vista que se mostró en el portal | Resultado verificable |
|---|---|---|
| `AZ-PORTAL-01` | Información general del grupo de recursos. Archivo: `screenshots/AZ-PORTAL-01_inventario_2026-10-01.png`. | Siete recursos: Storage, Key Vault, Log Analytics, Application Insights, Function App, plan App Service y acción automática de Smart Detection. PNG archivado. |
| `AZ-PORTAL-02` | Información general de la Function App. | El registro escrito informa estado **En ejecución** y dos funciones HTTP; PNG no archivado. |
| `AZ-PORTAL-03` | Prueba/ejecución de `HttpHealth`. | El registro escrito informa **HTTP 200**; PNG no archivado. |
| `AZ-PORTAL-04` | Prueba/ejecución y registros de `HttpFulfillment`. | El registro escrito informa **HTTP 202**, Blob **201**, Queue **201** y ejecución `Succeeded`; PNG no archivado. |

## Nota de integridad

Las capturas anteriores son pantallas reales tomadas durante la sesión activa del portal. Este archivo registra su contexto técnico y no sustituye los PNG: al guardarlos, se deben recortar o anonimizar los encabezados que muestren correo, suscripción, claves o identificadores personales. No se debe borrar este grupo de recursos hasta que los PNG estén archivados y el estudiante indique el cierre.

## Incidencia del panel de pruebas

Un reintento posterior de `HttpFulfillment` devolvió HTTP 400 `JSON inválido` pese a que el editor visual mostraba el cuerpo. El registro indica que la Function fue invocada y terminó correctamente, pero recibió una entrada vacía o no serializada por el panel. No se considera un fallo del servicio WMS: la prueba previa autenticada desde el mismo portal devolvió HTTP 202 y dejó registros de Blob/Queue. Para repetirlo, validar el cuerpo visible antes de ejecutar y, si el portal vuelve a perderlo, usar la invocación autenticada por CLI sin exponer la clave en la captura.
