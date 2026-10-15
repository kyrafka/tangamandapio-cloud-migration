# E2E del release local del portal hacia Azure — 14/10/2026

> El E2E más reciente parte del portal AWS desplegado en EC2, no del artefacto
> local: venta `completed_demo` y recepción `received_demo`, dos eventos
> entregados, ledger sintético 10→10; revisar el [reporte sanitizado del
> 14:56–14:58](../aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json) y la
> [revalidación cloud](../CLOUD-REVALIDATION-2026-10-14.md).

## E2E + barreras de ingreso — 07:43–07:49 America/Chicago

La última corrida del arnés actualizado comprobó antes del flujo de negocio:
POST sin Function key → HTTP 401; POST con key pero `source` no autorizada →
HTTP 400; consulta posterior del ID rechazado → `pending` (no persistido). La
venta y recepción legítimas recorrieron el portal local/SQLite temporal →
Azure Queue/Function → reconciliación, y terminaron con el saldo demo en su
línea base. El conteo aproximado de poison fue cero antes y después; no se
leyeron ni cambiaron mensajes.

| Operación sintética | Event ID | Resultado |
|---|---|---|
| Venta demo de una unidad de `SKU-ARROZ-001` | `evt-4995d65fee6c4993a4638926c0ee12b5` | `demo_fulfillment_completed` |
| Reposición compensatoria | `evt-6dd2a06bb1c44178a458cb6ea0663ce0` | `demo_restock_completed` |

Application Insights registró durante la última hora seis solicitudes
`receive_fulfillment_event` HTTP 202, una validación de fuente rechazada HTTP
400 y seis ejecuciones `process_fulfillment_message` con `resultCode=0`, para
tres corridas E2E. La respuesta 401 de la plataforma de Functions fue verificada
por el arnés; las solicitudes bloqueadas en el gateway no necesariamente se
registran como invocaciones de la Function. El probe de seguridad no generó
Blob ni Queue. Los dos eventos del flujo exitoso permanecen en la auditoría
Azure. No se usó EC2/RDS ni se cambió infraestructura.

Los resultados agregados y no sensibles se conservan en
[`AZURE-INGRESS-E2E-2026-10-14.json`](AZURE-INGRESS-E2E-2026-10-14.json).

## Reejecución con guarda de poison — 07:29 America/Chicago

`tests/run_live_azure_erp_smoke.py` ejecutó `app/aws_release/current` como un
proceso local con SQLite temporal; no usó EC2 ni RDS. Azure comprobó el modo
`demo-inventory-ledger`, el SKU y el saldo inicial antes de admitir la prueba.
La cola poison reportó metadatos disponibles y conteo aproximado cero antes y
después; el test no leyó, reintentó ni borró mensajes.

| Operación sintética | Event ID | Resultado directo del E2E |
|---|---|---|
| Venta demo de una unidad de `SKU-ARROZ-001` | `evt-9129cedfd4e74c0885e075ec90c6a4d8` | `demo_fulfillment_completed` |
| Reposición compensatoria de una unidad | `evt-250d4f154557442da98dc11b44e670a1` | `demo_restock_completed` |

ERP reconcilió la venta y la recepción; el saldo final fue exactamente la
línea base capturada antes de la prueba. Los dos eventos sintéticos permanecen
en la auditoría Azure. No se cambió infraestructura ni se escribió en AWS/RDS.

Application Insights, mediante consultas agregadas sin payloads, mostró en la
última hora cuatro solicitudes `receive_fulfillment_event` con resultado HTTP
202 y cuatro ejecuciones `process_fulfillment_message` con `resultCode=0`. Las
marcas UTC del worker fueron `12:23:16.901`, `12:23:23.062`, `12:29:42.963` y
`12:29:50.470`; corresponden a las dos corridas E2E de esta sesión. Esto prueba
el procesamiento del ledger ficticio y la compensación, no inventario
comercial ni tráfico originado desde la instancia AWS.

## E2E compensatorio verificado en Azure — 05:30 America/Chicago

La suscripción `Azure for Students` sigue `Enabled`; la Function
`tangama-wms-261008` está `Running`, HTTPS-only y `/api/health` respondió 200.
El arnés opt-in ejecutó la revisión local v6 de `app/aws_release/current` (la
prueba ocurrió antes del ajuste de diagnóstico que elevó el candidato a v7) con
SQLite temporal, no desde EC2/RDS. La prueba confirmó primero que el SKU
pertenece al ledger `demo-inventory-ledger`, vendió una unidad y procesó la
recepción compensatoria; verificó el resultado de cada evento y el saldo final
igual a la línea base.

| Operación sintética | Event ID | Estado |
|---|---|---|
| Venta demo de 1 unidad de `SKU-ARROZ-001` | `evt-eb137585cfe94bb4a3bed1cf8bbbceaa` | `demo_fulfillment_completed` |
| Recepción compensatoria | `evt-3813f19061c9460489162699054f3cb3` | `demo_restock_completed` |

Application Insights, consultado después de la prueba y solo en forma agregada,
registró en la última hora 2 ejecuciones de `process_fulfillment_message` y 2
de `receive_fulfillment_event`, todas exitosas (0 fallidas). La ejecución más
reciente fue `2026-10-14T10:30:38Z` (05:30:38 local); también registró consultas
de estado e inventario demo. Después, la operación REST de metadatos de cola
informó conteo aproximado 0 tanto en `fulfillment-events` como en
`fulfillment-events-poison` (HTTP 200). Solo se consultaron encabezados de
propiedades; no se leyeron ni reintentaron mensajes. Esto confirma el
procesamiento sintético reciente en Azure, no un WMS comercial ni la solicitud
del portal AWS en producción. Referencia del conteo aproximado:
[Get Queue Metadata de Microsoft](https://learn.microsoft.com/en-us/rest/api/storageservices/get-queue-metadata).
Los dos eventos de prueba permanecen en la auditoría Azure; la base local y las
cuentas/socios temporales se eliminaron al finalizar. No hubo escrituras en
AWS ni RDS.

## E2E compensatorio más reciente — 04:25 America/Chicago

La Azure Function `tangama-wms-261008` estaba `Running`, HTTPS-only. Se
ejecutó el candidato local v6
(`20261014-public-diagnostics-hardening-v6-python312`) con SQLite temporal:

| Operación | Event ID | Estado |
|---|---|---|
| Venta demo de 1 unidad de `SKU-ARROZ-001` | `evt-ace184920d8e4921b4bcf265d4babbf6` | `demo_fulfillment_completed` |
| Recepción compensatoria | `evt-88e01b6734f2427da35d04b819460989` | `demo_restock_completed` |

ERP creó y despachó el evento de venta por el outbox, Azure Queue/Function lo
procesó y ERP reconcilió ambos documentos. El smoke leyó y guardó la línea base,
validó cada resultado y confirmó que el saldo final volvió exactamente al
valor inicial. No se tocó AWS, RDS ni una instancia EC2; los dos eventos
sintéticos permanecen en la auditoría Azure. Esto prueba la integración desde
el artefacto local, no tráfico originado en el portal productivo y no un WMS
comercial.

## Corroboración de telemetría — 04:37 America/Chicago

Una consulta agregada de Application Insights sobre las últimas 12 horas
encontró 2 ejecuciones de `process_fulfillment_message`: 2 exitosas y 0
fallidas. La última fue `2026-10-14T09:25:28Z` (04:25:28 local), coherente con
la venta y la recepción compensatoria anteriores. Solo se consultaron conteos y
hora; no se leyeron payloads ni se generó un evento nuevo. Esto corrobora la
ejecución de la Function, pero no convierte el ledger demo en inventario real.

## Reejecución compensatoria más reciente — 02:25 America/Chicago

La Function Azure (`Running`, HTTPS-only) volvió a procesar el flujo usando el
artefacto `app/aws_release/current` en un proceso local y SQLite temporal:

| Operación | Event ID | Estado |
|---|---|---|
| Venta demo de una unidad | `evt-94d171a6cda84a42bcff5bb5939d1bc7` | `demo_fulfillment_completed` |
| Recepción compensatoria | `evt-21077807ad594cb298a591c5ee062f81` | `demo_restock_completed` |

El script validó el resultado de ambas operaciones y que el saldo final volviera
al nivel inicial. El flujo ERP → outbox local → Azure HTTPS/Queue/Function →
reconciliación terminó `LIVE_E2E=PASSED`. Los dos eventos sintéticos quedan en
la auditoría Azure; las credenciales temporales, la base SQLite y los socios
demo se eliminaron con el proceso. No se tocó AWS, EC2 ni RDS; esta prueba no
equivale a una solicitud originada por el portal productivo en EC2.

## Reejecución E2E y estado final de colas — 01:35 America/Chicago

La prueba opt-in ejecutó de nuevo la venta y la recepción compensatoria con el
release AWS v5 en un proceso local y SQLite temporal. Azure aceptó y procesó
ambos eventos:

| Operación | Event ID | Estado |
|---|---|---|
| Venta demo de una unidad | `evt-ad76778256c64cb08ef437bf50ac389b` | `demo_fulfillment_completed` |
| Reposición compensatoria | `evt-16333bedb5724b4d999168a64884c8f0` | `demo_restock_completed` |

La prueba confirmó el saldo final del SKU `SKU-ARROZ-001` igual a su línea base
(24 unidades). La lectura posterior confirmó `mode=demo-inventory-ledger`,
`is_real_erp=false` y la cola poison en estado `ok`, conteo aproximado 0, sin
exponer payloads. El ledger fue modificado transitoriamente y restaurado; los
dos registros sintéticos permanecen en la auditoría de Azure. No se tocaron
RDS, instancias AWS ni configuración de infraestructura.

## Resultado

`tests/run_live_azure_erp_smoke.py` terminó `LIVE_E2E=PASSED` contra la
suscripción Azure for Students habilitada y la Function
`tangama-wms-261008` (`Running`, HTTPS-only). El proceso cargó el código local
del release `20261014-erp-admin-security-v5-python312` y usó una SQLite
temporal; **no ejecutó el proceso sobre EC2 ni escribió pedidos en RDS**.

| Paso | Event ID | Resultado |
|---|---|---|
| Venta demo de una unidad | `evt-382635e483a345c38ce960ba923d8b78` | `demo_fulfillment_completed`; Azure Queue/Function descontó una unidad del ledger ficticio y ERP reconcilió la venta. |
| Recepción compensatoria | `evt-eb49f18bc9cd40bc86f073ae59c81b08` | `demo_restock_completed`; ERP reconcilió la compra y la prueba verificó el saldo final igual al inicial. |

El test valida primero que el inventario se identifique explícitamente como
demo. La SQLite, el usuario temporal y sus credenciales vivieron solo durante
la ejecución y se eliminaron al terminar. Azure conserva los dos eventos
sintéticos en su almacenamiento de auditoría. No se reporta un conteo de cola
poison como parte de esta prueba.

## Alcance

Esto prueba ERP local (código del release v5) → outbox → HTTPS → Queue/Function
→ reconciliación y compensación en el ledger ficticio Azure. No prueba el
recorrido desde una sesión de usuario en la EC2 productiva, conectividad privada
AWS–Azure ni inventario de un WMS comercial.

## Paquete actualizado y E2E posterior al despliegue — 14/10/2026

El plan anterior coincidía con el ZIP publicado `6eea3b6a…82065`; el artefacto
actual local era distinto. Terraform aplicó exclusivamente la publicación del
ZIP `azure_function_package-ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27.zip`
(SHA-256 `ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27`).
El plan hizo 1 creación (nuevo blob inmutable), 1 actualización in-place de la
Function y 1 eliminación del blob anterior; no modificó colas, ledger, red,
roles, alertas ni grupo de recursos. El ZIP anterior se conserva localmente para
recuperación. El plan posterior de Terraform terminó `No changes`.
El archivo `rebuild.tfvars.example` quedó alineado a ese ZIP; un plan posterior
sin overrides volvió a resultar `No changes`.

Después del reinicio, el test opt-in confirmó suscripción Enabled, Function
`Running` y HTTPS-only; validó 401 sin Function key y 400 para un productor no
autorizado sin persistir ese evento. La venta y recepción compensatoria llegaron
a Queue/Function y reconciliaron el ledger demo. El saldo volvió al inicial; el
test terminó `LIVE_E2E=PASSED`. Event IDs: venta
`evt-224ba08b1aee4acca74c0e21eb23d2f1`, compensación
`evt-e0af71d4e5e1448c9d58df6959b3928b`. Los eventos sintéticos quedan en la
auditoría Azure.

El productor en esta corrida fue el proceso **local** `app/aws_release/current`
con SQLite temporal, no las EC2 ni RDS. En una comprobación separada el login
admin de AWS respondió 200, pero el portal forzó cambio de contraseña con HTTP
428 en la lectura protegida del inventario. La prueba productiva AWS→Azure se
detuvo antes de crear socio, pedido o evento; requiere completar el cambio de
contraseña y repetirla. El ledger sigue siendo demo, no WMS comercial.

## Smoke de transporte iniciado desde EC2 — 14/10/2026, 09:38 America/Chicago

Una instancia EC2 `Online` en SSM consultó Azure desde su configuración de
productor, sin exponer la Function key. `/api/inventory` respondió 200 y
devolvió `SKU-ARROZ-001=24` en modo `demo-inventory-ledger`. Luego se envió el
evento sintético sin artículos
`qa-ec2-bfbd32f277174229bfc6a9bbb7ccbbf2`; Azure contestó 202 y la Function
terminó en `awaiting_items`. La lectura posterior volvió a mostrar 24. No se
registró una venta en el portal ni se escribió en RDS, y no hubo cambio de
stock. El evento se conserva en la auditoría Azure.

La prueba confirma solo transporte y procesamiento de un evento incompleto
desde EC2 por HTTPS público. No reemplaza el E2E de venta autenticada portal →
RDS/outbox → Azure; ese flujo sigue pendiente del cambio obligatorio de
contraseña admin (HTTP 428). Tampoco prueba VPN privada ni inventario de un WMS
comercial.

## E2E desde el portal AWS con dataset sintético — 14/10/2026, 10:18 America/Chicago

El cambio de contraseña admin y el bloqueo previo HTTP 428 ya están resueltos;
la nota anterior describe el intento de las 09:38 y queda superada por esta
prueba posterior. Desde el portal productivo (PostgreSQL/RDS) se registraron
tres ventas QA para distribuidores ficticios: arroz ×2, azúcar ×2 y aceite ×1.
Las referencias `VTA-20261014-56B41E`, `VTA-20261014-3A9EE2` y
`VTA-20261014-6E5D21` llegaron a Azure y reconciliaron como `completed_demo`.
Una recepción de compra sintética `OC-20261014-012D70` procesó arroz ×2,
azúcar ×2 y aceite ×1 como `received_demo`.

La consulta final confirmó los eventos entregados y saldos sin cambio neto:
aceite 18, arroz 24 y azúcar 40, iguales a los valores iniciales. La venta y
recepción integran un ciclo de datos sintéticos para probar ventas, compras y
reconciliación; no hay inventario físico que compensar. Esto valida la ruta de
integración y el ledger sintético Azure; no representa WMS comercial, inventario
de terceros ni una conexión privada entre nubes.

## Revalidación posterior del paquete Azure — 14/10/2026, 11:58 America/Chicago

Terraform aplicó el paquete Function de catálogo sintético
`364cf88c934a236eb72ef929f96faabc4ea4cbd08844d7cae8ab286dbc379d1d`; el plan
posterior quedó `No changes`. Health devolvió 200 y una actualización viva de
metadatos de un SKU existente conservó exactamente su `on_hand`. Se repitió el
smoke de venta/recepción sintética por Queue/Function y el ledger regresó a su
saldo de línea base. Esa nueva prueba volvió a usar el paquete local con SQLite
como productor, no la ruta portal AWS v10 → RDS/outbox → Azure.

## E2E del portal AWS v10 tras el release — 14/10/2026, 12:09 America/Chicago

Se completó después la prueba que faltaba desde una EC2 v10 vía SSM. La cuenta
QA admin inició sesión en el portal desplegado; una importación autenticada creó
el SKU sintético aislado `SKU-QA-V10-20261014` con saldo inicial 10. La venta de
una unidad llegó a Azure y se concilió como `completed_demo`; la recepción
compensatoria llegó y se concilió como `received_demo`. Ambos outbox quedaron
`delivered` y el ledger terminó con 10 unidades, igual a la línea base. La
contraseña se leyó en memoria desde SSM dentro de AWS y no atravesó el ALB HTTP
público. Esta corrida sí cubre portal AWS v10 → base de datos/outbox → Azure;
queda pendiente importar el archivo CSV usando la interfaz del navegador.

## Segunda repetición y microcarga — 14/10/2026, 12:16 America/Chicago

El E2E anterior se repitió desde el portal AWS v10: el SKU aislado volvió a
10→10, venta y recepción se conciliaron correctamente y ambos eventos quedaron
entregados. El productor generó después 24 lecturas autenticadas de pedidos,
compras y outbox (concurrencia 6, 24/24 HTTP 200, p95 304.09 ms) en una única
EC2; estas consultas no generaron escrituras adicionales ni pasaron por el ALB.
La cifra no demuestra una capacidad de 3,000 sesiones ni escalado multinodo.

## E2E Azure compensado — 14/10/2026, 12:30–12:32 America/Chicago

`tests/run_live_azure_erp_smoke.py` verificó la cuenta Azure for Students
habilitada y la Function `Running`/HTTPS-only. El ingreso sin clave dio 401;
un productor no autorizado dio 400 y no generó evento. La cola poison tenía
conteo aproximado cero antes y después; solo se consultó metadata, nunca sus
mensajes.

El productor fue la aplicación local del release AWS con SQLite temporal, no
una instancia AWS. La venta sintética `evt-685412ec9a284bae89d80a07249ec903`
terminó `demo_fulfillment_completed`; la recepción compensatoria
`evt-a17b3eeba08743b3981f88550b48011f` terminó
`demo_restock_completed`. El ledger acabó exactamente en su saldo de línea
base, ambos outbox se marcaron `delivered` al primer intento y los dos eventos
permanecen en la auditoría Azure. No se imprimió la Function key, no hubo
cambios IaC y no se tocó AWS. `LIVE_E2E=PASSED`.

La suite unitaria local del harness (`tests/test_live_azure_erp_smoke.py`) se
repitió después del smoke y pasó 17/17; prueba guardas y manejo de fallos, no
sustituye la ejecución viva descrita arriba.
