# Índice de evidencias del proyecto

## Incidente de disponibilidad y Azure vivo — 16/10/2026, 05:44–05:47 UTC

El dominio HTTPS sigue con TLS válido, pero tanto Cloudflare como el ALB
respondieron 503. El listener HTTP del ALB redirige a HTTPS; la consulta directa
HTTPS confirmó que la respuesta 503 proviene de `awselb/2.0`. AWS STS rechazó el
token nuevo y no se hizo ninguna mutación; por ello aún no se sabe qué destino
falla ni por qué. Azure sigue `Enabled`, Function `Running`/HTTPS-only y health
200. El E2E local→Azure volvió a pasar con venta y reposición sintéticas, stock
demo restaurado y poison count cero. No prueba el portal AWS ni el flujo desde
EC2. Véase la [revalidación vigente](current/CLOUD-REVALIDATION-2026-10-16-0547UTC.md).

## Puerta local y E2E Azure — 16/10/2026, 05:37 UTC

La puerta integral aprobó 216 pruebas Python, 14 pruebas frontend, build y
auditorías, `cfn-lint`, Terraform `fmt`/`validate` y cinco pruebas mock de
red/costo; no ejecutó cambios de nube. Luego el arnés compensado
ERP-local→Azure pasó guards 401/400, venta y reposición sintéticas, saldo
ficticio restaurado y poison count cero. No se originó desde EC2/RDS. Véanse
la [puerta local](current/QA-LOCAL-2026-10-16-0537UTC.md) y el
[E2E Azure](current/azure/AZURE-ERP-E2E-2026-10-16-0537UTC.md). Application
Insights reportó en la ventana de 20 minutos dos ejecuciones correctas del
worker, cero fallidas.

## Despliegue de sonda Azure GET/HEAD — 16/10/2026, 05:08–05:19 UTC

La Function quedó `Running`/HTTPS-only; GET y HEAD `/api/health` respondieron
200 con TLS verificado, HEAD sin cuerpo y siete Functions indexadas. Pasaron
32 pruebas unitarias y el verificador del ZIP; Terraform aplicó solo el nuevo
Blob de paquete y la actualización de Function, y el plan posterior quedó en
`No changes`. El E2E AWS→Azure y la restauración son del corte anterior, no se
repitieron tras este cambio. Detalle en la
[evidencia de Azure](current/azure/AZURE-HEALTH-HEAD-DEPLOY-2026-10-16-0519UTC.md).

## E2E AWS–Azure, recuperación y HTTPS — 16/10/2026, 04:42–05:09 UTC

El E2E desplegado AWS→Azure completó venta/compra sintéticas con ledger demo
10→10 y outbox 51/51 entregado; el smoke de roles devolvió los 200/403
esperados. PT-DR-01 restauró una base cifrada y privada (RTO 289 s, RPO
observado ≤10 s) y se verificó la limpieza; el origen RDS continúa Single-AZ
con un día de backup. La detección fresca de CloudFormation fue `IN_SYNC` a las
05:00:46 UTC. HTTPS `/health` devolvió 200 a las 05:02:29 UTC con HSTS.

El token AWS pegado en este corte fue rechazado por STS; por ello el inventario
CLI no se pudo revalidar después de esa hora. No hubo cambios de infraestructura
en el corte. Azure CLI confirmó RG `Succeeded`, Function `Running`/HTTPS-only
y GET `/api/health` HTTP 200 con TLS válido; el 404 de HEAD se debió a que la
ruta solo acepta GET. Véase la [evidencia detallada](current/CLOUD-E2E-DR-2026-10-16-0500UTC.md).

## Revalidación puntual previa — 16/10/2026, 04:22–04:24 UTC

El perfil AWS autenticó; el stack quedó `UPDATE_COMPLETE` y la detección fresca
de drift terminó `IN_SYNC`. HTTPS `/health` devolvió 200, HTTP redirigió con
301, Azure WMS health devolvió 200, ASG/ALB tienen 2/2 sanos y las alarmas
consultadas están `OK` (la alarma 5xx no tuvo datos y considera los faltantes
como no infractores). El smoke autenticado de solo lectura por origen ALB pasó:
24 GET, concurrencia 6, 24/24 HTTP 200, p95 191.51 ms; outbox 49/49 y dos
suscripciones SNS confirmadas. No prueba capacidad sostenida ni 3,000 usuarios.
Véase [evidencia AWS de 04:24 UTC](current/aws/AWS-READONLY-LOAD-2026-10-16-0424UTC.md).

## Revalidación puntual más reciente — 16/10/2026, 04:00 UTC

HTTPS/ACM, ALB, targets AWS y health Azure se confirmaron vivos a las 03:53–03:58
UTC; RDS sigue Single-AZ y con retención de un día. Una sonda Python al dominio
recibió 403 de Cloudflare mientras `curl` e `Invoke-WebRequest` al health
recibieron 200. El runner ahora distingue códigos HTTP de errores de transporte.
Véase el [corte vivo de 04:00](current/CLOUD-REVALIDATION-2026-10-16-0400UTC.md).
El commit `b1d36a9` que incorpora la sonda autenticada también pasó los tres
trabajos de GitHub Actions ([run 38851449937](https://github.com/kyrafka/tangamandapio-cloud-migration/actions/runs/38851449937)).

La revalidación autenticada previa de roles y outbox se hizo a las 04:22–04:24
UTC: el smoke solo lectura pasó y se conciliaron 49/49 eventos. Después, el
E2E/restore de 04:42–05:00 dejó el outbox en 51/51. Véase la
[sonda previa](current/aws/AWS-READONLY-LOAD-2026-10-16-0424UTC.md) y la
[matriz cualitativa](../core/04_matriz_rubrica.md).

Siguen pendientes la ruta privada AWS–Azure (bloqueada por SCP y sin VNet),
failover/RDS Multi-AZ, carga transaccional que mida capacidad por ALB, WAF,
recorrido visual completo y capturas recientes. El mecanismo ASG sí tiene
pruebas sintéticas históricas de scale-out/in; el ciclo sintético de alarma SNS
también pasó y el usuario confirmó recepción. Falta correlacionar alarmas con
métricas reales. La base
está Single-AZ con un día de retención. La alarma de CPU baja actualmente en
`ALARM` porque el promedio quedó cerca de 1%, pero el ASG conserva su mínimo de
dos instancias. Las fuentes de evaluación también discrepan: la hoja cloud suma
18.5 aunque imprime 20; el PDF general es un instrumento diferente. No se
infiere una nota.

## Corte histórico supersedido — 15/10/2026, 19:21–19:23 UTC

Portal HTTPS, `/health` y `/ready` devolvieron 200; la portada no registró
errores JavaScript. Azure for Students está Enabled y la Function devolvió
`/api/health=200`. En Chrome, sin escribir credenciales, el portal siguió en
login y no se recorrieron vistas privadas.

La sesión web AWS mostró el stack `tangamandapio-live-20261013`
`UPDATE_COMPLETE` con 47 recursos, 2/2 destinos `Healthy` y 10 objetos en el
prefijo de releases; entre ellos está el artefacto v12. No se hizo detección
de drift ni se consultó RDS. El CLI local devuelve `ExpiredToken`; v13 no
aparece en los 10 objetos listados y la subcarpeta `qa/` no se inspeccionó.
Esto confirma estado de consola, no operatividad CLI ni una aplicación del v13.

La prueba de procesamiento de Azure de las 18:56 y la puerta local aprobada
(181 Python, 14 Node, build, auditorías, CloudFormation, seis Terraform
validate y cinco mock tests) son evidencia anterior a este corte. GitHub
Actions `38792459084` pasó para `977f437`; el documento local actualizado aún
no está en ese commit. Véase la [revalidación 19:23](current/CLOUD-REVALIDATION-2026-10-15-1923UTC.md),
la [revalidación HTTPS/headers 19:13](current/CLOUD-REVALIDATION-2026-10-15-1913UTC.md),
el [corte cloud 18:56](current/CLOUD-REVALIDATION-2026-10-15-1856UTC.md) y
la [matriz](../core/04_matriz_rubrica.md).

## Corte histórico — 15/10/2026, 00:34 UTC

En ese corte, el release v11 estaba en `UPDATE_COMPLETE`/`IN_SYNC`, con dos EC2 y targets ALB
sanos; portal, health y readiness devuelven HTTP 200. La VPC segmenta subredes
públicas del ALB, privadas de aplicación y aisladas para RDS; las reglas
permiten ALB→app→DB, sin ingreso directo a EC2 ni RDS. El E2E autenticado v11
comprobó roles, venta/recepción sintéticas, entrega AWS→Azure y ledger demo
10→10. La puerta local también pasó. Detalles: [revalidación cloud](current/CLOUD-REVALIDATION-2026-10-15.md),
[release v11](current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md),
[E2E sanitizado](current/aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-15.json) y
[QA local](current/QA-LOCAL-2026-10-15.md).

La comprobación posterior también verificó en el portal desplegado que Admin
puede consultar el estado agregado de SNS y que Comercial/Operaciones no tienen
ese acceso; véase el [smoke de permisos y alarmas](current/aws/AWS-ALARM-SUBSCRIPTIONS-ROLE-SMOKE-2026-10-15.md).

## Revalidación viva — 14/10/2026, 14:30–15:36 America/Chicago (histórico)

AWS STS autenticó con el token temporal recién entregado. CloudFormation está
`UPDATE_COMPLETE`/`IN_SYNC`; el ALB activo tiene 2/2 destinos sanos, las dos
EC2 están `InService` y sus hashes v10 coinciden con el árbol local. Los
health checks públicos respondieron 200 y el API admin anónimo dio 401. RDS
está disponible, privada/cifrada, Single-AZ con un día de backup. Este corte
supersede el 503 histórico de las 13:11.

La microprueba de lectura por el ALB tuvo 60/60 respuestas 200 (concurrencia 6,
p95 447.61 ms); el ASG se mantuvo 2/2 y sus dos destinos siguieron sanos. Eso
prueba la ruta balanceada en carga baja, no el autoescalado ni 3,000 sesiones.

La última lectura volvió a confirmar STS, CloudFormation `IN_SYNC` (14:54:31),
RDS `available` cifrada/no pública/Single-AZ con un día de backups, y salud
200 de portal, Function Azure y ambos servidores locales. No hubo cambios.

Después se completó E2E autenticado desde el portal v10 ejecutado en EC2 por
SSM: Admin inició sesión y completó ERP; Comercial/Operaciones pasaron sus
rutas 200/403; importación de SKU sintético,
venta/recepción compensatoria, 2 eventos `delivered` y ledger 10→10. Veinticuatro
lecturas autenticadas dieron 200 (concurrencia 6, p95 1,360.41 ms) por loopback
en EC2, no por ALB. Se conservaron registros de QA; no hubo cambios de
infraestructura. Application Insights registró 2 recepciones 202 y 2 workers
correctos, cero fallos. Ver el [reporte sanitizado](current/aws/AWS-PORTAL-ERP-AZURE-E2E-2026-10-14.json).

La sonda CPU de 240 s también activó Target Tracking: la alarma alta cruzó a
`ALARM`, el ASG aumentó automáticamente de 2 a 3, el target nuevo quedó sano y
la alarma volvió a `OK` al terminar la carga. Se restauró 2, la instancia
adicional se retiró tras el drenaje de 300 s y CloudFormation quedó `IN_SYNC`.
La prueba no simula una campaña de ventas ni mide capacidad de 3,000 usuarios.
Ver el [reporte sanitizado de escalado](current/aws/AWS-AUTOSCALING-TEST-2026-10-14.json).

La relectura posterior confirmó 2/2 instancias y targets sanos, ambas alarmas
Target Tracking en `OK`, health 200 de ALB/Azure Function y CloudFormation
`IN_SYNC` a las 15:36:04; no quedó carga ni instancia temporal activa.

Azure Function está `Running`/HTTPS-only y health devolvió 200. Application
Insights mostró dos eventos recibidos y dos ejecuciones correctas, sin fallos;
la ruta segura de metadatos indicó poison count aproximado 0, sin exponer
mensajes. Terraform Azure dio `No changes`; las reglas/Action Group están
habilitados, pero la entrega de alertas Azure no está probada. No hay VNet ni
túnel privado AWS–Azure. El gate local pasó 163 pruebas Python y 14 Node,
frontend y validaciones IaC.

Consulta el [checklist de cierre](current/CHECKLIST-CIERRE-2026-10-14.md) y el
[detalle de revalidación](current/CLOUD-REVALIDATION-2026-10-14.md).

## Corte anterior — 14/10/2026, 14:12–14:20 America/Chicago (supersedido)

AWS STS aceptó el token temporal; CloudFormation está `UPDATE_COMPLETE`/
`IN_SYNC`, ALB `active` con 2/2 targets sanos, dos EC2 en ejecución y RDS
disponible, privada/cifrada, Single-AZ con un día de backups. El E2E autenticado
desde EC2 v10 verificó Admin, Comercial y Operaciones, importación por API,
venta y recepción, dos eventos `delivered` por Azure y ledger demo 10→10.
Veinticuatro lecturas autenticadas tuvieron 24/24 HTTP 200 y p95 267.93 ms por
loopback, no por ALB. La puerta local pasó 163 pruebas Python y 14 Node, además
de build, auditorías y validaciones IaC. El usuario confirmó que AWS SNS entregó
alerta y recuperación; falta archivar esa evidencia. No se modificó
infraestructura; sí quedaron registros de QA sintéticos en aplicación/Azure.
La sonda posterior confirmó `/ready` y `/api` 200, `/metrics` anónimo 404.
PT-DR-01 ya había pasado con sonda SQL el 13/10: igualdad de 14 tablas,
RTO 289 s, RPO observado 14 s y limpieza verificada; no se repitió tras v10.
Application Insights registró en la ventana reciente 2 eventos aceptados, 2
ejecuciones de consumidor y cero fallos. El peek de `fulfillment-events-poison`
fue denegado por RBAC y no alteró mensajes.

En ese corte aún faltaba la consulta de la cola poison; el acceso directo de la
identidad local a Storage fue denegado. El conteo actual se consultó después
por una ruta autenticada de solo metadatos. Para los pendientes vigentes,
consulte el checklist enlazado arriba.

## Despliegue, E2E, IaC y lectura concurrente — pruebas de 12:13–12:17; estado revalidado 12:25 America/Chicago

AWS v10 quedó en `UPDATE_COMPLETE` e `IN_SYNC`, con 2/2 destinos sanos; Azure
Function usa el paquete vigente y Terraform quedó en `No changes`. La compuerta
local aprobó 155 pruebas Python y 8 Node. El E2E desde la cuenta admin del
portal v10 confirmó venta, recepción compensatoria, dos eventos entregados y
saldo sintético inicial/final 10. Una detección fresca de deriva dio cero
desviaciones; el plan Terraform Azure terminó `No changes` y la Function está
`Running`/HTTPS-only. 24 lecturas en una EC2 con concurrencia 6 dieron 24/24
HTTP 200, p95 304 ms; no es prueba de capacidad del ALB/ASG. Queda pendiente
probar la importación CSV desde navegador autenticado. Ver el [informe de despliegue](current/DEPLOY-CATALOGO-SINTETICO-2026-10-14.md) y
la [evidencia funcional del catálogo](current/CATALOGO-SINTETICO-IMPORT-2026-10-14.md).

La relectura de las 12:25, posterior a esas pruebas, encontró el ALB en HTTP
503; Azure health continuó en 200. AWS STS autentica, pero `voc-cancel-cred`
deniega las lecturas de CloudFormation y SSM, por lo que no se confirmó el
estado actual de EC2/targets. No hubo cambios cloud. Ver el
[corte vigente](current/CLOUD-REVALIDATION-2026-10-14.md).

Después, a las 12:30–12:32, el smoke vivo Azure volvió a comprobar los guards
de ingreso y el recorrido sintético venta/recepción, restaurando el saldo demo.
El productor fue local/SQLite, no AWS; ver el [E2E Azure](current/azure/AZURE-ERP-E2E-2026-10-14.md).

## Reejecución transaccional con credenciales efímeras — 14/10/2026, 05:11

40/40 transacciones creadas y leídas, 40 eventos outbox pendientes, cero
errores, p95 550.73 ms y 53.18 transacciones/s con concurrencia 8. El harness
ahora genera credenciales aleatorias por proceso; la base es temporal y no hubo
llamadas cloud. Ver el [resultado bruto](current/LOCAL-TRANSACTIONAL-LOAD-2026-10-14-0511.json)
y sus límites en la [revalidación](current/CLOUD-REVALIDATION-2026-10-14.md).

## Compuerta repetida con carga transaccional integrada — 14/10/2026, 05:09 America/Chicago

La puerta local pasó con 130 pruebas Python, 8 Node, frontend, auditorías,
CloudFormation/Terraform y PT-PERF-02 (40 pedidos concurrentes en SQLite
temporal). El nuevo flujo quedó integrado también al workflow GitHub Actions;
no hubo escrituras cloud. Ver [QA](current/QA-LOCAL-2026-10-14.md),
[carga](current/LOCAL-TRANSACTIONAL-LOAD-2026-10-14.json) y
[workflow](../.github/workflows/quality-gate.yml).

## Estado cloud comprobado — 14/10/2026, 04:59 America/Chicago

AWS `default` vuelve a fallar STS por `ExpiredToken`; el ALB responde salud,
readiness y API 200, métricas 200 sin sesión y rechaza la API admin anónima
(401). `/api` y `/health` continúan indicando el campo `instance`, por lo que
el hardening v6 local no se debe confundir con el release público. Azure for
Students está `Enabled`; ARM devuelve la Function `Running`/HTTPS-only y el
endpoint health devuelve `ok`. Application Insights registra 18 solicitudes
en 12 h, 0 fallidas y 2 ejecuciones del consumidor de eventos, la última a las
04:25:28. No hubo mutaciones ni invocación nueva. El [corte detallado](current/CLOUD-REVALIDATION-2026-10-14.md)
separa salud, procesamiento real e inventario demo.

## Compuerta integral repetida — 14/10/2026, 04:58 America/Chicago

Tras la prueba transaccional local, la puerta completa volvió a aprobar:
130 pruebas Python, 8 Node, frontend, auditorías, CloudFormation y Terraform
fmt/validate/tests. No hizo escrituras cloud. Ver el [detalle QA](current/QA-LOCAL-2026-10-14.md).

## Carga transaccional local — 14/10/2026, 04:53 America/Chicago

PT-PERF-02 ejercitó 40 flujos autenticados de creación y lectura concurrente
con SQLite temporal (40 pedidos y 40 eventos outbox persistidos, sin errores;
p95 450.81 ms). No tocó servicios externos, la base compartida ni la nube.
El alcance y sus límites están en el
[corte de revalidación](current/CLOUD-REVALIDATION-2026-10-14.md); el
[resultado bruto](current/LOCAL-TRANSACTIONAL-LOAD-2026-10-14.json) y el
[harness reproducible](../tests/performance/transactional_load_test.py) quedan
en el proyecto.

## Compuerta integral local — 14/10/2026, 04:37 America/Chicago

La puerta oficial volvió a terminar `QUALITY_GATE=APROBADA`: 130 pruebas
Python, 8 Node, build, auditorías sin vulnerabilidades conocidas,
CloudFormation, Terraform y pruebas mock. No hizo escrituras cloud. También se
confirmó que el tarball v6 local coincide con la revisión declarada y su SHA
documentada; no se subió a AWS. Ver
[detalle QA](current/QA-LOCAL-2026-10-14.md).

## Corte live, telemetría y reconciliación IaC — 14/10/2026, 04:30–04:45 America/Chicago

El perfil AWS CLI `default` se resuelve desde el archivo compartido de
credenciales, pero STS devolvió `ExpiredToken`; la sesión temporal venció. No
se consultó inventario privado ni se hicieron cambios. El ALB respondió 200 en
salud/readiness, pero `/api`
incluye el campo `instance` y `/metrics` acepta GET anónimo; la API admin
anónima responde 401. Azure `/api/health` y el plan Terraform normal
`azure-rebuild` respondieron 200 / `No changes` (salida 0), sin `apply`. La
sonda ALB a las 04:43 obtuvo 20/20 health 200 y dos marcadores de backend; no
reemplaza la lectura del ASG/target group. PT-PERF-01 obtuvo 100/100 health
200 con concurrencia 10, p95 851.9 ms y cero errores; no mide transacciones.
Ver [resultado bruto de rendimiento](current/aws/AWS-PERF-HEALTH-2026-10-14.json). La
vista previa v6 en `:8081` no publica `instance` ni `/metrics`; el proceso
heredado `:8080` aún sí. Application Insights confirmó 2 ejecuciones exitosas,
0 fallidas, con la más reciente a las 04:25:28; no se repitió el E2E ni se
leyeron payloads. Ver
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-14.md),
[plan Terraform](current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md) y
[E2E/telemetría Azure](current/azure/AZURE-ERP-E2E-2026-10-14.md).

## E2E Azure desde release local — 14/10/2026, 04:25 America/Chicago

El candidato local v6 recorrió ERP→outbox→Azure Queue/Function→reconciliación:
venta `evt-ace184920d8e4921b4bcf265d4babbf6`, recepción compensatoria
`evt-88e01b6734f2427da35d04b819460989`. Ambos eventos terminaron con sus estados
demo esperados y el saldo volvió al valor inicial. Los registros sintéticos
permanecen en Azure Audit; no se escribió a RDS/EC2 ni se aplicó infraestructura.
El gate local actual aprobó 130 pruebas unitarias y 8 Node. Véanse el
[E2E detallado](current/azure/AZURE-ERP-E2E-2026-10-14.md) y la
[QA local](current/QA-LOCAL-2026-10-14.md).

## Lectura autenticada Azure — 14/10/2026, 04:14 America/Chicago

La suscripción sigue `Enabled`. Se verificó por ARM autenticado que la Function
`tangama-wms-261008` está `Running`, HTTPS-only y en Linux; salud pública 200.
El Azure CLI se quedó esperando por una ruta IPv6 sin respuesta, así que la
lectura se completó por IPv4 sin guardar ni mostrar el token. AWS STS autenticó,
pero CloudFormation, Auto Scaling y ELB siguen denegados. Solo lecturas; sin
despliegues ni mutaciones. Detalle en el
[corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md).

## Gate y prueba HTTP del candidato local v6 — 14/10/2026, 04:07 America/Chicago

El gate pasó con 126 pruebas Python, 8 Node, auditorías, build, CloudFormation y
Terraform fmt/validate/tests. El candidato AWS v6 elimina hostnames privados
de las respuestas públicas `/api` y `/health`, y reduce `/ready` a estado
genérico; deshabilita `/metrics` por defecto y conserva Prometheus en Compose
local mediante opt-in. El paquete local verificado es
`portal-b2b-20261014-public-diagnostics-hardening-v6-python312.tar.gz`, SHA-256
`bfe3e7e45dd4f5c4a06ff6a795740801e88b9e949778b566682b0624bdd1606c`.
La compuerta se repitió a las 04:07 y volvió a aprobar las 126 pruebas Python,
8 Node, auditorías, build y validaciones IaC. El candidato también respondió
por HTTP real en `127.0.0.1:8081`: portada/assets/API/health/readiness 200,
sin `instance`; métricas 404 y API admin anónima 401. El login de una cuenta
temporal admin con CSRF válido permitió abrir `/administracion` (200) y consultar
una única cuenta de prueba. El proceso en `:8080` se preservó y aún expone el
comportamiento anterior. v6 permanece sin publicar;
el release AWS vivo aún tiene la filtración descrita en
[el corte de seguridad](current/SECURITY-PUBLIC-DIAGNOSTICS-2026-10-14.md).

## Salud pública tras reintento — 14/10/2026, 03:25 America/Chicago

El ALB ahora responde 200 en portada/health/readiness; su API administrativa
anónima responde 401; cinco health checks consecutivos del ALB dieron 200.
Azure Function está `Running`, fuerza HTTPS y su health devuelve 200; se
confirmó inventario de Application Insights/Log Analytics,
Action Group y alertas de latencia/5xx. Local health responde 200. AWS STS
autentica, pero la política del lab deniega leer ASG y balanceadores, por lo
que el número/estado de destinos no está confirmado. No hubo mutaciones ni
nueva captura visual. Ver [corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md).

## QA local integral — 14/10/2026, 03:17 America/Chicago

La compuerta local terminó `QUALITY_GATE=APROBADA`: 122 pruebas Python, 8
Node, build Vite, auditoría de dependencias, CloudFormation y Terraform
fmt/validate/tests. No hubo operaciones cloud; la prueba de salud posterior de
las 03:25 dio HTTP 200 en AWS. Ver [detalle QA](current/QA-LOCAL-2026-10-14.md)
y [corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md).

## Revalidación de Auto Scaling y ALB — 14/10/2026, 03:12 America/Chicago

AWS ahora muestra el grupo con 0 instancias pese a deseada 2, 0 destinos en el
target group y HTTP 503 en portada/health/readiness. Auto Scaling registra
`Client.InternalError` al lanzar; CloudTrail y parte de la API EC2 están
denegados, así que la causa raíz aún no está confirmada. Azure Function
`/api/health` sí respondió 200 en la suscripción activa; la interfaz local
mostró correctamente el inicio de sesión y el smoke local dio 200/200/200 en
portada/health/readiness y 401 en el API admin anónimo. No se aplicó IaC ni se
modificó la nube. Ver
[revalidación EC2/ALB](current/aws/AWS-REVALIDACION-EC2-BOOT-2026-10-14.md).

## Terraform Azure reconciliado — 14/10/2026, 02:50:40–02:51:38

Plan normal de solo lectura terminó `No changes`, salida 0; sin `apply` ni
plan guardado. En el mismo corte, AWS denegó también la lectura del ASG. Ver
[plan Azure](current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md) y
[corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md).

## Confirmación AWS posterior a QA — 14/10/2026, 02:45 America/Chicago

El 503 persiste en portada, health, readiness y API admin del ALB. Azure
health responde 200; local health responde 200 y su API admin anónima devuelve
401. La causa AWS sigue sin determinar porque el rol no permite leer el
inventario. [Corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md).

## QA local más reciente — 14/10/2026, 02:44 America/Chicago

La compuerta volvió a pasar (122 pruebas Python, 8 Node, frontend, auditorías,
CloudFormation y Terraform). El empaquetador Azure y el chequeo del ZIP
generado quedaron compatibles con Windows PowerShell 5.1; no hubo cambios
cloud. [Detalle QA](current/QA-LOCAL-2026-10-14.md).

## E2E Azure con compensación — 14/10/2026, 02:25 America/Chicago

La Function volvió a procesar venta demo y recepción compensatoria; el smoke
validó que el ledger ficticio retornara a su valor inicial. El E2E fue desde
proceso local, no desde EC2. Dos eventos sintéticos permanecen en auditoría
Azure. Ver [prueba detallada](current/azure/AZURE-ERP-E2E-2026-10-14.md).

## Revalidación pública de servicios — 14/10/2026, 02:20 America/Chicago

El hostname vigente del ALB respondió 503 en portada, health, readiness y
administración. Azure Function `/api/health` respondió 200 y el portal local
respondió 200 en health/readiness; la API admin anónima local respondió 401.
CloudFormation/EC2 no se pudieron consultar por permisos, por lo que la causa
del 503 AWS no está determinada. Ver [corte actualizado](current/CLOUD-REVALIDATION-2026-10-14.md).

## Preflight VPN AWS–Azure — 14/10/2026, 02:17 America/Chicago

AWS STS autenticó, pero AWS denegó el `CreateCustomerGateway --dry-run`; las
consultas de inventario VPN no se pudieron completar. Azure está autenticado,
pero el grupo de red privado no existe. No se desplegaron recursos. La evidencia
y el siguiente paso seguro están en
[preflight AWS–Azure VPN](current/aws/AWS-AZURE-VPN-PREFLIGHT-2026-10-14.md).

## Estimación inicial de costos — 14/10/2026

Con el inventario AWS consultado y precios públicos oficiales se creó un cálculo
reproducible de **$91.92 USD/mes de subtotal AWS** para 730 horas, 1 LCU promedio
y 10 GB procesados por NAT. No es una cotización ni incluye todos los cargos.
Function Azure Consumption puede usar subvenciones bajo requisitos de
elegibilidad; Blob/Queue, tráfico y costos académicos reales no están medidos.
El cálculo y las exclusiones están en
[estimación cloud](../core/13_estimacion_costos_cloud_2026-10-14.md) y el
[script local](../iac/scripts/estimate_cloud_costs.ps1). No se desplegó ni
modificó infraestructura para estimar.

## Compuerta local completa — 14/10/2026, 02:12 America/Chicago

Pasaron 122 pruebas Python y 8 de navegación por rol, build, auditorías,
CloudFormation y Terraform; `QUALITY_GATE=APROBADA`, sin operaciones cloud.
También pasó la nueva prueba del estimador PowerShell en sus escenarios de
$91.92 y $64.19, incluida la separación de horas de cómputo e infraestructura
compartida.
Las suites de UI validan el menú esperado, no sesión autenticada en navegador.
El detalle está en [QA local](current/QA-LOCAL-2026-10-14.md).

## Estado AWS/Azure — 14/10/2026, 01:46 America/Chicago

AWS STS aceptó la sesión; CloudFormation `UPDATE_COMPLETE`, 2/2 destinos
`healthy` y RDS disponible, cifrada, privada, Single-AZ, con un día de backup.
En Azure, el plan Terraform más reciente terminó `No changes` con la
suscripción activa. Solo lecturas; sin cambios cloud. Véase el
[corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md) y el
[plan Azure](current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

El usuario confirmó recibir tanto el correo de alarma como el de recuperación
de la prueba sintética; se registra como confirmación directa, sin captura ni
telemetría independiente. Detalle en [prueba de alarma](current/aws/AWS-ALARM-TEST-2026-10-14.md).

## Terraform Azure sin drift — 14/10/2026, 01:44 America/Chicago

Con la suscripción **Azure for Students** activa, `terraform validate` pasó y
el plan normal de `azure-rebuild` terminó `No changes` (salida 0); el state
local y la cuenta coinciden. Sin `apply` ni mutaciones. Confirma el root y las
variables de reconstrucción actuales, no el WMS comercial ni VPN. Evidencia en
[el plan Azure](current/azure/AZURE-TERRAFORM-PLAN-2026-10-14.md).

## Paridad del código AWS más reciente — 14/10/2026, 01:40 America/Chicago

Las dos EC2 del ASG reportaron por SSM la revisión v5 activa y SHA-256 iguales
al árbol local para `app.py`, `erp_service.py` y `requirements.lock`. Lectura
remota; sin reinicios ni cambios. La comprobación no cubre cada asset ni una
sesión autenticada en navegador. Véase [el release AWS v5](current/aws/AWS-DESPLIEGUE-2026-10-14.md).

## Revalidación cloud más reciente — 14/10/2026, 01:37 America/Chicago

AWS STS autenticó en la cuenta esperada; CloudFormation está
`UPDATE_COMPLETE`/`IN_SYNC`, el ALB actual está activo, ambos destinos sanos y
RDS disponible, cifrada y privada. El DNS vigente del ALB responde `/health` y
`/ready` HTTP 200; los seis assets del portal también cargan. Sin sesión, la
vista admin redirige (303) y su API devuelve 401. Azure ARM confirmó la
Function `Running`, HTTPS-only, Linux, y `/api/health` respondió `ok`. Solo
lecturas; sin despliegues ni mutaciones. Véase [el corte de revalidación del
14/10](current/CLOUD-REVALIDATION-2026-10-14.md).

## E2E Azure más reciente — 14/10/2026, 01:35 America/Chicago

El E2E ERP local→Queue/Function completó venta y reposición compensatoria; el
saldo demo volvió a 24. La cola poison informó `ok`, conteo aproximado 0 y no
expuso payloads. Quedaron dos eventos sintéticos auditables; no se tocó RDS ni
infraestructura. Detalle en [E2E Azure del 14/10](current/azure/AZURE-ERP-E2E-2026-10-14.md).

## SMTP de desarrollo — 14/10/2026, 01:38 America/Chicago

La prueba local de API envió por SMTP a un receptor temporal y guardó el mismo
mensaje en el portal. Docker/Mailpit no estaba operativo y no se comprobó
entrega externa. El resultado y la limitación están en [QA local](current/QA-LOCAL-2026-10-14.md).

## QA local más reciente — 14/10/2026, 01:27 America/Chicago

La compuerta integral volvió a pasar: 122 pruebas Python (47 API, 23 Azure,
42 release AWS y 10 guards/smoke) y 8 de navegación por rol, build web,
auditorías, CloudFormation, Terraform y pruebas mock de costo y red. Las
pruebas verifican también que ambos HTML puedan servir sus bundles. La
navegación de admin incluye sus módulos administrativos; roles desconocidos
fallan cerrados. Esto no sustituye pruebas visuales ni de autorización con
sesiones reales en navegador. La instancia local devolvió `/health` y `/ready`
con estado `ok`. No hubo cambios cloud. El detalle y límites están
en [QA local del 14/10](current/QA-LOCAL-2026-10-14.md).

Después se regeneró el build servido por Flask en `app/src/static`; la página y
los assets respondieron HTTP 200 junto con `/health` y `/ready`. El bundle AWS
es separado y no se sustituyó.

## Revalidación autenticada y alarma — 14/10/2026, 01:02 America/Chicago

AWS STS autenticó; CloudFormation sigue `UPDATE_COMPLETE`/`IN_SYNC`, con dos
destinos saludables y RDS cifrada, privada y disponible. Los health checks
de AWS y Azure devolvieron 200. ARM confirmó la cuenta `Enabled` y la
Function `Running`, `httpsOnly=true`, Linux, West US. No hubo despliegues ni
cambios de configuración; la alarma cambió de estado temporalmente y quedó
restaurada. Application Insights registró dos solicitudes del procesador de
fulfillment, código 0 y cero fallidas. La alarma ejecutó el ciclo sintético
`OK → ALARM → OK`, con acciones SNS exitosas; la recepción del correo no está
confirmada. El preview HTTPS tuvo cero cambios de recursos y se eliminó sin
ejecutarlo. El detalle está en [la revalidación del 14/10](current/CLOUD-REVALIDATION-2026-10-14.md) y [la prueba de alarma](current/aws/AWS-ALARM-TEST-2026-10-14.md).

## Último release y salud pública — 14/10/2026, 00:45 America/Chicago

AWS ya ejecuta el release v5 probado: CloudFormation `UPDATE_COMPLETE`, drift
`IN_SYNC`, dos instancias en zonas distintas, `/health` y `/ready` 200, y RDS
preservada. Las rutas admin redirigen o exigen sesión como se espera. Nuevas
lecturas públicas y anónimas a las 00:45 devolvieron HTTP 200 en `/health` del
ALB (PostgreSQL `ok`) y en `/api/health` de Azure. Esto no consulta inventario
autenticado ni cambia recursos. La CLI de Azure se demoró al consultar el
hash vivo, así que esa huella queda pendiente de relectura. El detalle, SHA,
pruebas, límites y preparación local del cierre HTTPS están en [el release AWS v5](current/aws/AWS-DESPLIEGUE-2026-10-14.md).
El E2E compensado del mismo código hacia Azure pasó y quedó separado de la
evidencia previa de EC2 en [el E2E del 14/10](current/azure/AZURE-ERP-E2E-2026-10-14.md).

## Revisión cloud más reciente — 13/10/2026, 23:50 America/Chicago

AWS STS autenticó; CloudFormation sigue `UPDATE_COMPLETE`, el target group tiene
2/2 `healthy` y RDS está disponible, cifrada, Single-AZ y con un día de backup.
El portal local dio `/health` y `/ready` 200. En Azure, ARM confirmó el grupo
`rg-tangamandapio-rebuild-wus` `Succeeded` y la Function `tangama-wms-261008`
`Running`/HTTPS-only; `/api/health` respondió 200. Azure CLI estaba instalada
fuera del `PATH`, así que se corrigió la lectura previa que afirmaba que no
estaba instalada. No se modificó infraestructura. Estas lecturas no prueban
conectividad privada ni convierten el ledger ficticio en un WMS comercial.
Detalle en
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md),
[despliegue AWS](current/aws/AWS-DESPLIEGUE-2026-10-13.md) y
[E2E Azure](current/azure/AZURE-ERP-E2E-2026-10-13.md). La QA local pasó por
separado, sin operaciones cloud.

## Revisión local más reciente — 14/10/2026, 01:08 America/Chicago

La compuerta `tests/run_local_quality.ps1 -ValidateTerraform` se volvió a
ejecutar después de reforzar el preflight HTTPS: terminó con
`QUALITY_GATE=APROBADA`, 120 pruebas, build web, auditorías de dependencias,
CloudFormation y validaciones Terraform. El nuevo mock ACM prueba hostname,
región, estado del certificado, SAN y wildcard, sin crear change sets ni tocar
la nube. La corrida más reciente también validó el patrón DNS reforzado de
CloudFormation. Fue una ejecución local y no revalida la salud cloud. Véase [QA local
del 14/10](current/QA-LOCAL-2026-10-14.md). El corte cloud previo sigue siendo
el del 13/10. A las 23:50, el portal local en
`127.0.0.1:8080` respondió `/health` y `/ready` con HTTP 200; la base local
reportó `ok`. No se inició sesión ni se modificaron datos. La última compuerta
está registrada en [QA local del 14/10](current/QA-LOCAL-2026-10-14.md); la
[revalidación local](current/LOCAL-LIVE-RECHECK-2026-10-13.md) conserva el
detalle del health check.

## Runtime fijado y release candidato — 13/10/2026, 21:32 America/Chicago

El bootstrap EC2 instala Python 3.12 en un virtualenv aislado porque el Python
de sistema de AL2023 sigue en 3.9; el runtime y el lock con hashes pasaron el
dry-run Linux y la auditoría. QA integral aprobada: 120 pruebas, frontend,
CloudFormation y Terraform sin operaciones cloud. El candidato v4 permanece
local; revisión y SHA-256 están en [QA](current/QA-LOCAL-2026-10-13.md). AWS
`default` requiere renovar el token, por lo que no se publicó.

## Claves de release inmutables — 13/10/2026, 20:52 America/Chicago

La reconstrucción y publicación AWS ahora requieren SHA-256, una clave S3
derivada de esa huella y validación del paquete en EC2 antes de extraerlo. Se
probaron ambos rechazos fail-closed (hash inválido y clave mutable). QA local
completa: 120 pruebas y validaciones AWS/Azure IaC, sin `apply`. El artefacto
actual está comprobado pero no se publicó; AWS sigue en `ExpiredToken`. Detalle
en [QA local](current/QA-LOCAL-2026-10-13.md) y
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md).

## Integridad del release AWS y QA — 13/10/2026, 20:41 America/Chicago

Se añadió checksum SHA-256 del paquete en la reconstrucción y actualización
CloudFormation, con verificación en EC2 antes de extraer. La compuerta local
completa aprobó: 120 pruebas, auditorías, build web, `cfn-lint` y Terraform
fmt/validate/tests mock; sin cambios cloud. AWS `default` devuelve
`ExpiredToken`, así que no se publicó AWS. Véase la
[QA local](current/QA-LOCAL-2026-10-13.md) y la
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md).

El candidato histórico v2 conservado localmente tiene SHA-256
`706AD7199E7B0A1A249BF434E89003D4030093B4AD7423AFB1665084B10039D7`; quedó
supersedido porque no contiene el lock de runtime. El candidato vigente es v3,
con hash y contenido verificados en [QA local](current/QA-LOCAL-2026-10-13.md);
ninguno de los dos se ha subido a S3.

## Release Azure y corte operativo — 13/10/2026, 20:14 America/Chicago

El release de validación de eventos quedó desplegado y sin drift posterior. El
E2E ERP local→Azure terminó con venta y reposición compensatoria, saldo demo
restaurado y cola poison en 0; ARM confirmó la Function `Running`/HTTPS-only,
el health Azure y readiness local respondieron 200. AWS `default` expiró en la última consulta y la lectura autenticada
anterior había sido denegada explícitamente por `voc-cancel-cred`. No se publica
AWS ni se infiere su estado actual. Véanse la
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md), la
[evidencia del release](current/azure/AZURE-RELEASE-EVENT-TYPE-GUARD-2026-10-13.md)
y la [revalidación local](current/LOCAL-LIVE-RECHECK-2026-10-13.md).

## Corrección de permisos ERP — 13/10/2026, 19:00 America/Chicago

El resumen ERP ya filtra indicadores según permisos server-side, incluidos
los saldos financieros. Las regresiones demostraron el defecto y verificaron
la corrección en backend local y release AWS; la compuerta integral aprobó 118
pruebas. El candidato v2 está empaquetado localmente y no se publicó. Detalle:
[QA local](current/QA-LOCAL-2026-10-13.md),
[matriz](../core/04_matriz_rubrica.md) y
[revalidación AWS/Azure](current/CLOUD-REVALIDATION-2026-10-13.md).

## Compuerta integral local — 13/10/2026, 18:48 America/Chicago

La última ejecución de `run_local_quality.ps1 -ValidateTerraform` terminó
aprobada: 116 pruebas unitarias, auditorías de dependencias, build de
producción y validaciones CloudFormation/Terraform. No hizo operaciones de
nube. El stack vivo local y sus respuestas están en la
[revalidación local](current/LOCAL-LIVE-RECHECK-2026-10-13.md).

## Revalidación cloud y E2E — 13/10/2026, 18:43 America/Chicago

AWS STS autentica, pero una denegación explícita impide leer CloudFormation;
el ALB está sano y las rutas administrativas live continúan en 404. Azure
Function está `Running`, HTTPS-only, y el E2E compensado volvió a completar la
venta/recepción en Queue/Function, restaurando el saldo del ledger ficticio.
No se desplegó ni cambió infraestructura. Véanse la
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md), la
[prueba E2E](current/azure/AZURE-ERP-E2E-2026-10-13.md) y la
[revalidación local](current/LOCAL-LIVE-RECHECK-2026-10-13.md).

## Última revalidación local — 13/10/2026, 18:39 America/Chicago

El stack local está `healthy` y portal, APIs protegidas, assets del panel admin,
Function Azure local y Mailpit respondieron según lo esperado. No se reinició
ningún servicio. Este corte no modifica la nube: en la última consulta AWS
registrada, STS autenticó pero una política explícita denegó leer CloudFormation;
el ALB respondió, aunque las rutas admin publicadas dieron 404. No se debe
desplegar hasta recuperar lectura fiable del stack y reconciliar la versión live.
Detalle local: [revalidación viva](current/LOCAL-LIVE-RECHECK-2026-10-13.md).

## Revalidación final — 13/10/2026, 18:33 America/Chicago

La compuerta local pasó con 116 pruebas; el artefacto de administración
coincide archivo por archivo con la fuente y no se publicó. AWS ALB responde
200, pero las rutas de administración dan 404 y AWS deniega el inventario por
una política explícita: hace falta reconciliar el backend live antes de
desplegar. Se quitaron los nombres predeterminados antiguos de los scripts
deploy/rebuild/destroy; el guard nuevo bloquea nombres no verificados antes de
cualquier llamada AWS. También se endurecieron PT-STO/PT-MON y se probó que la
alarma recupere su estado incluso ante un error. Azure Function aparece
`Running` con health `ok`. No se cambió nube. Detalle:
[QA local](current/QA-LOCAL-2026-10-13.md) y
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md).

## Revalidación de AWS/Azure — 13/10/2026

La Function Azure correcta (`tangama-wms-261008`) está `Running`, HTTPS-only,
con health 200; el E2E ERP→Queue/Function pasó y compensó el SKU demo al saldo
inicial. AWS STS autenticó como `voclabs`, pero la política denegó las lecturas
de inventario y CloudFormation, así que su estado actual y un change set antiguo
no se pudieron verificar. No se desplegó. Véase la
[revalidación cloud](current/CLOUD-REVALIDATION-2026-10-13.md).

## QA local previa a publicación — 13/10/2026

La puerta local aprobó 116 pruebas unitarias, frontend, auditorías de
dependencias, CloudFormation y Terraform; el stack Docker local pasó sus probes
de salud, recursos y control de acceso. Esto no certifica servicios cloud,
WebRTC entre navegadores ni correo externo. Antes del siguiente despliegue hay
que revisar si quedó un change set preparado por un proceso local previo y
volver a generarlo desde el código probado. El paquete local candidato tiene
SHA-256 `9cc7cea6bc501267bdff919d0790b447077748c0abf4df51167ed4d0eeba878a`;
no se ha subido a S3. Detalle:
[QA local del 13/10](current/QA-LOCAL-2026-10-13.md).

## Revalidación — 13/10/2026, 16:23 America/Chicago

AWS aceptó el change set inspeccionado para `HighCPUAlarm`: fue el único
recurso modificado, sin reemplazo. Después, se añadió SNS con dos suscripciones
confirmadas y acciones en las cinco alarmas; tampoco hubo reemplazos. La alarma
usa períodos de 300 s y falta de datos indeterminada. CloudFormation quedó
`UPDATE_COMPLETE` y `IN_SYNC` con cero drift. `/health` dio 200, el ALB conserva
2/2 destinos sanos y la Function Azure dio 200. Las rutas de negocio sin sesión
devolvieron 401. RDS está privado/cifrado y los dos buckets del stack usan
AES256. Las alarmas notifican cambios de estado; no se envió un mensaje
artificial. Detalle: [revalidación operativa](current/aws/AWS-OBSERVABILIDAD-2026-10-13.md).

La puerta local terminó con 98 pruebas unitarias, build frontend, auditoría de
dependencias, validación CloudFormation/Terraform y cinco gates mock de
red/costo. El intercambio AWS→Azure a nivel de aplicación funciona por HTTPS
público; no necesita VPN. La conectividad IP privada sí queda aplazada al
cierre. No se creó dominio/certificado.

## Revalidación anterior — 13/10/2026, 15:57 America/Chicago

AWS `tangamandapio-live-20261013` está `UPDATE_COMPLETE`, el ALB tiene 2/2
destinos sanos y `/health` respondió HTTP 200 con PostgreSQL `ok`. Azure
`/api/health` respondió HTTP 200. RDS principal sigue `available`, privado y
cifrado. La repetición PT-DR-01 restauró el marcador y verificó los conteos de
negocio; RTO **289 s**, RPO superior observado **14 s** y limpieza confirmada:
sin copia ni snapshot temporales. Ver el [registro de recuperación](current/aws/AWS-DR-RESTORE-2026-10-13.md).

La comprobación de dominio no encontró hosted zones en Route 53; además, el rol
AWS Academy denegó `cloudfront:ListDistributions`, así que no se usó CloudFront.
El ALB sigue HTTP-only y no hay dominio/certificado adjunto. La plantilla ya
admite un ARN ACM opcional, listener 443, redirección HTTP→HTTPS y cookies
`Secure`. La rúbrica final XLSX tiene 14 criterios y 20 puntos. No incluye
dominio/HTTPS como renglón separado; sí evalúa cifrado/seguridad (criterio 5) y
pruebas de seguridad/conectividad (criterio 12), por lo que HTTPS válido
fortalece esos criterios sin sumar puntos automáticos. El DOCX de cinco
categorías es la rúbrica breve del Entregable 1, no sustituye la final.

## Último corte combinado — 13/10/2026, aproximadamente 15:28 America/Chicago

En la lectura final AWS el stack del portal estaba `UPDATE_COMPLETE`, con dos
destinos ALB `healthy`, `/health` HTTP 200 (`database=ok`) y `/ready` HTTP 200.
Azure `/api/health` también dio HTTP 200 (`ok`). La lectura RDS de 15:15 lo vio
`available`, privado, Single-AZ y con un día de backup. No se cambiaron
recursos. CloudFormation terminó una detección `IN_SYNC` a las 15:30, con cero
recursos drifted; no es una comprobación Terraform Azure.

Alrededor de las 15:18 el smoke vivo procesó una venta y su compensación por
Azure Queue/Function usando el release ERP local; el ledger ficticio volvió a
24 (24 → 23 → 24). El E2E anterior desde EC2, a las 02:32, ya había confirmado
el camino de aplicación AWS→Azure por HTTPS público. Ninguna de esas pruebas
demuestra una ruta privada entre subredes. El VPN queda para el final y Azure no
tiene VNet. Véanse el [E2E reciente](current/azure/AZURE-ERP-E2E-2026-10-13.md),
la [prueba AWS–Azure desde EC2](current/azure/AZURE-AWS-INTEROP-2026-10-13.md)
y la [revalidación](current/REVALIDACION_ESTADO_2026-10-13.md).

El intento temporal de VPN de las 14:46 quedó limpio después de que AWS Academy
denegara `ec2:CreateCustomerGateway` mediante una SCP; no se estableció túnel,
BGP ni ruta privada. A las 14:53 Tailscale seguía offline y Azure no tenía
VNet. No se volvieron a tocar recursos cloud. Los detalles están en el
[registro de interoperabilidad](current/azure/AZURE-AWS-INTEROP-2026-10-13.md)
y el [diseño overlay](../iac/environments/aws-azure-tailscale/README.md).

La puerta local completa terminó con 98 pruebas, auditoría de dependencias,
build frontend, validación CloudFormation/Terraform y cinco pruebas mock de
costo/red; no aplicó recursos. **Corrección 13/10:** no publicar 11.75/20.
La rúbrica fuente suma 18.5 en sus pesos, aunque imprime 20, y no asigna
puntos por descriptor. Véase la [nota de auditoría de rúbrica](current/REVALIDACION_ESTADO_2026-10-13.md).

## Corte anterior — 13/10/2026, 13:15 America/Chicago

AWS `default` autentica por STS en la cuenta académica `841113066612` con la
terna temporal entregada para el laboratorio. El stack
`tangamandapio-live-20261013` está `UPDATE_COMPLETE`; el ALB y `/`, `/health` y
`/ready` responden HTTP 200. Ocho consultas de salud alcanzaron ambas instancias
`InService`/`Healthy`; `/health` reportó `database=ok`. Tras un corte HTTP 503 a
las 13:08, Auto Scaling lanzó reemplazos con éxito sin que se modificara AWS.
RDS está `available`, PostgreSQL `db.t3.micro`, Single-AZ y retención de backup
de 1 día. El ALB solo tiene listener HTTP/80; no hay conexión VPN AWS–Azure.
Las alarmas aparecen `OK`, pero sus periodos carecen de datos y el missing-data
está configurado como `NonBreaching`, así que no prueban disponibilidad continua.

Azure `tangama-wms-261008` está `Running` en
`rg-tangamandapio-rebuild-wus`, con acceso público habilitado; `/api/health`
responde HTTP 200. El grupo `rg-tangama-private-network` no existe. No se
modificaron recursos de AWS ni Azure. Se preparó y eliminó, sin ejecutar, un
change set de monitoreo: también alteraba el launch template y la política de
escalado con reemplazo condicional, así que queda pendiente reconciliar esa
diferencia antes de desplegar. Los registros posteriores
son históricos y no sustituyen este estado vivo hasta una nueva comprobación.
Ver [revalidación actual](current/REVALIDACION_ESTADO_2026-10-13.md),
[inventario AWS](current/aws/AWS-INVENTARIO-2026-10-13.md) y
[STS AWS](current/aws/AWS-REVALIDACION-STS-2026-10-13.md).

El E2E compensado de las 12:16 procesó 24→23→24 en el ledger ficticio y no
invocó EC2. El release Azure anterior usó el paquete reproducible SHA-256
`643750B5497FEC9705BC7FE04742060FEC48F947AA81D6C7E86C5FAB6758A3BE`. Terraform
creó el Blob nuevo, actualizó la configuración de la Function y retiró el Blob
previo (1 alta/1 cambio/1 destrucción); el Blob tiene soft delete de 7 días y
el ZIP previo se conservó localmente. Se sincronizaron triggers, `/api/health`
dio `ok` y un E2E posterior completó una venta y su compensación; el SKU
ficticio volvió a 24 unidades. El plan posterior terminó `No changes`. Ese flujo usó el release local del ERP, no el
runtime AWS. El WMS sigue siendo un ledger demo y no hay red privada AWS–Azure.
Los recursos temporales de restore RDS anotados en la evidencia histórica
conservan limpieza sin verificar; no borrar el snapshot fuente. Ver
[revalidación actual](current/REVALIDACION_ESTADO_2026-10-13.md), [STS AWS](current/aws/AWS-REVALIDACION-STS-2026-10-13.md)
y [despliegue Azure](current/azure/AZURE-PLAN-PAQUETE-2026-10-13.md).
El corte local de las 05:28 amplió a ocho escenarios mock el preflight de la
VPN AWS–Azure (incluye asociación de las IP públicas al gateway). La puerta
completa aprobó 83 pruebas, CloudFormation, frontend y Terraform; dos
tests mock aprobaron el gate de costo. El smoke Azure agotó el timeout en una
consulta ARM antes de cualquier publicación. No se desplegó la VPN.
El resumen histórico que sigue conserva cortes previos; para el estado vigente,
usar siempre [la revalidación](current/REVALIDACION_ESTADO_2026-10-13.md) y
[STS AWS](current/aws/AWS-REVALIDACION-STS-2026-10-13.md).
La preparación local de la migración a Flex y sus límites está en
[AZURE-FLEX-IAC-VALIDACION](current/azure/AZURE-FLEX-IAC-VALIDACION-2026-10-13.md).
La actualización local de 03:39 añadió auditoría atómica a las mutaciones de
cuentas, pasó la compuerta completa con 81 pruebas y volvió a desplegarse en
Docker preservando el volumen. El stack local y sus comprobaciones están en
[LOCAL-STACK-2026-10-13.md](current/LOCAL-STACK-2026-10-13.md). El E2E de las
02:32 está conservado como evidencia de ese corte en
[AWS–Azure](current/azure/AZURE-AWS-INTEROP-2026-10-13.md), no como salud actual.
La prueba DR está en
[AWS-DR-RESTORE-2026-10-13.md](current/aws/AWS-DR-RESTORE-2026-10-13.md). El
corte previo de Azure es
[AZURE-RECONSTRUCCION-2026-10-12.md](current/azure/AZURE-RECONSTRUCCION-2026-10-12.md):
documenta una reconstrucción viva y la prueba autenticada/idempotente del WMS
ficticio. El 12/10 se añadió la cola poison con conteo autenticado, y la Function
se publicó desde Blob privado con identidad administrada; el endpoint probó
401 sin clave y 200 autenticado con conteo cero. Terraform confirmó después
`No changes`. La revalidación del perfil `default` comparó en memoria la terna
guardada con la suministrada y STS la aceptó a las 21:03 (hora local). Una
lectura histórica de inventario a las 21:09 encontró cero EC2, ELB/target groups
y RDS en línea, pero sí un snapshot manual PostgreSQL cifrado. AWS Academy
mostró el lab terminado en ese corte y una operación RDS fue denegada. Esos
datos no demuestran el estado actual; no se obtuvo un token nuevo ni se desplegó
nada. Véase [el inventario y revalidación](current/aws/AWS-INVENTARIO-2026-10-12.md)
y [el registro STS](current/aws/AWS-REVALIDACION-STS-2026-10-12.md).
Azure CLI autenticó y el 12/10 volvió a confirmar la Function `Running` en plan
`Y1`; `/api/health` respondió HTTP 200. El smoke ERP local → Queue/Function →
reconciliación pasó con compensación que restauró el stock ficticio, repetido
al corte 23:57. El corte
anterior de Application Insights mostró 15 solicitudes/0 fallos; la revalidación
posterior encontró 114 solicitudes y 5 fallos, incluidos 5 de 15 invocaciones
del worker. Una clasificación local sin mostrar textos encontró 10
`RpcException` con señal de checksum/mismatch, consistente con el mensaje
poison sintético previo; falta correlación por operación. La cola poison volvió
a responder 200 con conteo 0. Una falla sintética con checksum
inválido sí recorrió los reintentos y llegó a poison; se verificó y eliminó el
mensaje de prueba, dejando el conteo final en 0. No hay VNet ni VPN
desplegada en la suscripción activa. No se intentó crear un gateway de costo
recurrente; falta cerrar diseño, presupuesto y aprobación antes de desplegarlo.
El
[cierre del 09/10](current/APAGADO_NUBE_2026-10-09.md) documenta el ciclo de
apagado anterior y el único snapshot AWS conservado. El
[corte previo de despliegue](current/CIERRE_NUBE_2026-10-09.md), el mapa del
08/10, bitácoras Chrome y cierres anteriores son históricos; no prueban
recursos activos.

## Clasificación

`current/` significa carpeta de trabajo/evidencias del proyecto, no que cada
archivo o captura ahí sea vigente. Revisa siempre fecha, hora y nota de
precedencia de cada registro. Evidencia de despliegue anterior permanece válida
para ese corte, pero no prueba el inventario actual.

| Ubicación | Uso permitido |
|---|---|
| `current/aws/baseline-before-core/` | Línea base reciente de Tangamandapio; demuestra solo lo que su propio registro afirma y no reemplaza nuevas pruebas CUR-AWS. |
| `current/aws/`, `current/azure/` | Evidencias nuevas aptas para el informe y la sustentación. OCI quedó fuera de alcance del entregable. |
| `legacy/andemarket-historical/` | Antecedentes de otro nombre/alcance. Se pueden rescatar como procedimiento, pero no se presentan como evidencia vigente. |

## Mapa de evidencias de todo el proyecto

| Tema | Fuente principal | Cómo interpretarla |
|---|---|---|
| Alcance, empresa ficticia y decisiones de arquitectura | [`core/00_registro_maestro.md`](../core/00_registro_maestro.md), [`core/04_matriz_rubrica.md`](../core/04_matriz_rubrica.md), [`core/09_propuesta_cloud_aws_azure.md`](../core/09_propuesta_cloud_aws_azure.md) | Requisitos y propuesta; no equivalen a despliegue. |
| Diagrama multicloud | [`arquitectura_aws_examen.drawio`](../arquitectura_aws_examen.drawio), [`arquitectura_aws_examen.svg`](../arquitectura_aws_examen.svg) | Diseño objetivo; no constituye inventario de recursos. |
| AWS — publicación y pruebas de octubre 1–2 | [`CUR-AWS-03`](current/aws/CUR-AWS-03_despliegue_y_prueba_2026-10-01.md), [`CUR-AWS-10`](current/aws/CUR-AWS-10_portal_b2b_v1_despliegue_2026-10-02.md), [artefacto release](../app/aws_release/README.md) | Registros técnicos históricos y paquete; revisar la fecha/ciclo antes de sostener estado actual. Los PNG `CUR-AWS-06/08` son tarjetas resumen, no screenshots de AWS. |
| Azure — WMS e interoperabilidad | [E2E ERP→Azure 14/10](current/azure/AZURE-ERP-E2E-2026-10-14.md), [E2E AWS–Azure histórico desde EC2](current/azure/AZURE-AWS-INTEROP-2026-10-13.md), [release Azure](current/azure/AZURE-PLAN-PAQUETE-2026-10-13.md), [último corte](current/CLOUD-REVALIDATION-2026-10-14.md) | A las 03:25 ARM confirmó Function `Running`, HTTPS-only y `/api/health` 200; Application Insights, Log Analytics y alertas existen. El E2E procesó eventos demo por Queue/Function con ledger ficticio. Health no prueba invocación actual ni hay WMS comercial o VPN privada. |
| AWS — inventario y recuperación | [revalidación EC2/ALB](current/aws/AWS-REVALIDACION-EC2-BOOT-2026-10-14.md), [corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md), [release v5](current/aws/AWS-DESPLIEGUE-2026-10-14.md), [restore DR](current/aws/AWS-DR-RESTORE-2026-10-13.md) | A las 03:25 STS autenticó y ALB dio 200; 10 GET alcanzaron dos backends, aunque AWS deniega leer ASG/targets. RDS última lectura: privada/cifrada, Single-AZ y backup de un día. El restore aislado validó 14 tablas, RTO 289 s y RPO superior observado 14 s; no es una recuperación de incidente productivo. |
| Red privada y recuperación | [IaC BGP](../iac/environments/aws-azure-vpn/README.md), [plan de pruebas](../tests/00_plan_maestro_pruebas.md), [corte actual](current/CLOUD-REVALIDATION-2026-10-14.md), [intento VPN](current/azure/AZURE-AWS-INTEROP-2026-10-13.md), [restore DR](current/aws/AWS-DR-RESTORE-2026-10-13.md) | No hay VPN/rutas privadas desplegadas; IaC y gates mock no prueban conectividad. Restore aislado pasó; una recuperación productiva ante incidente sigue pendiente. |
| Portal, roles y brechas | [Pruebas backend](../app/tests/test_app.py), [pruebas release](../app/aws_release/current/tests), [corte cloud](current/CLOUD-REVALIDATION-2026-10-14.md), [hardening de diagnósticos](current/SECURITY-PUBLIC-DIAGNOSTICS-2026-10-14.md), [manual](../core/08_manual_evolucion_portal_y_telefonia_ip.md) | El release v5 sigue vivo; admin anónimo devuelve 401 y el ALB responde. Falta autenticar todos los roles en navegador. El v6 local corrige hostname y métricas públicas, no desplegado. A/V entre navegadores, grabaciones reales, dominio y HTTPS del ALB siguen pendientes. |
| Voz/WebRTC y grabaciones | [Pruebas AWS release](../app/aws_release/tests), [migraciones de voz](../app/aws_release/current/migrations) | Pruebas de backend/local y S3 simulado; no prueba llamada real entre dos navegadores ni graba conversaciones reales. |
| Pruebas locales | [`tests/README.md`](../tests/README.md), [`QA-LOCAL-2026-10-14.md`](current/QA-LOCAL-2026-10-14.md), [hardening v6](current/SECURITY-PUBLIC-DIAGNOSTICS-2026-10-14.md) | El gate más reciente aprobó 130 pruebas Python y 8 Node, auditorías, build, CloudFormation y Terraform. Son pruebas locales; no cubren el despliegue v6, roles autenticados en navegador ni A/V entre navegadores. El restore RDS validó una instancia aislada, no recuperación de incidente productivo. |
| Observación visual Chrome y validación live del 08/10 | [`REVISION_CHROME_2026-10-08.md`](current/REVISION_CHROME_2026-10-08.md), [`CAPTURAS_PENDIENTES.md`](current/CAPTURAS_PENDIENTES.md) | AWS CloudFormation mostró el stack actual (51 recursos) y el ALB tuvo 2 destinos Healthy; Azure aceptó, procesó y permitió consultar un evento sintético. El registro escrito existe; los nuevos PNG crudos de Chrome siguen pendientes de archivo. |

## Convención nueva

`CUR-{NUBE}-{NN}`: por ejemplo, `CUR-AWS-04_alb-health.png` o `CUR-AZ-03_function-evento.png`.

Cada evidencia debe registrar: fecha, región, recurso, configuración, prueba, resultado y estado de limpieza. Nunca incluir credenciales, claves, identificadores de cuenta ni datos personales. Identificar siempre si una imagen es una captura directa, una tarjeta/resumen creado a partir de CLI o un diagrama de diseño.

La secuencia concreta de capturas por tomar se mantiene en [CAPTURAS_PENDIENTES.md](current/CAPTURAS_PENDIENTES.md). Las imágenes de octubre 1–2 corresponden a ciclos anteriores; los registros del ciclo posterior y sus límites están en [el estado del portal](../app/WEB_STATUS_AND_GAPS_2026-10-08.md) y la [revisión visual de Chrome](current/REVISION_CHROME_2026-10-08.md). No inferir disponibilidad actual de imágenes históricas.

## Índice de Azure — 01/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AZ-01 | Terraform aplicó el vertical WMS temporal en West US | Infraestructura creada; 12 recursos |
| CUR-AZ-02 | Diagnóstico y corrección de empaquetado Linux | Antecedente; no prueba el flujo WMS completo |
| CUR-AZ-03 | Plan de cierre e inventario final del ciclo inicial | Ejecutado; evidencia histórica en CUR-AZ-08 |
| CUR-AZ-05 | Inventario Azure CLI | Function `Running`, recursos PaaS y dos rutas registradas |
| CUR-AZ-06 | Health WMS autenticado | HTTP 200 y CORS limitado al portal |
| CUR-AZ-07 | WMS extremo a extremo | Health 200; evento 202; Blob privado de 430 bytes, Queue y entrega del outbox local verificados |
| CUR-AZ-08 | Cierre Azure inicial | Grupos del primer ciclo eliminados; consulta por prefijo sin resultados en ese momento |
| CUR-AZ-09 | Validación actual del WMS r2 | Function actual, Health 200, Fulfillment 202 y reintento idempotente 200 registrados sin claves |
| AZ-PORTAL-01 | Captura real del inventario en el portal del ciclo previo | PNG disponible; antecedente, no inventario activo |
| AZ-PORTAL-02 a 04 | Vistas descritas en `LIVE_PORTAL_2026-10-01.md` | No hay PNG de esas tres vistas en el repositorio; tratar los resultados escritos como registro, no captura adjunta |

Los registros visuales de Azure se guardan como PNG dentro de `current/azure/screenshots/`. Están rotulados como consultas autenticadas de CLI, por lo que no se confunden con capturas del portal. El grupo `rg-tangamandapio-261001r2-wus` fue eliminado al cierre; las imágenes prueban el ciclo temporal y no un inventario vigente.

## Índice de AWS — 02/10/2026

| ID | Registro | Estado |
|---|---|---|
| CUR-AWS-03 | Validación CloudFormation, despliegue temporal y prueba funcional | Health 200, pedido 201, recuperación 200, dos targets healthy |
| CUR-AWS-06 | Infraestructura AWS CLI | ALB, ASG, RDS, S3 y observabilidad verificados antes de la revocación de sesión |
| CUR-AWS-08 | Prueba funcional AWS CLI | Resultados HTTP reales contra el ALB temporal |
| CUR-AWS-10 | Publicación B2B versionada | Validación IaC, diagnóstico del rollback inicial, corrección y `UPDATE_COMPLETE` de la actualización gradual |

Tras reiniciar el laboratorio el 02/10, el stack `tangamandapio-live-20261001` de ese ciclo quedó cerrado. En el corte visual posterior del 08/10, CloudFormation mostró `tangamandapio-live-20261005`, 51 recursos y dos destinos `Healthy`; el inventario vivo más reciente está en `current/MAPA_ESTADO_ACTUAL_2026-10-08.md`. La pila separada `tangamandapio-voice-recordings` figuró `CREATE_COMPLETE` en la revisión Chrome, pero no se revalidó en el corte más reciente. Las tarjetas PNG del 01/10 no prueban el ciclo actual y siguen pendientes capturas crudas nuevas de Chrome/consola.

### Aclaración de formato

`CUR-AWS-06_stack_operativo_2026-10-01.png` y
`CUR-AWS-08_prueba_funcional_2026-10-01.png` son **tarjetas visuales resumidas**
basadas en consultas AWS CLI registradas en sus documentos acompañantes. No son
capturas crudas de Chrome, CloudShell ni la consola. La revisión visual en Chrome
del 08/10 está descrita en `current/REVISION_CHROME_2026-10-08.md`; los PNG no
pudieron archivarse desde la sesión actual, así que el nuevo set sigue pendiente.

### Aclaración de formato Azure

`AZ-PORTAL-01_inventario_2026-10-01.png` sí es una captura directa del portal
Azure del ciclo histórico descrito en `current/azure/LIVE_PORTAL_2026-10-01.md`.
Los PNG `CUR-AZ-05` a `CUR-AZ-08` son **tarjetas visuales** creadas a partir de
resultados Azure CLI; no son capturas del terminal ni del portal. La vista
Azure observada el 08/10 y el evento sintético E2E también están en
`current/REVISION_CHROME_2026-10-08.md`: POST `202`, Queue worker `Succeeded`
(93 ms), estado GET `200 simulated_completed`. El monitor registró 9 éxitos y 5
errores en 30 días; se inspeccionó un error antiguo de checksum Blob/Queue y se
dejó intacto. La observación está documentada, pero no hay un PNG nuevo de
Chrome archivado.
