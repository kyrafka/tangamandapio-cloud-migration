# Revalidación Azure Function y Application Insights — 16/10/2026, 01:24 UTC

## Resultado

La Function `tangama-wms-261008` estaba `Running` y HTTPS-only durante el
smoke vivo de las 01:20 UTC. `/api/health` respondió HTTP 200. El flujo
sintético local recorrió ERP→outbox→Azure Queue/Function y devolvió al baseline
el ledger demo con una venta y una recepción compensatoria; las barreras de
ingreso respondieron 401 sin clave y 400 para productor no autorizado. La
prueba no se originó desde EC2. El detalle y los IDs de evento están en
[`AZURE-ERP-E2E-2026-10-13.md`](AZURE-ERP-E2E-2026-10-13.md).

Una consulta sin payloads a Application Insights, limitada a los últimos diez
minutos y ejecutada a las 01:24 UTC, devolvió:

| Solicitud/función | Código | Cantidad | Fallidas |
|---|---:|---:|---:|
| `receive_fulfillment_event` | 202 | 2 | 0 |
| `process_fulfillment_message` | 0 | 2 | 0 |
| `receive_fulfillment_event` — guarda de fuente inválida | 400 | 1 | 0 |
| `health` | 200 | 2 | 0 |
| `demo_inventory` | 200 | 4 | 0 |
| `fulfillment_status` | 200 | 8 | 0 |
| `poison_queue_status` | 200 | 2 | 0 |

Los dos `202` y dos workers sin fallo coinciden temporalmente con la corrida; el
smoke comprobó por separado los estados y la compensación de sus dos IDs. La
consulta agregada no demuestra por sí sola una unión de cada fila de telemetría
con cada evento. El count de poison fue cero antes y después, consultando solo
metadatos, sin leer ni borrar mensajes.

Consulta Kusto ejecutada:

```kusto
requests
| where timestamp > ago(10m)
| summarize requests=count(), failures=countif(success == false) by name, resultCode
| order by name asc
```

## Alertas métricas — lectura de configuración a las 01:25 UTC

Las reglas `tangama-wms-fn-5xx` (severity 2) y
`tangama-wms-fn-latency` (severity 3) permanecían habilitadas y cada una
apuntaba a un Action Group. `tangama-ops-ag` estaba habilitado y tenía dos
receptores de correo (no se imprimieron ni copiaron las direcciones). No se
disparó una alerta nueva; el usuario había confirmado previamente la entrega de
alerta y recuperación.

Esta evidencia acredita la ejecución del worker y el ledger **sintético** de
Azure. No acredita la salud del portal AWS, tráfico originado en EC2, ruta
privada AWS–Azure, inventario físico ni entrega de alertas en esta corrida.
