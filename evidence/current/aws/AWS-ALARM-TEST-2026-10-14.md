# Prueba sintética de alarma — 14/10/2026, 00:58 America/Chicago

## Ejecución

Se ejecutó `tests/aws/pt-mon-01-alarm.sh` contra el stack
`tangamandapio-live-20261013`, con opt-in explícito. El test identificó
`tangamandapio-high-cpu`, guardó el estado original (`OK`), pidió el cambio
temporal a `ALARM`, confirmó el estado y restauró el original automáticamente.

CloudWatch registra:

| Hora | Transición/acción | Resultado |
|---|---|---|
| 00:58:02.266 | `OK → ALARM` | Estado sintético aceptado |
| 00:58:02.324 | Acción de alarma | SNS ejecutada correctamente |
| 00:58:04.723 | `ALARM → OK` | Estado original restaurado |
| 00:58:04.753 | Acción de recuperación | SNS ejecutada correctamente |

La alarma volvió a `OK`; conserva acciones habilitadas y una acción SNS para
cada transición. SNS muestra dos suscripciones `email`, ambas confirmadas; no
se incluyen las direcciones en esta evidencia.

## Qué demuestra y qué no

Demuestra que CloudWatch acepta la transición controlada y envía las dos
acciones al tema SNS, y que el script restaura el estado previo. El usuario
confirmó posteriormente que recibió ambos avisos: alarma y recuperación. Esta
confirmación queda registrada como reporte del destinatario, no como captura ni
telemetría independiente del proveedor. En la consulta inicial, las métricas
SNS `NumberOfNotificationsDelivered` y `NumberOfNotificationsFailed` no
devolvieron datapoints en la ventana de la prueba.

La prueba no simula CPU real ni acredita una alarma disparada por carga real;
solo prueba el ciclo sintético y la recepción reportada de sus dos correos.

No se cambió la definición/configuración de la alarma ni se desplegó
infraestructura. La prueba es temporal y sintética, no un incidente productivo.
