# Revalidación AWS–Azure — 16/10/2026, 09:34–09:56 UTC

## Estado actual verificado

- AWS STS acepta la sesión del laboratorio. CloudFormation
  `tangamandapio-live-20261013` sigue `UPDATE_COMPLETE`; detección de drift
  iniciada en este corte terminó `IN_SYNC`, 0 recursos divergentes.
- El portal responde por HTTPS/TLS con HTTP 200; HTTP redirige a HTTPS. El
  ASG mantiene 2/2 EC2 `InService`/`Healthy` y el target group 2/2 `healthy`.
  Los volúmenes raíz EBS están cifrados.
- RDS está `available`, privada y cifrada; continúa Single-AZ con retención de
  backup de un día. PT-DR-01 de este mismo día restauró marcador y conteos
  correctamente (RTO 258 s; límite superior observado de RPO 8 s); no equivale
  a probar failover Multi-AZ.
- La Azure Function sigue `Running`, `httpsOnly=true`; health HTTPS/TLS devuelve
  200. Application Insights registró en este corte dos invocaciones exitosas de
  `process_fulfillment_message`, con `DequeueCount: 1`: venta
  `demo_fulfillment_completed` y reposición `demo_restock_completed`. Las dos
  reglas de alertas Azure (5xx y latencia) están habilitadas.
- No se encontró ningún recurso VNet de Azure en la suscripción. El dry-run de
  `CreateCustomerGateway` AWS fue denegado por política del laboratorio. No se
  crearon gateways ni conexiones VPN. No sortear la SCP.
- Terraform Azure (`azure-rebuild`) volvió a consultar ARM: plan normal y
  `refresh-only` terminaron `No changes` (código 0, sin `apply`). El plan usó
  el archivo local protegido de receptores; ningún valor de receptor se registró
  en la evidencia.

## Pruebas funcionales y de rendimiento

- E2E en instancia administrada por SSM: venta `completed_demo`, compra
  `received_demo`, dos eventos entregados a Azure y saldo sintético
  `SKU-QA-V10-20261014` restaurado de 10 a 10.
- Tras esos cambios, Admin read-only por ALB con certificado HTTPS validado
  reconcilió 63/63 eventos entregados, cero pendientes, 2/2 suscripciones SNS
  confirmadas y 24/24 lecturas HTTP 200 (p95 618 ms). Comercial y Operaciones
  mantuvieron los 200/403 esperados.
- Matriz ERP en vivo: 48 sondas de seis perfiles (Admin, Ventas, Finanzas,
  Compras, Datos Maestros y Auditoría) pasaron. Las cuatro cuentas temporales
  quedaron desactivadas; las escrituras inválidas autorizadas pararon en 400 y
  las no autorizadas en 403.
- Módulos vivos: gasto sintético de S/ 0.05 liquidado en el ledger demo; correo
  enviado y leído solo en la bandeja interna, sin SMTP; cola poison con conteo
  aproximado 0 y sin exponer payloads.
- PT-PERF-01 directa al origen ALB, conservando Host/SNI y verificación de
  certificado TLS: 100 solicitudes/10 concurrentes, 100 HTTP 200, p95 490 ms;
  y 500 solicitudes/20 concurrentes, 500 HTTP 200, p95 467 ms. No representa
  carga transaccional ni capacidad probada para 3,000 usuarios. Evidencias:
  [`AWS-PERF-HTTPS-ORIGIN-2026-10-16.json`](aws/AWS-PERF-HTTPS-ORIGIN-2026-10-16.json)
  y [`AWS-PERF-HTTPS-ORIGIN-500-2026-10-16.json`](aws/AWS-PERF-HTTPS-ORIGIN-500-2026-10-16.json).
- Se añadió a `tests/performance/load_test.py` el modo `--connect-to`, que
  llega al origen evitando el proxy Cloudflare sin desactivar verificación TLS.
  Sus cinco pruebas unitarias pasaron.
- `tests/run_local_quality.ps1 -ValidateTerraform` terminó
  `QUALITY_GATE=APROBADA`: 228 pruebas Python, 14 Node, 40 transacciones
  aisladas, build, auditorías sin vulnerabilidades conocidas, CloudFormation y
  Terraform validados; sin `apply` ni operaciones cloud en esa puerta.

## Límites y pendientes

- Una solicitud automatizada de login a través del proxy público Cloudflare
  recibió 403; la misma comprobación de solo lectura pasó conectando al ALB con
  HTTPS/TLS validado. No se desactivó ni eludió protección del proxy.
- No se completó inspección visual autenticada/CSV en Chrome: el control de
  navegador se detuvo porque no pudo verificar la URL actual con confianza.
- WebRTC entre dos navegadores y su audio/video bidireccional siguen pendientes.
- No se indujo una falla transitoria real para observar el retry automático;
  tampoco se probó escalado 2→3 ni concurrencia de 3,000 usuarios.
- AWS–Azure no tiene red privada. WAF sigue apagado (`EnableWaf=false`); RDS no
  es Multi-AZ y conserva solo un día de backups.
- El recorrido WMS procesa un ledger de inventario sintético, no existencias
  físicas. El gasto/mail de QA, la venta y la compra creados por los tests quedan
  como registros sintéticos auditables; el saldo ficticio sí quedó compensado.
- El gate local no desplegó código; el único cambio de nube previo fue la
  reconciliación in-place de descripción de alarma descrita en la evidencia
  09:26 UTC. El medidor de carga y sus pruebas quedan pendientes de commit/push.
