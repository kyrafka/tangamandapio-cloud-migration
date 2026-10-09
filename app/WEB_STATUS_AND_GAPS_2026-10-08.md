# Bitácora histórica del portal y sus brechas — 8 de octubre de 2026

Este documento conserva cortes de desarrollo del 08/10; **no es el inventario vigente ni una lista actual de pendientes**. Algunas afirmaciones de sus secciones históricas cambiaron más tarde ese día. Para saber qué existe ahora y qué falta, usa el [mapa de estado actual](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md), que prevalece. Se preserva aquí la cronología técnica. **No contiene credenciales ni claves.**

## Corte histórico de verificación operativa — 08/10/2026, 21:26 UTC

- **AWS/IaC:** se exportó la plantilla que ya tenía el stack vivo, se reconcilió `iac/cloudformation/aws-lab.yaml` y se validó con CloudFormation. El único cambio funcional aplicado fue `AUTO_DISPATCH_EVENTS=true`; el reintento periódico queda en 60 s. El stack terminó `UPDATE_COMPLETE`, la detección de drift reportó `IN_SYNC` con 0 recursos divergentes, y las 2 instancias activas/targets están saludables. SSM confirmó en ambas el despacho automático, el retry de 60 s y el servicio activo. El cambio se hizo gradualmente; no cambió red, WAF, RDS ni backups.
- **RDS:** la base original sigue `available`, privada, cifrada, Multi-AZ, clase `db.t3.micro`, retención de 7 días. Se restauró una copia temporal privada desde el último punto recuperable; la lectura de verificación encontró 10 tablas públicas. Se eliminó la copia temporal después de validar; la base original no se modificó. No se midió un RTO formal.
- **Azure/poison:** `https://tangama-wms-fn.azurewebsites.net/api/health` respondió `200`. En la cola poison se observó un mensaje del evento `evt-c7508545eb85461dabc9c4d96621ec13`: el Blob pasa su propio SHA-256, pero el hash incluido en el mensaje de cola es distinto. El outbox AWS registra ese evento como `delivered` en 1 intento y el resultado de fulfillment ya existe. Se dejó el mensaje sin cambiar ni borrar como evidencia; no se reencoló.
- **Calidad y permisos:** `tests/run_local_quality.ps1` pasó 59 pruebas (22 API base, 14 Azure y 23 release AWS) y compiló el frontend. La suite cubre admin/operaciones, rechazo de ventas para rutas administrativas y que el despacho automático se invoque después de persistir outbox. La revisión live autenticada queda pendiente: el login admin respondió, pero la cookie de sesión es `Secure`, así que no se conserva por HTTP loopback; HTTPS del ALB sigue pendiente de confianza. No se desactivó `Secure`.
- **Fuera de esta ejecución, según lo pedido:** no probé audio/video entre dos navegadores ni configuré dominio/HTTPS confiable. El ALB redirige HTTP a HTTPS; no se usó esa ruta para enviar credenciales porque la confianza del certificado queda pendiente.
- **Pendiente funcional real:** repetir un pedido sintético en vivo desde una sesión autenticada para observar el despacho nuevo con esta configuración; decidir la disposición de la copia poison, cuyo evento ya está entregado; y hacer la validación visual/manual de los roles cuando haya HTTPS confiable. Azure sigue siendo un ledger WMS demostrativo, no una integración con inventario empresarial.

## Corte histórico en vivo — 19:26 UTC (superado)

Esta actualización reemplaza los sondeos anteriores de este mismo día: se renovó la identidad temporal y luego se volvió a comprobar AWS y Azure.

- **AWS autenticado:** el perfil local `default` autenticó con STS en la cuenta del laboratorio. El stack `tangamandapio-live-20261005` terminó `UPDATE_COMPLETE` a las 19:26 UTC. El Auto Scaling Group está en deseado 2; ambas instancias están `InService/Healthy` y los dos destinos del ALB están `healthy`.
- **Portal público:** el ALB `tangamandapio-alb-829164422.us-east-1.elb.amazonaws.com` devolvió `/health` `200`, `/platform` `303` (redirige al login, ya no 404) y `/api/wms/inventory` `401` sin sesión (protección esperada). La consulta HTTPS de esta comprobación omitió la validación del certificado: el dominio propio y HTTPS confiable siguen pendientes.
- **RDS:** `tangamandapio-postgres` está `available`, Multi-AZ, cifrado y con retención de backups de 7 días. No se restauró ni modificó la base.
- **Azure:** la Function `tangama-wms-fn` recibió la publicación del paquete actual; `/api/health` devuelve `200`. Están habilitadas cinco funciones, incluida `demo_inventory`. La ruta de inventario devuelve `401` sin clave, como corresponde. La clave de servicio se sincronizó entre AWS Systems Manager y Secrets Manager; ambas EC2 fueron actualizadas gradualmente y comprobaron respuesta `200` del inventario autenticado.
- **Prueba AWS→Azure:** se creó un único pedido sintético (SKU `SKU-ARROZ-001`, cantidad 1), quedó durable en el outbox de AWS y se entregó a Azure con un reintento manual. El ledger **de demostración** pasó de 25 a 24; repetir el mismo evento lo mantuvo en 24 (`idempotencia verificada`). No se usaron datos de clientes ni se tocó inventario empresarial real.
- **Modo de despacho:** `AUTO_DISPATCH_EVENTS=false`; por diseño actual el pedido se guarda primero y el despacho ocurre al reintentar desde la operación. No se cambió a envío automático porque eso alteraría el comportamiento de pedidos futuros.
- **Pendiente real:** reconciliar el template local con la infraestructura viva antes de otro `apply`, probar una restauración RDS aislada, revisar la cola poison histórica de Azure sin borrarla, validar login/roles en navegador y probar audio/video WebRTC entre dos navegadores reales. El WMS continúa siendo un ledger ficticio, no un sistema de almacén conectado.

El detalle cronológico está en [cierre de nube](../evidence/current/CIERRE_NUBE_2026-10-08.md); la [revisión de Chrome](../evidence/current/REVISION_CHROME_2026-10-08.md) corresponde a una observación visual previa y no sustituye estas comprobaciones CLI/API.

## Actualización de implementación WMS — 08/10/2026

- Se agregó un catálogo ficticio de laboratorio con SKU, precio y saldo; Azure lo conserva en Blob Storage y procesa pedidos con líneas `SKU + cantidad` bajo lease/ETag para serializar concurrencia e impedir descuentos duplicados.
- El panel local `/platform` ahora muestra stock y un botón para generar un pedido demo. El backend restringe la acción a `admin`/`operations`, verifica existencias, conserva las líneas en la orden y crea un evento durable en outbox. El pedido muestra su referencia y resultado de Azure.
- Los eventos viejos sin líneas devuelven `awaiting_items`; stock insuficiente queda `rejected_insufficient_stock` sin descuento parcial. Solo el ledger ficticio se modifica; no es un ERP/WMS real.
- La migración `0007_order_items` agrega el campo compatible `items_json` en SQLite/PostgreSQL. En esta ejecución inicial aprobaron 14 pruebas Azure, 22 del release (incluyen idempotencia con lease, rechazo atómico, outbox y autorización) y 22 de la suite base: 58 en total. Una ejecución posterior aprobó 59/59; ver el [registro consolidado de pruebas](../evidence/current/PRUEBAS_LOCALES_2026-10-08.md). `node --check` del JavaScript también pasó.
- **Estado de ese corte, superado por la actualización en vivo superior:** la publicación ZIP de Azure se completó con build remoto; el endpoint de inventario y `/platform` en AWS quedaron disponibles detrás de autenticación.
- IaC no cambió. La diferencia local/viva RDS (`MultiAZ: false`/1 día frente a la última lectura Multi-AZ/7 días) sigue pendiente de reconciliación. Dominio y HTTPS propio continúan diferidos.

## Historial de verificación anterior a la renovación del token — 08/10/2026

Los resultados siguientes son una bitácora de antes de renovar credenciales y desplegar. No describen el estado actual; consultar primero el [mapa de estado actual](../evidence/current/MAPA_ESTADO_ACTUAL_2026-10-08.md). La verificación de las 21:26 UTC también es histórica y está conservada arriba como evidencia de su propio corte.

- En esta revisión, AWS CLI no autenticó: STS devolvió InvalidClientTokenId usando el perfil local default. AWS Academy mostraba el laboratorio Ready, 2 h 28 min restantes y “No running instance”. No se consultó ni modificó infraestructura con esa identidad; el perfil local recibió el bloque compartido para esta sesión, pero no se considera válido hasta que STS confirme identidad.
- La web pública del ALB respondió /health 200, /ready 200 y /api/auth/session 200. La ruta /platform respondió 404: la consola de plataforma/administración no está publicada en el endpoint desplegado. Chrome mostró el inicio de sesión tanto en AWS como en local; no se introdujeron credenciales.
- Azure Portal confirmó la Function tangama-wms-fn en ejecución y mostró una invocación correcta de process_fulfillment_message para el evento sintético evt-20261008-liveprobe-01, DequeueCount: 1, con resultado simulated_fulfillment_completed. Esto acredita el recorrido de demostración, no un movimiento de inventario.
- El contrato del pedido en el backend actual solo incluye cliente, referencia y total; no contiene líneas con SKU y cantidad. Sin esos datos y una fuente de existencias no se puede hacer una salida de stock correcta. El modo actual permanece claramente rotulado como demostración.
- Las pruebas locales se repitieron con el entorno del proyecto: backend base 22/22, Azure Function 14/14 y release AWS 22/22. Son pruebas locales; no sustituyen el inventario AWS ni una restauración de RDS.
- La plantilla CloudFormation local declara MultiAZ: false y BackupRetentionPeriod: 1; el último registro de la configuración viva documentó RDS privado, Multi-AZ y 7 días de retención. No se pudo volver a contrastar esa configuración hoy. No desplegar la plantilla local ni iniciar una restauración hasta recuperar STS y comparar la plantilla remota, los recursos y la configuración de RDS.
- El detalle y la lista de acciones pendientes están en [CIERRE_NUBE_2026-10-08.md](../evidence/current/CIERRE_NUBE_2026-10-08.md).

## 1. Estado desplegado y comprobado

> Las mejoras de administración de usuarios, el endpoint TURN y el primer
> endpoint de conciliación WMS se desplegaron como backend en ambas instancias
> AWS el 08/10/2026. El endpoint TURN no implica que exista un relay TURN ni
> que el frontend ya lo consuma.

### AWS — portal B2B

- Stack `tangamandapio-live-20261005`: actualización de aplicación finalizada como `UPDATE_COMPLETE`, preservando el template vivo para no modificar RDS/red de forma accidental. El template local aún debe reconciliarse antes de futuros cambios de infraestructura.
- El artefacto publicado está versionado en S3 bajo `releases/tangamandapio/portal-20261008-wms-inventory-publish.tar.gz` (SSE-S3). La actualización de Launch Template/ASG se aplicó gradualmente; el grupo quedó con dos instancias saludables.
- Las dos EC2 están `running` y `healthy`; RDS está `available`, privado, Multi-AZ y con 7 días de backups. La sonda directa de cada EC2 informa servicio y base de datos `ok`. El ALB redirige HTTP a HTTPS; el certificado del hostname `elb.amazonaws.com` no quedó validado como confiable y el dominio/certificado propio sigue al final.
- Las rutas nuevas protegidas `/api/voice/ice-config`, `/api/admin/users` y `/api/outbox/<event_id>/fulfillment-status` responden `401` sin sesión, como se espera.
- El endpoint de conciliación consulta el resultado final del evento en Azure y etiqueta estados de demostración; además, el despacho acepta el acuse `queued_duplicate` de Azure. Tras sincronizar la clave vigente, ambas EC2 consultaron el evento sintético y recibieron HTTP 200 con `simulated_completed` (`demo-only`); la clave no se imprimió en las verificaciones.
- La migración agrega versión de sesión y revoca las sesiones anteriores; todos deben volver a iniciar sesión.
- El acceso administrativo al portal funcionó. La API de grabaciones, autenticada como `admin`, devolvió `enabled: true` y cero grabaciones guardadas.
- WAF está asociado al ALB.
- RDS se verificó como `available`, cifrado, no público, Multi-AZ, clase `db.t3.micro` y retención de backups de 7 días.
- El bucket de grabaciones es independiente de los artefactos y respaldos generales. Tiene bloqueo de acceso público, cifrado SSE-S3, política que exige HTTPS, permiso del rol del portal solo sobre `voice-recordings/*`, versionado y expiración de 30 días. La expiración automática está configurada; no se esperó 30 días para observarla.
- No se subió audio de usuarios ni se reprodujo una grabación real durante esta comprobación.

### Azure — WMS de demostración

- Function App `tangama-wms-fn`, grupo `rg-tangamandapio-261005-wus`, está en ejecución; se publicaron cinco funciones: `demo_inventory`, `fulfillment_status`, `health`, `process_fulfillment_message` y `receive_fulfillment_event`. `/api/health` responde `200`; los endpoints protegidos devuelven `401` sin clave.
- La clave de función vigente se sincronizó desde Parameter Store a Secrets Manager para que la usen tanto las instancias actuales como las de futuros scale-out. Las dos EC2 se actualizaron gradualmente y consultaron el inventario autenticado con HTTP `200`; no se mostró la clave ni se usó `_master`.
- Azure se modificó en esta ejecución: se publicó el paquete ZIP con build remoto y se agregó una clave de función de alcance limitado para el endpoint de inventario. La verificación se hizo con HTTP/ARM sin incluir secretos en los registros.
- Se reparó el despliegue para que Oryx instale `requirements.txt`, se habilitó el indexado del modelo Python v2 y se corrigieron los nombres/lectura de parámetros HTTP que impedían cargar las funciones.
- La Function App expone una sonda pública de salud y endpoints protegidos por clave Function para recibir eventos y consultar su resultado. El consumidor de cola está habilitado y completó la nueva prueba sintética.
- Las pruebas anteriores de eventos registraron `simulated_completed`; la prueba actual descrita arriba recorrió además el inventario demo y cambió una unidad de stock ficticio con idempotencia.
- Prueba repetida el 08/10/2026 desde esta sesión: el evento sintético `evt-codex-1b9c1516a49441ef993820a3f17f6102` fue aceptado por `POST /api/fulfillment/events` con HTTP `202 queued`; `GET /api/fulfillment/events/{event_id}` respondió HTTP `200`, `simulated_completed`, `mode=demo-only`. No se enviaron datos de clientes ni se modificó inventario real.
- El consumidor y el inventario son **solo demostrativos**: pueden descontar stock del ledger ficticio de Blob, pero no modifican existencias empresariales, ERP, pedidos reales ni despacho.
- El evento y su resultado sintéticos permanecen en el contenedor de evidencia como rastro de prueba. No incluyen datos de clientes reales.
- Verificación adicional desde Azure Portal/Chrome (08/10): el evento sintético `evt-20261008-liveprobe-01` devolvió `202 queued`; el monitor de `process_fulfillment_message` mostró la ejecución correspondiente a las 09:10:18, `Succeeded`, `DequeueCount: 1`, 93 ms y `simulated_fulfillment_completed`. `fulfillment_status` devolvió `200` con `simulated_completed` y `mode=demo-only`. El flujo no alteró inventario real.
- El monitor de invocaciones reportaba 9 éxitos y 5 errores en los últimos 30 días. Se inspeccionó un error de un mensaje anterior (insertado el 06/10): el worker detectó que el SHA-256 del Blob no coincide con el enviado en Queue; el mensaje ya alcanzaba `DequeueCount: 5`. No se eliminó ni modificó; requiere diagnóstico y tratamiento explícito de mensaje poison/dead-letter antes de afirmar una cola sin pendientes.

### Pruebas locales

- Backend/base local: 22 pruebas aprobadas con `PYTHONPATH=app`. Esta línea fuente es anterior al artefacto AWS actual; no sustituye las pruebas separadas del release desplegado.
- Azure: 14 pruebas unitarias aprobadas — checksum, idempotencia, SKU/cantidad, transacción de inventario demo, rechazo atómico, rutas HTTP y bindings.
- Backend AWS release: 22 pruebas aprobadas — incluye llamadas, grabaciones privadas con S3 simulado, ciclo de vida de usuarios, autorización, credenciales TURN, consulta/acuse Azure, consola de plataforma y CloudWatch simulado.
- En esta sesión se repitieron y aprobaron 22 pruebas backend/base, 22 del release AWS y 14 de Azure, total 58.
- Las pruebas locales no acceden al micrófono, no graban audio real y no prueban la red entre dos navegadores.

### Laboratorio AWS Academy y CLI local

- Se renovó el Learner Lab con `Start Lab`: AWS quedó `Ready`, con 4 horas de sesión y presupuesto mostrado de `$16.20 usados de $50` en ese momento.
- `aws sts get-caller-identity --profile default --region us-east-1` autentica en la cuenta del laboratorio. La sesión local estaba vigente durante esta comprobación.
- **Historial anterior:** el bloque de arriba describía una transferencia incompleta en una revisión previa. En la actualización final de este documento se reemplazó el perfil local `default` con la sesión entregada por el usuario y STS confirmó la identidad de la cuenta del laboratorio. El token es temporal; no guardar sus valores en documentación ni capturas.

### Revisión visual anterior en Google Chrome — 08/10/2026

Esta inspección de Chrome precede a la actualización final de nube y conserva valor solo como evidencia visual histórica.

- El portal público de AWS mostró su pantalla de acceso. Esta observación solo
  confirma que se sirvió la interfaz; no prueba login, base de datos ni salud de
  destinos.
- AWS Academy indicaba que el laboratorio estaba listo. La consola abierta desde
  el laboratorio quedó en una pestaña en blanco, así que no se verificó el
  inventario CloudFormation/EC2/ALB/RDS en esta revisión.
- En Azure Portal, `tangama-wms-fn` aparecía **En ejecución**, Linux, West US,
  plan Consumption, y la lista visible mostraba `fulfillment_status` habilitada.
  No se ejecutó una invocación desde el portal en esta revisión.
- La captura real de Chrome se inspeccionó, pero no se guardó en el repositorio:
  la sesión solo expuso una imagen temporal y el intento de exportación fue
  bloqueado por la política de URL del navegador. No se intentó eludirla. Ver
  [la bitácora de Chrome](../evidence/current/REVISION_CHROME_2026-10-08.md) y
  [capturas pendientes](../evidence/current/CAPTURAS_PENDIENTES.md).
- Se repitieron las tres suites locales: **22 + 14 + 22 = 58 pruebas aprobadas**.
  Son pruebas aisladas/simuladas y no reemplazan la verificación de nube viva.
- No hay un actualizador automático permanente: Learner Lab requiere iniciar/renovar sesión en AWS Academy, y el token vence. En cada sesión nueva hay que copiar el bloque vigente y ejecutar el helper antes de usar la CLI.

## 2. Capacidades que ya tiene la web

| Módulo | Incluido |
|---|---|
| Acceso | Login, logout, sesión con cookie HttpOnly/SameSite, CSRF para cambios y límite de intentos de login por proceso. No hay registro público. |
| Roles | `customer`, `sales`, `warehouse`, `operations`, `admin`, `auditor`. Los permisos son aplicados en el backend, no solo ocultando botones. |
| Empresas | El administrador puede crear/listar empresas y separar usuarios por empresa. |
| Usuarios | La API AWS permite listar/crear/editar/desactivar y restablecer claves con auditoría. `/platform` está publicado y protegido por login; falta completar la regresión visual y validar cada rol/acción en navegador. |
| Nube y seguridad | `/platform`: solicitudes/latencia/5xx del ALB, salud de destinos, RDS, WAF y métricas ASG opcionales; estado de controles e integración Azure. Requiere permisos CloudWatch; no inventa datos si no están configurados. |
| Pedidos | El portal permite registrar y consultar pedidos; `customer` ve solo los de su empresa. |
| WMS / outbox | `/platform` lista eventos, consulta resultados, permite reintento auditado y genera pedidos demo con SKU/cantidad. El recorrido desplegado AWS→Azure descontó idempotentemente de un ledger ficticio en Blob. No está conectado a un ERP/WMS real. |
| Auditoría | Login, llamadas, operaciones sensibles y reintentos generan entradas de auditoría; admin, operaciones y auditor pueden consultarlas. |
| Telefonía | WebRTC punto a punto con señalización/API en AWS, directorio de extensiones del laboratorio, estados de llamada, aceptar/rechazar/finalizar y controles de micrófono/cámara en la interfaz. El servidor no transporta el audio/video. |
| Grabaciones | Audio únicamente y solo si ambos participantes aceptan; se detiene y carga desde el cliente que la inició. S3 privado sirve el archivo a participantes y admin autorizado; la retención objetivo es 30 días. La cámara nunca se graba. |

## 3. Pendientes del corte histórico (no tomar como lista vigente)

La lista siguiente corresponde al corte original de esta bitácora. Algunas tareas, como la reconciliación de la plantilla AWS y la prueba PITR temporal, avanzaron después. Usa el mapa vigente para el estado restante.

### Prioridad 1 — dominio propio y HTTPS confiable (dejado para el final, como pediste)

- Registrar o elegir un dominio y administrar su DNS (Cloudflare puede administrar DNS; GitHub no regala un dominio registrado).
- Emitir en ACM, región `us-east-1`, un certificado cuyo nombre coincida con el dominio; asociarlo al listener HTTPS del ALB y apuntar DNS al ALB.
- Verificar cadena del certificado, redirección HTTP→HTTPS, renovación, cabeceras y cookies.
- El ALB hoy cifra tráfico, pero el hostname `*.elb.amazonaws.com` no es un dominio propio y el certificado actual no debe presentarse como HTTPS confiable para usuarios.
- La configuración de arranque aún declara `SESSION_COOKIE_SECURE=false`; debe quedar en `true` al cerrar HTTPS y probarse login/logout en ambos temas y navegadores.

### Prioridad 2 — completar y probar telefonía real entre navegadores

- El backend probó el caso de llamada iniciada antes de que la otra cuenta ingrese; ambos pueden intercambiar señalización API en la prueba.
- **No está demostrado que audio/video conecten correctamente desde dos navegadores reales en redes distintas.** Sigue pendiente la observación previa de cámara remota unidireccional.
- El frontend compilado solo declara STUN (`stun.l.google.com:19302`); no hay TURN. En redes NAT/firewalls estrictos, STUN no basta y una llamada puede quedarse sin medios aunque la señalización diga “conectada”.
- Está desplegado `GET /api/voice/ice-config`, que solo genera credenciales TURN temporales si el entorno configura URL y secreto compartido. No hay servicio TURN desplegado ni integración del endpoint en el frontend; no se puede afirmar que esto corrija la cámara remota unidireccional.
- Falta una prueba guiada con dos cuentas, dos navegadores/dispositivos, permiso de micrófono/cámara, audio bidireccional, video bidireccional, mute, cámara apagada, reconexión, rechazo, timeout y cierre.
- Se prepararon dos sesiones locales independientes. El clic no llegó a crear una llamada en el servidor; el permiso nativo de audio/video no quedó visible para verificarlo desde la automatización. El resultado de medios sigue sin ser concluyente. No se guardó ni grabó audio/video.
- No se instaló Asterisk ni hay cuentas SIP/PBX. Esta implementación es WebRTC de navegador, no telefonía SIP tradicional.

### Prioridad 3 — cerrar ciclo de vida de usuarios y control de acceso

- En AWS están desplegadas `PATCH /api/admin/users/<id>` para editar rol/empresa/estado e invalidar sesiones; `POST /api/admin/users/<id>/reset-password` para emitir una contraseña temporal de un solo vistazo con cambio obligatorio; y `POST /api/auth/password` para validar/cambiar contraseña y revocar la sesión. Los flujos quedan auditados y se impide al admin quitarse el último acceso administrativo.
- La interfaz compilada en AWS sigue limitada a listar y crear usuarios. En local `/platform` permite editar rol/empresa/estado y restablecer claves con revelado único; falta publicarla tras validar el bundle y el rollback.
- Falta invitación de usuarios, recuperación asistida, MFA y, si se desea, SSO corporativo.
- El rate limit actual vive en memoria de cada instancia; con dos EC2 no es un contador global. Se recomienda un almacén compartido y una política de bloqueo temporal consistente.
- Definir y probar matriz formal de permisos por vista y acción, especialmente auditoría, datos multiempresa y grabaciones.

### Prioridad 4 — frontend mantenible y pruebas de navegador

- AWS sirve un bundle frontend compilado. La fuente exacta del SPA no se recuperó; por eso no se reemplazó el bundle. Se agregó en local una página independiente `/platform` para telemetría, usuarios y conciliación WMS, manteniendo el frontend existente.
- No compilar `app/web` sobre el release: se perderían vistas actuales. El siguiente paso seguro es reconstruir React/CSS desde el bundle y validarlo con pruebas antes de reemplazarlo.
- Faltan versiones fijadas de dependencias, build reproducible, source maps privados y pruebas Playwright/Cypress para sesión/roles, llamadas y grabaciones.
- Las pruebas API confirman que `/platform` y sus APIs de telemetría/conciliación están restringidas por rol; CloudWatch se prueba con cliente falso. Aún falta prueba de navegador del módulo y de llamada WebRTC real.
- Falta auditoría de accesibilidad (teclado, contraste, foco, labels), tamaños móvil/tablet, estados vacíos y fallos de red.

### Prioridad 5 — integrar un WMS/ERP real

- El ledger de Azure permite demostrar SKU/cantidad, stock insuficiente, concurrencia e idempotencia con datos ficticios. No debe mostrarse como inventario o despacho real.
- Para conectar un ERP/WMS se requieren contrato de SKU/cantidad/almacén, autenticación del sistema destino, idempotencia y deduplicación de negocio, estados de aceptación/rechazo, compensación, alertas y pruebas con datos autorizados.
- Conectar un WMS auténtico requiere contrato e integración autorizados; verificar un stock de laboratorio no sustituye la prueba contra el sistema dueño del inventario.

### Prioridad 6 — seguridad, resiliencia y operación

- La aplicación tiene CSRF, cookies HttpOnly/SameSite, cabeceras, límites de tamaño, hash de eventos, IAM acotado y WAF. Pendiente: Secure cookie al cerrar TLS, MFA/SSO, rate limit distribuido, despliegue de la revocación de sesiones, revisión de sesiones y política formal de borrado de grabaciones.
- RDS tiene Multi-AZ y 7 días de backup, pero no hay evidencia de una restauración probada ni de RTO/RPO aprobados.
- Falta una prueba controlada de fallo de Azure, reintento/outbox, DLQ/poison message, recuperación y alertas con notificación efectiva.
- Hace falta CI/CD que ejecute ambas suites, escanee dependencias/secretos, firme/versione artefactos, cree un cambio revisable, despliegue gradual y permita rollback.
- El artefacto frontend está en S3 versionado, pero reconciliar artefacto, fuente Git y plantilla viva es pendiente. La plantilla local `iac/cloudformation/aws-lab.yaml` difiere de la activa (por ejemplo, declara RDS con `MultiAZ: false`/retención 1 día mientras el recurso vivo se verificó con Multi-AZ/7 días). Las actualizaciones recientes preservaron la plantilla remota usando `--use-previous-template`; **no desplegar la plantilla local completa hasta reconciliarla**.
- Falta sincronizar/publicar estos cambios en GitHub. No se hizo commit ni push durante esta ejecución.

## 4. Orden recomendado para cerrar

1. Completar la prueba A/V local al permitir micrófono/cámara en las dos sesiones; registrar solo resultados técnicos, sin grabar la conversación.
2. Recuperar la fuente frontend, conectar `ice-config` y validar en navegador los módulos desplegados de plataforma/usuarios/WMS; el endpoint existe, pero falta la regresión autenticada de interfaz.
3. Si la ruta directa falla, evaluar TURN en un entorno de costo controlado; no hay relay desplegado todavía.
4. Aprobar un contrato de WMS real o mantener el estado simulado explícito; hoy la conciliación está visible localmente y falta validarla con eventos autorizados en navegador.
5. Reconciliar IaC con la infraestructura activa, probar restore/failover y automatizar releases/rollback.
6. **Al final:** dominio, DNS y certificado ACM válido; activar cookie Secure y validar HTTPS completo.

## 5. Referencias de Azure

- [Modelo Python v2 y parámetros de ruta](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python): las rutas se leen desde `HttpRequest.route_params`; no se agregan como argumentos separados.
- [Opciones de build para Python en Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/python-build-options): el build remoto instala dependencias de `requirements.txt` en el entorno Linux de Azure.
