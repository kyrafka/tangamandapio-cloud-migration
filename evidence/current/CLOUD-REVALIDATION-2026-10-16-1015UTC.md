# Revalidación AWS–Azure — 16/10/2026, 10:06–10:15 UTC

## AWS

- AWS STS acepta el perfil local. La pila CloudFormation
  `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; una detección fresca
  terminó `IN_SYNC`, cero recursos divergentes. Las dos instancias SSM están
  `Online` y los dos destinos ALB `healthy`.
- RDS `tangamandapio-postgres`: `available`, cifrada, privada, Single-AZ y
  retención de backup de un día. Los dos volúmenes EBS raíz activos reportan
  cifrado. No se modificó ni reinició infraestructura.
- El portal HTTPS respondió 200 con TLS validado y HTTP redirigió a HTTPS con
  301.
- En el replay del evento `evt-3bd54a16682041ff82c7afa68bf4e1fe`, Azure
  Application Insights guardó `duplicate=True` y
  `wms_demo_already_processed`; el outbox permaneció `delivered`, incrementó
  intentos 1→2 y el saldo de ledger demo no cambió.

## Azure y recorrido de negocio

- `tangama-wms-261008` está `Running`, en la suscripción
  `Azure for Students`, con HTTPS-only; su health HTTPS/TLS respondió 200.
- El smoke Azure independiente usó el artefacto ERP local con una base SQLite
  temporal (no la instancia EC2 ni RDS): sondas sin clave/no autorizadas dieron
  401/400 y no persistieron el evento rechazado; una venta y su recepción
  sintéticas concluyeron `demo_fulfillment_completed` y
  `demo_restock_completed`, con saldo restaurado al nivel inicial y poison
  queue vacía antes/después.
- Application Insights correlacionó los eventos sintéticos
  `evt-2c4fc7577acf4e5cab91c477293233b8` y
  `evt-0884593500de4c41a540be2fe5985c99` con resultados escritos por el
  consumidor a las 10:14:30 y 10:14:36 UTC respectivamente.
- Terraform Azure: plan normal y `refresh-only` indicaron `No changes` con
  salida 0; no se guardó/aplicó un plan.

## QA y límites

- Smoke idempotente nuevo: 36 pruebas unitarias del archivo, incluyendo no
  mutación del ledger; PowerShell parseado correctamente. Puerta integral
  posterior: `QUALITY_GATE=APROBADA`, 230 Python, 14 Node y 40 transacciones
  aisladas; build, auditorías, CloudFormation y Terraform aprobados.
- La prueba directa del portal local a Azure no se cuenta como el flujo
  desplegado AWS→Azure. El replay idempotente sí se inició desde una EC2 por
  SSM; el E2E compensado AWS→RDS/outbox→Azure ya estaba registrado en el corte
  anterior.
- Aún sin evidencia de indisponibilidad transitoria real/backoff, WebRTC
  bidireccional, importación CSV visual, carga transaccional de 3,000 usuarios,
  failover Multi-AZ o WAF. VPN AWS–Azure sigue bloqueada por SCP. El stock es un
  ledger de demostración, no existencias físicas.
