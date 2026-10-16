# Plan maestro de pruebas AWS–Azure

**Corte vigente:** 16/10/2026, 08:53–09:01 UTC. Los antecedentes conservan su fecha;
una prueba histórica no sustituye una revalidación cuando hubo cambios.

## Estado actual

- Revalidación 08:53–09:01 UTC: E2E AWS→Azure pasó con ledger demo 10→10;
  Admin read-only reconcilió 61/61 eventos, cero pendientes y 24/24 lecturas
  HTTP 200. Health público HTTPS de AWS y Azure respondió 200; ASG quedó 2/2
  `InService`/`Healthy`, stack `UPDATE_COMPLETE`, drift reportado `IN_SYNC`.
- Smoke ERP en vivo: 48/48 pruebas de autorización para Admin, Ventas,
  Finanzas, Compras, Datos Maestros y Auditoría. Cuatro cuentas QA quedaron
  desactivadas y verificadas; las solicitudes de escritura se detuvieron en
  validación 400 y no crearon documentos de negocio.
- Gate local completo: `QUALITY_GATE=APROBADA`, 225 pruebas Python, 14 Node,
  40 transacciones aisladas, build, auditorías, CloudFormation y Terraform
  formato/init/validate/tests. Sin `apply`. Detalle en
  [revalidación 09:01](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0901UTC.md).
- Siguen abiertos recorrido visual por rol/CSV, reintento live inducido,
  WebRTC entre dos navegadores, carga sostenida, WAF, failover Multi-AZ,
  conectividad privada (SCP deniega `CreateCustomerGateway`) y atribución Azure.

- Revalidación viva 08:43–08:46 UTC: STS aceptado; CloudFormation
  `UPDATE_COMPLETE`/`IN_SYNC`; ASG 2/2 sano y discos raíz cifrados; HTTPS 200,
  HTTP→HTTPS 301. E2E AWS→Azure pasó (venta/recepción, 2 eventos, ledger
  sintético 10→10); `admin-readonly` pasó con outbox 59/59, 0 pendientes,
  matriz Comercial/Operaciones 200/403 y 24/24 lecturas 200. El p95 fue
  585.97 ms en la prueba solo lectura y 225.67 ms en el E2E; son smokes cortos,
  no capacidad sostenida. No hubo cambios IaC.
- Preflight de interconexión: el `--dry-run` de `CreateVpnGateway` fue permitido,
  pero `CreateCustomerGateway` fue denegado explícitamente por una SCP de AWS
  Organizations; Azure tiene suscripción activa y `Microsoft.Network`
  registrado, pero no tiene VNets del proyecto. No se creó infraestructura ni
  se inició costo VPN. Véase el
  [corte 08:46 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0846UTC.md).
- El despliegue conserva cifrado: ambos volúmenes raíz EBS activos reportan
  `Encrypted=true`. No se necesita excepción sin cifrado ni autorización para
  retirarlo.

- Revalidación viva 07:59–08:08 UTC: AWS STS aceptado; CloudFormation
  `UPDATE_COMPLETE`, detección fresca `IN_SYNC` (0 drift), ASG y destinos ALB
  2/2 sanos, volúmenes raíz cifrados; RDS disponible/cifrado, Single-AZ y
  backup 1 día. HTTPS del portal respondió 200 y HTTP redirigió 301; Azure
  Function `Running`/HTTPS-only y health 200; Terraform Azure
  `plan -refresh-only` y el plan normal sin cambios, usando sus variables
  locales protegidas y sin `apply`. Véase el
  [corte cloud 08:08](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0808UTC.md).
- E2E AWS→Azure 08:00 UTC pasó venta/compra sintéticas y dos entregas; ledger
  ficticio 10→10. Application Insights correlaciona ambos `event_id` con
  workers `success=true`, `resultCode=0`. Admin de solo lectura reconcilió
  57/57 eventos, cero pendientes, 24/24 lecturas 200 (p95 243.2 ms); Admin
  módulos aprobó Finanzas S/ 0.05 `paid`, correo interno portal-only y poison
  count 0 sin exponer payloads. No se aplicó ni reinició infraestructura.
- Las limitaciones de capacidad, red privada, failover, fallo live del outbox,
  WAF, CSV/recorrido visual, WebRTC y coste Azure permanecen abiertas; no se
  presentan como verificadas.

- Revalidación 06:39–06:54 UTC: AWS STS aceptó el token; stack
  `UPDATE_COMPLETE`; drift fresco `IN_SYNC` (06:53:38); ASG con dos
  `InService`/`Healthy`, dos targets `healthy`, health HTTPS 200. El incidente
  KMS de las 06:07 no se corrigió con una excepción: el mismo template y
  Launch Template cifrado volvió a lanzar correctamente. CloudTrail registró
  detención de dos instancias anteriores por `vocareum/resource`; una prueba
  SSM pendiente en una de ellas no llegó a iniciar y se canceló. El smoke
  `admin-modules` pasó después en una instancia sana.
- Smoke de módulos Admin desde EC2 por HTTPS: gasto sintético 0.05 persistido
  y liquidado; correo del portal enviado y leído en modo `portal_only`, sin
  SMTP externo; endpoint Azure de poison queue devolvió count 0 y ningún
  payload. No se ejecutó pago real ni se modificó inventario físico.
- E2E completo AWS→Azure: venta y compra sintéticas compensadas, saldo demo
  10→10, dos eventos entregados, matriz de permisos API y 24/24 GET 200 con
  concurrencia 6 (p95 346.89 ms). No equivale a carga sostenida ni a soporte
  comprobado para 3,000 usuarios.
- Azure: suscripción `Enabled`, Function `Running`/HTTPS-only y `/api/health`
  200 a las 06:54 UTC.
- Evidencia consolidada:
  [revalidación de nube 06:54 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0654UTC.md).
- La puerta integral local terminó `QUALITY_GATE=APROBADA` a las 07:02 UTC:
  218 pruebas unitarias, 14 Node, 40 transacciones aisladas, build,
  dependencias, CloudFormation y validaciones/tests Terraform. Sin operaciones
  de nube. [Registro QA](../evidence/current/QA-LOCAL-2026-10-16-0702UTC.md).
- Reconsulta a las 07:03: ASG estable con exactamente 2/2 instancias y targets
  sanos; los health endpoints públicos de AWS y Azure devolvieron 200.
- Revalidación 07:10–07:22: AWS STS válido, CloudFormation `UPDATE_COMPLETE` y
  detección de drift fresca `IN_SYNC` (cero recursos); ASG 2/2 y RDS disponible.
  Azure `/api/health` respondió 200 y Terraform remoto `-refresh-only` indicó
  `No changes`. En Chrome se recorrieron módulos del portal con sesión Admin.
  La carga externa de 300 solicitudes fue bloqueada por Cloudflare 1010 y no
  midió la aplicación. Detalle en el
  [corte cloud 07:22 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0722UTC.md).
- Prueba desplegada AWS→Azure 07:28–07:29: venta `completed_demo`, compra
  `received_demo`, dos eventos confirmados y ledger de demo 10→10; health de
  RDS `ok`. El smoke Admin posterior comprobó 55/55 eventos entregados, cero
  pendientes, matriz de roles 200/403 y 24/24 GET con p95 511.97 ms. No es una
  prueba de carga sostenida. Véase el
  [corte cloud 07:30 UTC](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0730UTC.md).
- Puerta local integral 07:31–07:36: `QUALITY_GATE=APROBADA`, 218 pruebas
  Python, 14 Node, 40 transacciones aisladas, build Vite, auditorías de
  dependencias, CloudFormation lint y Terraform fmt/validate/tests. No se
  aplicó infraestructura; véase el
  [registro QA 07:36 UTC](../evidence/current/QA-LOCAL-2026-10-16-0736UTC.md).
- Puerta local integral 07:42–07:48: `QUALITY_GATE=APROBADA`, 222 pruebas
  Python, 14 Node y todas las validaciones frontend/CloudFormation/Terraform;
  incluye 4 pruebas nuevas del ciclo outbox 503→backoff→recuperación. Sin
  `apply`. Véase el
  [registro QA 07:48 UTC](../evidence/current/QA-LOCAL-2026-10-16-0748UTC.md).
- Smoke autenticado desde el equipo local hacia el origen ALB por HTTPS 07:39:
  24/24 HTTP 200, p95 599.37 ms; sin modificar Cloudflare. El límite sigue
  siendo carga corta, no capacidad sostenida.
- GitHub Actions del commit `f453cba` terminó 3/3 checks aprobados. En el
  commit previo `c61a07c`, el runner de infraestructura falló únicamente al
  instalar el lock, antes de ejecutar CloudFormation/Terraform; el commit
  anterior y el nuevo pasaron. Se añadió cache/reintento pip. [Checks del
  commit](https://github.com/kyrafka/tangamandapio-cloud-migration/commit/f453cba/checks).

- El token AWS más reciente quedó actualizado en `default` y STS lo aceptó a
  las 06:13 UTC para la cuenta académica `841113066612`. Esto reemplaza el
  rechazo (`InvalidClientTokenId`) del token anterior, observado a las 06:04.
- La lectura autenticada de 06:14–06:16 encuentra CloudFormation
  `UPDATE_COMPLETE` (último cambio 00:27:59), ALB `active`, ASG mínimo/deseado
  2 y máximo 5 **sin instancias**, y target group sin destinos. Los dos
  lanzamientos de las 06:07 terminaron con `Client.InternalError` en ambas AZ;
  CloudTrail acepta `RunInstances` pero no expone la causa final, y la consola
  EC2 no ofreció salida para esas instancias terminadas. El 503 ya no queda
  solo como un síntoma: el target group vacío lo explica. A las 06:16 aún no se
  había identificado la falla raíz; se determinó después con CloudTrail KMS.
  No se modificó AWS. Véase el
  [corte AWS 06:22](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0622UTC.md).
- La verificación pública más reciente (05:44–05:58 UTC) cambia el estado
  operativo: dominio HTTPS con TLS válido, pero `/` y `/health` responden 503.
  El ALB directo confirma 503 en 443 y 301 en 80→443. Por eso el estado 2/2 de
  instancias y destinos sanos que sigue corresponde a la última lectura
  autenticada de 05:00, no a una condición vigente confirmada. El estado del
  ASG/target group y la causa del 503 quedan pendientes de lectura con credencial
  aceptada. Detalle:
  [corte de disponibilidad 05:58](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0547UTC.md).
- El inventario AWS sano de las 05:00 UTC es histórico y fue seguido por una
  falla de lanzamiento: ahora hay cero instancias y cero destinos sanos.
- A las 05:02:29 UTC el dominio HTTPS `/health` devolvió `200`; la respuesta
  pública mostró HSTS. La última lectura AWS autenticada verificó HTTP→HTTPS
  (`301`). Azure CLI reporta el grupo `Succeeded` y la Function `Running` /
  HTTPS-only; GET `/api/health` devolvió 200 con TLS verificado. HEAD dio 404
  en el corte 05:09; se corrigió y publicó a las 05:15. A las 05:18 GET y HEAD
  devolvieron 200 con TLS verificado y HEAD sin cuerpo. Terraform posterior:
  `No changes`.
- A las 05:37 UTC pasó de nuevo el E2E compensado ERP local→Azure después del
  despliegue de health: guardas 401/400, venta/reposición sintéticas,
  reconciliación ERP y saldo ficticio de vuelta a la línea base; poison count
  cero antes/después. Application Insights reportó dos ejecuciones correctas
  del worker y cero fallidas en la ventana de 20 minutos (conteo agregado).
  No fue tráfico originado desde EC2/RDS.
- Entre 05:45 y 05:47 UTC se repitió el E2E local→Azure: Function `Running`,
  salud 200, guardas 401/400, venta y reposición demo completadas, saldo
  restaurado y poison count cero antes/después. Los eventos quedan en auditoría
  Azure; la prueba no usó EC2 ni RDS.
- A las 05:57 UTC, el plan Terraform de `azure-rebuild` consultó el backend
  remoto y terminó `No changes`; no se ejecutó `apply`. AWS no se pudo planear
  ni consultar por el rechazo de STS.
- A las 06:00 UTC, ARM enumeró diez recursos en el grupo de reconstrucción
  Azure: Function, plan, Storage, Key Vault, Log Analytics, Application
  Insights, dos alertas métricas y dos Action Groups.
- A las 06:04 UTC, el token anterior fue rechazado por AWS STS. El token nuevo
  sí quedó guardado en el perfil local `default` y autenticó a las 06:13 UTC.
- A las 06:09 UTC, el E2E compensado local→Azure volvió a pasar: outbox
  entregado, venta `demo_fulfillment_completed`, recepción
  `demo_restock_completed`, ledger ficticio restaurado, salida 0. IDs de
  auditoría `evt-0cf05101ca0942a09ff51610ba99ab4c` y
  `evt-795a36230f7843c7978b675dbae3d58d`. No es origen EC2/RDS.
- La sonda de las 06:22 UTC devolvió HTTP 503 para el health público del portal
  (Cloudflare) y HTTP 200 para la Function Azure.
- La investigación KMS de las 06:24–06:28 encontró en CloudTrail dos `Decrypt`
  denegados por una SCP de Academy. La plantilla pide cifrar el volumen raíz.
  Esa propuesta local de excepción temporal se retiró luego; el corte actual
  confirma que el mismo Launch Template cifrado volvió a iniciar sin cambiar la
  plantilla. No se quitó el cifrado. Detalle en el
  [diagnóstico KMS](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0628UTC.md).
- Después del cambio, la puerta local completa aprobó 218 pruebas unitarias,
  14 Node, 40 transacciones aisladas, build, auditorías, CloudFormation y
  Terraform; no se aplicaron recursos cloud.
- La puerta integral local a las 05:37 aprobó 216 pruebas Python, 14 Node,
  build/auditorías, CloudFormation y Terraform `fmt`/`validate`, sin mutaciones
  cloud.
- El E2E desplegado AWS→Azure completó venta/compra sintéticas y dejó el saldo
  demo 10→10; el outbox quedó 51/51 entregado, cero pendiente. La prueba Admin
  de solo lectura ejecutó 24 GET autenticados, concurrencia 6, p95 217.69 ms;
  los permisos API Comercial/Operaciones dieron los 200/403 esperados.
- RDS sigue disponible, cifrada y privada, Single-AZ con un día de backup.
  PT-DR-01 pasó en esta sesión: restore aislado, RTO 289 s, RPO observado ≤10 s,
  marcador verificado y recursos temporales limpiados. Failover/Multi-AZ no se
  probó.
- En la consulta de 04:24 UTC, las cinco alarmas estaban `OK`. La alarma de
  5xx no recibió datapoints y los faltantes cuentan como `NonBreaching`, así que
  su estado no demuestra que haya observado tráfico. El ciclo sintético de SNS
  y recepción/recuperación ya pasó el 14/10.
- Pruebas sintéticas históricas demostraron scale-out e in 2↔3; falta carga
  transaccional medida a través del ALB. No se afirma capacidad para 3,000
  usuarios.
- La prueba Admin de solo lectura ejecutó 24 GET autenticados al origen ALB con
  concurrencia 6: 24/24 HTTP 200, p95 217.69 ms. Es un smoke pequeño, no un
  benchmark de capacidad ni una prueba de 3,000 usuarios.
- En una sonda reciente, Python `urllib` recibió 403 de Cloudflare (3/3; la
  corrida anterior fue 25/25), mientras `curl` e `Invoke-WebRequest` al mismo
  health recibieron 200. No se cambió ni se sorteó la regla del proxy. La
  métrica de latencia de esas respuestas 403 no representa rendimiento del
  origen.
- WAF regional no está desplegado. No existe ruta privada AWS–Azure: AWS
  Academy denegó Customer Gateway por SCP y no hay VNet Azure del proyecto.
- El template local CloudFormation usa defaults v18 y los parámetros efectivos
  del stack también son v18; el template guardado en AWS conserva tres defaults
  de artefacto v16. La comparación no encontró diferencias de recursos; no se
  forzó una actualización vacía. Terraform está validado localmente, sin `apply`.
- La evidencia agregada de Azure consultada mostró 4 recepciones 202 y 4
  ejecuciones correctas de la Function (`resultCode=0`) en una hora; un 400
  esperado por origen inválido y ningún fallo observado en esos eventos. El
  poison queue quedó en cero por consulta de metadatos, sin leer ni eliminar
  mensajes. No se correlacionaron los conteos con IDs de evento ni se disparó
  una alarma por métrica real.
- El recorrido visual de Chrome 07:10–07:22 se hizo con sesión Admin; Comercial,
  Operaciones y CSV aún no se probaron visualmente. WebRTC entre dos navegadores
  tampoco está probado recientemente.
- La revisión de rúbrica sigue ambigua: la hoja del proyecto suma 18.5 aunque
  declara 20; el PDF general es otro instrumento con máximos que suman 90. No
  se combinan las escalas ni se inventa una nota.
- La compuerta local recién repetida pasó 215 pruebas unitarias, 14 Node,
  frontend/build, auditorías, CloudFormation, Terraform y cinco pruebas mock;
  no aplicó cambios cloud. GitHub Actions para `b1d36a9` también pasó sus tres
  trabajos (run `38851449937`).

## Matriz de pruebas

| ID | Prueba | Estado verificado | Qué falta |
|---|---|---|---|
| PT-HTTPS-01 | Dominio, TLS y redirect | Health público HTTPS 200 a las 08:08; HTTP redirige 301; HSTS presente | Mantener monitoreo TLS/DNS; carga automatizada previa bloqueada por Cloudflare 1010 antes de llegar a la app. |
| PT-AWS-01 | Salud y disponibilidad | STS acepta token; stack `UPDATE_COMPLETE`, drift fresco `IN_SYNC` (0, 07:59), ASG/targets 2/2 sanos y raíz cifrada; portal disponible | ASG permanece en su mínimo 2; no hay prueba actual de failover regional. |
| PT-AWS-02 | Login y roles | API Admin, Comercial y Operaciones pasó 200/403 por TLS en smokes 08:00–08:03 | Recorrido visual por rol no confirmado en este corte: Chrome automatizado no pudo determinar la URL activa. |
| PT-WMS-01 | ERP→AWS→Azure→ledger sintético | E2E desplegado 08:00: venta `completed_demo`, compra `received_demo`, dos eventos entregados y ledger 10→10; Application Insights correlacionó cada `event_id` con worker `success=true`/`resultCode=0` | Integración es un WMS/ledger ficticio; conectarlo a un WMS autorizado queda fuera del demo. |
| PT-OUTBOX-01 | Historial paginado | Smoke Admin 08:01 reconcilió 57/57 entregados y cero pendientes | Verificar visualmente paginación en Chrome y revisar conjuntos mayores. |
| PT-RETRY-01 | Reintento y poison | Barrido automático a 60 s, máximo 10 intentos, backoff capado a 1 h (primera espera 120 s); cuatro pruebas aisladas cubren HTTP 503, backoff y recuperación; poison count 0 sin exponer payloads | Falla transitoria inducida y recuperación live aún pendientes; no se leyó ni manipuló poison message. |
| PT-DR-01 | Backup/restore/failover | Restore aislado histórico: RTO 289 s, RPO observado ≤10 s; marcador y limpieza verificados | RDS Single-AZ y backup 1 día; failover no probado en este corte. |
| PT-NET-01 | Red privada AWS–Azure | E2E usa HTTPS público | VNet/ruta privada ausente; SCP bloquea Customer Gateway en AWS Academy. |
| PT-PERF-01 | Carga y escalado | 24 GET autenticados por ALB HTTPS 24/24 HTTP 200, concurrencia 6, p95 243.2 ms | Carga sostenida y observar 2↔3; no se afirma soportar 3,000 usuarios. |
| PT-SEC-01 | Seguridad y navegador | TLS, cookies `Secure`/`HttpOnly`, controles de rol por API, SNS y auditoría activos; centro de nube declara WAF no desplegado | WAF ausente; recorrido con roles no-admin/CSV pendiente. Cloudflare bloqueó User-Agent de prueba; no se desactivó ni eludió. |
| PT-AZ-MON-01 | Invocaciones y alertas | E2E 08:00: dos recepciones 202 y dos ejecuciones `process_fulfillment_message` exitosas; correlación exacta por `event_id`/`operation_Id`; alertas 5xx/latencia habilitadas | Confirmar entrega real de una alarma Azure; la prueba 08:00 no disparó alarma nueva. |
| PT-IAC-01 | CloudFormation/Terraform | Drift CloudFormation `IN_SYNC` (0) a las 07:59; Terraform Azure refresh-only y plan normal: `No changes` con valores locales protegidos | No hay cambios IaC pendientes en este corte; no desplegar planes vacíos. |
| PT-APP-01 | CSV, correo y finanzas | Smoke Admin 08:03: Finanzas sintética S/0.05 liquidada; correo interno enviado/leído (`portal_only`, sin SMTP); tres cuentas/roles y auditoría | CSV y recorrido visual de cada rol pendientes; SMTP externo no configurado ni afirmado. |
| PT-RTC-01 | WebRTC | UI lista 2 extensiones, 3 llamadas históricas y 1 grabación de audio | Prueba de audio/video bidireccional entre dos navegadores. |
| PT-COST-01 | Costos | AWS con créditos Academy que compensan el consumo medido | Importe Azure fiable y atribución por proyecto. |
| PT-DOC-01 | Evidencia/entrega | Puerta local 07:48 aprobada (222 Python, 14 Node, CloudFormation/Terraform); smokes cloud 08:00–08:03 y CI `f453cba` 3/3; nuevo corte documentado | Capturas recientes de inventario AWS y monitor Azure; defensa oral. |

La revalidación más reciente está en
[`CLOUD-REVALIDATION-2026-10-16-0808UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0808UTC.md); la puerta local 07:48 está en
[`QA-LOCAL-2026-10-16-0748UTC.md`](../evidence/current/QA-LOCAL-2026-10-16-0748UTC.md).

## Secuencia de cierre

1. Si la sonda Python a través de Cloudflare sigue siendo necesaria, revisar la
   regla del proxy con su administrador; el test al origen ALB ya separa el
   rendimiento de la app del 403 del proxy. No desactivar controles a ciegas.
2. Completar recorrido Chrome de roles, módulos ERP y carga CSV cuando el control
   de ventana pueda identificar la URL activa.
3. Definir objetivo de capacidad y correr carga sostenida de bajo impacto por
   ALB con datos sintéticos, límites aprobados, reconciliación y limpieza
   documentada; observar el escalado gradualmente.
4. Investigar el fallo EC2/ASG con evidencia de la cuenta/lab; no sustituir AMI,
   plantilla o permisos hasta confirmar la causa. Luego generar change set y
   revisar cada reemplazo antes de ejecutarlo.
5. Revisar costo/permiso antes de Multi-AZ, WAF o VPN; no crear rutas privadas si
   la SCP/ausencia de VNet sigue bloqueando el diseño.
6. Capturar evidencia AWS/Azure, terminar prueba WebRTC si sigue en el alcance y
   pedir al docente aclaración de rúbrica/ponderación.

La validación E2E, recuperación, HTTPS y estado de Function de este corte se registra en
[`CLOUD-E2E-DR-2026-10-16-0500UTC.md`](../evidence/current/CLOUD-E2E-DR-2026-10-16-0500UTC.md).
La corrección de la sonda y su validación viva se registra en
[`AZURE-HEALTH-HEAD-DEPLOY-2026-10-16-0519UTC.md`](../evidence/current/azure/AZURE-HEALTH-HEAD-DEPLOY-2026-10-16-0519UTC.md).
La puerta local y el E2E compensado posteriores están en
[`QA-LOCAL-2026-10-16-0537UTC.md`](../evidence/current/QA-LOCAL-2026-10-16-0537UTC.md) y
[`AZURE-ERP-E2E-2026-10-16-0537UTC.md`](../evidence/current/azure/AZURE-ERP-E2E-2026-10-16-0537UTC.md).
La revalidación previa y el smoke de lectura siguen en
[`CLOUD-REVALIDATION-2026-10-16-0400UTC.md`](../evidence/current/CLOUD-REVALIDATION-2026-10-16-0400UTC.md).
El smoke autenticado y la sonda de lectura del 16/10 se registran en
[`AWS-READONLY-LOAD-2026-10-16-0424UTC.md`](../evidence/current/aws/AWS-READONLY-LOAD-2026-10-16-0424UTC.md).
