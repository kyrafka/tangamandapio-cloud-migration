# Smoke vivo ERP local → Azure WMS — 2026-10-16 01:47 UTC

## Resultado

`tests/run_live_azure_erp_smoke.py` terminó con `LIVE_E2E=PASSED`. La
suscripción `Azure for Students` figura `Enabled`; `tangama-wms-261008` está
`Running` y configurada para HTTPS-only.

La prueba ejecutó el artefacto actual `app/aws_release/current` en un proceso
local, con registros ERP temporales en SQLite. No atravesó el ALB ni usó una
instancia AWS.

## Flujo y controles verificados

- Sin clave de Function, el ingreso responde HTTP 401.
- Con clave pero origen no autorizado, responde HTTP 400 y no persiste el
  evento.
- Una venta sintética entró por el outbox, llegó a Azure Queue/Function y fue
  reconciliada como `demo_fulfillment_completed` (un SKU ficticio).
- La compra de compensación terminó como `demo_restock_completed`; el ledger
  ficticio volvió al saldo inicial.
- Los dos eventos sintéticos quedaron en el almacenamiento de auditoría de
  Azure, según el comportamiento esperado del servicio.

| Operación | Event ID | Resultado |
|---|---|---|
| Venta | `evt-a36d104709094d0381383afa158b134f` | `demo_fulfillment_completed` |
| Reposición compensatoria | `evt-320487ed540246e98736c8ddc3be34aa` | `demo_restock_completed` |

## Alcance y estado al momento de la prueba

Esto acredita el recorrido local→Azure, guards de ingreso y conciliación del
ledger sintético; no acredita stock real ni el recorrido desde EC2. A las
01:47 UTC AWS ALB devolvía 503 y no se pudo ejecutar el E2E desde el portal
publicado. Ese estado fue transitorio: la matriz registra que el servicio se
recuperó a las 02:10 UTC y la
[revalidación posterior](../aws/AWS-REVALIDACION-HTTPS-2026-10-16-0228UTC.md)
confirmó 2/2 destinos sanos y un smoke Admin de solo lectura directo al ALB.
