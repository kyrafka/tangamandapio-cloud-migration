# E2E vivo ERP local → Azure Function — historial actualizado al 16/10/2026

## Repetición compensada más reciente — 16/10/2026, 01:20 UTC

El smoke opt-in verificó la suscripción `Azure for Students`, Function en
`Running` y HTTPS-only, e inventario marcado explícitamente como demo antes de
escribir. Comprobó que el ingreso sin clave devuelve 401 y el origen no
autorizado devuelve 400 sin persistir un evento. Luego ejecutó el release ERP
local con SQLite temporal: venta por outbox→Queue→Function y compra
compensatoria por el mismo recorrido. La Function reportó
`demo_fulfillment_completed` y `demo_restock_completed`; el saldo del SKU demo
regresó exactamente al baseline. La cola poison reportó cero antes y después;
solo se leyó metadato.

| Paso | Evento | Resultado |
|---|---|---|
| Venta sintética | `evt-48d2bfcb51574f0c90c951122d3346db` | `demo_fulfillment_completed`; una unidad menos |
| Recepción compensatoria | `evt-ff800324c0804b3fab34dec6ac5eca41` | `demo_restock_completed`; baseline restaurado |

`LIVE_E2E=PASSED`. La base SQLite temporal se eliminó y quedaron en Azure los
dos eventos sintéticos de auditoría. Este proceso usó el artefacto
`app/aws_release/current` localmente: **no** fue iniciado por EC2, no valida la
conectividad privada AWS–Azure y no representa stock físico.

## Repetición compensada más reciente — 13/10/2026, 23:00 America/Chicago

La verificación ARM/CLI localizó el grupo `rg-tangamandapio-rebuild-wus` en
West US y confirmó la Function `tangama-wms-261008` `Running`, HTTPS-only. La
clave no se imprimió; solo se consultó la app setting no sensible de SHA, que
coincide con el paquete publicado
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065`. El
endpoint HTTPS `/api/health` devolvió 200.

Se volvió a ejecutar el smoke opt-in sobre el ledger explícitamente marcado
como demo. El release ERP local escribió una venta de una unidad a outbox,
Azure la entregó por Queue/Function y ERP reconcilió el resultado. Una recepción
compensatoria siguió el mismo camino; el test confirmó el saldo exacto de
regreso a la línea base antes de aprobar.

| Paso | Evento | Resultado |
|---|---|---|
| Venta sintética | `evt-575d325f09fa49f38a65b35e5a492c5f` | `demo_fulfillment_completed`; una unidad menos |
| Recepción compensatoria | `evt-10d9608ebc5b4a81b0f2aa98619e4723` | `demo_restock_completed`; saldo original verificado |

`LIVE_E2E=PASSED`. El SQLite temporal local se eliminó al terminar; quedan
registros sintéticos de auditoría en Azure. Este flujo fue originado por el
proceso local, no por EC2. No acredita red privada ni movimiento de inventario
de un WMS real.

## Repetición compensada — 13/10/2026, 18:43 America/Chicago

El smoke vivo pasó otra vez contra `Azure for Students`. Verificó primero que
la Function `tangama-wms-261008` estuviera `Running`, HTTPS-only y que el
endpoint identificara el ledger como demo antes de escribir. El release de
`app/aws_release/current` corrió localmente con SQLite temporal; el outbox
envió a Azure Queue/Function y el ERP concilió ambos resultados.

| Paso | Evento | Resultado | Stock `SKU-ARROZ-001` |
|---|---|---|---|
| Línea base | — | Ledger ficticio validado | Saldo original |
| Venta | `evt-11931b9e2c544f879e68cac3b14b7779` | `demo_fulfillment_completed` | Una unidad menos |
| Recepción compensatoria | `evt-924b144dfe3f4a9d997110654625013a` | `demo_restock_completed` | Saldo original restaurado |

Resultado `LIVE_E2E=PASSED`. Se eliminaron la base y el administrador locales
temporales; los dos eventos sintéticos quedan en el almacenamiento de auditoría
de Azure. No se tocó infraestructura. Esto demuestra el flujo de aplicación
desde un proceso local, no desde EC2, no demuestra red privada AWS–Azure y no
convierte el ledger ficticio en inventario comercial real.

## Repetición posterior — 13/10/2026, aproximadamente 15:18 America/Chicago

Se volvió a ejecutar el smoke con el release ERP de AWS cargado en un proceso
local. La Function Azure estaba `Running`, HTTPS-only y en modo
`demo-inventory-ledger`. Venta y reversa se procesaron por outbox, Azure Queue
y Function; el saldo ficticio retornó exactamente a 24 unidades.

| Paso | Evento Azure | Resultado | Stock `SKU-ARROZ-001` |
|---|---|---|---:|
| Línea base leída | — | Ledger marcado como demo | 24 |
| Venta ERP → outbox → Queue/Function | `evt-191c0fd8557442ad9e7ef3de35e7d5f0` | `demo_fulfillment_completed` | 23 |
| Recepción compensatoria → Queue/Function | `evt-f50f7286ced5469581b1bbc44d8e76d1` | `demo_restock_completed` | 24 |

La SQLite temporal local se eliminó al terminar; quedan en Azure los registros
sintéticos de auditoría. No se modificó infraestructura. Esto prueba el
procesamiento real de la Function/Queue usando el release ejecutado localmente,
pero no una solicitud originada por las EC2 desplegadas ni conectividad privada
AWS–Azure. El inventario sigue siendo ficticio.

## Repetición más reciente — 13/10/2026, revisión de media mañana

El smoke `tests/run_live_azure_erp_smoke.py` volvió a pasar contra la suscripción
Azure for Students. La revisión previa de la Function confirmó
`tangama-wms-261008` en `Running`, `httpsOnly=true` y modo
`demo-inventory-ledger`. El paquete del ERP se ejecutó localmente; la venta
transitó por el outbox, Azure Queue y Function, y una recepción compensatoria
devolvió el saldo a su línea base de 24 unidades.

| Paso | Evento Azure | Resultado | Stock `SKU-ARROZ-001` |
|---|---|---|---:|
| Línea base leída | — | Ledger marcado como demo | 24 |
| Venta ERP → outbox → Queue/Function | `evt-8f136f8799534663b34a67f65c291149` | `demo_fulfillment_completed`; ERP `completed_demo` | 23 |
| Recepción compensatoria → Queue/Function | `evt-027f7465fb3044bda0a97a294d5b7d50` | `demo_restock_completed`; ERP `received_demo` | 24 |

El test limpió la SQLite temporal local; los eventos sintéticos de auditoría
permanecen en Azure. En la misma revisión, Terraform planizó `No changes`, sin
`apply`. El E2E acredita procesamiento de Queue/Function desde el release local,
no desde EC2, y el inventario sigue siendo ficticio, no un WMS real.

## Resultado — 03:54 America/Chicago

Se ejecutó `tests/run_live_azure_erp_smoke.py` con su opt-in explícito. El
script validó la suscripción Azure for Students habilitada, la Function
`tangama-wms-261008` en `Running` y `httpsOnly=true`, y el modo
`demo-inventory-ledger` antes de mutar datos. La clave Function solo estuvo en
memoria; no quedó en logs ni en este archivo.

El test cargó el release de `app/aws_release/current` dentro de un proceso
local, con SQLite y administrador temporales. El flujo fue:

| Paso | Evento Azure | Resultado | Stock `SKU-ARROZ-001` |
|---|---|---|---:|
| Baseline leído antes del test | — | Ledger marcado como demo | 24 |
| Venta ERP → outbox → Queue/Function | `evt-4f2e2c0b6f7f46178e4f16f8fc8a7620` | `demo_fulfillment_completed`; ERP `completed_demo` | 23 |
| Recepción compensatoria ERP → outbox → Queue/Function | `evt-b13b4229eeee41b9905ac86def0037a9` | `demo_restock_completed`; ERP `received_demo` | 24 |

Después del smoke, consultas HTTP autenticadas de solo lectura confirmaron ambos
estados persistidos y el inventario actual en 24. El proceso temporal local
terminó y su directorio/SQLite fue eliminado automáticamente. Los registros de
eventos sintéticos permanecen en el almacenamiento de auditoría Azure.

## Alcance

Esto demuestra que Azure aceptó, procesó y permitió reconciliar dos eventos
reales de Queue/Function disparados por el release ERP **local**. No es una
prueba originada por EC2, no demuestra una VNet/VPN privada AWS–Azure, y el
ledger es ficticio: no representa stock de una empresa ni un WMS externo. No se
modificaron recursos de infraestructura.

## Verificación de corte actual — 13/10/2026, 12:16 America/Chicago

Se volvió a ejecutar el smoke compensado contra Azure for Students. La
Function `tangama-wms-261008` estaba `Running`, HTTPS-only y procesó la venta y
su recepción por Queue/Function. El ERP del artefacto AWS ejecutado en un
proceso local reconcilió ambos resultados y comprobó el inventario en su línea
base exacta.

| Paso | Evento Azure | Resultado | Stock `SKU-ARROZ-001` |
|---|---|---|---:|
| Línea base leída | — | Ledger marcado como demo | 24 |
| Venta ERP → outbox → Queue/Function | `evt-200ef62e52bf4939a440797f152a9407` | `demo_fulfillment_completed`; ERP `completed_demo` | 23 |
| Recepción compensatoria ERP → outbox → Queue/Function | `evt-496021a8d93a41e18e05e7308ceb247f` | `demo_restock_completed`; ERP `received_demo` | 24 |

`LIVE_E2E=PASSED`; la SQLite temporal local terminó con el proceso y se
eliminó. Los dos registros de auditoría sintéticos permanecen en Azure. Esta
prueba no ejecutó el portal desde EC2, no movió inventario real y no demostró
red privada AWS–Azure.
