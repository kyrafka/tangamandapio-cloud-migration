# Revalidación del estado actual — 13/10/2026

## Revalidación más reciente — 23:00 America/Chicago

- AWS volvió a autenticar por STS; el stack está `UPDATE_COMPLETE`, target
  group 2/2 sano, `/health` y `/ready` 200. RDS permanece cifrada y disponible,
  pero Single-AZ con un día de backup. Son pruebas de disponibilidad, no de
  roles autenticados.
- Azure `tangama-wms-261008` está `Running`, HTTPS-only, con hash de paquete
  coincidente; `/api/health` dio 200. Terraform plan contra el state/paquete
  actuales terminó `No changes`.
- La prueba sintética de venta y reposición compensatoria volvió a dejar el
  ledger demo en su saldo base. Se originó en un proceso local, no demuestra
  tráfico desde EC2 ni conectividad privada; el inventario continúa ficticio.
- Para el informe final, la cifra 11.75/20 queda retirada: el XLSX fuente ya se
  revisó y sus pesos suman 18.5, aunque su celda final declara 20. Tampoco fija
  puntos por descriptor. No publicar un total hasta aclarar el denominador y la
  regla de evaluación.

## Corte operativo más reciente — 22:15 America/Chicago

- Azure `tangama-wms-261008`: despliegue de paquete inmutable SHA-256
  `6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065`.
  Cambiaron solamente el Blob del paquete (crear nuevo y retirar el anterior)
  y settings de la Function. La app no se reemplazó.
- Post-apply ARM: `Running`, HTTPS-only y el SHA de configuración coincide;
  `/api/health` devolvió HTTP 200. Terraform normal posterior terminó
  `No changes`.
- E2E compensado posterior: venta `evt-058124ac95d442238e45fc83cc197a77`
  llegó a `demo_fulfillment_completed`; compra compensatoria
  `evt-0ac5e6b060cd4dea98644b6b05eb8ee9` llegó a `demo_restock_completed`.
  El test verificó saldo final idéntico a la línea base. Los eventos sintéticos
  permanecen en auditoría Azure; la SQLite temporal fue eliminada.
- ARM confirmó retención de Blob eliminado habilitada durante 7 días. El
  listado data-plane de blobs eliminados no se pudo consultar con la identidad
  actual; el ZIP anterior se conserva localmente. Esto no equivale a una prueba
  de restauración remota.
- AWS `default` devolvió `ExpiredToken` al comprobar STS. No se modificó ni
  publicó nada en AWS. Se requiere sesión nueva del lab para intentar avanzar.
- La compuerta integral local volvió a aprobar 120 pruebas, tres locks Python
  auditados, build frontend, `cfn-lint` y validaciones/tests mock Terraform;
  no hubo operaciones cloud durante esa compuerta. El stack local contestó
  HTTP 200 en `/health` y `/ready`.
- Lectura final a las 22:15: AWS STS sigue `ExpiredToken`; Azure `/api/health`
  contestó 200 y el plan Terraform de Azure mantuvo cero cambios.

Véase el detalle del paquete y el plan en
[release Azure](azure/AZURE-PLAN-PAQUETE-2026-10-13.md).

## Corte más reciente — 13/10/2026, 18:43 America/Chicago

- AWS STS aceptó el perfil `default` para la cuenta Academy esperada. La
  consulta `cloudformation:ListStacks` fue rechazada por explicit deny de
  `voc-cancel-cred`; una consulta por nombre exacto también recibió explicit
  deny en `DescribeStacks`. No se puede confirmar inventario de stack, EC2, ALB
  a nivel AWS API, RDS ni Change Sets. No se intentó desplegar.
- El ALB público respondió 200 en `/health` y `/ready`; las rutas
  `/administracion` y `/api/admin/alarm-subscriptions` siguen en 404. Este es un
  desfase confirmado entre el release publicado y el candidato local.
- Azure CLI confirmó la Function `tangama-wms-261008` en `Running`,
  `httpsOnly=true`; `/api/health` respondió 200 (`ok`). El E2E compensado
  procesó venta y reposición por Queue/Function desde un proceso ERP local, y
  restauró el ledger ficticio al saldo de línea base. Los eventos sintéticos
  permanecen en auditoría Azure.
- No se cambiaron recursos de infraestructura. El flujo no demuestra tráfico
  originado por EC2, red privada AWS–Azure ni stock de un WMS real.

Detalles: [corte AWS](aws/AWS-REVALIDACION-STS-2026-10-13.md),
[E2E Azure](azure/AZURE-ERP-E2E-2026-10-13.md) y
[corte combinado](CLOUD-REVALIDATION-2026-10-13.md).

## Verificación viva adicional — 15:15 America/Chicago

- AWS CLI volvió a autenticar por STS. El stack
  `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; RDS está `available`,
  PostgreSQL, privado, Single-AZ y con retención de backup de un día.
- Azure `tangama-wms-261008` está `Running`, `httpsOnly=true` y
  `publicNetworkAccess=Enabled`. `GET /api/health` respondió HTTP 200 con
  `status=ok` para `tangamandapio-wms`.
- No se creó VNet Azure, no se estableció túnel Tailscale y no se cambiaron
  recursos en ninguna nube. La salud del endpoint WMS no demuestra integración
  privada; el procesamiento se verificó en una ejecución E2E posterior descrita
  abajo.

## E2E compensado ERP → Azure — aproximadamente 15:18 America/Chicago

- El smoke vivo procesó una venta y su recepción compensatoria mediante el
  outbox del ERP ejecutado localmente, Azure Queue y la Function
  `tangama-wms-261008`: `demo_fulfillment_completed` y
  `demo_restock_completed`. Los eventos fueron
  `evt-191c0fd8557442ad9e7ef3de35e7d5f0` y
  `evt-f50f7286ced5469581b1bbc44d8e76d1`; el ledger ficticio recorrió **24 →
  23 → 24**. La Function permaneció en HTTPS-only.
- El proceso eliminó su SQLite temporal. Los eventos sintéticos de auditoría
  permanecen en Azure. No se tocaron recursos de infraestructura ni el RDS.
- Esto cierra una prueba funcional del camino público HTTPS/Queue/Function,
  pero no prueba tráfico originado por EC2, conectividad privada AWS–Azure ni un
  WMS/inventario real. El VPN queda aplazado; Azure sigue sin VNet.
- La rúbrica conserva la estimación provisional **11.75/20**: es evidencia
  nueva, no una reevaluación oficial ni motivo suficiente para asignar puntos
  automáticamente.

## Salud final de servicios — aproximadamente 15:28 America/Chicago

- Lectura AWS de solo lectura: stack `UPDATE_COMPLETE`, target group con
  **2/2 destinos `healthy`**, `/health` HTTP 200 (`ok`, base `ok`) y `/ready`
  HTTP 200 (`ready`).
- Lectura Azure de solo lectura: `/api/health` HTTP 200 (`ok`) para
  `tangamandapio-wms`.
- La detección CloudFormation terminó `IN_SYNC`, con **0 recursos drifted**
  (15:30). Esta comparación solo cubre el stack AWS; no equivale a una
  verificación Terraform en vivo para Azure.
- No se cambiaron recursos. Esta comprobación confirma que los dos servicios
  web estaban levantados al corte; no afirma VPN ni red privada. La última
  lectura de RDS sigue siendo la de 15:15 documentada arriba.

## Relectura de prerequisitos Tailscale — 14:53 America/Chicago

- AWS STS autenticó el perfil local `default` y `describe-vpcs` encontró la VPC
  disponible `10.10.0.0/16`; esta lectura no comprueba permiso de crear EC2,
  modificar rutas ni IAM.
- Azure CLI tiene una suscripción activa seleccionada; `az network vnet list`
  devolvió `[]`. No hay una VNet en la que colocar un router Azure.
- El servicio Tailscale de Windows está instalado y en ejecución, pero dos
  lecturas de `tailscale status --json` reportaron `BackendState=NoState` y el
  nodo local offline. No se enrolaron dispositivos cloud ni se modificó el
  tailnet; el cliente desconectado no permite verificar el inventario remoto.
- Se añadió un preflight local de solo lectura, documentación de la alternativa
  overlay y pruebas mock. Este trabajo no crea infraestructura ni suma evidencia
  al criterio de conectividad. La rúbrica queda en **11.75/20 provisional**;
  no se afirma un túnel AWS–Azure.
- La suite específica Tailscale pasó **4/4** pruebas mock. Después, la puerta
  local completa aprobó **98 pruebas**, auditoría de dependencias, build
  frontend, validación CloudFormation, Terraform `fmt`/`validate` y cinco
  pruebas mock Terraform; no hubo `apply` ni escrituras cloud.

## Corte más reciente — 14:46 America/Chicago

- El perfil local `default` autenticó con STS usando las credenciales vigentes
  del laboratorio; el token no se guardó en el repositorio.
- El stack del portal AWS continúa `UPDATE_COMPLETE`. `/health` y `/ready`
  respondieron HTTP 200; `/health` informó PostgreSQL `ok`. El target group
  tiene 2/2 destinos `healthy`. La alarma `tangamandapio-in-service-capacity`
  está `OK` y recibió el dato de capacidad `2`.
- La conexión privada AWS–Azure **no** quedó establecida. La SCP de la
  organización denegó `ec2:CreateCustomerGateway`; CloudFormation revirtió y se
  eliminó el stack VPN fallido. No se crearon túneles ni rutas privadas.
- Azure sí completó temporalmente el gateway activo-activo con BGP en el grupo
  aislado de prueba. Después de la denegación AWS, Terraform destruyó los 10
  recursos; Azure confirma que `rg-tangama-private-network` no existe y el
  state de ese root está vacío. La Function/WMS en su grupo separado no fue
  modificada.
- La plantilla VPN ahora supera `aws cloudformation validate-template` y el
  root Terraform supera `fmt -check` y `validate`. La matriz de rúbrica no se
  recalcula: esta prueba fallida no acredita el criterio de conectividad
  multinube; permanece como dependencia obtener autorización organizacional
  AWS antes de repetirla.

## Mejora de seguridad de despliegue — 11:43 America/Chicago

- El proceso para VPN ahora permite ejecutar un preflight AWS de solo lectura
  antes de crear el gateway facturable Azure. Comprueba STS, que el stack del
  portal esté estable, VPC/CIDR, la tabla de rutas de aplicación y que el stack
  VPN esté ausente o estable; con `AccessDenied` falla cerrado antes de invocar
  Azure. Reporta explícitamente que permisos de creación no quedan probados.
- Los nueve escenarios mock pasaron. La puerta integral terminó con **94
  pruebas unitarias**, auditoría de dependencias sin vulnerabilidades
  conocidas, build frontend, CloudFormation y validaciones Terraform. No hubo
  `apply` ni operaciones cloud.
- El preflight se ejecutó también contra la sesión real y se bloqueó al no
  poder leer el stack portal AWS. Terminó antes de cualquier consulta Azure;
  no se creó el gateway ni se incurrió en nuevo costo de VPN.
- Esta mejora reduce el riesgo de volver a pagar el gateway Azure si AWS ya
  niega consultas básicas, pero no sustituye la autorización de
  `ec2:CreateCustomerGateway`, no prueba túneles y no cambia la evaluación
  provisional de la rúbrica.

## Corte más reciente — 11:33 America/Chicago

- El perfil local `default` autentica con AWS STS en la cuenta académica
  `841113066612`. Las consultas actuales a `cloudformation:DescribeStacks`,
  `autoscaling:DescribeAutoScalingGroups` y `ssm:DescribeInstanceInformation`
  son rechazadas por una denegación explícita de `voc-cancel-cred`. No es un
  token inválido; el inventario AWS queda sin verificar en este corte.
- Última observación de salud previa: a las 10:43 el stack estaba
  `UPDATE_COMPLETE`, el ASG y el ALB estaban 2/2 sanos, y `/health` devolvió
  HTTP 200 con base de datos `ok`. La detección de drift terminada a las 10:44
  dio `IN_SYNC` (cero divergencias). Son datos históricos recientes, no una
  confirmación del estado a las 11:33.
- Azure for Students continúa `Enabled`. En el corte anterior (~11:26), la
  Function `tangama-wms-261008` estaba `Running` y `httpsOnly=true`; el E2E
  ERP local→Queue→Function de esta revisión pasó con venta y recepción
  compensatoria, restaurando el ledger demo a 24 unidades. Sus nuevos IDs y
  alcance están en [AZURE-ERP-E2E-2026-10-13.md](azure/AZURE-ERP-E2E-2026-10-13.md).
- Terraform Azure terminó `No changes`; no se aplicó infraestructura. La
  puerta local aprobó 94 pruebas, `pip-audit` no halló vulnerabilidades
  conocidas, el build web pasó y CloudFormation/Terraform validaron. Estas
  pruebas no revalidan AWS ni convierten el WMS demo en inventario real.
- La consola AWS Academy no se pudo revisar visualmente: la automatización del
  navegador se detuvo porque no pudo identificar la URL activa con suficiente
  certeza. No se inició, apagó ni modificó el laboratorio desde la consola.

El inventario AWS, su disponibilidad y el estado del laboratorio siguen
pendientes de una consulta autorizada. No se ejecutó ningún cambio de
infraestructura en este corte.

## Actualización vigente — 10:25 America/Chicago

- STS volvió a aceptar el perfil local `default` en la cuenta académica
  `841113066612`; no se guardó la sesión en el repositorio.
- El ASG tenía 2 instancias sanas y el scale-in bajo no se observaba porque el
  grupo estaba en su mínimo. Se elevó manualmente el deseado a 3 para probar la
  política; la alarma baja de Target Tracking redujo automáticamente 3→2 a las
  10:04:19. A las 10:10 quedaron 2/2 instancias `InService`/`Healthy` y 2/2
  destinos `healthy`.
- Revalidación a las 10:25: el stack sigue `UPDATE_COMPLETE`, el ASG permanece
  en 2/2 `InService`/`Healthy` y el ALB en 2/2 destinos `healthy`. Una nueva
  solicitud `/health` respondió HTTP 200 con `database=ok`; el chequeo de drift
  de las 10:10 había terminado `DETECTION_COMPLETE`/`IN_SYNC`, cero recursos
  divergentes.
- El resultado acredita scale-out automático por CPU sintética y scale-in
  automático ante capacidad ociosa tras preparar manualmente el deseado en 3.
  No es una prueba de tráfico transaccional ni de 3,000 usuarios concurrentes.
- La prueba de recuperación RDS PT-DR-01 ya había pasado (RTO 289 s, RPO
  superior observado 10 s, conteos iguales en 14 tablas); los recursos de
  restore temporales fueron eliminados.
- Azure procesó un E2E ERP→Queue→Function con compensación del ledger demo;
  sigue siendo inventario ficticio. La VPN privada no se estableció: AWS
  Academy denegó `ec2:CreateCustomerGateway` y Azure temporal se limpió.
- La estimación interna se mantiene en 11.75/20, no es nota docente. Persisten
  VNet/VPN, WMS real, dominio con TLS confiable, MFA/identidad corporativa y
  medición de carga empresarial.

Detalle: [AWS-AUTOSCALING-2026-10-13.md](aws/AWS-AUTOSCALING-2026-10-13.md).

## Primera verificación — 09:30 America/Chicago

- El token nuevo se instaló solo en `default`; STS confirmó la cuenta académica
  `841113066612`. No se copió a archivos del repositorio.
- AWS `tangamandapio-live-20261013` está `UPDATE_COMPLETE`; el chequeo de drift
  de las 09:30 terminó `IN_SYNC`. ALB `/health` devolvió HTTP 200 con PostgreSQL
  `ok`. El ASG probó scale-out 2→3 con CPU sintética (pico medio observado
  66.0%); los tres destinos llegaron a `healthy`.
- Tras parar la carga, el promedio de CPU observado volvió a ~1%, pero la alarma
  de scale-in siguió en `OK` con una muestra antigua. Se fijó manualmente el
  deseado en 2, su valor base. En la lectura de las 09:30 había dos instancias
  `InService`/`Healthy` y una en `Terminating`; dos destinos estaban sanos y el
  tercero drenando. Esto prueba scale-out automático, no scale-in automático.
- PT-DR-01 pasó con RTO 289 s, RPO superior 10 s, marcador restaurado y conteos
  iguales en 14 tablas; se eliminaron los recursos de prueba. RDS principal y
  snapshot fuente se conservaron.
- El E2E Azure de ERP→Queue→Function y compensación restauró el ledger demo a
  su saldo inicial. Es inventario ficticio. La VPN no se creó: AWS Academy
  denegó `ec2:CreateCustomerGateway`; el intento temporal en Azure se destruyó.
- La estimación interna revisada es 11.75/20: criterios 6 y 9 en nivel Bueno.
  No es nota docente. Persisten VNet/VPN, WMS real, dominio con TLS confiable,
  MFA/identidad corporativa y prueba de 3,000 usuarios.
- **Convergencia confirmada después del drenaje:** el ASG terminó con deseado 2,
  dos instancias `InService`/`Healthy` y dos destinos `healthy`. El balanceador
  siguió devolviendo HTTP 200. CloudFormation permanece `UPDATE_COMPLETE` y el
  último chequeo a las 09:30 sigue `IN_SYNC`.

Detalle de escalado: [AWS-AUTOSCALING-2026-10-13.md](aws/AWS-AUTOSCALING-2026-10-13.md).

## Recuperación de datos RDS — 08:57 America/Chicago

- La prueba temporal `PT-DR-01` pasó en AWS usando un snapshot temporal del RDS
  principal. La restauración recuperó el marcador SQL confirmado antes del
  snapshot y comparó sin diferencias los conteos de **14 tablas de negocio**.
- RTO medido desde la solicitud de restore hasta la sonda SQL: **289 s**. RPO
  superior observado entre el checkpoint y la creación del snapshot: **10 s**.
  La copia temporal fue privada, cifrada y con retención automática 0 días.
- El script verificó y limpió el marcador tanto en la instancia principal como
  en la restaurada, eliminó la copia temporal y el snapshot de prueba y reportó
  `cleanup=verified`. Ver [detalle PT-DR-01](aws/AWS-DR-RESTORE-2026-10-13.md).
  La instancia RDS principal quedó `available`; se conserva aparte el snapshot
  manual operativo cifrado.
- Para hacer ejecutable la prueba en el stack vivo, el arnés ahora resuelve el
  ARN exportado de `DatabaseSecretArn` (incluido el secreto maestro administrado
  por RDS), deriva región del ARN, normaliza CRLF de Python Windows y serializa
  el booleano de sonda como JSON. La primera restauración comprobó marcador y
  conteos, pero la comparación de mayúsculas del arnés la reportó falsamente
  fallida; limpió todos sus recursos. La repetición posterior pasó y midió los
  valores indicados.

## Revalidación posterior — 08:20 America/Chicago

- Se instaló el token temporal AWS recién entregado en el perfil local
  `default`. STS confirma la cuenta académica `841113066612`; el token no se
  guarda ni se reproduce en esta evidencia.
- La detección nueva de CloudFormation para
  `tangamandapio-live-20261013` terminó `DETECTION_COMPLETE` con `IN_SYNC` y
  cero recursos divergentes. No se aplicó infraestructura. RDS principal sigue
  `available`, privada, cifrada, Single-AZ y con un día de retención; el
  snapshot manual fuente está `available` y cifrado. La copia temporal
  `tng-drrestore-20261013023830` ya no existe.
- Azure for Students está `Enabled`; la Function `tangama-wms-261008` está
  `Running`, HTTPS-only y responde inventario autenticado en modo
  `demo-inventory-ledger` (`is_real_erp=false`). Se pasó una prueba viva,
  sintética y compensada: el artefacto `app/aws_release/current` se ejecutó
  localmente, creó una venta ERP, entregó su outbox a Azure Queue/Function y
  observó `demo_fulfillment_completed`; luego registró una recepción que
  produjo `demo_restock_completed` y devolvió el saldo demo exactamente a su
  línea base. IDs: venta `evt-17bba4db400d44849d94c63c7f2407cd`, compensación
  `evt-eb5e0edd29504ccd91c2d25a110daa47`. Los registros de auditoría sintéticos
  permanecen en Azure. Esto **no** ejecuta el portal desde EC2 ni convierte el
  inventario ficticio en WMS real.
- El smoke consultó metadatos y llave de la Function por ARM directo, porque
  los comandos Azure CLI de App Service excedían 90 s en este entorno. La llave
  se mantuvo en memoria y no se imprimió. Terraform Azure terminó su refresh y
  plan con `No changes`; no se aplicó. La prueba VPN AWS–Azure sigue bloqueada
  por la SCP que denegó `ec2:CreateCustomerGateway`; sus recursos temporales se
  destruyeron y no hay túnel.
- Se corrigió el arnés `tests/run_live_azure_erp_smoke.py` para consultar Azure
  Resource Manager directamente después de autenticar con CLI; sus dos pruebas
  unitarias pasaron. La puerta completa local terminó aprobada: **94 pruebas**,
  auditorías de dependencias, build frontend, CloudFormation y validación/formato
  Terraform, sin aplicar infraestructura. No se cambió el puntaje provisional
  11/20 ni se afirma cumplimiento total de la rúbrica.

## Reconciliación AWS–Azure y E2E — 02:32 America/Chicago

- Se corrigió el secreto de Function que no coincidía con la clave vigente de
  Azure. El valor quedó en una nueva versión de AWS Secrets Manager; no se
  imprimió ni guardó en evidencia.
- AWS Academy negó el API `StartInstanceRefresh` por una SCP. Las dos EC2 se
  reemplazaron secuencialmente con capacidad deseada constante; ambas regresaron
  sanas y consultaron Azure desde su proceso con HTTP 200.
- El artefacto AWS ejecutó desde EC2 un flujo ERP/outbox→Azure Queue/Function
  con SQLite temporal: venta `demo_fulfillment_completed`, recepción
  `demo_restock_completed`, stock ficticio **24 → 23 → 24** y conciliación de
  ambos resultados. SQLite se eliminó; no se tocó RDS. Los IDs están en
  [la evidencia E2E AWS–Azure](azure/AZURE-AWS-INTEROP-2026-10-13.md).
- Revisión final: CloudFormation `UPDATE_COMPLETE`, drift `IN_SYNC`, ASG 2/2
  sano, target group 2 sanos/0 drenando, ALB `/health` `ok` y base `ok`; RDS
  disponible, cifrada, privada, Single-AZ y con 1 día de backups.
- En el portal de producción, la API de inventario contestó HTTP 428
  `password_change_required` para la sesión admin. No se cambió ni se sorteó la
  contraseña. Azure usa HTTPS público; la red VNet/VPN privada sigue pendiente.

La matriz sigue mostrando **11/20 como corte provisional anterior**; todavía
no se hizo una reevaluación completa criterio por criterio tras esta prueba.

## Prueba de recuperación EC2 — 01:49 America/Chicago

- El perfil `default` contiene el identificador de clave entregado para la
  sesión actual y AWS STS lo acepta; no se guardan claves ni tokens en este
  registro.
- Se terminó una instancia del ASG para validar recuperación. En la comprobación
  posterior, el grupo volvió a dos instancias `InService`/`Healthy`, el ALB
  informó dos destinos `healthy` y uno anterior `draining`, y `/health` devolvió
  `status: ok` con `database: ok`. La actividad de reemplazo figura
  `Successful`. En el chequeo final a las 01:51 ya no había instancia
  `Terminating` ni destino `draining`: quedaron exactamente dos destinos
  `healthy` y cero `unhealthy`. Es una verificación posterior, no un RTO
  cronometrado; tampoco sustituye la prueba de restauración de datos RDS.
- Evidencia detallada: [despliegue y recuperación AWS](aws/AWS-DESPLIEGUE-2026-10-13.md).

## Corte posterior al despliegue — 01:14 America/Chicago

- AWS `default` autenticó con STS. El stack CloudFormation del portal terminó
  `UPDATE_COMPLETE`; la detección de drift más reciente quedó `IN_SYNC`.
- El portal respondió HTTP 200 por el ALB en `/` y `/health`; el health informó
  base de datos `ok`. Dos instancias `t3.micro`, distribuidas entre `us-east-1a`
  y `us-east-1b`, están `InService` y ambos destinos del ALB `healthy`. Sondas
  SSM directas confirmaron `/health` 200 y `/ready` con PostgreSQL `ok` en cada
  instancia.
- RDS está `available`, privado y cifrado; conserva perfil Single-AZ y un día
  de backups. El secreto maestro administrado está `active`. No se reemplazó la
  base al habilitar el portal. Ver [despliegue AWS](aws/AWS-DESPLIEGUE-2026-10-13.md).
- Azure `/api/health` respondió 200, pero la lectura autenticada de inventario
  iniciada desde EC2 devolvió 401 con la clave obtenida del secreto AWS actual.
  No se creó ningún evento ni se tocaron existencias. Esto confirma salida de
  red, pero revela que la autenticación AWS→Function no está reconciliada; la
  consulta de solo lectura de claves Azure se quedó esperando y se canceló.

La matriz conserva **11/20** como estimación provisional anterior, sin
reevaluación completa tras el despliegue. No inferir que todos los criterios
están cerrados por tener el portal arriba. En ese corte seguían pendientes la
clave Azure y el E2E, resueltos en la verificación posterior arriba. Siguen
pendientes red privada entre nubes, restauración RDS con integridad y RTO/RPO,
escala por carga, cambio de contraseña admin en navegador y validación posterior
de RBAC, pruebas reales de voz, HTTPS/dominio del ALB y capturas crudas actuales.

## Corte previo al despliegue — 00:22 America/Chicago

- AWS `default`: AWS STS aceptó la sesión nueva. El inventario posterior a la
  prueba no muestra recursos de aplicación EC2, ALB o RDS activos; permanece un
  stack administrado por AWS Academy, no Tangamandapio.
- La restauración aislada del snapshot PostgreSQL cifrado pasó, activó el secreto
  maestro administrado por RDS y limpió la instancia y el subnet group
  temporales. El snapshot original sigue disponible y cifrado. No se realizó
  consulta SQL de integridad ni se midió RTO/RPO. Evidencia: [prueba DR](aws/AWS-DR-RESTORE-2026-10-13.md)
  y [inventario AWS](aws/AWS-INVENTARIO-2026-10-13.md).
- Azure for Students aparece `Enabled`; una consulta HTTP directa a
  `/api/health` devolvió 200. La consulta de control de la Function tardó más de
  un minuto y se canceló; su estado de ejecución no se revalidó hoy. La última
  consulta de red de suscripción (12/10) no encontró recursos `Microsoft.Network/`.
- La compuerta local ejecutada hoy aprobó 79 pruebas unitarias, auditorías de
  dependencias, build frontend, CloudFormation, formato/validación Terraform y
  dos casos mock de la compuerta VPN.

## Qué demuestra y qué no

La prueba DR demuestra restauración técnica a `available`, cifrado, acceso no
público, rotación de credenciales y limpieza temporal. No demuestra que el
contenido restaurado tenga integridad lógica, que el portal restaurado arranque,
ni un RTO/RPO cuantificado. Tampoco hay despliegue permanente de Tangamandapio
en AWS ni conectividad privada AWS–Azure.

No quedó ninguna instancia RDS temporal al terminar el corte. Solo se ejecutó
una prueba temporal facturable y se borraron sus recursos. El health de Azure es
una comprobación HTTP, no una captura del portal ni evidencia de procesamiento
originado desde EC2.

## Siguientes verificaciones

1. Restaurar el snapshot en un entorno de prueba con una sonda PostgreSQL
   autorizada y comparar tablas/datos de negocio; medir RTO/RPO y limpiar.
2. Desplegar el portal en AWS con stack y secretos versionados, verificar health,
   login y outbox→Azure desde EC2, dejando por separado los costos y límites del
   Learner Lab.
3. Migrar Azure Function a un plan apto para integración privada, desplegar la
   VNet/VPN AWS–Azure con su compuerta de costo y comprobar rutas/DNS/túneles.
4. Revalidar Application Insights, alertas/poison, roles en navegador,
   accesibilidad/responsive y conservar capturas crudas actuales.

La prueba de audio/video entre dos navegadores reales y el dominio/HTTPS propio
siguen diferidos como pidió el usuario.

## Revalidación posterior — 04:37 America/Chicago

- Se aplicó al perfil AWS local `default` la terna temporal que entregó el
  usuario en este corte. STS la aceptó como sesión del rol `voclabs`; esto
  confirma autenticación, no permisos para operar servicios.
- Las consultas de solo lectura a CloudFormation `ListStacks`, EC2
  `DescribeInstances`, ELB `DescribeLoadBalancers` y RDS `DescribeDBInstances`
  fueron denegadas por la política explícita `voc-cancel-cred`. No se pudo
  comprobar el inventario ni modificar AWS. El estado de instancias, ALB y RDS
  sigue sin verificar en este corte; los resultados históricos no lo sustituyen.
- Azure for Students aparece `Enabled`; la Function `tangama-wms-261008` está
  `Running` y requiere HTTPS. Storage informa soft delete de Blob habilitado
  por 7 días y versionado de Blob deshabilitado.
- El empaquetador de Azure creó dos ZIP independientes byte-idénticos
  (SHA-256 `643750B5497FEC9705BC7FE04742060FEC48F947AA81D6C7E86C5FAB6758A3BE`);
  las 21 pruebas de Azure Functions pasaron. El plan Terraform vivo propuso
  reemplazar únicamente el Blob content-addressed y actualizar la Function:
  1 alta, 1 cambio y 1 destrucción del Blob anterior. Tras añadir
  `create_before_destroy`, el plan confirmó crear el nuevo Blob antes de
  retirar el anterior y no propuso otros cambios. Se preservó localmente el ZIP
  previo; Azure ofrece soft delete por 7 días.
- El plan guardado temporalmente pasó un guard que permitió solo esas dos
  mutaciones y se aplicó. Terraform informó 1 recurso creado, 1 actualizado y
  1 destruido (el Blob antiguo). Se sincronizaron los triggers; la Function
  continuó `Running`, `httpsOnly=true` y `/api/health` respondió `ok`.
- El plan Terraform de solo lectura posterior terminó `No changes`, con
  `POST_APPLY_PLAN_EXIT=0`; la infraestructura Azure quedó reconciliada con
  el código Terraform para este release.
- El E2E posterior usó el release **local** del ERP contra la Function recién
  publicada. Venta `evt-46a72c6479634d05ba50ec5c13af32b1` terminó
  `demo_fulfillment_completed`; recepción compensatoria
  `evt-74641a0938814524a8cb17edc0b34f0e` terminó
  `demo_restock_completed`. La lectura autenticada confirmó ambos estados y el
  SKU ficticio `SKU-ARROZ-001` en 24 unidades, modo `demo-inventory-ledger`.
  Esto no ejecuta el ERP desde EC2 ni acredita conectividad privada.
- No se verificó el estado visual de Start Lab en AWS Academy ni se afirmó un
  cambio del laboratorio. Evidencia detallada: [corte AWS](aws/AWS-REVALIDACION-STS-2026-10-13.md)
  y [corte Azure](azure/AZURE-PLAN-PAQUETE-2026-10-13.md).

## Actualización posterior — 02:38 America/Chicago

Se aplicaron al perfil local `default` las nuevas credenciales temporales y
AWS STS confirmó la identidad de la cuenta del laboratorio. Sin embargo, un
reintento de restauración RDS quedó incompleto: la política IAM
`voc-cancel-cred` deniega operaciones de EC2, CloudFormation y RDS, incluida la inspección y eliminación de los recursos de prueba
`tng-drrestore-20261013023830` y `tng-drtest-20261013023830`. Su limpieza y
estado final están sin verificar; podrían seguir generando costo. El snapshot
de origen no se eliminó. No afirmar que el restore quedó limpio hasta recuperar
permisos y comprobarlo. Detalle: [evidencia de restore RDS](aws/AWS-DR-RESTORE-2026-10-13.md).

## Corte actual — 02:58 America/Chicago

- AWS STS autentica la cuenta del laboratorio, pero llamadas de solo lectura a
  EC2 y CloudFormation y las operaciones RDS reciben `AccessDenied`/
  `UnauthorizedOperation` por la política explícita `voc-cancel-cred`.
- El endpoint público del ALB devolvió HTTP 503 tanto en `/` como en `/health`.
  El servicio AWS no está verificado como disponible en este corte; el resultado
  200 documentado antes ya no representa el estado actual. No se modificó la
  infraestructura durante esta revalidación.
- Azure for Students aparece `Enabled`; la Function `tangama-wms-261008` está
  `Running` en West US, `httpsOnly=true`, y `/api/health` devolvió HTTP 200.
- La puerta local completa pasó: 79 pruebas unitarias, auditoría Python sin
  vulnerabilidades conocidas, build web, lint CloudFormation, formato y
  validación Terraform, y dos pruebas mock de la compuerta VPN. No hubo `apply`
  de infraestructura.
- El restore temporal `tng-drrestore-20261013023830` y el subnet group
  `tng-drtest-20261013023830` continúan con estado final sin verificar por la
  denegación de permisos; podrían seguir facturando. No borrar el snapshot fuente.

## Corte posterior — 03:19 America/Chicago

- Se aplicó la terna nueva al perfil local `default`; `aws sts
  get-caller-identity` autenticó la cuenta del laboratorio. Esto confirma
  autenticación, no permisos de servicio.
- AWS Academy muestra `Ready`, 3 h 58 min restantes y $22/$50 utilizados; el
  panel AWS Details muestra “No running instance”. No se pulsó Start Lab porque
  la sesión figura preparada y el usuario indicó que ya estaba encendida.
- CloudFormation (`ListStacks`), EC2 (`DescribeInstances`), ELB
  (`DescribeLoadBalancers`) y RDS (`DescribeDBInstances`) siguen con denegación
  explícita `voc-cancel-cred`. El ALB tampoco resolvió por DNS en la comprobación
  externa. No se desplegó ni modificó infraestructura.
- Azure `/api/health` respondió HTTP 200. Esto no verifica conectividad privada
  AWS–Azure ni procesamiento de un evento WMS.
- La incertidumbre de limpieza de `tng-drrestore-20261013023830` y
  `tng-drtest-20261013023830` persiste; podrían generar consumo. El snapshot
  fuente no se tocó. Detalle: [autenticación AWS](aws/AWS-REVALIDACION-STS-2026-10-13.md)
  y [restore RDS](aws/AWS-DR-RESTORE-2026-10-13.md).
- El stack local estaba arriba y saludable en la verificación previa de 03:13;
  consulta [LOCAL-STACK-2026-10-13.md](LOCAL-STACK-2026-10-13.md). La puerta de
  calidad aprobó 79 pruebas.

## Actualización local — 03:39 America/Chicago

- Se hizo atómica la escritura de auditoría con altas/cambios administrativos
  en el portal y el artefacto release. Dos pruebas locales y tres pruebas
  enfocadas al ERP release demuestran rollback de alta, cambio de usuario y
  reseteo cuando falla la auditoría.
- El stack Docker local fue reconstruido conservando `app_aws-data`. Los tres
  servicios (`aws-app`, `azure-service`, `mailpit`) están saludables; la página
  principal da 200, `/health` da `ok`/base `ok` y el endpoint admin anónimo
  responde 401.
- La compuerta completa aprobó **81 pruebas** (30 portal, 21 Function Azure,
  30 release AWS), auditorías Python/frontend, build, CloudFormation lint,
  Terraform format/validate para cuatro entornos y 2/2 pruebas mock VPN. Además,
  el test suite ERP del artefacto AWS pasó 7/7. No hubo `apply` ni cambios cloud.
- AWS conserva el último estado cloud observado a las 03:19: credenciales STS
  aceptadas pero APIs de servicio denegadas por `voc-cancel-cred`. Esta mejora
  de código solo está probada/local; AWS no se pudo actualizar.

## E2E Azure posterior — 03:54 America/Chicago

- La suscripción `Azure for Students` siguió `Enabled`; la Function
  `tangama-wms-261008` estaba `Running` y HTTPS-only. El smoke opt-in del release
  ERP local creó una venta demo y una recepción compensatoria mediante Queue y
  Function. Los resultados persistidos fueron `demo_fulfillment_completed` y
  `demo_restock_completed`; el ERP reconcilió `completed_demo`/`received_demo`.
- El stock del SKU sintético bajó 24→23 y volvió a 24. Una consulta final de
  inventario autenticada confirmó 24, sin reejecutar el flujo. Los eventos
  sintéticos permanecen en auditoría Azure; la SQLite/ERP temporal local se
  eliminó al terminar.
- Esto confirma el worker Azure para un flujo originado en el release **local**,
  no desde EC2. No verifica VNet/VPN ni un WMS empresarial. Evidencia e IDs:
  [AZURE-ERP-E2E-2026-10-13.md](azure/AZURE-ERP-E2E-2026-10-13.md).

## Corte de seguimiento — 04:53 America/Chicago

- AWS: el perfil local `default` contiene el identificador de clave entregado
  para este corte y tiene secreto/token presentes, pero STS rechazó la sesión
  como token inválido. No se cambiaron recursos. La interfaz de AWS Academy no
  se pudo inspeccionar en este turno; por tanto, no afirmo que Start Lab se haya
  pulsado ni que el laboratorio esté apagado.
- Azure: `az account show` devolvió el estado de suscripción `Enabled`. La
  consulta de control `az functionapp show` no terminó dentro del tiempo de
  espera; sin embargo, la comprobación directa de solo lectura a
  `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200 y
  `{"status":"ok","service":"tangamandapio-wms"}`. Esto acredita salud HTTP
  del endpoint, no estado completo de recursos ni VPN privada.
- La compuerta local volvió a aprobar 81 pruebas, auditoría de dependencias,
  build frontend, validación CloudFormation y formato/validación Terraform.
  No ejecutó operaciones cloud. `git diff --check` no encontró errores de
  whitespace (solo avisos CRLF/LF).
- La prueba de restore PT-DR-01 quedó endurecida localmente: el reloj RTO inicia
  al solicitar la restauración, la instancia temporal pide retención automática
  de 0 días y el preflight valida ese valor. La puerta verifica estas guardas,
  pero la prueba real SQL/restore no se ejecutó en este corte.

## Endurecimiento local del preflight VPN — 05:07 America/Chicago

- El despliegue AWS VPN ahora verifica que el stack del portal exponga la VPC
  `10.10.0.0/16`, que la VNet Azure sea `10.20.0.0/16`, que la tabla de rutas
  pertenezca a esa VPC y que las dos IP configurations del gateway estén en la
  `GatewaySubnet` correcta.
- Un error al consultar el stack VPN existente ya no se interpreta como “no
  existe”. Si existe con parámetros distintos, el wrapper exige
  `-ApproveStackUpdate`; el CIDR Azure queda fijado en CloudFormation para que
  el contrato no se cambie aisladamente.
- Cuatro escenarios con AWS/Azure simulados pasaron: AccessDenied no despliega,
  `ValidationError` de stack inexistente permite creación, update divergente se
  bloquea sin aprobación y procede con aprobación explícita; un CIDR AWS
  incorrecto también se bloquea. El formato JSON del resultado se validó en la
  ruta mock positiva.
- La puerta completa volvió a aprobar 81 pruebas, auditoría de dependencias,
  build, CloudFormation lint y Terraform; sumó los cuatro casos mock. No hubo
  operaciones cloud. La VPN real sigue sin desplegarse y AWS no autentica en el
  corte actual, por lo que túneles/rutas permanecen pendientes.

## Revalidación local y credenciales — 05:23 America/Chicago

- Se sustituyó el perfil AWS CLI `default` por las tres credenciales entregadas
  en este turno. La comparación local confirmó coincidencia exacta y
  `aws configure list` indicó que las lee de `shared-credentials-file`; la
  consulta `sts get-caller-identity` devolvió `ExpiredToken`. No se invocó
  ninguna operación mutante de AWS. Aunque el usuario informó que el lab está
  encendido, su estado y el inventario AWS no quedaron verificados por API.
- El preflight VPN pasó **7 escenarios mock**: AccessDenied bloquea, not-found
  explícito permite crear, parámetros divergentes exigen aprobación para
  actualizar, CIDR AWS, route table distinta y ASN Azure inesperados bloquean.
- `tests/run_local_quality.ps1 -ValidateTerraform` aprobó **83 pruebas**,
  auditorías de Python/frontend, build, CloudFormation lint, formato/init/
  validate de Terraform y **2 tests mock** del gate de costo VPN. No se hicieron
  operaciones de red en AWS ni Azure. La VPN, sus cuatro túneles y las rutas
  reales siguen sin probarse.
- El resultado no cambia la evaluación de la rúbrica: es evidencia de guardas
  locales, no de conectividad multinube desplegada.

## Verificación Azure y smoke con timeout — 05:23 America/Chicago

- A las 05:17:36, el endpoint HTTPS `/api/health` devolvió HTTP 200 con
  `status=ok` y `service=tangamandapio-wms`. Esto es salud HTTP, no inventario
  ARM ni prueba de ejecución del worker.
- Se intentó el smoke ERP→Azure con la prueba opt-in existente. `az account show`
  aceptó la sesión, pero `az functionapp show` quedó sin responder. El primer
  intento se detuvo en esa consulta de solo lectura; el segundo terminó con el
  nuevo límite de 30 segundos. Ambos ocurrieron antes de recuperar la Function
  key, leer inventario o publicar eventos; no hubo mutaciones Azure.
- Se corrigió el harness para imponer ese timeout y se añadieron dos pruebas
  unitarias para el timeout y la respuesta exitosa. La puerta completa volvió
  a aprobar **83 pruebas**, auditorías, CloudFormation, build y Terraform. El
  E2E vivo sigue pendiente porque no se confirmó el estado de la Function por
  ARM.

## Asociación de IPs del gateway — 05:28 America/Chicago

- El preflight AWS VPN ahora compara los IDs de `publicIPAddress` de las dos
  configuraciones de gateway con los recursos `pip-tangama-vpn-a/b` antes de
  usar sus direcciones para CloudFormation. La verificación usa el campo de
  asociación `publicIPAddress.id` del recurso Azure Virtual Network Gateway.
- El octavo escenario mock entrega deliberadamente una IP no asociada; el
  wrapper falla cerrado y no invoca `cloudformation deploy`. Los ocho escenarios
  pasan sin llamadas cloud.
- La puerta completa con `-ValidateTerraform` volvió a aprobar **83 pruebas**,
  auditorías, CloudFormation, frontend, Terraform fmt/init/validate y los dos
  tests de costo. Ningún stack VPN se desplegó; AWS sigue rechazando STS con
  `ExpiredToken`.

## Salud HTTP local — 05:34 America/Chicago

- El portal local respondió HTTP 200 en `/` y `/health`; el health payload
  informó `status=ok` y `database=ok`.
- `/api/health` devolvió 404 porque esa ruta pertenece a la Function Azure; el
  portal publica `/health`. No se hicieron mutaciones ni se infirió estado de
  AWS/Azure a partir del stack local.

## Rate limiting de autenticación — 06:02 America/Chicago

- La variante local de Flask ahora persiste el rate limit en la base compartida
  por instancias. Cinco fallos consecutivos producen bloqueo temporal de 300
  segundos con HTTP 429 y `Retry-After`; un login correcto reinicia el contador.
  IP y usuario se combinan con HMAC y no se almacenan como texto legible.
- Tres pruebas cubren persistencia al crear otra instancia del portal, `429`,
  encabezado `Retry-After`, limpieza tras login correcto y actualización
  atómica bajo fallos concurrentes; la suite de release AWS prueba el flujo y
  que no persista el usuario en claro. La migración 0008 limpia contadores
  legibles heredados al actualizar el servicio, sin tocar datos de negocio.
  No prueban MFA, WAF
  ni política de identidad productiva.
- La compuerta integral `tests/run_local_quality.ps1 -ValidateTerraform` aprobó
  87 pruebas unitarias, auditorías de dependencias, CloudFormation, build del
  frontend, formato/validación Terraform y guards mock; no ejecutó acciones
  cloud.
- Se reemplazó el perfil AWS local `default` con la terna temporal recibida en
  este corte. AWS STS respondió `ExpiredToken`; no se hicieron cambios cloud y
  no se afirma que el inventario AWS esté disponible o actualizado.

## Protección CSRF y revalidación local — 06:23 America/Chicago

- El backend local ahora emite un token CSRF en `/api/auth/session`, exige
  `X-CSRF-Token` en métodos de escritura (incluido el login), valida `Origin` o
  `Referer` cuando llegan, y rota el token después de autenticación. El cliente
  React obtiene el token antes de su primera escritura, envía la cabecera y
  vuelve a obtener token al salir/expirar la sesión.
- Dos pruebas focalizadas verifican sesión anónima, origen ajeno, login,
  escritura autenticada sin/con token, logout y rotación. La puerta integral
  `tests/run_local_quality.ps1 -ValidateTerraform` pasó **91 pruebas**: API 36,
  Azure Functions 21, release AWS 32 y guards 2; también pasaron auditoría de
  dependencias, CloudFormation, build frontend, formato/validación Terraform y
  gates mock. No se ejecutaron acciones cloud.
- Se reconstruyeron los servicios Docker locales del portal y Function Azure
  preservando los volúmenes; el portal respondió `/health` HTTP 200 con base
  `ok`. En el runtime se comprobó token anónimo, escritura sin token `403`,
  logout con token `204`, rotación después de logout y bundle actualizado con
  `X-CSRF-Token`. No se realizó login de usuario en navegador ni prueba contra
  el ALB.
- El perfil AWS `default` fue escrito desde la terna temporal recibida; `aws
  configure list` confirma que la clave se lee desde el archivo compartido.
  STS devolvió `ExpiredToken`, por lo que el perfil no sirve para operar en AWS
  y no se cambiaron recursos cloud. El control de navegador no pudo validar la
  URL de AWS Academy y se detuvo; no se afirma haber iniciado/reiniciado el lab.
- Esta evidencia no valida MFA, CSRF detrás del proxy productivo, roles en
  navegador, conectividad AWS–Azure, restauración RDS viva ni ejecución cloud.
  La autoevaluación anterior 11/20 no se recalcula con este corte local.

## Gestión de contraseñas y revalidación local — 06:45 America/Chicago

- La aplicación local ya fuerza el cambio de la contraseña de bootstrap y de
  claves temporales antes de operar. `POST /api/auth/password` valida la clave
  actual, longitud y reutilización; `POST /api/admin/users/{id}/reset-password`
  permite al administrador generar una clave temporal de una sola respuesta
  para otra cuenta activa. El evento de auditoría no contiene el secreto y el
  cambio de `auth_version` invalida sesiones anteriores. La migración añade los
  campos necesarios sin reconstruir las tablas existentes.
- Las tres pruebas nuevas de gestión de contraseñas pasaron; la puerta integral
  `tests/run_local_quality.ps1 -ValidateTerraform` aprobó **94 pruebas** (39
  API, 21 Azure Functions, 32 release AWS y 2 guards), auditorías de
  dependencias Python/frontend, build frontend, CloudFormation y formato,
  inicialización y validación de los entornos Terraform. Los tests de red/costo
  fueron mocks; Terraform no aplicó recursos.
- Se reconstruyó solo `aws-app` en Docker local con los valores de entorno ya
  usados por el contenedor y se conservó el volumen de datos; Azure local y
  Mailpit no se reiniciaron. A las 06:49, la Function simulada local devolvió
  `status=ok`; esto no prueba la Function desplegada en Azure. El portal devolvió HTTP 200, `/health` reportó
  `status=ok` y `database=ok`, `/api/auth/session` emitió CSRF y el bundle
  servido contiene las vistas de cuenta, cambio y restablecimiento temporal.
  Esto comprueba el artefacto local servido, no una sesión manual de admin ni
  roles interactuados en navegador.
- El perfil AWS CLI `default` está leyendo el archivo compartido actualizado,
  pero la verificación `sts get-caller-identity` responde `ExpiredToken`. No se
  verificó inventario ni se modificó AWS. En una pestaña nueva de AWS Academy,
  la vista cargó `AWS Status: Terminated`, `Lab terminated`, temporizador
  `00:00` y `No running instance` (presupuesto mostrado: $22/$50). La pestaña
  antigua presentaba un contador residual de 3:58 y era inconsistente; no se
  tomó como estado actual. El intento de continuar el control de navegador se
  detuvo por la barrera de validación de URL antes de pulsar `Start Lab`; el
  laboratorio no se reinició. No se afirma despliegue de este flujo en AWS;
  permanece pendiente iniciar una sesión válida y confirmar identidad e
  inventario. Azure real tampoco se modificó en este corte.
- El puntaje **11/20** permanece como autoevaluación provisional del corte
  anterior; no se aumenta con pruebas locales ni se presenta como nota vigente.

## Línea base de rendimiento local — 06:54 America/Chicago

- Contra el contenedor local `aws-app`, el smoke de 100 solicitudes con
  concurrencia 10 pasó con p95 303.93 ms y 0 errores. La prueba de 1000 con
  concurrencia 50 pasó con p95 68.34 ms, máximo 328.72 ms y 0 errores; el
  umbral predefinido fue p95 ≤ 2000 ms y error ≤ 1 %.
- Los resultados JSON están preservados como
  [`LOCAL-LOAD-BASELINE-2026-10-13.json`](LOCAL-LOAD-BASELINE-2026-10-13.json)
  y [`LOCAL-LOAD-STRESS-2026-10-13.json`](LOCAL-LOAD-STRESS-2026-10-13.json).
  Solo se consultó `/health`: es un endpoint de lectura sobre una instancia
  local, no prueba rendimiento de pedidos, escalado de ASG, dos AZ, RDS ni
  capacidad para 3000 usuarios externos. No cambia la estimación de rúbrica.

## Prueba temporal de red privada AWS–Azure — 13/10/2026

- El perfil local `default` se actualizó con las credenciales temporales nuevas;
  `aws sts get-caller-identity` tuvo éxito. No se guarda ni reproduce el token
  en la documentación.
- La VPC existente del portal se confirmó en `10.10.0.0/16`, con su output
  `AppRouteTableId` asociado a esa VPC; no existía VPN Gateway ni stack VPN.
  Azure estaba habilitado, no tenía VNets y el grupo de red temporal no existía.
- El plan mock Terraform aprobó los dos casos de la barrera de costos. La
  primera creación de Azure falló porque `VpnGw1` no zonal ya no se admite para
  gateways nuevos (`NonAzSkusNotAllowedForVPNGateway`). Se cambió el default
  del entorno a `VpnGw1AZ`, se añadió validación y aserción de SKU y volvieron a
  pasar ambos tests. El plan posterior fue solo `1 to add`; el gateway temporal
  se creó correctamente en West US con BGP y activo-activo.
- La creación del stack AWS se revirtió: la SCP del laboratorio denegó
  explícitamente `ec2:CreateCustomerGateway`. Es una limitación de autorización
  del entorno académico; no se intentó rodearla. CloudFormation terminó en
  `ROLLBACK_COMPLETE`, no hubo conexiones VPN/túneles y se eliminó el registro
  vacío de la pila. El portal y sus recursos existentes no se modificaron.
- Se ejecutó `terraform destroy` y terminó con **9 recursos destruidos**.
  Verificaciones finales: el grupo `rg-tangama-private-network` no existe,
  el estado Terraform está vacío y AWS no muestra un VPN Gateway adjunto a la
  VPC del portal. No queda infraestructura temporal de esta prueba.
- La tarifa minorista consultada para el gateway fue US$0.21/h, más las IP
  públicas mientras estuvieron asignadas; el total facturado no es visible
  todavía y puede tardar en reflejarse. No hubo tráfico de aplicación ni túnel
  establecido. La prueba no demuestra conectividad AWS–Azure; se requiere que
  el administrador del laboratorio permita `ec2:CreateCustomerGateway` para
  repetirla. El cálculo 11/20 se conserva sin aumento.

La tarifa se consultó en la [API oficial de precios minoristas de Azure para
VPN Gateway en West US](https://prices.azure.com/api/retail/prices?$filter=serviceName%20eq%20%27VPN%20Gateway%27%20and%20armRegionName%20eq%20%27westus%27); el
despliegue está documentado en
[`iac/environments/aws-azure-vpn/README.md`](../../iac/environments/aws-azure-vpn/README.md).

## Revalidación AWS del token más reciente — 11:52 America/Chicago

- El perfil local `default` se reemplazó con la terna temporal entregada en
  este corte. El identificador guardado coincide y no hay variables de entorno
  `AWS_*` que la sustituyan. `aws sts get-caller-identity` autenticó la cuenta
  académica `841113066612`; no se guardaron credenciales en el proyecto.
- Las consultas de solo lectura a VPC, EC2, Auto Scaling, ELB, RDS y conexiones
  VPN fueron rechazadas por denegaciones explícitas de `voc-cancel-cred`.
  CloudFormation también denegó `ListStacks`. La autenticación es válida, pero
  el inventario y la autorización para desplegar no están disponibles; no se
  ejecutaron operaciones de escritura ni se modificó AWS.
- El estado de stack, balanceador, EC2 y base de datos reportado en cortes
  previos es histórico hasta que AWS permita una nueva lectura. La prueba
  temporal de VPN sigue sin túnel ni gateway Azure residual, según el último
  `terraform destroy` documentado.

## Revalidación Azure — 12:06 America/Chicago

- La suscripción Azure for Students está `Enabled` y el Resource Group
  `rg-tangamandapio-rebuild-wus` existe.
- La Function `tangama-wms-261008` figura `Running`, solo HTTPS, con
  `publicNetworkAccess=Enabled`; su plan observado es Linux Consumption `Y1`
  (`Dynamic`). La lista de VNet integrations está vacía. El endpoint
  `https://tangama-wms-261008.azurewebsites.net/api/health` devolvió HTTP 200 y
  `{"status":"ok","service":"tangamandapio-wms"}`.
- Por tanto, Azure está vivo para la demostración, pero no es un endpoint
  privado y su Function no cruza una VPN desde AWS. El plan `Y1` no admite
  Private Endpoint ni integración VNet; se requiere una Function Flex/plan
  compatible y un corte blue-green con DNS privado antes de afirmar ese flujo.
  No se cambió Azure. `az functionapp show` tardó aproximadamente dos minutos;
  la consulta concluyó correctamente.

## Verificación local y preflight VPN — corte actual

- `tests/run_local_quality.ps1 -ValidateTerraform` terminó con
  `QUALITY_GATE=APROBADA`: 94 tests unitarios (API 39, Azure Functions 21,
  release AWS 32 y smoke guard 2), auditoría de dependencias sin vulnerabilidades
  conocidas, build frontend, lint CloudFormation, formato/validación Terraform y
  dos escenarios del gate de costo. No aplicó recursos cloud.
- Después de añadir la subnet de integración Flex al stack de red, su
  `terraform validate` aprobó y `terraform test` aprobó 2/2; tampoco se aplicaron
  recursos.
- Se ejecutó `deploy_aws_vpn.ps1 -AwsPreflightOnly` contra el stack del portal.
  STS pasó, pero la consulta del stack falló por denegación de política; el
  script terminó antes de invocar Azure. Confirmado: cero cambios cloud.
- A las 12:16 se repitió el E2E compensado ERP local→outbox→Azure Queue/Function:
  `evt-200ef62e52bf4939a440797f152a9407` terminó
  `demo_fulfillment_completed`; `evt-496021a8d93a41e18e05e7308ceb247f`
  terminó `demo_restock_completed`. El ledger demo comprobó 24→23→24 y quedó en
  su línea base; los registros sintéticos permanecen en Blob. La ejecución no
  usó EC2 ni prueba el túnel privado. Ver [E2E Azure](azure/AZURE-ERP-E2E-2026-10-13.md).

## Revalidación de credencial AWS y avance local — 12:46 America/Chicago

- Se actualizó el perfil local `default` con la terna temporal recién entregada.
  AWS STS autenticó la cuenta `841113066612` bajo el rol `voclabs`. No se
  imprimieron ni copiaron los secretos al repositorio.
- Las lecturas de CloudFormation, VPC/EC2/VPN, ELB y RDS volvieron a recibir
  denegaciones explícitas de `voc-cancel-cred`. No hay inventario AWS confirmado
  ni se hicieron escrituras. Véase el [registro STS](aws/AWS-REVALIDACION-STS-2026-10-13.md).
- Azure for Students seguía `Enabled`; `az group exists` confirmó que
  `rg-tangama-private-network` no existe. Por ello no se ejecutó plan ni apply
  de una Function privada. La salud Y1/200 de las 12:06 es la última comprobación
  de la Function en vivo; una enumeración Azure posterior no terminó dentro del
  límite de espera y no se usa como evidencia.
- Localmente, `iac/environments/azure-flex-private` quedó validado con
  AzureRM 4.79.0: `terraform validate` y 3/3 pruebas mock. Su estado final es
  private-by-default, con compuertas para costos y bootstrap público,
  identidad administrada, package blob, Private Endpoint y Private DNS. Se
  corrigió `storage_container_endpoint` para usar la URL Blob + contenedor.
- `aws-azure-vpn.yaml` ahora permite una zona privada Route 53 de alcance
  limitado al FQDN exacto de la Function, solo si se suministran juntos el
  hostname y una IP asignable `10.20.2.4–30`; queda apagada si se omiten. El
  preflight tiene 13 escenarios mock. `tests/run_local_quality.ps1
  -ValidateTerraform` terminó con **94/94 pruebas de aplicación**, auditoría
  Python/frontend limpia, build, `cfn-lint`, formato/validación Terraform y
  pruebas de costo/red Flex 3/3. Ninguna prueba creó recursos.
- El estado provisional de rúbrica se conserva en **11.75/20**: estas son
  pruebas e IaC locales, no una VPN, migración Flex ni flujo EC2→Azure desplegado.
  No hubo cambios cloud en este corte.

## Revalidación posterior — 13:03 America/Chicago

- AWS `default` ya no autentica: `sts get-caller-identity` devolvió
  `ExpiredToken` y `cloudformation:ListStacks` falló igual. Por tanto, el
  inventario sigue sin confirmar; la denegación `voc-cancel-cred` observada
  cuando STS sí autenticaba a las 12:46 es un resultado separado e histórico.
- Azure for Students permanece `Enabled`. La consulta `az group exists` devolvió
  `false` para `rg-tangama-private-network`. La Function `tangama-wms-261008`
  está `Running`, `publicNetworkAccess=Enabled`; `tangama-wms-plan` es SKU
  `Y1`/tier `Dynamic` en West US. `/api/health` devolvió HTTP 200 con
  `{"status":"ok","service":"tangamandapio-wms"}`. No hay base para afirmar
  que Flex, Private Endpoint, DNS privado o VPN estén desplegados.
- No hubo escrituras en Azure ni AWS. El paquete local Flex y las pruebas
  permanecen en el último corte aprobado; la revalidación de nube no alteró el
  código.

## Revalidación con laboratorio AWS iniciado — 13:08 America/Chicago

- La terna temporal recién entregada quedó activa en el perfil local `default`:
  la access key coincide con el sufijo recibido y `aws sts get-caller-identity`
  autenticó la cuenta `841113066612`, rol `voclabs`. No se guardaron valores
  secretos en el repositorio.
- AWS responde lecturas de inventario. CloudFormation muestra
  `tangamandapio-live-20261013` en `UPDATE_COMPLETE`; sin embargo, el ASG pide 2
  instancias y tiene 0 en servicio, el target group está vacío y el ALB devuelve
  HTTP 503. Los intentos de EC2 terminan con `Client.InternalError`; la causa
  raíz no quedó identificada. No se hicieron cambios de nube.
- RDS continúa `available`, pero su configuración real es Single-AZ y backup
  de 1 día. El listener del ALB es HTTP/80; todavía no hay HTTPS ni dominio.
  No hay VPN AWS en la región.
- Azure for Students está `Enabled`. La Function
  `tangama-wms-261008` está `Running` en `rg-tangamandapio-rebuild-wus`, pública;
  `/api/health` responde HTTP 200. `rg-tangama-private-network` no existe, por
  lo que no se afirma que exista red privada AWS–Azure.
- El estado provisional de rúbrica anterior no se considera verificado para
  este corte: la disponibilidad pública del portal falló y la conectividad
  privada aún no existe. Debe reevaluarse tras recuperar los destinos del ALB.

## Seguimiento — 13:15 America/Chicago

Auto Scaling recuperó el portal sin cambios manuales: ahora hay 2/2 instancias
`InService`/`Healthy`, 2/2 destinos ALB sanos, y `/`, `/health` y `/ready`
responden HTTP 200. Ocho GET de `/health` alternaron entre ambas instancias y
mostraron `database=ok`. El 503 anterior fue transitorio. Las alarmas de
CloudWatch están `OK`, aunque sin datapoints y con faltantes tratados como
`NonBreaching`; eso debe corregirse para que la señal sea fiable. La salud
recuperada no completa la VPN ni cambia por sí sola la puntuación de rúbrica.
Se validó la plantilla AWS local con CloudFormation. El change set de la mejora
de métricas reveló cambios adicionales a `LaunchTemplate` y `ScalingPolicy`,
con reemplazo condicional del ASG; se eliminó sin ejecutarlo para preservar la
capacidad sana mientras se reconcilia IaC.

## Seguimiento — 13/10/2026, 15:57 America/Chicago

- AWS: el stack `tangamandapio-live-20261013` permanece `UPDATE_COMPLETE`;
  2/2 destinos del ALB están `healthy` y `/health` respondió 200 con
  `database=ok`.
- RDS: `tangamandapio-postgres` está `available`, privado y cifrado. La
  repetición PT-DR-01 verificó marcador SQL y conteos iguales en la copia;
  RTO=289 s y RPO superior observado=14 s. Limpieza verificada: no quedan
  `tng-dr-restore-*` ni `tng-dr-snap-*`; la base y el snapshot fuente se
  conservaron.
- Azure: `/api/health` respondió HTTP 200.
- Dominio/TLS: `list-hosted-zones` no devolvió zonas Route 53. El rol de AWS
  Academy denegó `cloudfront:ListDistributions`; no se creó una distribución.
  El ALB público continúa HTTP-only, sin dominio ni certificado. CloudFormation
  ya soporta `CertificateArn` opcional, HTTPS/443, redirección HTTP→HTTPS y
  cookie segura, pero no es posible emitir un certificado para un dominio que
  aún no se controla.
- Rúbrica: la rúbrica final XLSX contiene 14 criterios/20 puntos; no enumera
  dominio/HTTPS como criterio separado. El criterio 5 requiere cifrado y
  seguridad de red; el 12 requiere pruebas de seguridad y conectividad. HTTPS
  válido fortalecería ambas evidencias, pero no suma puntos automáticos. El
  DOCX de cinco categorías corresponde solo al Entregable 1.

## Revalidación — 13/10/2026, 16:12 America/Chicago

AWS STS y Azure for Students autenticaron. El portal quedó operativo tras un
change set revisado que modificó únicamente `HighCPUAlarm`, sin reemplazos:
periodo 300 s, dos de dos períodos y datos ausentes como indeterminados.
CloudFormation terminó `UPDATE_COMPLETE`. Después, ALB `/health` respondió 200
y el target group mostró 2/2 `healthy`; Azure Function `/api/health` respondió
200. Cuatro endpoints de negocio sin sesión devolvieron 401.

RDS quedó confirmado `available`, privado, cifrado, Single-AZ y con un día de
retención. Los dos buckets de archivos reportaron AES256. Las acciones de la
alarma están habilitadas, pero no hay destinos SNS suscritos; no se envía correo.
La matriz autenticada de roles no se repitió porque producción exige cambio de
contraseña admin (428); no se evitó esa protección.

La validación local terminó `QUALITY_GATE=APROBADA` con 98 pruebas unitarias,
build frontend, auditoría limpia, validación CloudFormation/Terraform y cinco
tests mock de red/costo. La integración AWS→Azure por HTTPS público está
demostrada por el E2E desde EC2 a las 02:32. No hay VPN, VNet ni ruta privada;
queda aplazada al final por la denegación AWS Academy a
`ec2:CreateCustomerGateway`. Véase [detalle operativo](aws/AWS-OBSERVABILIDAD-2026-10-13.md).

## Seguimiento de alertas — 13/10/2026, 16:23 America/Chicago

Se configuró el tema SNS de CloudFormation con las dos direcciones de correo
proporcionadas por el usuario. La pila terminó `UPDATE_COMPLETE`; un change set
previo a la ejecución mostró únicamente el tema y las cinco alarmas, sin
reemplazos. SNS lista dos suscripciones confirmadas y cada alarma tiene una
acción SNS. La detección de drift terminó `IN_SYNC`, cero recursos drifted. No
se envió correo de prueba. Después del cambio, `/health` AWS siguió 200, el
target group mantuvo 2/2 destinos sanos y Azure `/api/health` siguió 200.
Véase [evidencia operativa](aws/AWS-OBSERVABILIDAD-2026-10-13.md).
