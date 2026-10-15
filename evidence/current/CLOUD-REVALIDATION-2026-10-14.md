# Revalidación cloud — 14/10/2026

> **Corte vigente: 15/10/2026, 00:16 UTC.** Este documento conserva cortes
> cronológicos previos; el registro más reciente confirma v11 desplegado,
> CloudFormation `UPDATE_COMPLETE`, drift `IN_SYNC`, dos EC2 `InService` con
> v11, dos destinos ALB `healthy` y `/`, `/health`, `/ready` en HTTP 200. Dos
> instancias reemplazadas aún completan el drenaje. Consulta la sección
> “Revalidación final v11” al final y el [registro de despliegue](aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

## Lectura final de estado — 14/10/2026, 14:52–15:27 America/Chicago

AWS STS aceptó nuevamente el perfil local. CloudFormation permaneció en
`UPDATE_COMPLETE`; una detección nueva terminó `IN_SYNC` a las 14:54:31.
El ASG mantuvo 2/2 instancias `InService`, sus dos destinos del ALB estaban
`healthy` y los endpoints `/`, `/health` y `/ready` respondieron HTTP 200.
La base `tangamandapio-postgres` está `available`, cifrada, no pública,
Single-AZ y con retención de backups de un día.

Azure CLI confirmó `tangama-wms-261008` `Running` y HTTPS-only; su endpoint
`/api/health` respondió 200. Los health checks locales de `127.0.0.1:8080` y
`:8081` también respondieron 200. Esta relectura fue solo de estado y salud;
no se modificaron recursos ni datos.

## Estado después de las pruebas — 14/10/2026, 15:35–15:36 America/Chicago

La sesión AWS siguió válida; ASG quedó en deseado/mínimo 2, con dos EC2
`InService`/`Healthy`; los dos targets del ALB están `healthy` y sus rutas
`/health` y `/ready` dan HTTP 200. La pila CloudFormation sigue
`UPDATE_COMPLETE`; detección de drift completó `IN_SYNC` a las 15:36:04. Las
alarmas alta y baja de Target Tracking están `OK`. Azure Function sigue
`Running`/HTTPS-only y `/api/health` devuelve 200. No quedó la instancia
temporal ni una carga de prueba activa.

## Pruebas de escalado horizontal — 14/10/2026, 15:04–15:27 America/Chicago

Primero se solicitó temporalmente capacidad 3 para validar el ciclo EC2→ASG→
ALB. El nuevo nodo entró `InService`/`Healthy`; luego se restauró el deseado 2.
El ALB lo drenó durante los 300 s configurados y la instancia terminó sin
afectar a los otros dos destinos.

Después se probó Target Tracking automáticamente: dos workers CPU por instancia
durante 240 s, sin tocar pedidos ni catálogo. La alarma alta CPU 60% pasó de
`OK` a `ALARM` a las 15:19:21; la actividad del ASG confirma que esa alarma
activó la política y cambió el deseado 2→3. El tercer EC2 entró `InService` y
su target pasó a `healthy`. La sonda terminó con estado SSM `Success`; la alarma
volvió a `OK` a las 15:21:21. Se fijó deseado 2 para limpieza, el nodo temporal
terminó tras drenaje, los dos targets finales están `healthy` y la detección
CloudFormation terminó `IN_SYNC` a las 15:27:50. `/health` y `/ready` siguieron
en HTTP 200.

Esta prueba demuestra el mecanismo de escalado y la incorporación/retirada de
capacidad bajo carga CPU sintética. No es una carga de ventas por ALB/RDS ni
demuestra 3,000 usuarios. Los intentos de reemplazo cancelados anteriores con
`Client.InternalError` no se reprodujeron, pero su causa histórica sigue sin
confirmación. El reporte sanitizado se conserva en
[`AWS-AUTOSCALING-TEST-2026-10-14.json`](aws/AWS-AUTOSCALING-TEST-2026-10-14.json).

## E2E autenticado desde el portal AWS desplegado — 14/10/2026, 14:56–14:58

Se ejecutó por SSM en una EC2 activa el arnés
`tests/cloud/live_aws_portal_azure_e2e.py`, contra el runtime desplegado v10 y
la base RDS. Terminó `LIVE_E2E_PASSED`: el catálogo aceptó el SKU sintético
`SKU-QA-V10-20261014`; una venta completó (`completed_demo`) y la recepción
compensatoria completó (`received_demo`); ambos eventos outbox quedaron
`delivered`; el ledger Azure volvió de 10 a 10. La prueba conserva los pedidos
y sus eventos de auditoría de QA en RDS/Azure, pero no modifica infraestructura
ni representa existencias reales.

Admin inició sesión, obtuvo la autorización ERP y completó la venta/recepción.
Comercial y Operaciones pasaron sus rutas esperadas 200/403. Hubo 24/24
lecturas autenticadas 200, concurrencia 6 y p95
1,360.41 ms, realizadas contra `127.0.0.1:8080` dentro de EC2; no pasan por el
ALB y no prueban escalado. El reporte sanitizado está en
[`AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json`](aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json).

Application Insights se consultó otra vez con una agregación sin payloads: en
los diez minutos alrededor del E2E aparecen 2 solicitudes
`receive_fulfillment_event` HTTP 202 y 2 ejecuciones
`process_fulfillment_message` `resultCode=0`, cero fallidas; la más reciente
fue `2026-10-14T19:57:57Z`. Esto corrobora el trabajo del consumidor Azure,
además del estado final consultado por el portal.

## Corte revalidado — 14/10/2026, 14:30–14:51 America/Chicago

Se actualizó el perfil local AWS `default` con el token temporal que entregó el
usuario; STS autenticó en la cuenta académica. No se guardó el token en el
repositorio ni se mostró en la evidencia.

CloudFormation `tangamandapio-live-20261013` devolvió
`UPDATE_COMPLETE`; una detección de drift terminó `IN_SYNC`. El ALB estuvo
`active`, con 2/2 destinos `healthy`. La portada, `/health` y `/ready`
devolvieron HTTP 200; `/api/admin/users` sin sesión devolvió 401. El ASG
conservó mínimo/deseado 2 y máximo 4; ambas instancias estuvieron
`InService`. RDS está `available`, privada, cifrada, Single-AZ y con un día
de backup automático.

Una microprueba posterior por el ALB hizo 60 solicitudes de solo lectura a
`/health`, concurrencia 6: 60/60 HTTP 200, p95 447.61 ms y máximo 525.96 ms.
El ASG permaneció en 2/2 (mínimo 2, máximo 4) y ambos targets siguieron sanos.
Hay una política Target Tracking de CPU media con objetivo 60%; la prueba no
elevó suficiente carga para dispararla y no demuestra capacidad de 3,000
usuarios ni escalado dinámico.

SSM ejecutó solo lecturas en ambas EC2: versión
`20261014-synthetic-catalog-v10-python312`, servicio activo, y los hashes
completos locales/remotos coincidieron exactamente:

| Archivo | SHA-256 |
|---|---|
| `app.py` | `f8b0d1b9a733581936a21320a5e81a36a9c0132000b2010f131adb0e72aa1ee5` |
| `erp_service.py` | `8b07c5528a30ff4738d08c442d0936e0ea70f81ff2f0da6727f13231583d7b1a` |
| `requirements.lock` | `b93d99918791772134a7fa1da366ee0d1859f39e9cd4f535406d6573ea018a9b` |

Azure CLI confirmó la suscripción habilitada, la Function
`tangama-wms-261008` `Running`/HTTPS-only y `/api/health=200`. Application
Insights (ventana de 30 minutos) mostró dos recepciones de evento HTTP 202,
dos ejecuciones exitosas de `process_fulfillment_message` y cero fallos. La
ruta de solo metadatos `/api/wms/poison-queue`, llamada con la Function key en
memoria, devolvió conteo aproximado 0 y `payloads_exposed=false`; no se leyó ni
alteró ningún mensaje. El acceso directo de la identidad local al Storage
Queue sigue denegado y no se amplió RBAC.

Las dos reglas Azure Monitor y el Action Group estaban habilitados; los dos
receptores figuran `Enabled`, lo cual no prueba entrega. CloudWatch mostró sus
cinco alarmas en `OK`, acciones habilitadas y dos suscripciones SNS
confirmadas; el usuario había confirmado recepción de la prueba SNS de
recuperación.

Terraform 1.16 ejecutó un plan normal de solo lectura contra
`iac/environments/azure-rebuild`: `No changes`, salida 0, sin plan guardado ni
`apply`. El hash ARM `DEPLOYMENT_PACKAGE_SHA256` coincide con el ZIP fijado
por `rebuild.tfvars.example` (prefijo `364cf88c`). No se encontró ninguna
VNet en la suscripción Azure activa ni integración VNet de la Function. El
preflight de Tailscale encontró el CLI, pero no una sesión conectada, clave
efímera ni VNet dedicada; no se creó red. El corte del ALB 503 de las 13:11
queda supersedido por los health checks 200 actuales.

No se hicieron cambios de infraestructura. La compuerta local terminó
`QUALITY_GATE=APROBADA`: 163 pruebas Python, 14 Node, PT-PERF-02 40/40,
frontend construido, auditoría de dependencias sin vulnerabilidades conocidas,
CloudFormation validada y Terraform formateado/validado/testeado.

## Revalidación de configuración de alertas Azure — 08:08 America/Chicago

Azure CLI volvió a confirmar la suscripción `Azure for Students` como
`Enabled` y la Function `tangama-wms-261008` como `Running`. La lectura del
Action Group `tangama-ops-ag` encontró dos receptores de correo habilitados;
no se imprimieron ni copiaron sus direcciones. También confirmó habilitadas
`tangama-wms-fn-5xx` (severidad 2, métrica `Http5xx`) y
`tangama-wms-fn-latency` (severidad 3, métrica `HttpResponseTime`), cada una
con una acción asociada.

La confirmación del usuario sobre recepción de alerta y recuperación
corresponde a la prueba sintética SNS de AWS documentada en
[`AWS-ALARM-TEST-2026-10-14.md`](aws/AWS-ALARM-TEST-2026-10-14.md); no se
atribuye a Azure. En esta revalidación Azure no se disparó una regla ni se
verificó entrega de correo. Solo se leyó configuración, sin cambios en Azure.

Después, Terraform 1.16.0 consultó el root `azure-rebuild` contra ARM con los
dos archivos de variables requeridos y terminó `No changes` (salida 0) a las
08:14–08:15. No se guardó un plan aplicable ni se ejecutó `apply`; Azure sigue
reconciliado con ese root en este corte.

## Intentos posteriores y estado de sesión — 07:05–07:39 America/Chicago

Una llamada de solo lectura a AWS STS devolvió `ExpiredToken`; no se ejecutaron
más llamadas AWS con esa sesión. Chrome rechazó la automatización antes de
leer la consola porque no pudo confirmar la URL actual; no se pulsó ningún
control. Por eso el corte de 06:46 de abajo es el último inventario de nube
confirmado, no una afirmación de estado vigente a las 07:05. No se hicieron
cambios en AWS ni Azure.

Una nueva consulta STS de solo lectura a las 07:39 volvió a devolver
`ExpiredToken`; no se hicieron llamadas adicionales ni cambios AWS.

En local terminó `tests/run_local_quality.ps1 -ValidateTerraform` con 133
pruebas Python, 8 Node, PT-PERF-02, build, auditorías y validaciones IaC
aprobadas. El release v9, SHA-256
`78327e426cf86368cbc3a455be6241b57148bf8c43de6fe14f4e33041ea15316`, sigue
local y no está subido ni desplegado. La comprobación del navegador no produjo
capturas archivadas.

## Revalidación Azure de solo lectura — 07:16–07:18 America/Chicago

Azure CLI muestra la suscripción `Azure for Students` en estado `Enabled` y el
grupo `rg-tangamandapio-rebuild-wus` en `Succeeded` (West US). El inventario ARM
enumeró diez recursos del grupo, incluida la Function `tangama-wms-261008`,
Application Insights, Storage, Key Vault, Log Analytics, App Service Plan,
Action Group y dos alertas. GET
Una segunda lectura confirmó el grupo `Succeeded` y
`https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200 y
`{"status":"ok","service":"tangamandapio-wms"}`. Esto confirma respuesta
del endpoint de salud, no una invocación de procesamiento ni entrega de alertas.
Terraform 1.16.0 volvió a refrescar el root con los archivos de variables
locales requeridos y terminó `No changes. Your infrastructure matches the
configuration.` (salida 0); no se guardó plan ni se ejecutó `apply`. No se
enviaron eventos ni se modificó Azure.

## E2E Azure + control de ingreso — 07:43–07:49 America/Chicago

La corrida más reciente del smoke opt-in verificó HTTP 401 sin Function key y
HTTP 400 para un `source` no permitido; la consulta del ID rechazado quedó
`pending`, sin Blob/Queue creado. La venta/recepción legítimas
`evt-4995d65fee6c4993a4638926c0ee12b5` y
`evt-6dd2a06bb1c44178a458cb6ea0663ce0` completaron ERP/outbox →
Azure Queue/Function → reconciliación, dejando el ledger demo en su saldo
inicial. Poison metadata fue cero antes/después y no se leyeron ni mutaron
mensajes. Application Insights registró seis HTTP 202, un rechazo HTTP 400 y
seis ejecuciones del worker `resultCode=0` para tres corridas compensadas en la
última hora. No hubo EC2/RDS ni cambios de infraestructura; los seis eventos
válidos sintéticos permanecen en auditoría Azure.

## E2E Azure compensado y telemetría — 07:29–07:35 America/Chicago

El smoke opt-in del artefacto local recorrió ERP/outbox → endpoint HTTPS de
Azure → Queue/Function → reconciliación. La venta y reposición sintéticas
`evt-9129cedfd4e74c0885e075ec90c6a4d8` y
`evt-250d4f154557442da98dc11b44e670a1` terminaron correctamente y el saldo del
ledger demo volvió a su línea base. La ruta de metadatos informó poison count
cero antes y después, sin leer ni cambiar mensajes. La evidencia detallada está
en [E2E Azure](azure/AZURE-ERP-E2E-2026-10-14.md).

Application Insights registró en la última hora cuatro solicitudes
`receive_fulfillment_event` con HTTP 202 y cuatro ejecuciones
`process_fulfillment_message` con `resultCode=0`, correspondientes a dos
corridas compensadas. El portal fue un proceso local con SQLite temporal; esta
prueba no se originó en EC2/RDS. Los eventos sintéticos quedan en la auditoría
Azure. No hubo cambios de infraestructura.

## Corte operativo — 06:46 America/Chicago

- La consola web AWS está autenticada en la cuenta del laboratorio. AWS
  Academy, en una pestaña distinta, sigue mostrando `Ready`/`Lab environment
  ready`, pero también `No running instance`, avisos de expiración inminente y
  un contador de 00:08 junto a 03:57 restantes en Details. El medidor Academy
  indica `$25.1 of $50`; la consola Cost Management muestra `$20.40` del mes y
  proyección `$23.93`. No se revelaron ni descargaron credenciales y no se
  inició/terminó el lab. La lectura de inventario de consola prevalece para el
  estado actual de recursos, no esos timers inconsistentes.
- La consola AWS muestra 3 stacks activos: `tangamandapio-live-20261013`
  (`UPDATE_COMPLETE`), `tangamandapio-voice-recordings` (`CREATE_COMPLETE`) y
  el stack de Learner Lab (`CREATE_COMPLETE`). El stack principal contiene 46
  recursos; CloudFormation informa `IN_SYNC` en su última detección de drift,
  fechada 00:22:32 America/Chicago. Eso compara recursos con la plantilla
  almacenada en el stack, no demuestra igualdad con el archivo local actual.
- El panel EC2 muestra dos `t3.micro` `tangamandapio-app`, en `us-east-1a` y
  `us-east-1b`, con 3/3 comprobaciones aprobadas. El ALB
  `tangamandapio-alb` está activo y su target group `tangamandapio-tg` tiene
  2/2 destinos `Healthy` en el puerto 8080.
- El ASG `tangamandapio-asg` muestra capacidad deseada/mínima 2, máximo 4,
  dos instancias saludables, distribución en ambas AZ y Launch Template
  `tangamandapio-app` versión 5. Health checks EC2+ELB están activos. CloudWatch
  lista 7 alarmas: 6 `OK` y 1 `ALARM`, la alarma baja dinámica
  `TargetTracking-...-AlarmLow` por CPU <42% durante 15 puntos; sus acciones
  están habilitadas. Al estar el grupo en su mínimo de dos instancias, este
  estado puede ser una señal normal de baja demanda y no se interpreta como
  caída sin revisar historial/actividad de escalado.
- RDS tiene una instancia PostgreSQL `db.t3.micro` disponible en `us-east-1b`;
  `Multi-AZ` es `No` y los backups automáticos están habilitados con retención
  de 1 día. La consola lista snapshots manuales; no se restauró ninguna base.
- Los parámetros de CloudFormation identifican el release desplegado como
  `20261014-erp-admin-security-v5-python312`, SHA-256
  `19d1c9ae9225316a5802932ab89f2781480ae9eeedf4945ee5e2308ae0273bad`. El
  candidato local v8 (`2a910e9f…`) no está publicado ni desplegado. El parámetro
  `CertificateArn` está vacío y el listener comprobado es HTTP; dominio/HTTPS
  siguen para el cierre.
- En el ALB activo, GET anónimo a `/health`, `/ready` y `/api` devolvió 200;
  `/api/admin/users` devolvió 401. `/health` todavía devuelve las claves
  `database` e `instance`, y `/api` la clave `instance`. GET anónimo a
  `/metrics` devolvió 200 y 592 bytes; no se inspeccionó ni registró el cuerpo.
  El hardening del candidato v8 todavía no está desplegado.
- Azure for Students está `Enabled`; ARM enumera el grupo
  `rg-tangamandapio-rebuild-wus` como `Succeeded` y contiene Log Analytics,
  App Service Plan, Action Group, Storage, Key Vault, Application Insights,
  Function `tangama-wms-261008` y dos alertas. El endpoint público
  `/api/health` volvió a responder HTTP 200 (`status=ok`). Una llamada de
  lectura `az functionapp show` tardó más de 60 s y se canceló; el inventario
  visible y el health HTTP sí terminaron correctamente.
- Application Insights a las 06:29 devolvió en la última hora 3 solicitudes
  `health`, todas exitosas, 9 trazas con menciones de
  `process_fulfillment_message`, 6 con menciones de
  `receive_fulfillment_event`, 0 trazas con severidad de error y 0 excepciones.
  Los conteos de trazas no equivalen a invocaciones; no se devolvió el texto de
  logs ni payloads.
- Terraform aplicó únicamente una actualización in-place de
  `tangama-ops-ag`: 0 recursos añadidos, 1 cambiado y 0 destruidos. El grupo
  quedó habilitado con dos receptores, ambos con estado `Enabled`; las alertas
  5xx (severidad 2) y latencia (severidad 3) siguen activas. La lectura de
  configuración a las 06:29 confirmó esos estados. El plan posterior terminó
  `No changes`. No se disparó una alerta ni se verificó la entrega de correo.
- La compuerta integral local terminó aprobada: 132 pruebas Python, 8 Node,
  PT-PERF-02, build, auditorías y validaciones IaC. El release candidato v8 se
  empaquetó de forma reproducible con SHA-256
  `2a910e9ff040f3d4480e263e5e4c6a03805d4efe7655a92fbd30cd4235d9d252`; no se
  subió a S3 ni se desplegó.
- Los servidores Flask en `127.0.0.1:8080` y `:8081` aún responden con campos
  de health heredados (`database`; `instance` también en `:8080`), distintos
  del código actual. Se dejaron intactos porque no se confirmó qué base,
  sesión y entorno usan. La interfaz sí se revisó visualmente en Chrome a las
  06:26: en `:8080` el login se presenta en dos columnas a 1344×664; la vista
  angosta de `:8081` se apila a 524×658 sin desbordamiento horizontal visible.
  No se guardó la captura en el repositorio.

## Observación AWS Academy y UI local — 06:26 America/Chicago

- La pestaña de AWS Academy mostraba `AWS Status: Ready`, pero el panel `AWS
  Details` decía `No running instance`; el terminal tenía avisos de que el
  servidor del laboratorio terminaría en uno/dos minutos. A la vez, el panel
  informaba 03:57 de sesión restante, inicio 00:55 y fin 04:55 (hora -0700), y
  el encabezado mostraba `00:31`. El medidor indicaba `$24.1 of $50`. Por la
  inconsistencia no se inició/terminó el laboratorio ni se revelaron claves.
  Se intentó una consulta AWS CLI de solo lectura en el terminal incrustado,
  pero no apareció salida verificable; no se confirmó identidad ni se hicieron
  escrituras AWS.
- En Chrome, `http://127.0.0.1:8080/` cargó la portada/login; en la pestaña
  integrada, `http://127.0.0.1:8081/` mostró el mismo formulario en formato
  angosto. No se ingresaron credenciales ni se enviaron formularios.
- GET local a `/health` devolvió 200 en ambos puertos; `:8080` todavía incluye
  `database`, `instance`, `status`, `timestamp`, y `:8081` incluye
  `database`, `status`, `timestamp`. Se conservaron los procesos sin reiniciar
  porque la configuración runtime/base/sesión no está confirmada.

## Relectura HTTP pública del ALB anterior — 06:35 America/Chicago

Comprobaciones GET de solo lectura al balanceador conocido: `/health`,
`/ready` y `/api` dieron HTTP 200; `/api/admin/users` sin autenticación dio
401. `/health` todavía incluye los nombres de campo `database` e `instance`,
y `/api` incluye `instance`. `HEAD /metrics` dio 200 sin descargar el cuerpo.
El GET anónimo de `/metrics` a las 04:59 había dado 200, por lo que esa
exposición sigue pendiente, aunque el contenido no se ha vuelto a leer. AWS
STS continúa expirado y no se pudo confirmar qué instancias o release atienden
estas rutas.

## Corte posterior a v7 local — 05:39 America/Chicago

- AWS STS rechazó `default` con `ExpiredToken`; no se confirmó inventario ni
  drift, y no hubo escrituras. La última lectura HTTP del ALB sigue siendo la
  de las 04:59: 200 en salud/API, `/metrics` anónimo y el campo `instance`.
- Azure sigue `Enabled`; el E2E de las 05:30 procesó venta y recepción
  compensatoria en el ledger demo. Application Insights mostró 2 ejecuciones
  `process_fulfillment_message` y 2 `receive_fulfillment_event`, todas sin
  fallo. No se inspeccionaron payloads.
- El hardening health v7 pasó la puerta local y se empaquetó, pero no se subió
  a S3 ni se desplegó. El proceso Flask en `127.0.0.1:8081` no se reinició: es
  un servidor anterior cargado con `src.app` y aún informa `database` en
  `/health`. No se alteraron su proceso, base ni sesión.

## Metadatos de colas Azure — 05:43 America/Chicago

La API REST de Get Queue Metadata respondió 200 para las colas
`fulfillment-events` y `fulfillment-events-poison`; el conteo aproximado fue 0
en ambas. Solo se pidieron propiedades y conteos, no se leyeron ni reintentaron
mensajes. El estado no asegura que la cola permanezca vacía después de esta
lectura.

## Configuración Azure observada — 05:55 America/Chicago

La regla `tangama-wms-fn-5xx` está habilitada (severidad 2) y
`tangama-wms-fn-latency` está habilitada (severidad 3). El Action Group
`tangama-ops-ag` está habilitado, pero en ese momento no tenía receptores de
ningún tipo. Se agregó la configuración por Terraform en el corte 06:15; no se
probó el envío ni se disparó una alerta.

## Revalidación Azure y E2E — 05:30 America/Chicago

- `Azure for Students` está `Enabled`; en el grupo
  `rg-tangamandapio-rebuild-wus` la Function `tangama-wms-261008` aparece
  `Running` y HTTPS-only. `/api/health` respondió 200 (`status=ok`).
- El E2E sintético ERP local → outbox → Azure Queue/Function → reconciliación
  terminó `LIVE_E2E=PASSED`: venta de una unidad demo y recepción compensatoria
  devolvieron el ledger exactamente a su saldo inicial. IDs y límites en
  [AZURE-ERP-E2E-2026-10-14](azure/AZURE-ERP-E2E-2026-10-14.md).
- Application Insights informó 2 ejecuciones recientes de
  `process_fulfillment_message`, 2 de `receive_fulfillment_event` y 0 fallidas
  en la última hora, con última ejecución `2026-10-14T10:30:38Z`. Solo se
  consultaron agregados/endpoints; no se leyeron payloads. No se tocó AWS/RDS.
- AWS STS sigue rechazando el perfil `default` con `ExpiredToken`; no hay
  inventario AWS actual confirmado. No se hizo ningún cambio cloud en AWS.

## Guard de reconstrucción local — 05:21 America/Chicago

Se corrigió `rebuild.sh`: un error cualquiera de `DescribeStacks` ya no se
interpreta como “stack inexistente”. Solo se acepta el `ValidationError` que
nombra exactamente el stack consultado; stack existente, `AccessDenied`,
`ExpiredToken` y fallo de red abortan antes de validar o crear infraestructura.
La prueba mock pasó dentro de la puerta integral. No es un despliegue ni una
consulta cloud; AWS sigue sin inventario de control-plane vigente mientras
STS rechace las credenciales y el hardening v6 no está desplegado.

## Reejecución de carga transaccional — 05:11 America/Chicago

Tras cambiar las credenciales sintéticas a valores aleatorios por ejecución,
PT-PERF-02 completó 40/40 pedidos creados y leídos bajo concurrencia 8, con
40 eventos outbox pendientes persistidos, cero errores, p95 550.73 ms y 53.18
transacciones/s. Continúa siendo una prueba aislada del Flask en proceso y
SQLite temporal; no prueba rendimiento de producción, RDS, ALB ni autoscaling.
Resultado bruto en
[LOCAL-TRANSACTIONAL-LOAD-0511](LOCAL-TRANSACTIONAL-LOAD-2026-10-14-0511.json).

## Flujo transaccional local — 04:53 America/Chicago

`PT-PERF-02` ejecutó 40 flujos autenticados concurrentes (concurrencia 8)
contra el `create_app` del release v6. Las 40 escrituras `POST /api/orders`
devolvieron 201; los 40 detalles devolvieron 200 y coincidieron con su
referencia sintética. SQLite temporal confirmó 40 pedidos, 40 eventos outbox y
40 eventos en `pending`; 0 errores, 54.39 transacciones/s, p95 450.81 ms.
El script no acepta URLs externas: desactivó el despacho a Azure y los
servicios auxiliares; la base temporal se borró al finalizar. Es evidencia de
concurrencia dentro del proceso y persistencia local, no valida HTTP/Gunicorn,
PostgreSQL/RDS, ALB, autoscaling ni capacidad cloud. Resultado bruto en
[LOCAL-TRANSACTIONAL-LOAD](LOCAL-TRANSACTIONAL-LOAD-2026-10-14.json).

## Revalidación de credenciales y endpoints — 04:59 America/Chicago

- AWS STS volvió a responder `ExpiredToken` en el perfil `default`. No hubo
  intentos de escritura; no se pudo consultar el inventario privado.
- El ALB conocido respondió `/health` 200, `/ready` 200, `/api` 200,
  `/metrics` 200 y `/api/admin/users` 401 anónimo. Solo se comprobó la
  presencia del campo `instance` en `/health` y `/api`; no se copió su valor ni
  se descargó el cuerpo de métricas. El hardening v6 continúa pendiente de
  despliegue y la exposición pública sigue abierta.
- Azure CLI informa la suscripción `Azure for Students` como `Enabled`; ARM
  devuelve la Function `tangama-wms-261008` como `Running`, Linux y
  `httpsOnly=true`; `/api/health` devuelve `ok`.
- Una consulta agregada de Application Insights a 12 h devolvió 18 solicitudes,
  0 fallidas. Incluye 2 ejecuciones de `process_fulfillment_message` sin error;
  la más reciente fue `2026-10-14T09:25:28Z` (04:25:28 local). No se generó una
  invocación nueva; esto corrobora el E2E sintético previo, no inventario/WMS
  comercial ni procesamiento después de las 04:25.
- Chrome no se pudo inspeccionar porque el control de escritorio detuvo la
  sesión al no poder verificar la URL activa. Esta revisión se hizo por CLI y
  HTTP, sin interacción visual ni cambios cloud.

## Corte live ALB, telemetría y sesión — 04:45 America/Chicago

- `aws configure list --profile default` confirma que las claves se resuelven
  desde el archivo compartido de credenciales, no desde otro perfil o fuente
  de entorno; aun así AWS STS `GetCallerIdentity` devuelve `ExpiredToken`. La
  sesión temporal cargada ya venció. No se ejecutaron escrituras ni cambios
  cloud.
- El ALB responde HTTP 200 en `/health`, `/ready` y `/api`; la API pública aún
  incluye el campo `instance` (no se copió su valor). `/api/admin/users` da 401,
  pero `/metrics` da 200 anónimo: el hardening local v6 no está en el runtime
  AWS. No se pudo verificar ASG, targets ni RDS mediante el plano de control.
- A las 04:43, 20 GET secuenciales a `/health` dieron 20/20 HTTP 200 y dos
  marcadores de backend distintos. No se revelaron sus valores. Esto confirma
  que dos backends respondieron durante la muestra, no el tamaño/configuración
  actual del ASG ni el estado formal `Healthy` del target group.
- PT-PERF-01 realizó 100 GET a `/health` a concurrencia 10: duró 3.043 s,
  p95 851.9 ms y 0 errores (umbral p95 < 2 s, error ≤ 1%). Solo mide el health
  check detrás del ALB; no es carga transaccional ni prueba autoscaling. Datos
  brutos en [AWS-PERF-HEALTH](aws/AWS-PERF-HEALTH-2026-10-14.json).
- Azure Function `/api/health` responde HTTP 200. Esto confirma salud, no un
  procesamiento nuevo; el último E2E compensatorio fue el de las 04:25.
- Una consulta agregada de Application Insights a las 04:37 encontró 2
  ejecuciones de `process_fulfillment_message` en las últimas 12 horas: 2
  exitosas, 0 fallidas; la más reciente fue `2026-10-14T09:25:28Z`
  (04:25:28 America/Chicago). Corrobora el E2E anterior; no se leyeron cuerpos
  de mensajes ni se ejecutó un evento nuevo.
- La vista previa local `127.0.0.1:8081` responde 200 en `/health`, `/ready` y
  `/api`; su `/api` no incluye `instance` y `/metrics` responde 404.
- El servicio heredado local `127.0.0.1:8080` responde 200 en `/health` y
  `/api`, ambos incluyen el campo `instance`, y `/metrics` responde 200
  anónimo. Se dejó intacto; usar `:8081` para supervisar el hardening v6.
- Entre las 04:30 y 04:31, Terraform 1.16.2 consultó el root
  `iac/environments/azure-rebuild` con `rebuild.tfvars.example`; el plan
  detallado terminó con salida 0 y `No changes`. No se guardó un plan ni se
  aplicó nada.
- No se obtuvo una captura de Chrome. La herramienta de control no pudo
  determinar con seguridad la URL de la ventana; las comprobaciones anteriores
  fueron HTTP directo y no visuales.

## E2E Azure compensatorio — 04:25 America/Chicago

La Function seguía `Running`/HTTPS-only. El release local v6 completó una venta
demo de una unidad por ERP→outbox→Azure Queue/Function y reconcilió el resultado;
el ERP luego despachó una recepción compensatoria. El saldo final coincidió
con la línea base. Event IDs sintéticos: venta
`evt-ace184920d8e4921b4bcf265d4babbf6`, recepción
`evt-88e01b6734f2427da35d04b819460989`. Permanecen en la auditoría de Azure.
No se escribió a RDS ni a EC2; no hubo cambios de infraestructura. AWS
CloudFormation/ASG/ELB siguen sin permiso de lectura, por lo que v6 no se
desplegó. Evidencia detallada en
[E2E ERP→Azure](azure/AZURE-ERP-E2E-2026-10-14.md).

## Lectura ARM autenticada y control AWS — 04:14 America/Chicago

AWS STS aceptó la sesión, pero las lecturas de CloudFormation, Auto Scaling y
ELB siguen denegadas. No se ejecutó ningún cambio. En Azure, `az account show`
confirma una suscripción `Enabled`; el comando `az functionapp show` quedó
esperando una conexión IPv6 sin respuesta. Se comprobó el camino IPv4 a ARM y
se hizo un GET autenticado de solo lectura al recurso: Function
`tangama-wms-261008`, `Running`, `httpsOnly=true`, `kind=functionapp,linux`.
El endpoint público `/api/health` también responde 200. La lectura no prueba
procesamiento nuevo de eventos. No se desplegó ni mutó recurso alguno.

## Smoke público adicional — 04:07 America/Chicago

GET anónimos al ALB respondieron 200 en `/`, `/health`, `/ready`, `/api` y
`/metrics`; `/api/admin/users` respondió 401. `/api` aún incluye el campo
`instance`, por lo que el release publicado no tiene el hardening v6. No se
leyó el cuerpo de métricas ni se imprimió el valor del hostname.
La Function Azure `/api/health` respondió 200. Esta pasada solo prueba los
endpoints públicos; no consultó inventarios del plano de control, no envió
eventos y no mutó recursos.

## Confirmación tras QA v6 — 03:40 America/Chicago

- AWS STS volvió a autenticar. `autoscaling:DescribeAutoScalingGroups` sigue
  denegado explícitamente por `voc-cancel-cred`; no se pudo revisar ASG.
- El ALB sigue entregando `/api` y `/health` con un campo `instance` público;
  el hostname no se copia a la evidencia. `/api/admin/users` anónimo responde
  `401`. `/metrics` también responde `200` sin sesión; no se leyó ni guardó el
  cuerpo. Por tanto, el fix local v6 sigue pendiente de publicación.
- Azure Resource Manager confirma Function `Running` y `httpsOnly=true`. El
  endpoint de salud había respondido `200` en la verificación anterior.
- El listener local `127.0.0.1:8080` todavía devuelve `/api` y `/health` con
  `instance` y `/metrics` con `200`; es un proceso anterior, no el candidato
  v6. No se reinició: faltan `app/.env`/`BOOTSTRAP_ADMIN_PASSWORD` y Docker
  Desktop no está disponible, así que no se pudo identificar/recrear su estado.
- No se modificó ningún recurso; esta lectura solo confirma que el hallazgo de
  seguridad sigue presente en la versión viva.

## Verificación pública posterior — 03:25 America/Chicago

- El ALB `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` volvió a
  responder HTTP `200` en `/`, `/health` y `/ready` (GET anónimos). Esto
  reemplaza la lectura HTTP `503/502` del corte anterior.
- Cinco solicitudes `/health` consecutivas, separadas por dos segundos,
  respondieron `200` (5/5, aprox. diez segundos).
- Diez consultas `/health` devolvieron 10 éxitos y dos valores distintos en el
  campo `instance`, señal de dos backends que atendieron tráfico. El plano de
  control sigue denegado; esto no sustituye el inventario ni prueba que ambos
  targets estén actualmente marcados `Healthy`.
- La portada del ALB entrega `text/html`; `/api/admin/users` anónimo devuelve
  `401`, igual que la instancia local. La barrera de administración no queda
  expuesta sin sesión.
- Las respuestas públicas `/api` y `/health` revelan el nombre DNS privado de
  la instancia EC2. El candidato local v6 lo elimina y reduce el detalle de
  `/ready`, pero no se publicó; el release vivo conserva la observación.
- AWS STS autenticó como la sesión `voclabs`, pero las lecturas de
  `autoscaling:DescribeAutoScalingGroups` y
  `elasticloadbalancing:DescribeLoadBalancers` fueron denegadas explícitamente
  por `voc-cancel-cred`; no se pudo confirmar el estado del ASG/target group.
- Azure Function `https://tangama-wms-261008.azurewebsites.net/api/health`
  respondió HTTP `200` con `status=ok`; Azure Resource Manager confirmó la
  Function `Running` y `httpsOnly=true`. El resource group también contiene
  Application Insights, Log Analytics, un Action Group y alertas de latencia y
  5xx. El portal local `/health` respondió `200`. No se enviaron eventos ni se
  alteraron recursos; el health check no acredita procesamiento de pedidos.
- La automatización de Chrome se detuvo porque no pudo validar la URL actual
  con suficiente confianza. Esta verificación se hizo por HTTP directo; no se
  capturó una nueva evidencia visual.

## Estado directo más reciente — 03:12 America/Chicago

- La consola AWS Academy está `Ready`. CloudFormation se había observado
  `UPDATE_COMPLETE`/`IN_SYNC`, pero eso no asegura disponibilidad del servicio.
- La consola EC2 ahora muestra el ASG con capacidad deseada 2 y **0 instancias**;
  hay **0 destinos** registrados en el target group. El ALB está `Active`, pero
  `/`, `/health` y `/ready` devuelven HTTP `503`.
- Auto Scaling acumula más de 100 intentos y registra `Client.InternalError:
  Client error on launch`. La instancia terminada inspeccionada no tiene VPC,
  subred, IP ni rol asociado en la vista de detalles. No hay evidencia suficiente
  para atribuirlo a la app ni declarar causa raíz.
- El ASG apunta a la versión 5 de `tangamandapio-app` (AMI Amazon Linux 2023,
  `t3.micro`, `LabInstanceProfile`, subredes privadas en dos AZ); la versión
  predeterminada de la plantilla sigue siendo 1. CloudTrail y la lectura CLI de
  `ec2:DescribeLaunchTemplateVersions` están denegados por la sesión/política,
  de modo que no se pudo inspeccionar el error de API original.
- Azure usa la suscripción activa `Azure for Students`; el grupo presente es
  `rg-tangamandapio-rebuild-wus`. La Function `tangama-wms-261008` respondió
  HTTP `200` en `/api/health`. El login de la interfaz local también cargó en
  Chrome; no se usaron credenciales ni se probaron módulos autenticados.
- No se aplicó IaC ni se alteró infraestructura. El detalle está en
  [la revalidación EC2/ALB](aws/AWS-REVALIDACION-EC2-BOOT-2026-10-14.md).

## Plan Azure e inventario ASG — 02:50–02:51 America/Chicago

Terraform 1.16.0 ejecutó un plan normal, sin guardar artefacto aplicable,
contra `iac/environments/azure-rebuild/rebuild.tfvars.example`. Entre 02:50:40
y 02:51:38 terminó `No changes` (salida 0); no hubo `apply`. En AWS, la lectura
de `AutoScalingGroups` para `tangamandapio-asg` también devolvió `AccessDenied`.
El ALB sigue sin poder diagnosticarse desde el plano de control. Ver [plan
Azure detallado](azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

## Confirmación posterior a QA — 02:45 America/Chicago

Después de terminar la compuerta local, se repitieron GET anónimos: AWS ALB
devolvió 503 en `/`, `/health`, `/ready` y `/api/admin/users`; Azure
`/api/health` devolvió 200; el portal local devolvió 200 en `/health` y 401 en
`/api/admin/users`. El 503 AWS persiste. No se iniciaron sesiones ni se
modificaron recursos; el inventario de EC2/ELB/CloudFormation continúa
inaccesible por los permisos anotados abajo, así que la causa permanece sin
determinar.

## Smoke público y red — 02:20 America/Chicago

El ALB conocido como vigente, `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com`,
devolvió HTTP 503 en `/`, `/health`, `/ready`, `/api/admin/users` y
`/administracion`. Los hostnames previos
`tangamandapio-alb-829164422.us-east-1.elb.amazonaws.com` y
`tangamandapio-alb-820217334.us-east-1.elb.amazonaws.com` no completaron conexión. Azure
`/api/health` devolvió HTTP 200 (`service=tangamandapio-wms`).

La última pasada local respondió 200 en `/`, `/health` y `/ready`, y 401 en
`/api/admin/users` sin sesión. Por tanto, el fallo observado está en el entorno
AWS publicado, no se reproduce en esa comprobación local. La respuesta 503 no
permite determinar si faltan destinos sanos, EC2 o hay otra causa en el ALB;
CloudFormation devolvió `AccessDenied`; EC2 y ELBv2 denegaron el inventario con
`UnauthorizedOperation`/`AccessDenied`.
Fueron solicitudes GET anónimas: no se inició sesión ni se modificaron datos
o infraestructura.

## E2E Azure compensatorio — 02:25 America/Chicago

El smoke opt-in del artefacto local AWS v5 procesó una venta demo y su
reposición en Azure: `evt-94d171a6cda84a42bcff5bb5939d1bc7` terminó
`demo_fulfillment_completed` y
`evt-21077807ad594cb298a591c5ee062f81` terminó `demo_restock_completed`. El
script verificó que el saldo ficticio regresara al valor inicial. Quedaron dos
eventos sintéticos auditables; no se cambió AWS/RDS. Esto acredita que Azure
procesó eventos en este corte, pero no que el EC2 productivo los originó ni que
AWS esté disponible. Ver [E2E Azure](azure/AZURE-ERP-E2E-2026-10-14.md).

## Preflight VPN — 02:17 America/Chicago

AWS STS autenticó, pero CloudFormation devolvió `AccessDenied` al leer el stack
portal y las consultas EC2 `Describe*Vpn*` devolvieron `UnauthorizedOperation`.
Una prueba
`CreateCustomerGateway --dry-run` fue denegada y no creó recursos. Azure CLI
autenticó en una suscripción `Enabled`, pero
`rg-tangama-private-network` devolvió `false`. No hubo `apply` ni mutaciones.
La VPN no está desplegada/demostrada; se requiere permiso AWS IAM/SCP y
reconstruir el grupo dedicado Azure. Ver [preflight AWS–Azure VPN](aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

## Corte de solo lectura más reciente — 01:46 America/Chicago

### AWS

- STS autenticó en la cuenta esperada. CloudFormation
  `tangamandapio-live-20261013` respondió `UPDATE_COMPLETE`; el ALB existe y
  sus dos destinos reportan `healthy`.
- RDS está `available`, cifrada, privada, Single-AZ y con retención de backup
  de un día.

### Azure

- A las 01:44, la suscripción activa **Azure for Students** coincidió con la
  única suscripción del state local. `terraform validate` pasó y un plan
  normal contra Azure terminó `No changes` (salida 0). No se ejecutó `apply`.
- Detalle en [el plan Azure del 14/10](azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

Estas lecturas no cambian recursos. El estado de AWS no se usa para afirmar
HTTPS: el ALB continúa con el listener HTTP hasta contar con un FQDN y
certificado ACM válidos.

## Insumos verificados para estimación — 02:03 America/Chicago

- AWS CloudFormation expuso los parámetros vigentes: `InstanceType=t3.micro`,
  `DBInstanceClass=db.t3.micro`, `DatabaseMultiAZ=false`, retención RDS de 1 día,
  WAF y AWS Backup deshabilitados. ASG mínimo/deseado/máximo: 2/2/4.
- RDS devolvió PostgreSQL `db.t3.micro`, Single-AZ, cifrada y privada, 20 GB
  `gp3`. La plantilla declara dos volúmenes EBS `gp3` de 8 GB cada uno.
- El inventario incluye ALB, NAT Gateway, IPv4 pública asociada al NAT y dos
  secretos. Con estos tamaños y tarifas públicas se generó un subtotal AWS
  aproximado de $91.92/mes bajo 730 horas, 1 LCU promedio y 10 GB procesados por
  NAT. Desglose, fórmulas y exclusiones: [estimación de costos](../../core/13_estimacion_costos_cloud_2026-10-14.md).
- Azure sigue con Function Consumption `Y1`; su cómputo puede estar cubierto
  por la subvención si la suscripción califica. Blob/Queue y su volumen siguen
  siendo cargos variables por medir; no se contaron como cero.

Solo lecturas de AWS y fuentes públicas de precios; no se tocaron recursos.

## Corte de solo lectura más reciente — 01:30 America/Chicago

### AWS

- STS autenticó en la cuenta esperada del laboratorio.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`, drift
  `IN_SYNC`; el ALB está `active` e internet-facing.
- El DNS vigente del ALB es
  `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com`; el hostname
  anterior no era el recurso actual. `/health` respondió HTTP 200 con
  `database=ok`. Ambos destinos del target group siguen `healthy`.
- RDS `available`, cifrada, no pública, Single-AZ y con retención de backup de
  un día.

### Azure

- La suscripción sigue `Enabled`; ARM informó la Function
  `tangama-wms-261008` `Running`, HTTPS-only, Linux, West US.
- `/api/health` respondió `ok`.

Todas las consultas de este corte fueron de solo lectura. No hubo cambios,
despliegues ni costos añadidos. El corte no prueba la VPN privada, correo
entregado, WMS comercial ni HTTPS del portal; el ALB permanece HTTP hasta tener
dominio y certificado.

## Smoke HTTP del release público — 01:37 America/Chicago

En el hostname vigente del ALB, `/` y los seis recursos JS/CSS declarados por
su HTML respondieron HTTP 200; `/health` y `/ready` también dieron 200. Sin
sesión, `/administracion` redirigió (303) y `/api/admin/users` rechazó el acceso
(401), conforme a la barrera esperada. Fueron lecturas anónimas; no se inició
sesión ni se cambió infraestructura. Esto no valida permisos de cada rol
autenticado en navegador.

## Corte autenticado y alarma — 01:02 America/Chicago

### AWS

- AWS CLI autenticó con STS en la cuenta del proyecto `841113066612`.
- CloudFormation `tangamandapio-live-20261013`: `UPDATE_COMPLETE`, drift
  `IN_SYNC`; última actualización observada `2026-10-14T05:14:13Z`.
- Auto Scaling Group y RDS figuran `UPDATE_COMPLETE`; los dos destinos del
  target group están `healthy`.
- RDS `tangamandapio-postgres`: `available`, cifrada, no pública, Single-AZ,
  backups automáticos de un día.
- El ALB respondió HTTP 200 en `/health`, con `database=ok`.
- `HighCPUAlarm` completó una prueba sintética `OK → ALARM → OK`; CloudWatch
  registró ambas acciones SNS como exitosas y el estado final `OK`. El detalle
  está en [la prueba de alarma](aws/AWS-ALARM-TEST-2026-10-14.md).
- Un preview de `deploy.sh` para el template local HTTPS terminó
  `CREATE_COMPLETE` con cero cambios de recursos. No se ejecutó; el change set
  temporal se borró. El stack activo conserva la plantilla aplicada y sigue
  HTTP hasta el dominio/certificado.

## Azure

- `az account show` informó la cuenta `Enabled`.
- `https://tangama-wms-261008.azurewebsites.net/api/health` respondió HTTP 200
  con `service=tangamandapio-wms`.
- La consulta ARM de `az functionapp show` confirmó estado `Running`,
  `httpsOnly=true`, Linux (`functionapp,linux`) y región West US.
- Application Insights (`tangama-wms-ai`) conserva dos solicitudes de
  `process_fulfillment_message` para `cloud_RoleName=tangama-wms-261008`,
  ambas con `resultCode=0`, `failed=0`; la última registrada fue
  `2026-10-14T05:36:58Z`. La consulta devolvió agregados, no payloads.

## Alcance del corte

Las consultas de inventario fueron de solo lectura. La prueba de alarma hizo
dos cambios transitorios de estado y los restauró; no hubo despliegues ni
cambios de configuración. CloudWatch registró acciones SNS exitosas, pero no
hay evidencia de recepción en bandeja. El `IN_SYNC` corresponde a la última
plantilla desplegada en CloudFormation; la preparación local más reciente para
`PortalDomainName`/ACM aún no se ha aplicado. El ALB sigue HTTP, pendiente de
dominio propio y certificado ACM validado. Esta revisión no acredita la VPN
AWS–Azure, WMS comercial, salida SMTP, roles autenticados en navegador ni
llamadas WebRTC entre dos navegadores.

## Corte posterior a las actualizaciones — 14/10/2026, 08:42–09:16 America/Chicago

### AWS

- Se verificó STS en la cuenta académica esperada; se publicó en S3 el artefacto
  AWS v9 `20261014-public-diagnostics-hardening-v9-python312`, SHA-256
  `78327e426cf86368cbc3a455be6241b57148bf8c43de6fe14f4e33041ea15316`.
- CloudFormation `tangamandapio-live-20261013` terminó `UPDATE_COMPLETE`; seis
  cambios de Launch Template/ASG/observabilidad, sin RDS ni eliminaciones. La
  detección posterior terminó `IN_SYNC`.
- ASG deseado/mínimo 2, máximo 4; dos instancias `InService`/`Healthy`, dos
  destinos ALB `healthy`. SSM corroboró v9 y tres hashes de runtime iguales al
  paquete probado.
- ALB: `/` 200, `/health` 200 (`status,timestamp`), `/ready` 200 (`status`),
  `/api` 200 (`endpoints,service`), `/metrics` 404 y `/api/admin/users` 401.
- RDS disponible, cifrada, privada, Single-AZ y retención automática de un día;
  no se modificó.
- El admin pudo iniciar sesión, pero `/api/wms/inventory` devolvió 428 por
  cambio obligatorio de contraseña inicial. El test se detuvo antes de crear
  socio, pedido o evento; la integración desde EC2 queda pendiente de terminar
  ese cambio y repetir la prueba.

### Azure

- Terraform publicó el ZIP nuevo de la Function: SHA-256
  `ecb71ccd2841b87a2dfc0b4e88ed6652beacb9281b045df26152f3f920642f27`. Plan
  aplicado: un blob nuevo, Function actualizada in-place y blob de versión
  anterior eliminado; el artefacto previo quedó guardado localmente y el
  Storage Account tiene retención de blob soft-delete de siete días configurada
  por IaC. El plan posterior terminó `No changes`; `rebuild.tfvars.example`
  ahora apunta al mismo paquete, y el plan sin overrides también terminó
  `No changes`.
- Tras el reinicio, el smoke reportó Function `Running`, HTTPS-only y
  `/api/health` 200. E2E local compensado terminó `LIVE_E2E=PASSED`: 401 sin
  Function key, 400 por source no autorizada sin persistencia, venta demo y
  recepción compensatoria procesadas; saldo de demo restituido. El proceso
  productor fue local/SQLite, no EC2/RDS.

### Límites registrados antes del smoke EC2→Azure de las 09:38

No hay HTTPS del portal AWS hasta contar con dominio controlado y certificado
ACM. No hay VNet/rutas/VPN privadas AWS–Azure; la SCP de AWS Academy denegó la
creación de la VPN temporal. El inventario Azure sigue siendo ficticio, el
correo no es un buzón corporativo/relay externo, no se probaron sesiones de cada
rol en navegador ni WebRTC entre dos navegadores. La restauración RDS y la carga
históricas no se repitieron en este corte. Las autoevaluaciones numéricas
anteriores siguen sin ser una calificación docente.

El smoke posterior, añadido abajo, acredita únicamente un evento incompleto
EC2→Azure por HTTPS público; no invalida los límites de venta autenticada,
conectividad privada o WMS comercial.

## Revalidación adicional — 14/10/2026, 09:20–09:24 America/Chicago

Se repitieron consultas de solo lectura después del despliegue: CloudFormation
permanece `UPDATE_COMPLETE`; ambos destinos del target group están `healthy`;
RDS está `available`, cifrada, no pública, Single-AZ y con retención de un día.
El ALB respondió `/` 200, `/health` 200, `/ready` 200, `/api` 200,
`/metrics` 404 y `/api/admin/users` anónimo 401. Azure `/api/health` respondió
200. Terraform volvió a refrescar los recursos Azure y terminó `No changes`.

La Action Group `tangama-ops-ag` conserva dos receptores de correo en estado
`Enabled`, y las alertas de 5xx y latencia están habilitadas. Se intentó usar
la operación oficial de prueba de notificaciones; Azure respondió
`Free subscription not supported`. No se cambiaron reglas ni recursos y no se
afirma recepción de alerta Azure. La configuración está presente, pero la
entrega de correo Azure sigue sin prueba; la confirmación del usuario aplica a
la alarma AWS, no a esta prueba Azure.

## Smoke directo EC2 → Azure — 14/10/2026, 09:38 America/Chicago

Desde una instancia EC2 en estado SSM `Online` se leyó la configuración del
productor en memoria, sin imprimir ni copiar secretos, y se consultó el ledger:
Azure respondió 200 en inventario y reportó el modo
`demo-inventory-ledger`, con `SKU-ARROZ-001` en 24 unidades. Se envió por HTTPS
un evento sintético sin líneas de producto (`event_type=order.created`, source
`tangamandapio-erp`, id
`qa-ec2-bfbd32f277174229bfc6a9bbb7ccbbf2`). Azure respondió 202 y la Function
lo procesó hasta `awaiting_items`; una lectura posterior mantuvo el SKU en 24.
No se creó pedido en RDS ni se modificó inventario. El evento queda en la
auditoría Azure.

Esto acredita la ruta pública EC2 → endpoint HTTPS → Queue/Function de Azure
para un evento de humo sin artículos. No acredita la venta autenticada completa
del portal, porque el acceso protegido sigue detenido en el cambio inicial de
contraseña admin (HTTP 428); tampoco acredita VPN privada AWS–Azure ni un WMS
comercial.

## Reconciliación de solo lectura — 14/10/2026, 09:39–09:44 America/Chicago

AWS STS autenticó en la cuenta `841113066612`. CloudFormation siguió
`UPDATE_COMPLETE` (última actualización 13:44 UTC); una detección de deriva
nueva terminó `IN_SYNC` con 0 recursos desviados. Los dos targets del ALB
estuvieron `healthy`, y `/health`, `/ready` y `/api` devolvieron 200. RDS está
`available`, cifrada y privada, Single-AZ, con retención de backup de un día.

La suscripción Azure `Azure for Students` está `Enabled`. El grupo correcto de
este despliegue es `rg-tangamandapio-rebuild-wus` (no el nombre antiguo
`rg-tangamandapio-261005-wus`); contiene la Function `tangama-wms-261008`, que
está `Running`, HTTPS-only y respondió 200 en `/api/health`. Terraform refrescó
los recursos Azure administrados, incluida Function, Storage/Queue, RBAC,
Application Insights y alertas, y concluyó `No changes` usando
`iac/environments/azure-rebuild/rebuild.tfvars.example` más
`alert-recipients.local.tfvars`. No se ejecutó `apply`, ni se cambió recurso
alguno. El ejemplo de `azure-demo` es un sandbox aislado y no se usó para
reconciliar el entorno activo.

## Revalidación autenticada y E2E ERP portal→Azure — 14/10/2026, 10:11 America/Chicago

El cambio obligatorio de clave admin se completó y la clave final se rotó por
túnel SSM; se guardó en Parameter Store como `SecureString` Standard, fuera del
repositorio. El túnel se cerró después de las pruebas. No se actualizó el
secreto de bootstrap ni se cambiaron instancias.

Se crearon cuentas de QA Comercial y Operaciones con claves independientes en
`SecureString`. Las pruebas de autorización autenticadas confirmaron la matriz
de 200/403 y las protecciones de `/platform` y `/administracion`; ver el detalle
en [AWS E2E y roles](aws/AWS-DESPLIEGUE-2026-10-14.md). La comprobación se hizo
contra API y rutas protegidas, no con una captura visual de navegador.

Una venta de QA recorrió la aplicación desplegada, PostgreSQL/RDS, outbox AWS,
endpoint HTTPS Azure, Queue y Function. El outbox quedó `delivered` (un
intento), Azure reportó `demo_fulfillment_completed` y el ERP `completed_demo`.
Una orden de compra QA recorrió la recepción compensatoria
(`demo_restock_completed` / `received_demo`). El SKU de demostración quedó
restaurado a 24 unidades (24→23→24), y se generaron una CxC y una CxP de prueba.
Referencias, ids y límites están en
[AWS E2E y roles](aws/AWS-DESPLIEGUE-2026-10-14.md). No hay WMS comercial,
stock real, contabilidad legal ni conectividad privada AWS–Azure.

CloudFormation seguía `UPDATE_COMPLETE`; la Function Azure `/api/health`
respondió 200. El ALB continúa HTTP: las credenciales nuevas se validaron por
el túnel privado temporal, y el inicio visual por el sitio público queda
pendiente hasta HTTPS.

## Dataset QA sintético y segunda pasada productiva — 14/10/2026, 10:18 America/Chicago

El inventario ficticio es el comportamiento esperado del prototipo académico,
no una brecha de “stock real”. Se agregaron tres distribuidores demo y un
proveedor demo. Tres ventas (arroz ×2, azúcar ×2, aceite ×1) del usuario
Comercial y una recepción de compra QA del usuario admin recorrieron el portal
AWS/PostgreSQL → outbox → HTTPS público de Azure → Queue/Function. Las tres
ventas reconciliaron como `completed_demo`; la recepción, `received_demo`.
La consulta autenticada final encontró 7/7 eventos outbox entregados y seis
documentos financieros sintéticos (4 CxC y 2 CxP). Los saldos del ledger Azure
coincidieron con los iniciales: `SKU-ACEITE-001=18`, `SKU-ARROZ-001=24` y
`SKU-AZUCAR-001=40`. Las referencias y límites están en
[la evidencia del despliegue AWS](aws/AWS-DESPLIEGUE-2026-10-14.md). No se hizo
`apply`, no hubo cambio de infraestructura y el ALB público sigue HTTP.

## Relectura AWS/Azure e IaC — 14/10/2026, 10:37 America/Chicago

AWS STS autenticó en la cuenta `841113066612`. CloudFormation
`tangamandapio-live-20261013` reportó `UPDATE_COMPLETE` y el estado de deriva
registrado `IN_SYNC`; el endpoint ALB `/health` dio 200 y ambos destinos del
target group están `healthy`. RDS está `available`, cifrada, privada, Single-AZ
y con retención de backup de un día. Estos parámetros son el estado efectivo,
no una política de HA.

Azure CLI confirmó `tangama-wms-261008` en `Running`; `https://…/api/health`
respondió 200. Un `terraform plan -detailed-exitcode` contra el grupo activo,
con `rebuild.tfvars.example` y el archivo local de receptores, terminó `No
changes` (exit 0). No se aplicó Terraform ni CloudFormation y no se mutó
infraestructura durante esta verificación.

## Estado operativo más reciente — 14/10/2026, 12:25 America/Chicago

Se repitieron sondas públicas de solo lectura desde el equipo local. El ALB
vigente `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` respondió
HTTP 503 tanto en `/` como en `/health`. La Function Azure
`tangama-wms-261008` respondió HTTP 200 en `/api/health`.

AWS STS autenticó correctamente la sesión `voclabs` en la cuenta académica
`841113066612`; sin embargo, `cloudformation:DescribeStacks` y
`ssm:DescribeInstanceInformation` recibieron denegación explícita de la
política de identidad `voc-cancel-cred`. Por ello no se pudo comprobar el
estado del stack, SSM, EC2 ni los destinos del balanceador. En la inspección de
ventanas locales no había una sesión visible de AWS Academy (Chrome mostraba
WhatsApp); no se intentó iniciar sesión ni se realizó ninguna operación de
escritura.

Este corte reemplaza como estado vigente los resultados 200/targets sanos
registrados a las 12:17; estos últimos siguen siendo evidencia válida de la
prueba ejecutada entonces, pero no del estado actual. Los E2E productivos
anteriores siguen demostrando el flujo sintético en ese momento. El smoke de
roles incluido en el harness posterior no se ejecutó en este corte. No se
modificaron AWS ni Azure.

## E2E Azure vivo posterior — 14/10/2026, 12:30–12:32 America/Chicago

La Function se confirmó `Running` y HTTPS-only mediante lectura autenticada de
ARM. El smoke sintético volvió a comprobar 401 sin Function key, 400 para un
`source` no permitido y ausencia de persistencia del evento rechazado; consultó
solo metadatos de la cola poison y confirmó conteo cero antes/después, sin leer
ni modificar mensajes. Después, la aplicación del release AWS ejecutada
localmente con SQLite temporal creó una venta y compra QA; Azure Queue/Function
las procesó como `demo_fulfillment_completed` y `demo_restock_completed`.
IDs: venta `evt-685412ec9a284bae89d80a07249ec903`, recepción
`evt-a17b3eeba08743b3981f88550b48011f`. El ledger demo terminó en el mismo
saldo que al inicio. Los eventos quedan en la auditoría Azure. Esta corrida no
atravesó AWS/EC2/RDS ni hizo cambios de infraestructura; el ALB AWS sigue
respondiendo 503 según la relectura de las 12:25.

## Refresco IaC y health Azure — 14/10/2026, 12:39–12:40 America/Chicago

Terraform 1.16.0 volvió a refrescar `iac/environments/azure-rebuild` usando
`rebuild.tfvars.example` y `alert-recipients.local.tfvars`; el plan con
`-detailed-exitcode` terminó exit 0 (`No changes`). No se ejecutó `apply` ni se
alteraron recursos. La Function health volvió a responder HTTP 200. AWS no se
reconsultó en este corte; su última sonda registrada es el 503 de las 12:25 y
persisten las denegaciones IAM observadas entonces.

## Comprobación pública y de permisos — 14/10/2026, 12:46 America/Chicago

AWS STS volvió a autenticar. La llamada de solo lectura
`elbv2:DescribeLoadBalancers` recibió `AccessDenied`, por lo que no se pudieron
leer balanceador ni destinos; la sonda pública del ALB siguió devolviendo HTTP
503 en `/health`. Azure Function `/api/health` respondió HTTP 200. No se
ejecutaron operaciones de escritura cloud. El fallo AWS sigue siendo de
disponibilidad y acceso de lectura, no evidencia de que el token haya sido
rechazado.

## Reintento de inventario de recursos — 14/10/2026, 13:03 America/Chicago

En una nueva pasada read-only, AWS STS autenticó, pero `ec2:DescribeInstances`,
`autoscaling:DescribeAutoScalingGroups` y `rds:DescribeDBInstances` devolvieron
`AccessDenied`; `elbv2:DescribeLoadBalancers` también sigue denegado. El ALB
continuó en HTTP 503 y Azure Function health respondió HTTP 200. No hubo llamadas
de escritura ni cambios en recursos. Por la denegación no puede determinarse si
faltan instancias o si falla otra dependencia detrás del balanceador.

## Revalidación y sonda read-only — 14/10/2026, 13:11 America/Chicago

AWS STS volvió a autenticar la cuenta académica `841113066612`. Las consultas
`cloudformation:DescribeStacks`, `elasticloadbalancing:DescribeLoadBalancers`,
`ec2:DescribeInstances`, `autoscaling:DescribeAutoScalingGroups` y
`rds:DescribeDBInstances` recibieron denegación explícita de la política
`voc-cancel-cred`; por tanto, no se conocen ahora el estado del stack, destinos,
instancias ni base. La sonda externa devolvió HTTP 503 por el ALB en `/health`;
HTTPS agotó el tiempo de espera. Azure Function `/api/health` respondió HTTP
200. No se ejecutaron escrituras cloud.

Se añadió `iac/scripts/inspect_aws_runtime.ps1`, un diagnóstico de solo lectura
que inspecciona STS, CloudFormation, ALB y salud de destinos, ASG, EC2 y RDS,
sin imprimir credenciales ni incluir comandos mutadores. Sus tres escenarios
mock (sano, destino degradado y acceso IAM denegado) pasaron; esto prepara la
revisión cuando se restablezcan permisos, pero no arregla ni confirma la
infraestructura actual. La compuerta local ampliada sigue en ejecución.

## Revalidación con credencial nueva — 14/10/2026, 13:29 America/Chicago

Se guardó el token temporal recién entregado en el perfil local `default` y
AWS STS autenticó la cuenta académica `841113066612`. Las consultas read-only
ahora sí están permitidas: CloudFormation reportó
`tangamandapio-live-20261013` en `UPDATE_COMPLETE` y `IN_SYNC`; el ALB
`tangamandapio-alb` está `active` y ambos targets figuran `healthy`; las dos
EC2 `t3.micro` están `running`. RDS `tangamandapio-postgres` está `available`,
privada y cifrada, Single-AZ, con 1 día de retención. Los parámetros efectivos
de CloudFormation (`DatabaseMultiAZ=false`, `DatabaseBackupRetentionDays=1`)
coinciden con lo configurado en la plantilla actual; no hay discrepancia en
esos dos valores.

Desde el host del ALB, `GET /` y `/health` devolvieron HTTP 200; las rutas
protegidas `/api/admin/users` y `/api/orders` devolvieron 401 sin sesión. El
listener público sigue siendo HTTP: no se probó HTTPS con certificado. Azure
no recibió cambios en esta revalidación. En este corte solo se hicieron
consultas read-only; el token se guardó localmente y no se copió a evidencias.

La compuerta integral local terminó con exit 0: 159 pruebas Python
(17 smoke Azure, 4 preflight Tailscale, 62 API, 31 Azure Functions y 45 release
AWS) y 14 Node, además de PT-PERF-02 40/40 transacciones aisladas, build Vite,
auditorías de dependencias, CloudFormation y validación Terraform con mocks.
No ejecutó despliegues cloud. Los resultados cubren los límites de 500/501 SKU
añadidos al test, pero la importación autenticada por la interfaz del navegador
todavía no se ha probado.

## Smoke sintético en AWS/Azure — 14/10/2026, 14:00 America/Chicago

Con el ALB y SSM ya accesibles se lanzó una sola ejecución del smoke vivo
documentado. Las comprobaciones de permisos para Comercial y Operaciones
pasaron. El login QA del usuario administrador autenticó, pero la sesión no
tenía el rol `admin` que exige el smoke; CloudWatch confirmó sesión válida en
la ruta de login/sesión. El comando terminó antes de crear SKU, socio, venta o
compra, por lo que no alteró el ledger ni añadió transacciones de negocio. Sí
quedaron registros de auditoría de los inicios/cierres de sesión y el registro
de Systems Manager de ese único comando. No se repitió automáticamente.

## Corrección del smoke y pasada E2E completa — 14/10/2026, 14:12 America/Chicago

La conclusión de las 14:00 fue un falso diagnóstico del harness: el cliente de
prueba esperaba `admin` también al autenticar Comercial y Operaciones. No era
un problema de la cuenta admin. Se parametrizó el rol esperado, se añadieron
cuatro pruebas unitarias (incluido rechazo seguro de rol inesperado) y la suite
focalizada pasó 4/4. La compuerta integral volvió a terminar con exit 0:
163 pruebas Python, 14 Node, PT-PERF-02 40/40, build, auditorías de
dependencias, CloudFormation y Terraform fmt/validate/tests.

Una nueva ejecución única desde EC2 v10 por SSM terminó `LIVE_E2E_PASSED`.
Admin autenticó con rol `admin`; Comercial pudo consultar ventas (200) y recibió
403 en outbox, WMS y administración; Operaciones pudo consultar outbox/WMS
(200) y recibió 403 en ventas y administración. Se importó por API autenticada
el SKU sintético `SKU-QA-V10-20261014`, una venta terminó `completed_demo`, la
recepción compensatoria `received_demo` y ambos eventos outbox quedaron
`delivered` por Azure Queue/Function. El ledger de demostración quedó en 10
antes y después. Esto prueba la API de catálogo, no la carga manual del CSV en
el navegador. La operación agregó/actualizó documentos sintéticos y auditoría
en RDS/Azure; no modificó recursos de infraestructura ni inventario físico.

El smoke hizo además 24 lecturas autenticadas desde el proceso de una EC2, con
concurrencia 6: 24/24 HTTP 200, p95 267.93 ms. Es una microprueba por loopback,
no atraviesa el ALB ni valida capacidad del ASG o 3,000 usuarios. Tras la
prueba, el control de solo lectura confirmó CloudFormation `UPDATE_COMPLETE`/
`IN_SYNC`, ALB `active`, 2/2 targets `healthy`, 2 EC2 `running`, RDS
`available`/cifrada/privada/Single-AZ con 1 día de retención; `/` y `/health`
respondieron 200 y APIs protegidas sin sesión 401. Azure Function health volvió
a responder 200. El token no se guardó en evidencia. El release sigue HTTP,
sin dominio ni HTTPS público.

Como comprobación adicional a las 14:17, `/ready` y `/api` dieron 200 y
`/metrics` dio 404 anónimo, confirmando que la ruta de métricas no está
publicada en este release.

La recuperación RDS no está pendiente como criterio básico: PT-DR-01 ya pasó
el 13/10 con marcador SQL, igualdad de conteos, RTO 289 s, RPO observado 14 s
y limpieza verificada. No se repitió después del release v10; hacerlo sería
una regresión opcional. Permanecen pendientes la importación CSV visual,
revisión de UX por rol, carga por ALB/ASG, evidencia de monitor/entrega Azure,
red privada AWS–Azure, dominio/HTTPS y WebRTC en dos navegadores.

## Observabilidad Azure y revisión de cola — 14/10/2026, 14:20 America/Chicago

Azure CLI autenticó en la suscripción `Azure for Students` (`Enabled`). La
Function y Application Insights existen en el grupo del proyecto. La consulta
agregada de los últimos 30 minutos mostró 2 solicitudes de recepción del evento
con HTTP 202, 2 ejecuciones de `process_fulfillment_message` y 0 fallos
registrados; la prueba E2E de las 14:12 correlaciona ese procesamiento con los
dos eventos entregados y el saldo demo restituido. No se leyeron trazas ni
payloads de mensajes. Esto confirma invocación/éxito del worker, no entrega de
una alerta de Azure Monitor.

Se listaron las colas `fulfillment-events` y `fulfillment-events-poison`. El
intento de peek no destructivo fue denegado por falta de rol de lectura de datos
de cola; no se cambió RBAC, no se obtuvo una clave y no se leyó, borró ni alteró
ningún mensaje. Por ello el conteo/estado de poison sigue pendiente. No hubo
cambios de recursos Azure.

## Revalidación final v11 — 15/10/2026, 00:14–00:18 UTC

El perfil local AWS `default` autenticó por STS en la cuenta académica
`841113066612`. Después de recuperar el rollback de un intento previo, el
artefacto `20261014-landing-loading-v11-python312` quedó desplegado mediante
CloudFormation. El stack terminó `UPDATE_COMPLETE` y la última detección de
drift `IN_SYNC` con cero recursos discrepantes. Las dos instancias activas
reportaron por SSM la misma revisión v11, servicio activo y health local 200.
El ASG final quedó mínimo/deseado 2, máximo 5, sin nodos terminando; los dos
targets del ALB están `healthy`. La portada, `/health` y `/ready` respondieron
HTTP 200.

RDS permanece `available`, cifrada y privada, 20 GB, Single-AZ y con un día de
retención de backups. El change set no incluyó RDS, VPC ni grupos de seguridad.
Las cinco alarmas CloudWatch están `OK`, con acciones habilitadas. Azure no se
modificó durante este despliegue; `/api/health` respondió 200 a las 00:17 UTC.
La actualización no tocó datos de negocio. El E2E autenticado de roles,
pedido/recepción sintéticos y envío AWS→Azure sigue siendo evidencia anterior
del runtime v10; no se repitió sobre v11. El ALB sigue en HTTP, y la VPN
privada, HTTPS/dominio, revisión visual por navegador y WebRTC real continúan
pendientes. La secuencia completa y los cambios a la política de rolling update
están en [AWS-DESPLIEGUE-V11](aws/AWS-DESPLIEGUE-V11-2026-10-14.md).
