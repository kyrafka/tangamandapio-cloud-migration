# Revalidación AWS–Azure — 16/10/2026, 08:18–08:30 UTC

## Estado operativo

- AWS Academy STS autenticó en la cuenta del proyecto. El stack
  `tangamandapio-live-20261013` continúa `UPDATE_COMPLETE`; una detección nueva
  terminó `IN_SYNC`, con 0 recursos desviados.
- El parámetro vivo `ApplicationArtifactRevision` es v18 y su SHA-256 es
  `c629ab0e7b07c007cfa74c3eca1b9879c601829f44ad3471615cb85e3e09197f`.
  El template almacenado por CloudFormation aún conserva defaults v16, mientras
  la fuente local define defaults v18. Un change set sin parámetros propuestos
  habría sustituido valores vigentes con defaults y mostró 13 cambios; se borró
  sin ejecutarlo. El segundo change set preservó los 27 parámetros con
  `UsePreviousValue` y no encontró cambios efectivos; también se eliminó. El
  artefacto y recursos activos no se modificaron; la diferencia de defaults del
  template remoto queda para el próximo cambio real. El script
  `iac/cloudformation/deploy.sh` preserva los parámetros actuales.
- Tras una prueba temporal de capacidad ASG 2→3, se restauraron `min=2`,
  `desired=2`, `max=5`. El grupo quedó con dos instancias `InService/Healthy` y
  el ALB con dos targets `healthy`. Los dos volúmenes raíz están cifrados. El
  tercer nodo pasó el health check del ALB antes de volver a 2; dos nodos
  anteriores quedaron drenando durante su retiro. El portal HTTPS devolvió
  200 y HTTP redirigió con 301. HSTS respondió `max-age=31536000;
  includeSubDomains`.
- La actualización manual 2→3 confirma el arranque/registro de capacidad, pero
  **no** es una prueba de autoscaling activado por carga ni acredita capacidad
  para 3,000 usuarios.
- RDS está `available`, privada y cifrada. Sigue Single-AZ y con un día de
  retención de backups. No se alteró para evitar un cambio de costo/HA sin una
  revisión separada.
- No hay Web ACL regional de AWS. La alarma de escala-baja está `ALARM` porque
  CPU (~1%) está debajo del umbral; el ASG conserva su mínimo 2. La alarma de
  5xx figura `OK` sin puntos de error y configura faltantes como
  `notBreaching`. La métrica independiente `RequestCount` sí registró 291
  solicitudes en 12 periodos de cinco minutos durante la última hora. Se
  conserva `notBreaching`, apropiado para una métrica de error dispersa; la
  ausencia de puntos 5xx por sí sola no reemplaza una prueba de disponibilidad.
  Véase [missing data en CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html)
  y [métricas del ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html).

## Pruebas funcionales vivas

- El primer E2E contra el FQDN público fue rechazado con HTTP 403 de Cloudflare
  al intentar el login. La propia prueba reportó `compensation=not_needed`; no
  se crearon pedidos. No se relajó ninguna regla de Cloudflare.
- La repetición aprobada contra el origen ALB por HTTPS mantuvo validación TLS,
  hostname y SNI. Resultado `LIVE_E2E_PASSED`: importación de catálogo sintético,
  venta `completed_demo`, recepción `received_demo`, dos eventos entregados,
  saldo del ledger ficticio igual al inicial (10→10), matriz API Comercial y
  Operaciones 200/403 esperada, y 24/24 lecturas Admin HTTP 200 (concurrencia
  6, p95 216.48 ms).
- El smoke `admin-modules` pasó: Finanzas sintética S/ 0.05 `paid`, mensaje
  interno `portal_only` enviado y leído, y poison queue con 0 mensajes; el
  endpoint no expuso payloads.
- El smoke `admin-readonly` pasó por ALB HTTPS: 59/59 eventos del outbox
  conciliados, 0 pendientes, 24/24 lecturas HTTP 200 (concurrencia 6,
  p95 205.03 ms), y permisos de Comercial/Operaciones 200/403 esperados. Las
  dos suscripciones SNS están confirmadas; esta ejecución no disparó alarmas.
- Application Insights, ventana móvil de 30 minutos: cuatro ejecuciones
  `process_fulfillment_message` sin fallas observadas (p95 327.06 ms), cuatro
  recepciones del evento sin fallas y cero fallas en las otras rutas consultadas.
  La consulta entrega agregados y no prueba duración sostenida.
- Azure for Students continúa `Enabled`; Function `tangama-wms-261008` está
  `Running`, HTTPS-only y `/api/health` respondió 200. Las alertas de Function
  5xx y latencia están habilitadas.
- Terraform Azure `plan -refresh-only` consultó ARM con los tfvars esperados y
  terminó `No changes`; no se hizo `apply`.
- La puerta local completa aprobó 222 pruebas Python, 14 pruebas Node, build
  Vite, auditoría de dependencias y validación CloudFormation. La puerta
  adicional `-ValidateTerraform` también aprobó: `fmt`, `init`, `validate` en
  las raíces configuradas y cinco pruebas mock de VPN/red privada; no aplicó
  recursos.

## Brechas que permanecen

La entrega automatizada normal AWS→Azure está probada, pero no se indujo una
falla transitiva viva para medir el reintento automático; la política de
backoff/recuperación sí tiene pruebas unitarias locales. Sigue pendiente una
revisión visual autenticada en navegador de todas las vistas y el importador
CSV interactivo. No se hizo una llamada WebRTC bidireccional con dos navegadores
reales. La conectividad entre nubes sigue siendo por HTTPS público: AWS Academy
denegó `CreateCustomerGateway` mediante SCP y Azure no tiene una VNet conectada.
Tampoco hay WAF regional, failover RDS Multi-AZ, prueba transaccional sostenida,
prueba de 3,000 usuarios ni atribución completa de costos Azure. El ledger WMS
es sintético y funcional para el caso académico; no representa inventario
físico.

No se copiaron tokens, claves ni contraseñas a este registro. No hubo cambios
de código ni despliegue IaC; la única mutación de recursos fue la prueba
temporal de capacidad del ASG, restaurada a 2/2. Los change sets se eliminaron
sin ejecutar.
