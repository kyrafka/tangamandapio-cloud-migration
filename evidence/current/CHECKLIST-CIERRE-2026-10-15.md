# Checklist de cierre — actualizado 15/10/2026, 14:45 UTC

Esta hoja sustituye como estado vigente al checklist del 14/10; los informes
anteriores se conservan como evidencia histórica. No asigna una nota.

## Estado cloud vigente — revalidación 14:20–14:32 UTC

- [x] AWS STS aceptó el perfil `default`; CloudFormation
  `tangamandapio-live-20261013` está `UPDATE_COMPLETE`.
- [x] ALB activo con HTTPS/443 y certificado ACM `ISSUED`; HTTP/80 redirige a
  HTTPS. Los dos destinos están `healthy`, el ASG está en 2/2/5 y sus dos EC2
  están `InService`/`Healthy`. `/health` y `/ready` responden 200.
- [x] RDS está `available`, privada y cifrada. Límite vigente: Single-AZ y
  retención de backups de un día.
- [x] Azure Function `tangama-wms-261008` está `Running`, `httpsOnly=true`, y
  `/api/health` HTTPS devolvió 200. Esto no equivale a procesar un evento nuevo
  en este corte; el E2E sintético previo está documentado aparte.
- [x] Chrome: portada, panel de acceso, validación, teclado y vista móvil
  390×844 revisados; consola sin errores/advertencias. Usuario sintético
  inexistente fue rechazado y la página se limpió al recargar.
- [x] Gate local: 176 Python, 14 Node, 40 transacciones aisladas, build,
  auditorías, CloudFormation y cinco entornos Terraform aprobados; no hubo
  `apply` ni servidor web local.
- [x] La revisión anterior HTTPS/QA está sincronizada en el branch GitHub
  `codex/aws-v11-deploy-sync`, commit `006d5e8`; sus tres jobs terminaron
  `success` a las 14:36 UTC.

Detalle: [corte cloud/navegador 14:30 UTC](CLOUD-REVALIDATION-2026-10-15-1430UTC.md).

## Seguimiento de navegador y prueba E2E — 14:38–14:45 UTC

- [x] Confirmación en Chrome: la prueba fue en la pestaña HTTPS desplegada,
  sin localhost ni control de otras ventanas. Tema claro/oscuro, panel de
  acceso y validación de formulario vacío respondieron; se restauró el tema
  oscuro y quedó el login abierto para la continuación manual.
- [ ] El E2E por dominio terminó en `POST /api/auth/login` HTTP 403 antes de
  autenticarse. No se confirmó qué capa generó el 403 y no se reintentó; no se
  inició venta/recepción ni se enviaron eventos.
- [ ] Vistas privadas siguen pendientes hasta que el usuario inicie sesión en
  la pestaña de Chrome. El modo claro se observó con contraste menor; requiere
  una revisión de estilos.
- [ ] Publicar esta actualización local de evidencia y del arnés E2E; volver a
  comprobar CI para el commit que la incluya.

Detalle: [seguimiento Chrome/E2E 14:45 UTC](CLOUD-UI-SMOKE-2026-10-15-1445UTC.md).

## Corte histórico — 05:10 UTC (supersedido)

- [x] AWS `UPDATE_COMPLETE` y nueva detección CloudFormation `IN_SYNC`;
  ALB 2/2 targets saludables; `/`, `/health` y `/ready` 200; API admin sin
  sesión 401. RDS disponible, Single-AZ, un día de backup.
- [x] Azure for Students Enabled; el grupo `rg-tangamandapio-rebuild-wus` está
  `Succeeded`; el health HTTPS de la Function respondió 200. El CLI no terminó
  `functionapp show`/inventario; el estado ARM completo no se volvió a certificar.
- [x] Suite repetida: 152 pruebas Python (157 subtests), 14 Node, build Vite,
  `cfn-lint`, seis entornos Terraform (`fmt`/`init`/`validate`) y tests mock 5/5.
- [x] E2E autenticado en la instancia viva: Admin; permisos de Comercial y
  Operaciones 200/403; importación, venta y compra sintéticas; dos eventos
  entregados a Azure; ledger demo 10→10; SNS 2/2 confirmadas; lecturas 24/24,
  concurrencia 6 y p95 246.02 ms. No prueba capacidad de 3,000 usuarios.
  [Reporte](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15-0515UTC.json).
- [x] Se solicitó el certificado ACM de
  `tangamandapio.kendellnm.me`; está `PENDING_VALIDATION` y el CNAME fue
  compartido con Diego para que Kendell lo publique como DNS only; la consulta
  pública todavía no encuentra ese registro.
- [ ] Esperar ACM `ISSUED`, actualizar el listener a HTTPS/443 y redirección
  HTTP→HTTPS, y comprobar el certificado desde navegador externo. HTTPS aún
  expira; WebRTC A/V entre dos navegadores sigue pendiente.

Detalle íntegro: [revalidación cloud 05:10 UTC](CLOUD-REVALIDATION-2026-10-15-0510UTC.md).

## Comprobado en el corte previo (02:58 UTC)

- [x] AWS CLI `default` autenticado por STS en la cuenta Academy `841113066612`;
  el token temporal no se guardó en Git ni en el repositorio.
- [x] CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; una
  detección nueva confirmó `IN_SYNC`, cero recursos discrepantes.
- [x] Release v11 confirmado por SSM en las dos EC2; servicio activo. ASG
  mínimo/deseado 2, máximo 5; dos destinos del target group `healthy`.
- [x] ALB `/`, `/health` y `/ready` devolvieron HTTP 200; `/api/admin/users`
  sin sesión devolvió 401. Portal todavía HTTP, sin dominio ni TLS confiable.
- [x] RDS `available`, privada, cifrada, 20 GB, Single-AZ, retención automática
  de backup de un día. La infraestructura AWS coincide con CloudFormation en el
  corte; no se actualizó RDS en este release.
- [x] E2E autenticado v11 por SSM: Admin, Comercial y Operaciones; reglas 200/403;
  importación sintética, venta `completed_demo`, recepción `received_demo`, dos
  eventos entregados por Azure y ledger demo 10→10. La carga RDS 24/24 fue de
  solo lectura, desde EC2 por loopback (no por ALB).
- [x] Azure for Students autenticada; inventario de recursos del grupo
  `rg-tangamandapio-rebuild-wus` incluye Function, Storage, Key Vault, Application
  Insights y reglas de alertas.
- [x] Function `tangama-wms-261008` `Running`, `httpsOnly=true`; health HTTPS
  200. Application Insights consultado en vivo: 17 solicitudes en 24 h, cero
  fallidas; dos registros exitosos de `process_fulfillment_message` y dos de
  `receive_fulfillment_event`. Ver
  [evidencia Azure Monitor](azure/AZURE-MONITOR-INVOCACIONES-2026-10-15.md).
- [x] Gate local del 15/10: 165 pruebas Python, 14 Node, 40 transacciones
  aisladas, build, auditorías de dependencias, validaciones CloudFormation y
  Terraform `fmt`/`validate`/mocks; sin cambios cloud.
- [x] Terraform 1.16.0 Linux, igual a GitHub Actions: los cinco entornos pasan
  `fmt`, `init -backend=false -lockfile=readonly` y `validate`; pruebas mock
  5/5. Lockfiles completados con los hashes Linux faltantes sin cambiar
  versiones de proveedores.
- [x] Código, IaC y evidencia del corte publicados en GitHub, branch
  `codex/aws-v11-deploy-sync`, commit publicado `fa8224e`; `main` no se modificó.
  El token AWS y las contraseñas no forman parte del commit.
- [x] GitHub Actions en `fa8224e`: backend/flujo, frontend e infraestructura
  AWS/Azure, los tres `success`.
- [x] Revalidación tras actualizar el token: Azure Function `Running`,
  HTTPS-only y health 200; la consulta de VNets devolvió lista vacía.
- [x] Preflight VPN repetido: AWS Academy deniega explícitamente
  `ec2:CreateCustomerGateway` por SCP; dry-run sin creación. No se instaló la
  extensión Azure solicitada por la CLI ni se generaron cargos.

## Pendiente vigente tras el seguimiento de 14:45 UTC

- [ ] Conectividad privada AWS–Azure: no desplegada ni verificada; un intento
  Site-to-Site previo fue rechazado por SCP. El E2E usa HTTPS público.
- [ ] WebRTC de audio/video bidireccional con dos navegadores reales.
- [x] Dominio `tangamandapio.kendellnm.me` y HTTPS confiable: ACM `ISSUED`,
  HTTPS/443 activo y HTTP/80 redirige; verificación del 15/10 a las 14:20.
- [ ] Revisar visualmente las vistas privadas de Admin, Comercial y Operaciones;
  la pestaña sigue en login y requiere que el usuario inicie sesión allí.
- [ ] Probar importación CSV desde archivo en la UI, con vista previa y
  verificación visual de persistencia.
- [ ] Ejecutar carga transaccional por ALB y dimensionar el objetivo de 3,000
  usuarios; las sondas anteriores eran acotadas y no prueban esa capacidad.
- [ ] Reconsultar alarmas/dashboards y guardar capturas del inventario AWS y del
  monitor Azure. La entrega de alerta/recuperación fue confirmada por el usuario,
  pero no existe captura independiente en el corte actual.
- [ ] Cualquier cambio posterior de código/IaC debe volver a pasar CI antes de
  considerarse validado.

## Revalidación posterior con el laboratorio renovado — 15/10/2026, 03:50–04:11 UTC

- [x] Perfil AWS default actualizado con el token proporcionado; STS autenticó
  en la cuenta Academy 841113066612. El secreto no se copió a archivos del
  proyecto ni al repositorio.
- [x] CloudFormation está UPDATE_COMPLETE; el estado de drift visible es
  IN_SYNC (la detección registrada más reciente fue a las 02:36 UTC).
- [x] ASG mínimo/deseado 2, máximo 5, dos instancias en servicio; ALB activo y
  2/2 destinos healthy. Portada y /health respondieron 200 antes y después
  del E2E. Listener solo HTTP/80.
- [x] RDS available, privada, cifrada, 20 GB, Single-AZ y backup de un día.
- [x] Siete alarmas métricas con acciones habilitadas: seis OK, una alarma
  TargetTracking de escala baja en INSUFFICIENT_DATA.
- [x] E2E portal/RDS/outbox → Azure desde EC2 vía SSM: Admin autenticó, venta
  completed_demo, recepción received_demo, dos eventos entregados y ledger
  sintético 10→10. Comercial y Operaciones recibieron los 200/403 esperados.
- [x] Lecturas autenticadas 24/24 HTTP 200, concurrencia 6, p95 277.17 ms. La
  carga fue loopback en una EC2; no prueba escrituras por ALB ni escala a 3,000.
- [x] Azure /api/health HTTPS 200. La consulta ARM directa de estado de la
  Function no terminó en este corte; Running y httpsOnly=true se habían
  confirmado en la revalidación de las 02:58 UTC.
- [x] Los dos blobs de state remoto existen. La cuenta usa HTTPS/TLS 1.2,
  autenticación Entra, shared-key deshabilitado y acceso anónimo al contenedor
  deshabilitado; la red pública de la cuenta permanece habilitada.
- [x] Planes vivos Terraform de azure-rebuild y azure-tfstate: No changes,
  sin apply.
- [x] Gate local completo: 165 Python, 14 Node, 40 transacciones aisladas,
  build Vite, auditorías sin vulnerabilidades conocidas, CloudFormation y
  Terraform validados; pruebas mock de costos/red aprobadas.
- [x] GitHub Actions en 39617c9 terminó success; el branch remoto y el local
  coincidían antes de esta actualización documental.

La evidencia íntegra de este corte está en
[CLOUD-REVALIDATION-2026-10-15-0410UTC.md](CLOUD-REVALIDATION-2026-10-15-0410UTC.md).

## Límites del prototipo

El saldo WMS es un ledger sintético, no inventario físico. Finanzas no es
contabilidad legal; el buzón interno no es un servicio de correo corporativo ni
SMTP público. La expansión internacional y 3,000 usuarios concurrentes son
objetivos de arquitectura, no capacidad ya demostrada. La rúbrica y su
discrepancia de puntaje siguen en
[`../../core/04_matriz_rubrica.md`](../../core/04_matriz_rubrica.md).

## Revisión puntual de telefonía — 15/10/2026, 01:43 UTC

- La URL pública del ALB `/` y el bundle desplegado
  `/assets/index-DMS--gIU.js` respondieron HTTP 200.
- El bundle contiene una guarda que aborta con `webrtc_not_supported` antes de
  pedir el micrófono cuando falta `navigator.mediaDevices.getUserMedia` o
  `RTCPeerConnection`; la interfaz muestra ese código técnico sin traducirlo.
- La página se sirve por HTTP. En un origen HTTP público, el navegador no expone
  `navigator.mediaDevices`; micrófono/cámara requieren contexto seguro (HTTPS o
  `localhost`). Esto concuerda con el error visto y es la causa más probable;
  no se comprobó desde una sesión de navegador instrumentada.
- Este fallo ocurre antes de la captura de medios y la negociación ICE: no
  demuestra que TURN o la señalización estén fallando. Tampoco demuestra que la
  llamada funcione. La prueba bidireccional A/V con dos navegadores sigue
  pendiente hasta disponer de HTTPS confiable.
- Referencia: [MDN, `getUserMedia()` y contextos seguros](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

## Revalidación breve de endpoints — 15/10/2026, 01:48 UTC

- AWS STS autenticó en la cuenta Academy `841113066612`; la pila
  `tangamandapio-live-20261013` continúa `UPDATE_COMPLETE`. Ambos destinos del
  target group están `healthy`; `/`, `/health` y `/ready` del ALB respondieron
  HTTP 200. El ALB sigue siendo HTTP, por lo que esto no habilita WebRTC.
- Azure for Students sigue `Enabled`; `tangama-wms-261008` figura `Running` y
  `httpsOnly=true`; el health HTTPS respondió 200 (`status: ok`).
- Son comprobaciones puntuales de disponibilidad; no equivalen a un nuevo
  inventario completo, detección de drift, recorrido autenticado ni prueba
  transaccional.

## Listener HTTPS — 15/10/2026, 01:56 UTC

- `DescribeListeners` del ALB muestra únicamente HTTP/80, sin certificado ni
  listener HTTPS/443. Una sonda HTTPS al ALB expiró al conectar; no hay una URL
  TLS funcional en el balanceador actual.
- El navegador no puede adquirir micrófono/cámara desde el HTTP público. No se
  puede habilitarlo desde el frontend sin debilitar la seguridad del navegador;
  la corrección de producción es añadir HTTPS confiable y redirigir HTTP.

## Recuperación RDS (PT-DR-01) — 15/10/2026, 02:09 UTC

- [x] Restauración SQL real desde snapshot temporal: `PASSED`; marcador y
  conteos de tablas verificados en la instancia recuperada.
- RTO medido: 260 s desde la solicitud de restore hasta la sonda SQL lista.
  Límite superior observado de RPO: 8 s.
- Instancia origen y restaurada privadas; ambas cifradas. Retención automática
  en la instancia temporal: 0 días para evitar respaldos adicionales.
- Limpieza automática verificada: se eliminó la instancia y el snapshot
  temporales, y se retiró el marcador de prueba del origen. El snapshot manual
  permanente de referencia no se modificó.
- La corrida anterior había fallado antes de tocar datos porque el Python de
  sistema carecía de `boto3`; se corrigió el intérprete remoto y se agregó un
  preflight de dependencias de solo lectura. El gate local completo volvió a
  pasar antes de repetir la prueba.

## Verificación posterior y limpieza — 15/10/2026, 02:22 UTC

- [x] El identificador temporal `tng-dr-restore-20261015020936` ya no aparece
  en RDS. La instancia productiva `tangamandapio-postgres` sigue `available`,
  privada y cifrada.
- [x] AWS ALB `/health` respondió HTTP 200 (`status: ok`); Azure WMS
  `/api/health` respondió HTTPS 200 (`status: ok`). El flujo de aplicación
  sigue accesible después del ejercicio DR.
- El ALB sigue HTTP/80 únicamente. No se creó DNS, certificado ni listener
  HTTPS durante esta comprobación.

## E2E portal→RDS/outbox→Azure — 15/10/2026, 02:29 UTC

- `tests/cloud/run_live_aws_portal_azure_e2e.ps1` terminó `LIVE_E2E_PASSED`
  desde una EC2 Online vía SSM; la clave QA se leyó dentro de AWS y no se envió
  al ALB HTTP público.
- El portal confirmó importación de catálogo, venta `completed_demo`, recepción
  `received_demo` y dos eventos outbox entregados; Azure continuó identificando
  el inventario como `demo-inventory-ledger`. El saldo del SKU QA quedó 10 antes
  y 10 después.
- La microcarga de lectura autenticada terminó 24/24 HTTP 200, concurrencia 6,
  p95 476.1 ms. Es una medición de una EC2 y no demuestra carga a través del ALB,
  escalado multinodo ni 3,000 usuarios concurrentes.
- La matriz API confirmó los permisos de Comercial y Operaciones descritos en
  el checklist. Esto no sustituye el recorrido visual en navegador ni la prueba
  de CSV desde archivo.

## Monitoreo y drift — 15/10/2026, 02:36 UTC

- [x] Las cinco alarmas CloudWatch del stack están `OK` y `ActionsEnabled=true`;
  el topic SNS tiene dos suscripciones `email` confirmadas (ARN no pendiente).
- [x] Azure Action Group `tangama-ops-ag` está habilitado y ambos receptores
  de email figuran `Enabled`; las reglas `tangama-wms-fn-5xx` (severidad 2) y
  `tangama-wms-fn-latency` (severidad 3) están habilitadas.
- No se forzó otra alarma ni se envió correo durante esta revisión. Esto
  confirma configuración viva; para evidencia independiente de entrega se
  conserva la confirmación del usuario y queda pendiente una captura del buzón.
- [x] Nueva detección CloudFormation de `tangamandapio-live-20261013`:
  `DETECTION_COMPLETE`, `IN_SYNC`, cero recursos discrepantes. No quedó RDS
  temporal del ejercicio PT-DR-01.

## Smoke check posterior a la publicación — 15/10/2026, 02:45–02:47 UTC

- [x] AWS STS autenticó en la cuenta `841113066612`; el ALB `tangamandapio-alb`
  aparece `active` y `/health` respondió 200.
- [x] Azure for Students figura `Enabled`; Function `tangama-wms-261008`
  `Running`, `httpsOnly=true`, y `/api/health` respondió HTTPS 200.
- [x] Los tres checks GitHub Actions de `7c96f36` terminaron `success`;
  `git ls-remote` confirmó la publicación de ese commit antes de este
  complemento de evidencia.

## Página pública y sondas ALB/RDS — 15/10/2026, 02:50–02:57 UTC

- [x] En una pestaña aislada del navegador cargó el título y la estructura
  accesible de la portada pública de AWS; no se inició sesión ni se transmitieron
  credenciales. La página presenta el acceso y sus controles.
- [x] GET de portada, JavaScript, CSS y póster pixelado: todos HTTP 200. El HTML
  incluye preload de imagen; el PNG de 2,081,152 bytes devuelve
  `public, max-age=31536000, immutable`.
- [x] Dos corridas de solo lectura a `/health`, cada una con 60 solicitudes y
  concurrencia máxima 8: 120/120 HTTP 200 y `status=ok`. La ruta ejecuta `SELECT
  1` en la base. Run 1: p50 230.4 ms, p95 1,719.7 ms, máximo 1,726.3 ms; run 2:
  p50 232.2 ms, p95 1,194.1 ms, máximo 1,226.4 ms. Dos destinos permanecieron
  `healthy` después de la prueba.
- El sondeo valida disponibilidad básica ALB→aplicación→RDS, no transacciones,
  distribución efectiva entre ambas instancias ni el objetivo de 3,000 usuarios.

## Revalidación final de salud — 15/10/2026, 02:58 UTC

- [x] AWS STS en la cuenta académica, ALB `active`, ambos destinos `healthy` y
  `/health` 200 después de las sondas.
- [x] Azure Function `/api/health` HTTPS 200 (`status: ok`). No se hicieron
  cambios de infraestructura ni escrituras en ninguno de los dos proveedores.

## Revalidación posterior — 15/10/2026, 04:48–04:53 UTC

- [x] AWS stack `UPDATE_COMPLETE`, ALB activo, dos targets `healthy` y `/health`
  y `/ready` HTTP 200. Listener comprobado: HTTP/80 únicamente.
- [x] Azure Function en `rg-tangamandapio-rebuild-wus` está `Running`,
  `httpsOnly=true`, con `/api/health` HTTPS 200. Se corrigió la referencia
  histórica del root `azure-demo`; no se aplicó ese root heredado.
- [x] Portada HTTP 200 y ocho recursos estáticos JS/CSS HTTP 200. Esto no
  sustituye la inspección visual autenticada ni el test WebRTC real.
- [ ] VPN privada pendiente: el `--dry-run` actual de `CreateCustomerGateway`
  fue denegado por una SCP explícita de AWS Organizations; no se creó nada. Se
  necesita permiso del administrador de AWS Academy antes de la prueba temporal.
- [ ] HTTPS pendiente: el ALB aún no tiene listener 443. El preflight de ACM
  pasa con mocks; falta subdominio bajo DNS controlado, certificado `ISSUED` y
  change set aprobado.
- [x] Commit `ef006a9` sincronizado con el remoto; GitHub Actions terminó
  `success`. La evidencia de este nuevo corte se detalla en
  [CLOUD-REVALIDATION-2026-10-15-0448UTC.md](CLOUD-REVALIDATION-2026-10-15-0448UTC.md).

## Revalidación posterior — 15/10/2026, 05:18–05:26 UTC

- [x] AWS STS autenticó en la cuenta Academy `841113066612`; CloudFormation
  `tangamandapio-live-20261013` sigue `UPDATE_COMPLETE`, ambos destinos del ALB
  `healthy` y `/health` del portal HTTP 200 (05:26:20 UTC). El único listener
  continúa en HTTP/80.
- [x] Azure for Students sigue `Enabled`; `/api/health` de la Function devolvió
  HTTPS 200. La consulta de inventario ARM con Azure CLI y REST excedió 20 s;
  por eso no se certifica el inventario/control plane completo en este corte.
- [x] Pruebas locales repetidas: Python 152 aprobadas (157 subtests), Node 8
  permisos + 6 CSV, build Vite y `cfn-lint` aprobados. GitHub Actions del tip
  `a1c1596` terminó `success` y el remoto apunta al mismo commit.
- [ ] HTTPS sigue pendiente: ACM reporta `PENDING_VALIDATION` y el CNAME
  `_9568d15842cb7c5bd79e0208316e57af.tangamandapio.kendellnm.me` aún no resuelve
  públicamente. Las capturas de Cloudflare muestran otros CNAME de validación,
  no el nombre que espera este certificado. HTTPS `/` y `/health` desde fuera
  agotaron 20 s a las 05:29 UTC. No se desplegó listener 443.
- [ ] Falta que Kendell publique el CNAME exacto de ACM como DNS only; al pasar
  ACM a `ISSUED`, desplegar el listener/redirect y probar HTTPS externamente.
  Después se podrá comprobar WebRTC desde navegadores seguros.

## E2E sintético por ALB — 15/10/2026, 05:33 UTC

- [x] El ALB directo `/health` respondió HTTP 200; una corrida E2E por el mismo
  ALB terminó `LIVE_E2E_PASSED`. Admin autenticó, Comercial/Operaciones
  respetaron 200/403, venta y recepción sintéticas se completaron, y dos eventos
  llegaron a Azure. El ledger demo regresó 10→10.
- [x] 24 lecturas autenticadas por el ALB: 24/24 HTTP 200, concurrencia 6,
  p95 216.61 ms; SNS: dos suscripciones confirmadas. No representa 3,000 usuarios.
  [Resultado sanitizado](aws/AWS-PORTAL-ERP-AZURE-ALB-E2E-2026-10-15-0533UTC.json).
- [x] El test runner ahora limita el destino a loopback o el ALB conocido y
  rechaza destinos arbitrarios; la suite Python completa pasó 167 pruebas y 159
  subtests, incluidas las pruebas del runner.
- [x] Capacidad AWS comprobada después del E2E: ASG deseado/mínimo 2, máximo 5,
  ambas EC2 `InService` y `Healthy`. Seis alarmas métricas están `OK`; la alarma
  target-tracking de escala baja está `ALARM` por CPU < 42%, condición que pide
  scale-in pero no baja el ASG de su mínimo 2. Acciones habilitadas. El usuario
  confirmó antes que recibió alertas y recuperación; no se archivó captura.
- [ ] El certificado ACM continúa `PENDING_VALIDATION`; el CNAME de validación
  esperado aún no aparece en DNS público. HTTPS externo sigue expirando, no se
  habilitó 443 y WebRTC con dos navegadores queda pendiente.
