# Prueba aislada de recuperación RDS — 13/10/2026

## Resultado

`tests/aws/pt-dr-snapshot-restore.ps1 -ConfirmCostlyTest -MaxWaitMinutes 30`
terminó con `PT-DR-SNAPSHOT-RESTORE=PASSED` en `us-east-1`.

- Fuente: snapshot manual PostgreSQL 18.3, cifrado, 20 GiB, conservado sin cambios.
- Restauración temporal: clase `db.t3.micro`, privada (`PubliclyAccessible=false`),
  cifrada y ubicada en subredes de dos zonas; sin retención automática adicional.
- Se activó el secreto maestro administrado por RDS después de que la instancia
  restaurada quedó disponible. El estado del secreto llegó a `active`; el valor
  no se leyó ni se imprimió.
- El script eliminó la instancia y el subnet group temporales. Una consulta
  posterior confirmó cero instancias RDS del proyecto, cero subnet groups
  `tng-drtest-*`, y ningún secreto huérfano de la prueba. El snapshot fuente
  seguía `available` y cifrado.

## Alcance pendiente

La prueba valida que el snapshot se puede restaurar y que las credenciales
maestras pueden recuperarse de forma segura; **no** ejecutó una consulta SQL ni
comparó tablas/datos. Tampoco midió RTO/RPO. Por ello no se presenta como una
recuperación de datos integral ni como despliegue permanente del portal.

Se usó el perfil local `default`; STS aceptó la sesión. La simulación IAM sin
contexto de recurso devuelve `implicitDeny` para `rds:ModifyDBInstance`; al
simular con región, motor PostgreSQL, clase `db.t3.micro` y almacenamiento de
20 GiB la decisión fue `allowed`. La llamada real posterior a la restauración
completó la rotación. El proceso no cambió ni eliminó el snapshot fuente.

El costo temporal corresponde a una instancia RDS micro durante la prueba; no
se dejó capacidad en ejecución. Los valores de credenciales y del secreto RDS
no forman parte de esta evidencia.

## Reintento posterior — 02:38 America/Chicago

Con una sesión AWS nueva, STS volvió a aceptar el perfil `default`. Se confirmó
un snapshot manual PostgreSQL disponible y cifrado y se inició otra restauración
aislada. AWS confirmó inicialmente la nueva instancia como privada, cifrada,
`db.t3.micro`, con retención automática 0; avanzó a
`resetting-master-credentials` y el secreto administrado figuraba `rotating`.

El script terminó con `CLEANUP_INCOMPLETE`. Al intentar verificar o eliminar
RDS, AWS devolvió una denegación explícita de la política
`voc-cancel-cred`. No se pudo confirmar el estado final de la instancia ni del
subnet group, y el intento de eliminación también fue denegado. Los únicos
recursos de prueba identificados son `tng-drrestore-20261013023830` y
`tng-drtest-20261013023830`; **podrían seguir activos y generar costo**. El
snapshot fuente `tangamandapio-live-20261005-final-20261009192408` no fue objeto
de ninguna operación de eliminación. Por tanto, el resultado de este reintento
es `INCOMPLETO`; no equivale a una restauración verificada ni limpia.

La identidad STS sigue autenticando, pero la política explícita
`voc-cancel-cred` también deniega `ec2:DescribeInstances` y
`cloudformation:DescribeStacks`, además de `rds:DescribeDBInstances`,
`rds:DescribeDBSnapshots`, `rds:DescribeDBSubnetGroups` y
`rds:DeleteDBInstance`. La revisión por consola tampoco pudo continuar: el
control del navegador detuvo la sesión porque no pudo determinar con fiabilidad
la URL actual. Hace falta recuperar permisos del laboratorio y borrar/verificar
exclusivamente los dos recursos temporales antes de volver a declarar la prueba
limpia.

## Ajuste local del arnés PT-DR-01 — 13/10/2026

Sin ejecutar operaciones cloud, se corrigió la medición para que RTO comience
al solicitar el restore y termine después de la sonda SQL de integridad; el
tiempo de creación del snapshot queda fuera de ese RTO. La instancia temporal
desactiva backups automáticos adicionales y valida `BackupRetentionPeriod=0`.
La compuerta local comprobó sintaxis, opt-in de costo y estas invariantes. Esto
es solo una mejora del procedimiento: no limpia ni revalida los recursos
`tng-drrestore-20261013023830` y `tng-drtest-20261013023830`, y no convierte el
reintento incompleto en una recuperación aprobada.

## Verificación y limpieza de copia residual — 13/10/2026, 08:16 America/Chicago

Con la siguiente sesión AWS válida se comprobó que la copia etiquetada
`tng-drrestore-20261013023830` aún estaba `available`, privada y cifrada. Antes
de eliminarla se verificaron la etiqueta `Purpose=temporary-dr-restore`, la
protección contra borrado desactivada y el snapshot manual fuente disponible y
cifrado. Se eliminó únicamente esa copia temporal y su subnet group
`tng-drtest-20261013023830`; AWS confirmó que ya no están presentes. La base
principal y el snapshot fuente no se modificaron. La prueba original continúa
sin sonda de integridad lógica ni medición RTO/RPO, así que no se declara un
restore funcional completo.

## Restore con integridad SQL PT-DR-01 — 13/10/2026, 08:57 America/Chicago

Resultado final: `PT-DR-01=PASSED`, con limpieza verificada. Se insertó y
confirmó un marcador SQL efímero en PostgreSQL, se creó un snapshot cifrado y se
restauró una copia no pública con backups automáticos desactivados. La sonda
remota confirmó el marcador en la restauración y el mismo conteo de **14 tablas
de negocio** en origen y copia. RTO (solicitud de restauración → verificación
SQL): **289 s**; RPO superior medido (commit del marcador → timestamp del
snapshot): **10 s**.

La limpieza eliminó el marcador de origen y copia, la instancia restaurada y el
snapshot temporal; el RDS principal quedó `available`. El snapshot manual
operativo se conservó. Estos tiempos corresponden a esta ejecución y no son una
garantía de SLA. Los intentos anteriores y su limpieza se mantienen arriba como
historial; este resultado los supersede para la prueba PT-DR-01.

## Repetición íntegra y limpieza confirmada — 13/10/2026, 15:46–15:57 America/Chicago

Se repitió `tests/aws/pt-dr-01-rds-restore.sh tangamandapio-live-20261013`
con la confirmación de costo requerida. El marcador SQL escrito antes del
snapshot apareció en la copia restaurada y los conteos de las tablas de negocio
coincidieron entre origen y copia. Resultado: `PT-DR-01=PASSED`,
`measured_rto_seconds=289`, `measured_rpo_upper_bound_seconds=14`, copia
privada y cifrada, sin backups automáticos adicionales.

La limpieza reportó `verified`. Una consulta posterior confirmó que la base
principal `tangamandapio-postgres` sigue `available`, privada y cifrada, y que
no queda ninguna instancia `tng-dr-restore-*` ni snapshot temporal
`tng-dr-snap-*`. El snapshot fuente permanente no se eliminó. El RPO es un
límite observado en esta prueba, no una garantía de SLA.
