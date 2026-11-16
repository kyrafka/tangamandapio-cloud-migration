# Estado real de Tangamandapio — 16 de noviembre de 2026

Este registro refleja consultas hechas a AWS y Azure el 16/11/2026. Reemplaza
como estado actual a los registros de AWS Academy y a las pruebas locales
anteriores. No contiene valores de secretos.

## Reconsulta complementaria — 16/11/2026, 21:00 UTC

- AWS `main` confirmó la cuenta `481056890449` mediante STS y el rol
  `AccountFullAccessRole`. El plan Free está `ACTIVE`, con USD 158,62
  disponibles de los USD 200 iniciales; la diferencia consumida del crédito es
  USD 41,38. Cost Explorer devolvió USD 0 para octubre y noviembre, aunque el
  saldo del plan disminuyó. La llamada `billing:GetCredits` fue denegada por
  una SCP explícita de AWS Organizations; no se pudo obtener el desglose de
  créditos/cargos por servicio. El budget AWS de USD 200 termina el 07/12/2026
  y notifica, no detiene recursos.
- Azure `Azure for Students` tiene crédito activo de USD 100 y saldo cerrado
  USD 92,95 (USD 7,05 consumidos según el último cierre; vence 25/09/2027).
  Cost Management reportó USD 6,842993 de costo real Month-to-Date en noviembre,
  de los cuales USD 6,790430 corresponden a `rg-tangama-private-network`.
  Estos importes tienen cortes distintos; el saldo de crédito es posterior al
  último cierre, y la consulta de costos puede retrasarse. El lote de alta
  antiguo de USD 200 expiró el 04/08/2026 con saldo cero. Azure no devuelve
  budgets configurados para esta suscripción.
- En CloudFormation no existe `tangamandapio-aws-azure-tailscale-ha`; las
  cuatro tablas de rutas consultadas en el VPC no incluyen
  `10.20.1.4/32`. No hay router AWS desplegado ni claves Tailscale disponibles.
  No se probó pedido privado ni se detuvo router alguno.
- ACM está `ISSUED`; los listeners actuales usan HTTPS/443 hacia la aplicación
  y HTTP/80 redirige a HTTPS. El usuario informó que desplegó en Cloudflare la
  regla `Full (strict)` limitada al hostname. Falta repetir comprobación HTTPS
  pública completa desde cliente.
- SNS: `josedario.zuniga@gmail.com` está confirmado; la suscripción UPeU aparece
  dos veces `PendingConfirmation`. La recepción real de una alarma de prueba no
  está demostrada.
- Evidencia de créditos y costos: `evidence/current/COST-CREDIT-RECHECK-2026-11-16-2100.json`.
- Esta reconsulta fue de solo lectura; no cambió recursos cloud.

## Reconsulta anterior de solo lectura — 16/11/2026, 15:09 UTC (superada)

- AWS STS volvió a autenticar la cuenta `481056890449`; la pila
  `tangamandapio-live-20261116` seguía `UPDATE_COMPLETE` y su último cambio
  `IN_SYNC`. No se modificó infraestructura en esta reconsulta.
- ASG `tangamandapio-asg`: min 2 / deseado 2 / max 5; dos instancias
  `Healthy`/`InService` en `us-east-2a` y `us-east-2b`. ALB activo; listener
  único HTTP/80, grupo de destino HTTP/8080 y health check `/health`; dos
  destinos sanos en la comprobación consolidada anterior.
- RDS `tangamandapio-postgres`: PostgreSQL 18.3, `db.t3.micro`, 20 GiB,
  `available`, cifrada, privada, Single-AZ en `us-east-2b`, retención de un
  día. No se aplicó el cambio local de defaults del template al stack vivo.
- Las tres tablas de rutas del stack no contienen una ruta `10.20.1.4/32`;
  por tanto, este corte no acredita camino desde la VPC AWS al Private
  Endpoint. El listener de origen sigue HTTP/80.
- Las cinco alarmas propias seguían `OK` y cada una conserva acción SNS. La
  consulta de las 15:09 UTC informó una suscripción de correo en
  `PendingConfirmation`; la consulta ampliada de las 18:12 UTC encontró dos.
- Cost Explorer y el presupuesto informaron USD 0 registrados al consultar el
  periodo 01–16/11, con USD 200 como umbral de presupuesto. AWS puede demorar
  el registro de cargos: no equivale a gasto final cero ni a límite de gasto.
  El saldo de créditos registrado en el corte previo fue USD 160; no se volvió
  a consultar el saldo de créditos en esta reconsulta.
- Azure CLI volvió a mostrar las dos VMs Tailscale en `Running`, tamaño
  `Standard_B2pts_v2`, con IP privadas `10.20.0.4` y `10.20.0.5`, ambas en
  West US. `vnet-tangama-private` conserva `10.20.0.0/16`; subredes consultadas:
  `snet-private-workloads` `10.20.0.0/24`, `snet-private-endpoints`
  `10.20.1.0/24`, `snet-flex-functions` `10.20.2.0/27` y `GatewaySubnet`
  `10.20.255.0/27`.
- Cambio local únicamente: CloudFormation ahora usa Single-AZ y un día de
  retención como valores por defecto; `cfn-lint` y las cinco pruebas de
  `test_ha_waf_defaults.py` pasan. No se ejecutó un Change Set ni `apply`.

## AWS — cuenta nueva

- Cuenta consultada: `481056890449`; región `us-east-2`.
- El perfil local `main` autentica en esta cuenta y el ARN consultado es un rol
  de acceso completo de la cuenta `481056890449`. Esta es la cuenta donde se
  han reconstruido los recursos actuales. No reutilizar IDs de cuentas antiguas
  ni de AWS Academy para describir este despliegue.
- CloudFormation `tangamandapio-live-20261116`: `UPDATE_COMPLETE`.
- CloudFormation `tangamandapio-voice-recordings`: `CREATE_COMPLETE`.
- Portal: `https://tangamandapio.kendellnm.me` respondió HTTP 200 en la
  comprobación pública del 16/11. `/health` y `/ready` también respondieron 200.
  Cloudflare está en modo `Flexible`; el ALB de origen aún solo tiene listener
  HTTP 80. Ya se solicitó el certificado ACM
  `dd53a568-5413-4140-bb26-9d6c566c7539`, pero sigue `PENDING_VALIDATION` porque
  falta crear el CNAME DNS-only de validación en Cloudflare. No cambiar el DNS
  del portal ni el modo SSL global mientras falta ese registro. Cuando ACM
  quede `ISSUED`, añadir HTTPS al ALB y una regla SSL `Full (strict)` limitada
  a `tangamandapio.kendellnm.me`.
- `/health` y `/ready` en el ALB respondieron HTTP 200.
- ASG `tangamandapio-asg`: mínimo 2, deseado 2, máximo 5. Tras la prueba, las
  políticas redujeron automáticamente 5→4→3→2 entre 12:18:48 y 12:20:39 UTC.
  La consulta final encontró dos instancias `InService`/`Healthy`, dos destinos
  `healthy`, y ninguna instancia extra. No se cambió la capacidad a mano. La
  detección de deriva posterior terminó `IN_SYNC`, con cero recursos desviados
  y `/DesiredCapacity=2`.
- Políticas de escalado: CPU promedio objetivo 60% y 2.500 solicitudes por
  destino por periodo de un minuto. La prueba HTTP anterior envió 21.600
  solicitudes/240 s y demostró el cambio automático 2→3. En la prueba larga del
  16/11 se enviaron 300.000 solicitudes al ALB durante 1.645,443 s con
  concurrencia 50. El p95 fue 315,47 ms y el promedio 273,63 ms; hubo 295.593
  HTTP 200, 8 HTTP 502 y 4.399 errores de red (1,47%), por lo que falló el
  umbral de errores de 1% aunque la latencia estuvo bajo el objetivo de 5 s.
  Auto Scaling registró el crecimiento automático 2→4 a las 11:42:14 UTC y
  4→5 a las 11:44:14 UTC, ambos a partir de la alarma
  `RequestCountPerTarget`; las cinco instancias y destinos quedaron sanos.
  Una comprobación posterior con WAF normal, 3.000 solicitudes y concurrencia
  30 dio 3.000 HTTP 200, cero errores y p95 263,86 ms. Los 4.276 errores
  `URLError` de la carga larga no guardaron el motivo detallado; no se atribuyen
  todavía a la aplicación ni al equipo local. El ensayo no valida 3.000 usuarios
  ni RTO de cinco segundos. Después, la reducción automática volvió a 2; la
  prueba no cambió `DesiredCapacity` manualmente. La consulta final a las
  12:40 UTC confirmó dos instancias `InService`/`Healthy` y dos destinos
  `healthy`.
- RDS PostgreSQL `tangamandapio-postgres`: `available`, PostgreSQL 18.3,
  `db.t3.micro`, 20 GiB, cifrado, privada, una zona de disponibilidad y
  retención de un día. La pila viva conserva `DatabaseMultiAZ=false` y
  `DatabaseBackupRetentionDays=1`. No se cambió el plan de facturación.
- No hay planes de AWS Backup. No se ha implementado la exportación cifrada de
  PostgreSQL a Azure Blob ni se ha restaurado una copia aislada.
- WAF está asociado al ALB. Los buckets de artefactos, archivos y grabaciones
  tienen cifrado AES256, versionado y los cuatro bloqueos de acceso público.
- Las cinco alarmas propias de CloudWatch están en `OK` y cada una tiene una
  acción SNS. El ASG publica eventos de lanzamiento, error de lanzamiento,
  terminación y error de terminación en `tangamandapio-alarms`. Durante la
  prueba de capacidad, CloudWatch registró siete publicaciones en el tema; la
  prueba de escalado por tráfico añadió otras dos (lanzamiento y terminación).
  La suscripción de correo sigue en `PendingConfirmation`, por lo que AWS
  publica los eventos pero todavía no entrega el correo a esa dirección. El
  usuario debe confirmar el mensaje de AWS; hasta entonces no se afirma que
  llegue una notificación humana.
- La consulta de las 12:35 UTC volvió a mostrar las cinco alarmas en `OK` y la
  suscripción SNS de correo en `PendingConfirmation`.
- Durante la prueba larga, CloudFormation elevó temporalmente el límite por IP
  del WAF a 90.000 por cinco minutos. Al finalizar, el stack volvió a
  `UPDATE_COMPLETE` con el valor habitual de 30.000; la prueba breve posterior
  pasó con ese límite.
- Terraform 1.16.2 pasó `fmt -check -recursive` para `iac/environments`; el root
  `azure-rebuild` pasó `init -backend=false` y `validate` con azurerm 3.117.1.
  No se ejecutó un plan ni `apply` de Terraform.
- La suite local `tests/iac` terminó con 89 pruebas aprobadas. Se agregó
  `cryptography` al manifiesto y lock de CI porque la prueba del módulo de
  cifrado dependía de ella; la dependencia de ejecución se instaló en un
  entorno temporal, sin cambiar el Python global.
- El presupuesto `Tangamandapio-3weeks-USD200-20261116` cubre del 16/11 al
  07/12/2026, con avisos al 50%, 75%, 90% y 100%. Su gasto registrado aparece
  en USD 0. Cost Explorer también informa USD 0; los cargos y presupuestos de
  AWS pueden actualizarse con retraso, así que este valor no prueba que el uso
  acumulado real sea cero.
- Billing muestra USD 160 de créditos restantes y USD 0 utilizado: USD 100 de
  Free Tier y tres créditos de Explore AWS de USD 20 (EC2, RDS y presupuesto).
  Quedan hasta USD 40 adicionales de actividades sin ganar. El plan Free muestra
  182 días restantes, hasta el 15/05/2027.
- La base de datos nueva no contiene una migración de datos de la cuenta vieja;
  el portal parte de datos de demostración/sintéticos.
- Se eliminó la pila temporal de comprobación `tangama-access-probe-20261116-c386cf`;
  solo contenía un `WaitConditionHandle`.

## Azure y Tailscale

- Suscripción `Azure for Students`.
- Function `tangama-flex-261104` está `Running`; su Private Endpoint está
  `Succeeded` y la conexión aprobada apunta a `10.20.1.4`.
- Los routers `vm-tangama-ts-pilot` (`10.20.0.4`) y
  `vm-tangama-ts-backup` (`10.20.0.5`) están encendidos. Ambos anuncian la ruta
  Tailscale `10.20.1.0/24`.
- Se corrigió un bucle de rutas en ambos routers: estaban aceptando por
  Tailscale la ruta de la misma subred privada que sirven. `tailscale set
  --accept-routes=false` dejó que Azure use su ruta VNet local. Después de la
  corrección, las pruebas desde ambos routers alcanzaron el hostname de la
  Function con HTTP 200; desde el respaldo se midieron 2.01 s.
- La Function de salud responde por su Private Endpoint desde Azure. Esto aún
  no demuestra un pedido desde el portal AWS: el VPC de AWS no tiene ruta a
  `10.20.1.4/32`, no hay zona privada Route 53 para el hostname, y falta el
  secreto de alta Tailscale `tangamandapio/tailscale/auth-key` en Secrets
  Manager. No se ha probado el failover desde un cliente AWS ni un pedido
  completo por la ruta privada.
- La Function Flex tiene `publicNetworkAccess=Disabled`, como corresponde al
  diseño privado. El intento desde una EC2 a la URL pública devolvió HTTP 403;
  no valida la ruta privada. La comparación, sin mostrar ni guardar valores,
  confirmó que el secreto AWS `tangamandapio/azure/function-key` coincide con la
  clave `default` de `receive_fulfillment_event`, usada en
  `/api/fulfillment/events`. No coincide con `demo_inventory` ni con la clave
  de host; no usarlo para `/api/wms/inventory`. La autenticación del evento no
  se ha probado desde AWS porque falta la ruta privada.
- Application Insights `tangama-wms-ai` está enlazado a la Function Flex y al
  workspace `tangama-ops-law`, con retención de 30 días. La consulta de
  solicitudes de la última hora devolvió cero registros; todavía no hay
  evidencia de telemetría de una petición privada reciente.
- El grupo `tangama-ops-ag` está habilitado y tiene dos receptores de correo
  configurados. Se desplegaron dos alertas de consulta de logs en español,
  conectadas a ese grupo: `tangama-flex-5xx-es` (HTTP 5xx, ventana 5 min,
  severidad 2) y `tangama-flex-latencia-es` (promedio >5.000 ms, ventana 15
  min, severidad 3). Las reglas están habilitadas, pero aún no han sido
  disparadas ni se ha confirmado una entrega de correo.
- `tangama-wms-261030` aparece `Stopped`; la Function activa es
  `tangama-flex-261104`.
- Las dos alertas métricas antiguas (`tangama-wms-fn-5xx` y
  `tangama-wms-fn-latency`) apuntaban a la Function detenida y no tenían grupo
  de acciones; quedaron deshabilitadas. La definición repetible de las nuevas
  reglas está en `iac/azure-monitoring/function-alerts.json`.
- El Storage Account `sttangama261030r` está en West US. Existen las colas
  `fulfillment-events` y `fulfillment-events-poison`. El contenedor privado
  `tangama-postgres-backups` tiene una política de ciclo de vida que elimina
  objetos bajo `postgres/` después de 30 días. Su objeto más reciente es
  `postgres/20261105-manual-validation.json` (86.362 bytes, 05/11 14:43 UTC);
  es una evidencia manual antigua, no una copia nueva generada automáticamente
  ni una restauración verificada de la RDS de la cuenta actual.
- No hay un Azure VPN Gateway Site-to-Site. La conexión existente usa los dos
  routers Tailscale indicados.

## Evidencia adicional de escalado automático

La prueba de tráfico al ALB está registrada en
`evidence/current/aws/AWS-ASG-TRAFFIC-SCALEOUT-2026-11-16.json`. El cambio
automático 2→3 fue confirmado en las actividades del ASG; no se cambió a mano.
La alarma volvió a `OK` cuando el tráfico se detuvo. A las 10:13:25 UTC se
ordenó bajar capacidad a 2 y retirar la instancia de prueba; terminó a las
10:19:07 UTC tras el drenaje de ALB. AWS confirmó `DesiredCapacity=2`, dos
instancias y destinos saludables, `/health` y `/ready` en HTTP 200 y CloudFormation
`IN_SYNC`. Ese primer ensayo anterior redujo capacidad manualmente; el ensayo
posterior del 16/11 sí confirmó scale-in automático 5→2.

### Prueba de carga hasta cinco instancias — 16/11/2026

La ejecución larga está en
`evidence/current/aws/AWS-ASG-SCALE-2-5-2026-11-16-http.json`: 300.000
solicitudes, 50 concurrentes, 1.645,443 segundos, p95 315,47 ms y 1,47% de
errores. Auto Scaling confirmó 2→4 y 4→5 sin cambiar la capacidad a mano. El
umbral de errores de 1% no se cumplió. La comprobación posterior está en
`evidence/current/aws/AWS-ASG-SCALE-POSTCHECK-2026-11-16-http.json`: 3.000
solicitudes, 30 concurrentes, p95 263,86 ms y cero errores. La carga larga
solo guardó clase de error (`URLError`) y no su causa, así que la causa queda
sin confirmar. Después el ASG redujo automáticamente 5→4→3→2; la bitácora de
Auto Scaling registra los tres pasos como exitosos y CloudFormation detectó
`IN_SYNC`/0. El WAF volvió a 30.000 por cinco minutos tras la carga.
El 16/11 a las 12:36 UTC se repitió la detección de deriva y volvió a terminar
`IN_SYNC`, con cero recursos desviados. La captura consolidada del ASG, los
destinos, las alarmas y las dos pruebas está en
`evidence/current/aws/AWS-ASG-SCALE-2-5-2026-11-16-cloud.json`.

## Siguientes pasos operativos

1. Crear una clave de alta Tailscale de corta duración, preautorizada para
   `tag:tangama-aws-router`; guardarla directamente en AWS Secrets Manager como
   `tangamandapio/tailscale/auth-key`. No enviar la clave por chat.
2. Desplegar con IaC los dos routers AWS, la ruta privada de aplicación y el
   DNS privado; enrolar ambos routers y validar con un pedido sintético que
   llegue a la Function y sus recursos Queue, Blob y Application Insights.
3. Confirmar la suscripción SNS desde el correo. La configuración ya publica
   los eventos del ASG; la entrega individual queda pendiente de confirmación.
4. El escalado automático bajo carga ya llegó a 5 (2→4→5) y volvió solo a 2
   (5→4→3→2). La prueba larga superó el umbral de error en 0,47 puntos
   porcentuales; investigar por qué el cliente registró errores de red antes de
   presentar esa carga como aprobada. Confirmar SNS desde el correo para
   habilitar la entrega humana.
5. Probar la conmutación de routers desde AWS y medir el RTO; no afirmar
   recuperación máxima de cinco segundos hasta medirla.
6. Implementar y probar copia cifrada PostgreSQL→Azure Blob y restauración en
   un entorno aislado. Mantener RDS Single-AZ mientras el plan Free impida
   Multi-AZ.
7. Crear más adelante en Cloudflare el CNAME de validación ACM que aparece a
   continuación; cuando ACM muestre `ISSUED`, activar HTTPS de origen y `Full
   (strict)` solo para el hostname del portal.
8. Reconciliar las raíces Terraform con este despliegue CloudFormation antes
   de ejecutar Terraform en la cuenta nueva. No se ha aplicado Terraform allí.

### CNAME de validación ACM pendiente en Cloudflare

Crear como `CNAME`, modo `DNS only`:

- Nombre: `_7408575772140ac4b6bcd8e3ab10a8ca.tangamandapio`
- Destino: `_694a9f814a3985f9576fb181841dc9d3.wzccmgtwzk.acm-validations.aws`

El usuario pidió dejar este paso para después. No reemplazar ni editar el
registro DNS actual del portal.

## Costos y límites observados

El presupuesto de USD 200 es un umbral de notificación, no un corte automático
de recursos. La consola de AWS documenta que Budgets puede retrasarse respecto
del uso facturable. El saldo consultado en créditos sí fue USD 160, no USD 200;
el crédito promocional restante solo subirá si se completan otras actividades
elegibles. No habilitar el plan Paid ni crear recursos adicionales de costo
relevante sin volver a comprobar saldo, gasto y previsión.

## Reconsulta ampliada — 16/11/2026, 18:12 UTC

- AWS CLI `main` se renovó con `aws login --profile main --region us-east-2`.
  STS confirmó la cuenta `481056890449` y el rol
  `arn:aws:sts::481056890449:assumed-role/AccountFullAccessRole/...`.
- EC2 `DescribeInstances` sin filtros en `us-east-2` devolvió únicamente las
  dos instancias `tangamandapio-app` en `10.10.10.160` y `10.10.11.91`.
  No se encontró un router AWS en esa región. Cinco tablas de rutas fueron
  consultadas; ninguna tiene `10.20.1.4/32`. RDS está `available` (PostgreSQL
  18.3, Single-AZ, retención 1), ALB `active`, y el stack
  `tangamandapio-live-20261116` sigue `UPDATE_COMPLETE`; los parámetros vivos
  siguen `DatabaseMultiAZ=false` y `DatabaseBackupRetentionDays=1`.
- La búsqueda de metadatos en Secrets Manager no devolvió secretos cuyo nombre
  contenga `tailscale`. No se consultó ni mostró ningún valor secreto.
- La consulta de `DescribeInstances` en `us-west-2` fue denegada por un `explicit
  deny` de la SCP `p-4lylrj0n` en AWS Organizations `976848034062`. La cuenta
  `481056890449` no pudo leer el contenido de esa política con
  `organizations:DescribePolicy`. No se afirma que no existan instancias en
  otras regiones; solo se verificó el inventario de `us-east-2`.
- El cliente Tailscale de esta PC informó `BackendState=NoState`, mapa de pares
  vacío y error al sincronizar con el servidor de coordinación. La salida de
  texto aún enseña nombres antiguos `tangamandapio-aws-20261109-*`; esa caché no
  demuestra que esos equipos estén online ni que sean instancias de la cuenta
  actual.
- Azure CLI confirmó `Azure for Students` habilitada; las VM
  `vm-tangama-ts-pilot` y `vm-tangama-ts-backup` siguen `Running`, con IP
  privadas `10.20.0.4` y `10.20.0.5`.
- ACM sigue `PENDING_VALIDATION` con el CNAME descrito arriba. Las dos
  suscripciones de correo del tema `tangamandapio-alarms` están
  `PendingConfirmation`.
- El presupuesto `Tangamandapio-3weeks-USD200-20261116` tiene límite USD 200
  entre el 16/11 y el 07/12/2026. Cost Explorer muestra USD 0 para noviembre;
  esto puede retrasarse y no es un límite de gasto.
- No se hicieron cambios de infraestructura cloud durante esta reconsulta.
