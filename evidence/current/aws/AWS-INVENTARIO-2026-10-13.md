# Inventario AWS — 13/10/2026

## Revalidación viva — 13/10/2026, 23:00 America/Chicago

Lectura de solo consulta con la sesión temporal actual. STS autenticó; la pila
`tangamandapio-live-20261013` sigue `UPDATE_COMPLETE` y conserva la revisión
`20261013-admin-alarm-rbac-metrics-v4-python312` con SHA-256
`00b1ea3faf123d603d368ddc8c6f777b53fc9e9964352abfb4039b7c1b026e23`. El target
group devolvió 2/2 destinos `healthy`. El ALB respondió `/health` 200,
`/ready` 200, `/administracion` 303 y 401 en ambas APIs admin consultadas sin
sesión. RDS sigue `available`, cifrada, Single-AZ y con un día de retención.
No hubo cambios de recursos en esta revalidación.

Azure se verificó en paralelo: Function `tangama-wms-261008`, en
`rg-tangamandapio-rebuild-wus`, está `Running` y HTTPS-only; el ajuste de
despliegue coincide con SHA-256
`6eea3b6ae6122348360bf26232f196f99bb675913a304cb22a99658495382065` y
`/api/health` respondió 200. El smoke compensado venta/recepción de esta misma
hora pasó desde el proceso local; no equivale a tráfico iniciado en EC2 ni a
conectividad privada entre redes.

## Inventario posterior al release v4 — 13/10/2026, 22:47 America/Chicago

Este es el corte vigente tras publicar la revisión `20261013-admin-alarm-rbac-metrics-v4-python312`.

| Recurso | Estado observado |
|---|---|
| CloudFormation | `tangamandapio-live-20261013`: `UPDATE_COMPLETE`; detección posterior `IN_SYNC`, 0 recursos drifteados. |
| Release | SHA-256 `00b1ea3faf123d603d368ddc8c6f777b53fc9e9964352abfb4039b7c1b026e23`; S3 privado, SSE-S3 AES256, objeto versionado. |
| ALB / target group | ALB activo, solo HTTP; 2 destinos `healthy`. |
| ASG | desired/min 2, max 4; 2/2 instancias `InService/Healthy` en zonas distintas. |
| Instancias | SSM confirmó en ambos nodos la revisión/checksum publicados, servicio activo y archivos ERP/admin. |
| Portal | `/health` y `/ready` 200; panel admin anónimo redirige al login (303), APIs admin sin sesión dan 401 y CSS admin 200. |
| RDS | `tangamandapio-postgres` `available`, `db.t3.micro`, Single-AZ, backup 1 día; configuración no se alteró. |
| Azure | Function `/api/health` HTTP 200 en la última lectura directa; consulta ARM posterior se atascó. |

La puerta local integral pasó con 120 pruebas, auditorías de dependencias,
build frontend y validación/lint de IaC. Estos checks no prueban live cada rol,
correo, WebRTC, WMS físico, conectividad VPN, dominio ni TLS del ALB. Véase el
[detalle del despliegue](AWS-DESPLIEGUE-2026-10-13.md).

## Revalidación de alcance limitado — 18:18 America/Chicago

AWS STS aceptó el perfil `default` en `841113066612`. La lectura de
CloudFormation falló por denegación explícita de la política `voc-cancel-cred`;
no se pudo obtener un inventario autoritativo de stacks, EC2, target groups,
RDS ni change sets en este corte.

El ALB conocido respondió 200 en `/`, `/health` (`database=ok`) y `/ready`.
Las dos rutas de administración esperadas en el candidato actual,
`/administracion` y `/api/admin/alarm-subscriptions`, devolvieron 404 en 12/12
lecturas. No se cambió AWS. Las observaciones de horas anteriores que siguen en
este documento son históricas y no prueban el inventario presente. Ver la
[revalidación completa](../CLOUD-REVALIDATION-2026-10-13.md).

## Revalidación viva — 13:15 America/Chicago

El perfil `default` autenticó por STS en la cuenta académica `841113066612`.
Esta consulta fue de solo lectura; no se desplegó ni modificó infraestructura.

| Recurso | Estado observado |
|---|---|
| CloudFormation | `tangamandapio-live-20261013` en `UPDATE_COMPLETE`. |
| ALB | `tangamandapio-alb` activo, solo HTTP/80; `/`, `/health` y `/ready` responden HTTP 200. |
| Target group | `tangamandapio-tg`: 2/2 destinos `healthy`. |
| ASG | `tangamandapio-asg`: desired 2, min 2, max 4; 2/2 instancias `InService`/`Healthy` en AZ distintas. |
| Recuperación | El corte de 13:08 devolvió 503 y mostró fallos `Client.InternalError`; a las 13:11 el siguiente reemplazo automático tuvo éxito. No se efectuó despliegue manual. |
| RDS | `tangamandapio-postgres` `available`, `db.t3.micro`, Single-AZ, backups 1 día. |
| VPN | No hay conexiones VPN listadas en la región. |

Ocho consultas sucesivas a `/health` respondieron 200 con `database=ok` y
alcanzaron ambas instancias; `/` y `/ready` también respondieron 200. El corte
de 13:08 sí observó 503, pero Auto Scaling lo recuperó por sí solo alrededor de
las 13:11. CloudFormation confirma parámetros `DatabaseMultiAZ=false` y
`DatabaseBackupRetentionDays=1`. No se detectó VPN ni listener HTTPS. La sección
antigua “Estado posterior al despliegue — 01:14” más abajo es histórica y no
representa esta revalidación.

La validación AWS de la plantilla local pasó. Para revisar la mejora de métricas
se preparó y eliminó un change set sin ejecutarlo: además de la alarma/capacidad,
el plan modificaría `LaunchTemplate` y `ScalingPolicy`, con reemplazo
condicional del ASG. No hubo cambio en los recursos vivos; hace falta reconciliar
el launch template antes de volver a preparar un despliegue.

## Estado posterior al despliegue — 01:14 America/Chicago

La sesión local `default` fue aceptada por STS. El stack
`tangamandapio-live-20261013` está `UPDATE_COMPLETE`; CloudFormation drift está
`IN_SYNC`. Inventario comprobado:

| Recurso | Estado actual observado |
|---|---|
| ALB | Activo; HTTP 200 en `/` y `/health`; target group con 2/2 destinos `healthy`. |
| EC2 / ASG | 2 instancias `t3.micro`, ambas `InService`/`Healthy`, en `us-east-1a` y `us-east-1b`; min/desired 2, max 4. |
| Portal / PostgreSQL | `/health` y `/ready` 200 desde ambas instancias; PostgreSQL `ok`. |
| RDS | `tangamandapio-postgres` `available`, PostgreSQL 18.3, `db.t3.micro`, privado, cifrado, Single-AZ, backup 1 día. Secreto administrado `active`, valor no leído. |
| URL | `http://tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com`; sin TLS ni dominio propio. |

La verificación más amplia y sus límites están en
[`AWS-DESPLIEGUE-2026-10-13.md`](AWS-DESPLIEGUE-2026-10-13.md). No hubo prueba
de evento completo desde EC2 hacia Azure, ni se midieron RTO/RPO. WMS continúa
siendo demostrativo.

## Corte previo al despliegue — 00:22 America/Chicago

Región `us-east-1`; credenciales locales en perfil `default`. AWS STS aceptó la
sesión. Las consultas son de solo lectura salvo la prueba temporal documentada
en [AWS-DR-RESTORE-2026-10-13.md](AWS-DR-RESTORE-2026-10-13.md).

| Servicio | Estado observado al corte 00:22 (-05:00) |
|---|---|
| CloudFormation | Un stack `CREATE_COMPLETE` de AWS Academy; no es el stack del portal. |
| EC2 / ALB | Cero instancias EC2 y cero balanceadores del proyecto. |
| RDS | Cero instancias RDS al terminar la prueba temporal. |
| Snapshot | `tangamandapio-live-20261005-final-20261009192408`: PostgreSQL 18.3, 20 GiB, cifrado, `available`. |
| Subnet groups de prueba | Cero nombres `tng-drtest-*` luego de la limpieza. |
| Secreto de prueba | No quedó secreto con nombre `tng-drrestore*` ni `tangamandapio/rds*` luego de la limpieza. |

Durante la prueba RDS se restauró desde ese snapshot como `db.t3.micro`; la copia
quedó privada y cifrada. Tras quedar disponible, el cambio a secreto maestro
administrado por RDS llegó a `active`. La instancia temporal y su subnet group
se eliminaron; el snapshot fuente se preservó. No se consultaron filas/tablas,
por lo que los datos lógicos y RTO/RPO no quedan verificados.

No se modificó infraestructura persistente. El inventario no demuestra que el
portal esté desplegado; el único stack activo observado era el de la cuenta
Academy.

## Revalidación viva — 13/10/2026, 16:12 America/Chicago

El stack `tangamandapio-live-20261013` quedó `UPDATE_COMPLETE`; el target group
mostró 2/2 destinos `healthy` y el ALB `/health` devolvió HTTP 200. RDS
`tangamandapio-postgres` está `available`, privada, cifrada, Single-AZ y con
backup de un día. Los buckets de artefactos y archivos reportaron AES256. El
listener continúa HTTP/80; no hay listener HTTPS ni dominio. La alarma de CPU
usa periodo 300 s y missing-data `missing`; está habilitada, pero carece de
acciones SNS. La corrección de alarma y su verificación se documentan en
[AWS-OBSERVABILIDAD-2026-10-13.md](AWS-OBSERVABILIDAD-2026-10-13.md).

## Seguimiento — 13/10/2026, 16:23 America/Chicago

Tras configurar notificaciones, CloudFormation volvió a `UPDATE_COMPLETE` y
la detección de drift terminó `IN_SYNC` con cero recursos drifted. Las cinco
alarmas tienen una acción SNS y dos suscripciones de correo confirmadas. No se
envió alerta de prueba. El estado de salud posterior fue ALB 2/2 `healthy`,
`/health` 200 y Azure `/api/health` 200.
