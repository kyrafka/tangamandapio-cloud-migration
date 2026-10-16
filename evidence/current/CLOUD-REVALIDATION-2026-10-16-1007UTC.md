# Revalidación AWS–Azure — 16/10/2026, 09:59–10:07 UTC

## Reintento duplicado AWS → Azure

- AWS STS aceptó la sesión de AWS Academy (cuenta `841113066612`). La pila
  `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; hay dos instancias SSM
  `Online` y los dos destinos del ALB están `healthy`.
- Se ejecutó desde EC2 un replay autenticado del evento sintético
  `evt-3bd54a16682041ff82c7afa68bf4e1fe`, que ya había completado una
  reposición demo. La API respondió `queued_duplicate`; el outbox conservó
  `delivered` y el contador de intentos avanzó de 1 a 2.
- El endpoint de inventario confirmó antes y después el modo
  `demo-inventory-ledger` y los mismos saldos. La consulta de Application
  Insights correlacionó el evento a las 09:59:58–09:59:59 UTC con
  `duplicate=True` y `wms_demo_already_processed`, manteniendo
  `demo_restock_completed`. El consumidor no aplicó el movimiento una segunda
  vez.
- El test de reenvío tiene dos pruebas unitarias: aceptación idempotente y fallo
  cerrado ante cualquier cambio inesperado de stock. El archivo de pruebas de
  smoke pasó 36 pruebas; el parser de PowerShell aprobó.

## Disponibilidad y calidad local

- `https://tangamandapio.kendellnm.me/` respondió HTTP 200 con verificación TLS
  correcta; HTTP redirigió con 301 a HTTPS.
- La Azure Function `tangama-wms-261008` está `Running`, en la suscripción
  `Azure for Students`; `https://tangama-wms-261008.azurewebsites.net/api/health`
  respondió 200 con TLS válido.
- La puerta local integral terminó `QUALITY_GATE=APROBADA`: 230 pruebas
  Python, 14 Node y 40 transacciones aisladas; build Vite, auditorías de
  dependencias, CloudFormation y validaciones/tests Terraform pasaron. No
  ejecutó `apply` ni cambió infraestructura.

## Alcance que sigue pendiente

La duplicación idempotente pasó, pero no se indujo un fallo transitorio real del
servicio para medir reintento automático/backoff y recuperación. Tampoco se
probó WebRTC entre dos navegadores, una carga transaccional de 3,000 usuarios,
failover Multi-AZ ni WAF. La red privada AWS–Azure continúa bloqueada por la
política SCP del laboratorio; el ledger WMS sigue siendo ficticio por alcance
académico. No se reinició ni se des-cifró ningún disco o instancia.
