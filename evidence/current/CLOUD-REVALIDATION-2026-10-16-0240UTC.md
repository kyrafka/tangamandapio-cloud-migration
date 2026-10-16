# Revalidación AWS, Azure y módulos Admin — 16/10/2026, 02:31–02:40 UTC

## Pruebas funcionales vivas

- AWS STS autenticó la sesión nueva de Academy. CloudFormation sigue
  `UPDATE_COMPLETE`; el portal público HTTPS respondió 200 en `/`, `/health` y
  `/ready`; HTTP redirige a HTTPS. ASG y target group: 2/2 destinos saludables.
- El smoke `full` desde EC2, con acceso HTTPS directo al ALB y validación normal
  del certificado, terminó `LIVE_E2E_PASSED`. El portal consultó RDS y entregó
  venta y recepción sintéticas a Azure; estados `completed_demo` y
  `received_demo`, ledger ficticio de 10 a 10 y dos eventos entregados. Roles
  API Comercial/Operaciones dieron los 200/403 esperados. Importación sintética
  pasó; 24 lecturas autenticadas dieron 200, concurrencia 6, p95 399.77 ms.
- El smoke `admin-modules` terminó `LIVE_ADMIN_MODULE_SMOKE_PASSED`: cuenta por
  pagar sintética de S/ 0.05 marcada `paid` en el ledger del portal (sin
  transferencia bancaria); mensaje privado al buzón Comercial en modo
  `portal_only`, recibido y marcado leído; SMTP externo no estaba configurado
  y no se envió correo fuera del portal. La cola poison reportó cero aproximado
  y no expuso payloads.

Las dos pruebas crearon documentos/eventos sintéticos persistentes de QA en el
portal/RDS y en la auditoría Azure; la venta se compensó. No se alteró inventario
físico ni se hicieron pagos reales.

## Azure y telemetría

- `Azure for Students`: `Enabled`. Function `tangama-wms-261008`:
  `Running`, HTTPS-only; `/api/health` respondió 200.
- Application Insights `tangama-wms-ai`, retención 30 días, enlazado al
  workspace `tangama-ops-law`. Consulta agregada de la última hora: 94 registros
  de requests, con códigos observados 200, 202, 400 y 0; el 400 coincide con
  la guarda negativa esperada del smoke. Una consulta de traces encontró 312
  trazas, 19 cuyo mensaje menciona `process_fulfillment_message` y cero con
  severidad de error. Conteos de traces no se presentan como invocaciones.
- El grupo de acciones `tangama-ops-ag` está habilitado y ambas alertas
  métricas (5xx y latencia) están habilitadas. No se disparó alarma en esta
  pasada.

## Recuperación y red privada

- RDS `available`, privada, cifrada, PostgreSQL 18.3, `db.t3.micro`, Single-AZ y
  retención automática de un día. Se observaron tres snapshots automáticos
  cifrados. El restore integral SQL PT-DR-01 ya pasó el 15/10: RTO observado
  260 s, límite superior RPO 8 s; la evidencia está en el
  [checklist de cierre](CHECKLIST-CIERRE-2026-10-15.md). La consulta actual no
  encontró instancias ni subnet groups temporales `tng-dr*`; no se repitió una
  restauración con costo.
- Un `--dry-run` de `CreateCustomerGateway` fue rechazado por un explicit deny
  en la SCP organizacional `p-qa2qn8qf`. Azure no tiene VNets en la suscripción
  activa; AWS no muestra VPN Site-to-Site. No se creó ni modificó red y no se
  intentó eludir la política. La ruta privada AWS–Azure queda bloqueada por el
  entorno Academy actual.

## Límites que siguen abiertos

- El dominio proxied recibió 403 en el POST de login desde el smoke HTTP; el
  mismo login y E2E pasaron contra el origen ALB con TLS verificado. No se pudo
  completar inspección visual en Chrome: el control de navegador no logró
  determinar la URL activa. El login de navegador por el FQDN queda sin
  verificar; hay que inspeccionar el evento de seguridad Cloudflare y probarlo
  en Chrome.
- No existe Web ACL regional AWS. Capacidad de 3,000 usuarios no demostrada por
  una microcarga de 24 solicitudes; los 503 anteriores no tienen causa raíz
  atribuida. WebRTC entre dos navegadores queda pendiente.
- AWS→Azure funciona por HTTPS público; no hay ruta IP privada. El WMS sigue
  siendo un ledger sintético, no inventario de un WMS comercial.

No se modificaron infraestructura, permisos, reglas Cloudflare ni credenciales
durante esta revalidación.
