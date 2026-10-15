# Despliegue AWS y comprobación del portal — 13/10/2026

## Roll forward del release v4 — 13/10/2026, 22:47 America/Chicago

Se actualizó el perfil local `default` con la sesión temporal entregada y STS
autenticó. Antes de desplegar, CloudFormation reportó la pila
`tangamandapio-live-20261013` estable y `IN_SYNC`; el detalle de recursos no
mostró elementos `MODIFIED`, `DELETED` ni `NOT_CHECKED`. El change set revisado
modificó seis recursos: Launch Template, Auto Scaling Group, Scaling Policy,
dos alarmas y dashboard. No propuso cambiar RDS, buckets ni borrar recursos.

Se publicó el release inmutable
`20261013-admin-alarm-rbac-metrics-v4-python312`, SHA-256
`00b1ea3faf123d603d368ddc8c6f777b53fc9e9964352abfb4039b7c1b026e23`, en el
bucket privado con SSE-S3 AES256, versionado y tamaño 18,180,462 bytes. La pila
terminó `UPDATE_COMPLETE`; la detección posterior quedó `IN_SYNC`, cero recursos
drifteados. El ASG volvió a desired/min 2, max 4; los dos nodos nuevos quedaron
`InService/Healthy` en AZ distintas y el target group finalizó 2/2 `healthy`.

La verificación de solo lectura vía SSM en ambas instancias confirmó la misma
revisión y SHA-256, servicio `tangamandapio` activo y archivos ERP/admin
presentes. Por el ALB, `/health` y `/ready` respondieron HTTP 200;
`/administracion` redirigió al login sin sesión (303), las APIs de usuarios y
suscripciones de alarmas devolvieron 401 sin sesión, y el CSS del panel admin
respondió 200. Esto valida despliegue y barrera anónima, no una sesión
administrativa autenticada ni la matriz completa de permisos en navegador.

RDS siguió `available`, Single-AZ y con retención de un día; los parámetros
`DatabaseMultiAZ=false` y `DatabaseBackupRetentionDays=1` se preservaron. Azure
Function `/api/health` respondió HTTP 200 en el corte posterior, aunque la
consulta ARM de solo lectura se atascó y se cerró; no se infiere de ese health
la ejecución actual del worker. No se configuró HTTPS/dominio ni VPN privada.

## Resultado — 01:14 America/Chicago

- El perfil local `default` autenticó con STS usando la sesión temporal nueva.
- CloudFormation `tangamandapio-live-20261013` terminó `UPDATE_COMPLETE`.
  La última detección de drift terminó `IN_SYNC`.
- El ALB `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` devolvió
  HTTP 200 en `/health` y `/`. El endpoint `/health` informó `database: ok`.
- Dos instancias `t3.micro`, una en `us-east-1a` y otra en `us-east-1b`, quedaron
  `InService`/`Healthy` en Auto Scaling y `healthy` en el target group. Una sonda
  SSM independiente en ambas devolvió `/health` 200 y `/ready` `ready`, ambas
  con dependencia PostgreSQL `ok`.
- RDS `tangamandapio-postgres` está `available`, PostgreSQL 18.3, clase
  `db.t3.micro`, cifrado, privado, Single-AZ y retención automática de un día.
  El secreto maestro administrado por RDS figura `active`; no se leyó su valor.
- El artefacto publicado es la revisión
  `20261012-rds-managed-secret-runtime`, en el bucket de artefactos privado.

## Revalidación de integración — 01:23 America/Chicago

Desde una instancia EC2, el perfil de instancia pudo leer en memoria el secreto
`tangamandapio/azure/function-key` y llamar
`https://tangama-wms-261008.azurewebsites.net/api/wms/inventory`; Azure devolvió
HTTP 401 (sin crear ni cambiar datos). El endpoint `/api/health` de la misma
Function App devolvió HTTP 200. Por tanto hay salida de red hacia Azure, pero
la llamada autenticada del portal no funciona con la clave guardada actualmente
en AWS. La consulta de solo lectura de claves de Azure (`listkeys`) se quedó
esperando y se canceló; no se expuso ni rotó ninguna clave. El evento AWS→Azure
de negocio queda sin validar hasta reconciliar de forma segura esa clave.

## Prueba controlada de recuperación del cómputo — 01:49 America/Chicago

Se verificó que el perfil `default` contiene el identificador de clave
entregado para esta sesión (sin imprimirlo) y STS lo aceptó. Como prueba de
tolerancia a falla, se terminó de forma controlada una instancia EC2 del ASG
sin reducir la capacidad deseada. En la verificación posterior, el ASG volvió
a tener sus dos instancias deseadas `InService`/`Healthy`, una por zona
(`us-east-1a` y `us-east-1b`); el target group tenía dos destinos `healthy` y
uno anterior aún en `draining`. El ALB siguió respondiendo `/health` con
`status: ok` y `database: ok`. La actividad de reemplazo figura `Successful`.

Esto demuestra reemplazo automático del nodo y recuperación del servicio web
en la comprobación posterior; no se cronometró un RTO exacto ni se midió una
prueba de escalado por carga. El destino antiguo seguía drenando al tomar el
estado. En una verificación final a las 01:51, el estado de drenaje había
terminado: ASG `desired=2`, `InService=2`, `Terminating=0`; target group con
`healthy=2`, `draining=0`, `unhealthy=0`; ALB `/health` continuó en `ok` con
base `ok`.

## Reconciliación AWS–Azure y E2E — 02:32 America/Chicago

La consulta de claves Azure permitió comparar valores sin imprimirlos: la clave
vigente de Function no coincidía con la guardada en
`tangamandapio/azure/function-key`. Se verificó la clave Azure por HTTP 200 y
se creó una nueva versión del secreto AWS. El `StartInstanceRefresh` solicitado
fue denegado por una SCP de AWS Academy; se reemplazaron las dos EC2 una por
una mediante el ASG, esperando salud y drenaje completos antes de cada cambio.
Desde el entorno de proceso de cada instancia nueva, `GET /api/wms/inventory`
respondió 200.

El artefacto AWS desplegado ejecutó un E2E sobre SQLite temporal dentro de EC2:
outbox `delivered`/Azure `queued`, venta `demo_fulfillment_completed`, recepción
compensatoria `demo_restock_completed` y stock ficticio **24 → 23 → 24**. El
SQLite temporal se eliminó y no se escribieron pedidos en RDS; Azure conserva
los blobs de los eventos sintéticos. IDs y alcance completos en
[evidencia de interoperabilidad](../azure/AZURE-AWS-INTEROP-2026-10-13.md).

El endpoint `/api/wms/inventory` del portal de producción contestó HTTP 428
`password_change_required` al usar la cuenta administrativa. No se omitió ese
control ni se cambió la contraseña.

Se revisó el change set antes de aplicarlo. Un change set diagnóstico que habría
revertido parámetros omitidos a sus valores por defecto proponía reemplazar RDS;
se eliminó sin ejecutarlo. El change set final preservó explícitamente los
parámetros no modificados, no incluyó cambios en RDS ni acciones de eliminación,
y solo actualizó el Auto Scaling Group, el Launch Template y dependencias de
observabilidad. La base existente no fue reemplazada.

## Límites y pendientes

- El ALB sirve por HTTP; no hay dominio propio ni certificado HTTPS configurado.
- La base desplegada conserva el perfil de bajo costo: Single-AZ y un día de
  backups. La prueba de restauración temporal previa no comparó datos ni midió
  RTO/RPO.
- No se desplegó una VNet/VPN privada AWS–Azure. El evento E2E autenticado pasó
  por HTTPS público; no demuestra conectividad privada multinube.
- El WMS Azure sigue siendo un ledger/flujo demostrativo; no descuenta inventario
  de un WMS empresarial real.
- La ruta de inventario con sesión administrativa de producción sigue bloqueada
  hasta que el usuario cambie la contraseña temporal (`428`). No se repitieron
  pruebas completas de roles en navegador, voz WebRTC o grabación.

No se guardaron credenciales, secretos ni capturas de consola en este registro.
En el corte de 02:32, ALB/EC2/RDS estaban activos y consumían recursos mientras
el laboratorio permaneciera encendido. La revalidación posterior de 03:19 no
pudo confirmar ese inventario y no debe interpretarse como estado vigente.

## Revalidación posterior — 03:19 America/Chicago

El token nuevo fue aplicado al perfil local `default` y AWS STS autenticó. Sin
embargo, `ListStacks`, `DescribeInstances`, `DescribeLoadBalancers` y
`DescribeDBInstances` fueron denegados por la política explícita
`voc-cancel-cred`. El DNS del ALB no resolvió en una consulta externa. Por tanto,
las observaciones de salud anteriores a 03:19 son históricas y el despliegue no
está confirmado como operativo en este corte. AWS Academy mostró el entorno
`Ready`, aunque el panel de AWS Details indicaba “No running instance”. No se
realizó ningún cambio de recursos. Véase [la revalidación STS](AWS-REVALIDACION-STS-2026-10-13.md).

## Revalidación posterior — 02:58 America/Chicago

La identidad STS continuó autenticando, pero `ec2:DescribeInstances`,
`cloudformation:DescribeStacks` y las lecturas/eliminación RDS fueron denegadas
explícitamente por `voc-cancel-cred`. En paralelo, la comprobación pública del
ALB devolvió HTTP 503 en `/` y `/health`. Por ello, las comprobaciones 200 y
`UPDATE_COMPLETE` anteriores son históricas; el estado actual de targets,
stack y RDS no pudo consultarse y el portal AWS no debe presentarse como
saludable en este corte. No se intentó reparar ni reemplazar recursos con el
permiso denegado. La evidencia más reciente y los dos recursos de restore con
limpieza pendiente están en [la revalidación del estado](../REVALIDACION_ESTADO_2026-10-13.md)
y [el informe de restore RDS](AWS-DR-RESTORE-2026-10-13.md).

## Revalidación viva posterior — 13/10/2026, 16:12 America/Chicago

Este corte supersede las revalidaciones históricas de 02:58/03:19 anteriores.
AWS STS autentica y CloudFormation está `UPDATE_COMPLETE`. El último change set
inspeccionado modificó solamente `HighCPUAlarm`, sin reemplazo; el ALB
`/health` devolvió HTTP 200 y el target group tenía 2/2 destinos `healthy`.
RDS fue revalidada `available`, privada y cifrada. Los dos buckets del stack
reportaron AES256. Azure Function `/api/health` devolvió HTTP 200. Los detalles
de seguridad, pruebas locales y alcance de alertas están en
[AWS-OBSERVABILIDAD-2026-10-13.md](AWS-OBSERVABILIDAD-2026-10-13.md).

## Seguimiento de alertas — 13/10/2026, 16:23 America/Chicago

Un change set revisado añadió el tema SNS de alertas y conectó las cinco
alarmas. No propuso reemplazos. AWS lista dos suscripciones confirmadas; no se
envió un mensaje artificial. El stack quedó `UPDATE_COMPLETE` y luego
`IN_SYNC` con cero drift; el ALB siguió con 2/2 destinos sanos. Véase la
[evidencia de observabilidad](AWS-OBSERVABILIDAD-2026-10-13.md).
