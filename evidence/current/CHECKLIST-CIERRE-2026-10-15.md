# Checklist de cierre — actualizado 15/10/2026, 02:29 UTC

Esta hoja sustituye como estado vigente al checklist del 14/10; los informes
anteriores se conservan como evidencia histórica. No asigna una nota.

## Comprobado en este corte

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
  `codex/aws-v11-deploy-sync`, commit publicado `327549f`; `main` no se modificó. El token
  AWS y las contraseñas no forman parte del commit.
- [x] Checks de GitHub Actions en `327549f`: backend/flujo, frontend e
  infraestructura AWS/Azure, los tres `success`.
- [x] Revalidación tras actualizar el token: Azure Function `Running`,
  HTTPS-only y health 200; la consulta de VNets devolvió lista vacía.
- [x] Preflight VPN repetido: AWS Academy deniega explícitamente
  `ec2:CreateCustomerGateway` por SCP; dry-run sin creación. No se instaló la
  extensión Azure solicitada por la CLI ni se generaron cargos.

## Pendiente, sin marcar como completado

- [x] Prueba funcional viva desde EC2 del portal desplegado: autenticación Admin,
  importación del SKU de QA por la API, venta/recepción compensatoria hacia
  Azure, ambos outbox `delivered` y saldo sintético 10→10; 24/24 lecturas
  autenticadas HTTP 200 (concurrencia 6, p95 476.1 ms). Ver detalle abajo.
- [x] Matriz de autorización por API desde EC2: Comercial venta 200 y outbox,
  inventario WMS y administración 403; Operaciones venta 403, outbox e
  inventario 200 y administración 403. El E2E Admin pudo importar y completar
  el ciclo sintético.
- [ ] Importar un archivo CSV desde el navegador y verificar previsualización y
  persistencia visual. La corrida viva anterior importó un producto mediante
  JSON a la API; parser, plantilla y límites pasan pruebas automatizadas, pero
  eso no es una prueba de la selección/preview del archivo en UI.
- [ ] Recorrido visual autenticado de Admin, Comercial y Operaciones. No se
  enviaron contraseñas al ALB HTTP; falta una sesión de navegador segura para
  comprobar vistas visuales, no solo la matriz de permisos API.
- [ ] Carga transaccional de ventas a través del ALB/RDS y análisis de capacidad
  para 3,000 usuarios. Las sondas de `/health` y las lecturas loopback no prueban
  esa capacidad.
- [ ] Entrega extremo a extremo de alertas Azure. La telemetría de invocaciones
  confirma actividad, no notificación.
- [ ] State remoto y privado de Terraform Azure. Los state y respaldos actuales
  están en la máquina local e ignorados por Git; conservarlos y migrarlos con un
  procedimiento revisado antes de reconstruir desde otro entorno.
- [ ] Conectividad privada AWS–Azure: no desplegada ni verificada; un intento
  Site-to-Site previo fue rechazado por SCP. El E2E usa HTTPS público.
- [ ] WebRTC de audio/video bidireccional con dos navegadores reales.
- [ ] Dominio y HTTPS confiable del portal, al final del cierre acordado.
- [ ] Capturas visuales crudas actuales para inventario AWS y monitor Azure; la
  evidencia de este corte es salida estructurada/registro, no captura de
  consola.
- [ ] Cualquier cambio posterior en el branch debe volver a pasar CI antes de
  considerarse validado.

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
