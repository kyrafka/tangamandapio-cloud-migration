# Revalidación cloud — 13/10/2026

## Revalidación viva — 13/10/2026, 23:50 America/Chicago

AWS STS aceptó el perfil local `default`. CloudFormation devolvió
`UPDATE_COMPLETE`; el target group registró 2/2 destinos `healthy`, RDS
`available`, cifrada, `MultiAZ=false` y retención de backup de 1 día. El ALB
respondió `/health` HTTP 200 con base `ok` y `/ready` HTTP 200. Sin sesión,
`/administracion` respondió 303 y `/api/admin/users` y
`/api/admin/alarm-subscriptions` respondieron 401 en el corte previo. Solo se
hicieron lecturas; no se modificaron recursos. El portal local respondió
`/health` y `/ready` HTTP 200.

Azure CLI sí está instalado, aunque fuera del `PATH` de PowerShell. La lectura
ARM confirmó que `rg-tangamandapio-rebuild-wus` está `Succeeded` y que la
Function `tangama-wms-261008` está `Running`, `httpsOnly=true`, con host
`tangama-wms-261008.azurewebsites.net`. El endpoint `/api/health` respondió
HTTP 200 (`status=ok`, `service=tangamandapio-wms`). Una repetición inmediata de
la consulta específica volvió a demorarse y se canceló; no se releyó el hash del
paquete ni se ejecutó un nuevo E2E en este corte. No hubo cambios de recursos.

## Lectura inicial — 13/10/2026, 23:41–23:43 America/Chicago (corregida)

La lectura AWS de ese momento confirmó stack, destinos, RDS y health. La primera
comprobación de Azure confundió “no encontrado en `PATH`” con “CLI no instalada”
y dejó ARM sin consultar. La CLI se localizó después en
`C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`; la lectura
ARM exitosa de las 23:50 está arriba. No se cambiaron recursos.

## Corte vivo AWS + Azure — 13/10/2026, 23:00 America/Chicago

AWS STS autenticó en la sesión del laboratorio. CloudFormation mantiene
`tangamandapio-live-20261013` en `UPDATE_COMPLETE` y con el artefacto
`20261013-admin-alarm-rbac-metrics-v4-python312` (SHA-256
`00b1ea3faf123d603d368ddc8c6f777b53fc9e9964352abfb4039b7c1b026e23`). El
target group presentó 2/2 destinos sanos. Pruebas HTTP: `/health` 200,
`/ready` 200, `/administracion` 303 sin sesión, `/api/admin/users` 401 y
`/api/admin/alarm-subscriptions` 401. RDS está `available`, cifrada,
Single-AZ, con backup de un día. Son lecturas de estado; no se cambió AWS.

En la suscripción activa de Azure, el grupo correcto es
`rg-tangamandapio-rebuild-wus` (West US). ARM/CLI confirma la Function
`tangama-wms-261008` `Running`, HTTPS-only y con el SHA de paquete esperado
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065`;
`/api/health` devolvió `{"status":"ok","service":"tangamandapio-wms"}`.
Un `terraform plan -detailed-exitcode` posterior, contra el state vigente y el
ZIP con este mismo hash, devolvió `No changes` (exit 0), sin apply.
El smoke vivo compensado ERP-local→Azure Queue/Function pasó: venta demo
`evt-575d325f09fa49f38a65b35e5a492c5f`, reposición
`evt-10d9608ebc5b4a81b0f2aa98619e4723`, con saldo restituido exactamente a la
línea base. La SQLite temporal terminó y fue eliminada; los eventos sintéticos
quedan en auditoría Azure. No prueba que EC2 originara la solicitud ni establece
red privada AWS–Azure; el ledger continúa siendo ficticio.

**Brechas que siguen abiertas:** falta probar roles autenticados en la
instancia live y una notificación SNS disparada de punta a punta. El servicio
de aplicación sí completó un E2E AWS EC2→Azure por HTTPS público en el corte de
02:32; lo pendiente de red es VNet/túnel y ruta IP privada entre redes (AWS
Academy denegó la creación del Customer Gateway). También faltan una estimación
reproducible de costos y capturas/consolidación final del informe. El ALB sigue
sin dominio/TLS confiable y WebRTC real entre dos navegadores continúa
aplazado. PT-DR-01 sí restauró marcador SQL y 14 tablas, con RTO 289 s, RPO
superior 14 s y limpieza confirmada. El ledger Azure sigue siendo ficticio,
no un WMS comercial. La cifra 11.75/20 queda retirada: el XLSX fuente confirma
que los pesos suman 18.5, aunque imprime 20 como total, y no especifica puntos
por descriptor.

## Último corte AWS v4 — 13/10/2026, 22:47 America/Chicago

AWS: el token temporal nuevo se aplicó al perfil local `default` y STS autenticó.
El release `20261013-admin-alarm-rbac-metrics-v4-python312` quedó publicado en
S3 privado con SHA-256
`00b1ea3faf123d603d368ddc8c6f777b53fc9e9964352abfb4039b7c1b026e23`. El stack
terminó `UPDATE_COMPLETE`; la detección posterior reportó `IN_SYNC`, cero
drift. Las dos instancias confirmaron por SSM la misma revisión y checksum,
servicio activo y archivos ERP/admin. El ALB conservó 2/2 targets healthy;
`/health` y `/ready` dieron HTTP 200. `/administracion` redirige al login sin
sesión y las APIs admin contestan 401 anónimo. RDS sigue disponible, Single-AZ,
backup de un día; no se cambió durante el release.

Azure: el endpoint HTTPS `/api/health` respondió HTTP 200 (`status=ok`) a las
22:46. La consulta de estado por Azure CLI se atascó antes de devolver estado
ARM y se cerró; por ello no se afirma un inventario Azure nuevo en este corte.
El último estado ARM/paquete confirmado permanece en la sección anterior.

La puerta local volvió a pasar con 120 pruebas, auditorías de dependencias,
build frontend y validación/lint de IaC. El despliegue no configuró VPN,
dominio ni HTTPS en el ALB. Aún faltan pruebas de roles autenticados en la
instancia live, llamada WebRTC real y un WMS/inventario físico. Véase el
[despliegue AWS](aws/AWS-DESPLIEGUE-2026-10-13.md) y el
[inventario AWS](aws/AWS-INVENTARIO-2026-10-13.md).

## Corte operativo — 22:15 America/Chicago

Azure: se construyó y publicó el paquete Function SHA-256
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065`. El plan
limitó el cambio al Blob content-addressed y settings de la Function
(`1 add / 1 update / 1 destroy` del Blob anterior); no reemplazó recursos base.
Post-apply: Function `Running`, HTTPS-only, `DEPLOYMENT_PACKAGE_SHA256`
coincide, health HTTP 200 y Terraform `No changes`. El E2E procesó la venta
`evt-058124ac95d442238e45fc83cc197a77` y la recepción compensatoria
`evt-0ac5e6b060cd4dea98644b6b05eb8ee9`; el test verificó restauración exacta
del saldo demo de línea base. ARM confirma soft delete de Blob habilitado por 7
días; no fue posible listar blobs eliminados con la identidad CLI, y la copia
del paquete anterior (`0e1f153f…`) permanece local. El WMS sigue siendo un
ledger ficticio y el E2E partió del ERP local, no de EC2.

AWS: `aws sts get-caller-identity` responde `ExpiredToken` en `default`. No se
realizaron cambios AWS ni se publicó el release local.

La compuerta local integral posterior pasó con 120 pruebas, auditoría de locks,
build web, CloudFormation lint y validaciones Terraform; `/health` y `/ready`
locales respondieron 200. La QA completa está en
[QA-LOCAL](QA-LOCAL-2026-10-13.md).

Lectura final a las 22:15: AWS STS continúa en `ExpiredToken`; Azure
`/api/health` y los endpoints locales `/health` y `/ready` respondieron HTTP
200. Terraform Azure mantuvo 0 acciones no-op en el plan final.

## Candidato AWS v4 — 21:32 America/Chicago

Se corrigió el runtime del release: el AL2023 system Python permanece en 3.9,
pero EC2 instala Python 3.12 en un virtualenv dedicado. El lock pasó auditoría
sin vulnerabilidades, dry-run Linux con hashes, y el empaquetado persistido se
comparó byte por byte contra la fuente. QA integral aprobada con 120 pruebas y
validación IaC, sin `apply` ni operaciones cloud. El release v4 continúa local;
no se publicó. La consulta AWS a las 21:32 respondió `ExpiredToken`; no se
proporcionó una sesión nueva.

## Corte AWS — 21:10 America/Chicago

La consulta actual `aws sts get-caller-identity` falló con `ExpiredToken` en
el perfil `default`. No se modificó AWS, no se creó change set y no se subió
ningún artefacto. Para avanzar hace falta renovar la sesión del laboratorio;
después se deberá volver a comprobar identidad y permisos de inventario porque
un token nuevo no resuelve el explicit deny `voc-cancel-cred` observado antes.

La reconstrucción local usa instalación Python fijada por versión y SHA-256
(`pip --require-hashes`). QA integral aprobada (120 pruebas, auditorías, build
y validación IaC sin `apply`). El artefacto v4 está guardado localmente, no
publicado; su hash y revisión están en la [QA local](QA-LOCAL-2026-10-13.md).

## Estado AWS y endurecimiento de release — 20:52 America/Chicago

`aws sts get-caller-identity` sigue respondiendo `ExpiredToken`; sin sesión
válida no se creó change set, no se subió el artefacto ni se cambió AWS. La
plantilla local ahora verifica SHA-256 antes de extraer el paquete y crea claves
de release que contienen el hash completo, para que un rollback pueda recuperar
su objeto original. La suite local completa aprobó 120 pruebas, dependencias,
build, CloudFormation lint y Terraform fmt/validate/mocks. Esto no demuestra
que el cambio esté aplicado en AWS. Véase la [QA local](QA-LOCAL-2026-10-13.md).

## Comprobación AWS y QA local — 20:41 America/Chicago

AWS CLI `default` respondió `ExpiredToken` en `sts:GetCallerIdentity`; no se
realizaron llamadas de modificación ni despliegues. Hace falta renovar las
credenciales temporales del laboratorio. Esto no elimina el explicit deny de
`voc-cancel-cred` observado anteriormente: incluso con token válido, ese
permiso debe verificarse antes de intentar inventario o publicación.

En paralelo, la QA local completa terminó aprobada con 120 pruebas unitarias,
auditorías de dependencias, build web, CloudFormation lint y Terraform
fmt/validate/tests mock. Se añadió verificación SHA-256 del paquete de portal
antes de extraerlo en EC2; el test validó contenido del paquete y exclusión de
rutas con nombres de secretos. No equivale a un release probado en AWS. Detalle:
[QA local](QA-LOCAL-2026-10-13.md).

## Corte actualizado — 20:10 America/Chicago

La Function Azure sigue respondiendo `/api/health` con HTTP 200. El E2E
posterior al release recorrió ERP local → outbox → Queue/Function → conciliación
ERP; la venta `evt-cfc7353b1e8e4708a7449e7bd160b3aa` terminó
`demo_fulfillment_completed` y la reposición
`evt-265c43727d0e4b51ba51e49527e3ccfd` terminó `demo_restock_completed`, con
saldo demo final igual a su línea base. La lectura autorizada de poison informó
0 mensajes y no expuso payloads. Es tráfico sintético originado en local, no en
EC2 ni un WMS comercial. Véase la [evidencia del release y el E2E](azure/AZURE-RELEASE-EVENT-TYPE-GUARD-2026-10-13.md).

AWS `default` ahora devuelve `ExpiredToken`; para volver a llamar la API se
necesita una sesión nueva del lab. La última llamada autenticada, a las 19:00,
sí llegó a AWS y recibió un explicit deny de `voc-cancel-cred` en
`cloudformation:DescribeStacks`. Son dos problemas distintos: renovar el token
restablece autenticación, pero la política del laboratorio todavía puede
impedir inventariar o desplegar. No se modificó AWS.

El portal local está `healthy`; `/ready` dio HTTP 200 y conserva el volumen
`app_aws-data`. La lectura ARM que terminó a las 20:14 confirmó Azure
`Running`, `httpsOnly=true` y el hostname esperado; el health HTTPS también dio
200 en esta revalidación.

## Release de Function y revalidación — 19:20 America/Chicago

Se publicó en Azure una corrección probada del consumidor de eventos: valida de
nuevo el tipo y consistencia entre sobre/payload antes de mutar el ledger. El
paquete `azure_function_package-20261013-event-guard-v1.zip` quedó desplegado,
su SHA-256 coincide con `DEPLOYMENT_PACKAGE_SHA256`, Function `Running`,
HTTPS-only, health 200. El endpoint real rechazó un evento sintético con tipo no
permitido (HTTP 400); ese camino retorna antes de almacenar o encolar. El plan
posterior a la aplicación fue `No changes`; solo se cambió el paquete de código
y su referencia. La Function sigue usando existencias ficticias de laboratorio.
Detalle: [release Azure](azure/AZURE-RELEASE-EVENT-TYPE-GUARD-2026-10-13.md).

En el mismo corte, AWS STS aceptó `default` para la cuenta Academy, pero
`cloudformation:DescribeStacks` del nombre conocido volvió a ser denegado por
el explicit deny `voc-cancel-cred`. No se modificó AWS ni se subió el candidato
AWS. En local, la suite completa pasó 120 pruebas y el contenedor conserva su
volumen nombrado y permanece saludable; el detalle está en la [QA local](QA-LOCAL-2026-10-13.md).

## Corte de solo lectura — 19:00 America/Chicago

AWS STS aceptó el perfil local `default` y devolvió la cuenta Academy
`841113066612` con rol `voclabs`; por tanto, **el token actual sí es válido**.
La lectura del stack exacto `tangamandapio-live-20261013` volvió a fallar con
`AccessDenied` por el explicit deny de la política `voc-cancel-cred` sobre
`cloudformation:DescribeStacks`. No hace falta renovar el token para resolver
este error y no se intentó desplegar ni cambiar recursos. El estado detallado
de EC2, RDS y change sets sigue sin poder verificarse.

Azure se revalidó a las 19:02: la Function `tangama-wms-261008` está `Running`,
con `httpsOnly=true`, y `/api/health` respondió HTTP 200 (`status: ok`). Esto
confirma disponibilidad del endpoint, no procesamiento de un evento nuevo.

El portal local se reconstruyó conservando el volumen `app_aws-data`; el
contenedor está `healthy`. `/`, `/health`, `/ready` y el bundle Vite actual
respondieron HTTP 200; `/api/erp/overview` sin sesión respondió 401. Esto
verifica que la corrección local de permisos quedó servida, no que esté en AWS.
El artefacto local v2 conserva SHA-256
`706ad7199e7b0a1a249bf434e89003d4030093b4ad7423afb1665084b10039d7` y sigue sin
publicarse.

## Revalidación de solo lectura — 18:42 America/Chicago

AWS STS volvió a aceptar el perfil `default` para la cuenta Academy
`841113066612`, así que el token no está vencido. La API denegó
`cloudformation:ListStacks` mediante un explicit deny de `voc-cancel-cred`.
También se denegó `DescribeStacks` al consultar el nombre exacto conocido; no
se pudo obtener inventario y el preflight de despliegue no puede continuar. El
ALB respondió 200
en `/health` y `/ready`, pero 404 en `/administracion` y
`/api/admin/alarm-subscriptions`. El estado de EC2, RDS y Change Sets no se
infiere sin lectura de CloudFormation.

Azure CLI confirmó `tangama-wms-261008` en `Running`, HTTPS-only, y su endpoint
`/api/health` respondió 200 (`ok`). A las 18:43 el smoke compensado
`tests/run_live_azure_erp_smoke.py` completó ERP del release AWS ejecutado en
un proceso local → outbox → Azure Queue/Function → conciliación ERP. El evento
de venta `evt-11931b9e2c544f879e68cac3b14b7779` reportó
`demo_fulfillment_completed`; la recepción compensatoria
`evt-924b144dfe3f4a9d997110654625013a` reportó `demo_restock_completed` y
restauró el ledger ficticio a su línea base. La SQLite de prueba fue temporal;
los registros sintéticos permanecen en auditoría Azure. Esto no fue tráfico
desde EC2, no integra inventario real y no cambió infraestructura. Detalle:
[E2E Azure](azure/AZURE-ERP-E2E-2026-10-13.md) y
[autenticación AWS](aws/AWS-REVALIDACION-STS-2026-10-13.md).

## Endurecimiento local del despliegue — 18:33 America/Chicago

Los entrypoints CloudFormation y las pruebas PT-STO-01/PT-MON-01 ahora exigen
un nombre de stack verificado con el formato del proyecto; ya no usan defaults
históricos. Los tests con AWS simulado confirman el bloqueo antes de toda
llamada al CLI y que PT-MON-01 restaura el estado original incluso si falla
después de mutarlo. La suite completa volvió a aprobar (116 pruebas y
validaciones IaC); no se ejecutó `apply`, ni se subió el artefacto.

La denegación explícita de lectura en AWS sigue vigente, por lo que esta mejora
no corrige aún el backend live ni autoriza un despliegue.

## Corte de solo lectura — 18:18 America/Chicago

AWS STS aceptó el perfil local `default` en la cuenta Academy `841113066612`,
pero `cloudformation:DescribeStacks` falló por un **explicit deny** de la
política `voc-cancel-cred`. No se intentó cambiar permisos ni publicar. El ALB
`tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` respondió HTTP 200 en
`/`, `/health` (`database=ok`) y `/ready`.

El release live no coincide con el candidato local en las rutas de
administración: `/administracion` y `/api/admin/alarm-subscriptions` devolvieron
404 en 12 de 12 lecturas cada una; el candidato declara ambas rutas y las
pruebas locales pasan. Hay que revisar la revisión de backend servida por el
ASG y el change set antes de cualquier despliegue. No se infiere aquí el estado
del stack, destinos, RDS ni change sets porque la API de inventario está
denegada.

Azure CLI mostró `tangama-wms-261008` en `Running` y
`/api/health` respondió `ok`. Esto no repite el E2E ERP→Azure, cuyos resultados
están en la evidencia más abajo.

## Azure — lectura y flujo end-to-end

La cuenta Azure CLI autenticó en `Azure for Students` (`Enabled`). En
`rg-tangamandapio-rebuild-wus`, la Function `tangama-wms-261008` figura
`Running`, solo HTTPS, y `https://tangama-wms-261008.azurewebsites.net/api/health`
respondió HTTP 200.

El smoke del release candidate local pasó el recorrido real ERP→outbox local→
Azure Queue/Function→reconciliación ERP. El evento de venta terminó
`demo_fulfillment_completed`; el evento de recepción compensatoria terminó
`demo_restock_completed` y restauró el SKU `SKU-ARROZ-001` al saldo inicial.
La verificación independiente del ciclo anterior leyó 24 unidades al final,
igual al valor inicial. El segundo ciclo completo también comprobó internamente
que el saldo final coincidiera exactamente con el baseline.

IDs del segundo ciclo, para correlación en el almacenamiento de auditoría:

- Venta: `evt-8c5f461aed65478ab2a85854174f36dc`
- Reposición: `evt-4ac004714daa40e0872b3307b010fa0b`

El smoke crea pedidos temporales solo en una base SQLite local; deja los dos
eventos sintéticos en la auditoría de Azure. En el primer intento un error
transitorio al consultar el evento produjo un falso fallo del harness, aunque la
reposición sí se procesó. Se verificaron ambos estados y saldo 24, se añadió
reintento acotado de lecturas (sin reenviar mutaciones), pasaron sus seis pruebas
unitarias y la repetición terminó `LIVE_E2E=PASSED`.

Esto prueba el ledger **ficticio** de demostración y no mueve inventario físico
ni sustituye la integración con un WMS comercial.

## AWS — acceso limitado

AWS STS autenticó con el rol `voclabs` en la cuenta Academy esperada. Las
consultas de solo lectura a CloudFormation, EC2, ELB y RDS fueron denegadas
(`AccessDenied`/`UnauthorizedOperation`). Por eso no se pudo confirmar el estado
actual del stack, el inventario ni la existencia de un change set anterior.

No se ejecutó un despliegue en esta revalidación. Se canceló el proceso local
antiguo antes de su confirmación `APPLY`; queda por comprobar, cuando la política
lo permita, si dejó un change set preparado. No ejecutar ese change set antiguo:
el candidato actual es
`artifacts/portal-b2b-20261013-admin-alarm-console-v1.tar.gz` y su SHA-256 está
registrado en [QA local](QA-LOCAL-2026-10-13.md).
