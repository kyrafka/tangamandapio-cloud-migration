# Azure Monitor: telemetría de invocaciones — 15/10/2026

## Observación viva

- Function App `tangama-wms-261008`, grupo `rg-tangamandapio-rebuild-wus`:
  `Running`, `httpsOnly=true`.
- `GET https://tangama-wms-261008.azurewebsites.net/api/health`: HTTP 200,
  `{"status":"ok","service":"tangamandapio-wms"}`.
- Azure Application Insights, consulta ejecutada desde Azure CLI, sobre la tabla
  `requests` en la ventana `ago(24h)`: 17 solicitudes y 0 fallidas.
- Desglose de esa misma consulta: `demo_inventory` 6, `fulfillment_status` 3,
  `health` 3, `process_fulfillment_message` 2,
  `receive_fulfillment_event` 2 y `update_demo_catalog` 1; todas con cero
  fallos.

Consulta Kusto:

```kusto
let recent = requests | where timestamp > ago(24h);
union
  (recent | summarize requests=count(), failures=countif(success == false) by name),
  (recent | summarize requests=count(), failures=countif(success == false) | extend name='TOTAL')
| project name, requests, failures
| order by name asc
```

La respuesta estructurada del comando reportó `TOTAL = 17`, `failures = 0`; el
trigger `process_fulfillment_message` tuvo dos entradas exitosas y el endpoint
`receive_fulfillment_event` dos. Esto complementa, pero no reemplaza, el E2E
AWS→Azure de v11 registrado en
[`AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json`](../aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json).

## Alcance y límites

La consulta fue agregada y no expuso cuerpos, claves, identificadores de
clientes ni datos personales. Los contadores de telemetría no prueban por sí
solos una correspondencia uno-a-uno entre cada invocación y un pedido; para eso
se conserva la prueba E2E correlacionada. No se disparó ni se envió una alerta,
no se leyó el contenido de la cola poison y no se modificó Azure ni su state de
Terraform durante esta revisión.
