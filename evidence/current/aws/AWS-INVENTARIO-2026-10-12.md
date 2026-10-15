# Inventario AWS de solo lectura — 12/10/2026

## Revisión posterior a renovación del token — 23:45 America/Chicago

STS aceptó la terna que el usuario entregó y que se guardó en `default`. En
consultas de solo lectura no aparecieron instancias RDS activas ni secretos del
proyecto; el snapshot manual PostgreSQL cifrado del 09/10 continúa en estado
`available`. La lectura actual reportó cero instancias RDS y no encontró un
secreto con prefijo del proyecto. El perfil `LabInstanceProfile` apunta a
`LabRole`; la simulación de permisos indicó
`secretsmanager:GetSecretValue=allowed`, mientras que la de
`rds:ModifyDBInstance` no fue concluyente por claves de contexto ausentes. Una
llamada de autorización contra un ID de instancia deliberadamente inexistente
respondió `AccessDenied`; no se creó ni modificó una instancia. La lectura de
las políticas IAM quedó bloqueada por un `explicit deny`. No se restauraron
bases ni se hizo otro cambio cloud en esta revisión.

## Corte actualizado — 12/10/2026, 22:52 America/Chicago

El usuario indicó que el Learner Lab estaba encendido y entregó una terna nueva.
Se guardó en el perfil local `default`; `aws sts get-caller-identity` fue
aceptado y las consultas de inventario respondieron. No se hicieron cambios a
recursos.

| Servicio | Estado actual observado en `us-east-1` |
|---|---|
| CloudFormation | 1 stack `CREATE_COMPLETE`, descripción `associate Learner Lab template (academy)`, 26 recursos de administración del laboratorio; no es el stack Tangamandapio. |
| EC2 | 0 instancias |
| ELBv2 | 0 balanceadores |
| RDS | 0 instancias en línea; 1 snapshot manual `tangamandapio-live-20261005-final-20261009192408`, PostgreSQL 18.3, `available`, cifrado, 20 GiB, creado el 09/10. |
| VPC | Solo la VPC predeterminada `172.31.0.0/16`; no existe la VPC del portal. |
| S3 / SQS / ECS | No se encontraron buckets, colas ni clusters ECS. |
| Lambda | Solo 5 funciones del stack Academy/Redshift, no funciones del portal. |

El secreto `tangamandapio/rds/master` no existe. La pila de apagado del 09/10
registró que los secretos de RDS y admin se eliminaron; por ello el snapshot se
conserva, pero la restauración administrada por el flujo actual aún está
bloqueada hasta preparar una ruta explícita y segura para recuperar/rotar la
credencial maestra. El snapshot fuente no se modificó.

**Conclusión actual:** el laboratorio autentica y permite lecturas; el portal
no está desplegado. El único stack activo es administrado por AWS Academy. No
se restauró RDS ni se inició un despliegue.

**Corte:** 21:09 (America/Chicago), región `us-east-1`. La autenticación STS
había sido aceptada a las 21:03. No se ejecutaron operaciones de escritura ni
se imprimieron ID de cuenta, ARN o identificadores de recursos.

| Servicio | Resultado observado |
|---|---|
| EC2 | 0 instancias |
| ELBv2 | 0 balanceadores y 0 target groups |
| RDS | 0 instancias en línea; se identificó un snapshot manual PostgreSQL disponible y cifrado (20 GiB, del 09/10). No se conserva aquí su identificador. |
| VPC | 1 VPC disponible, `IsDefault=true`, CIDR `172.31.0.0/16` |
| Subredes / Internet Gateway | 6 subredes / 1 gateway; corresponden al entorno predeterminado del lab, no prueban la red privada del proyecto |
| CloudFormation | 1 stack activo en `CREATE_COMPLETE`, con 26 recursos: IAM, Lambda, EventBridge, SNS y recursos/custom resources relacionados |
| Servicios con prefijo Tangamandapio | 0 buckets S3, parámetros SSM, funciones Lambda y grupos de logs encontrados; el secreto `tangamandapio/rds/master` no existe |

El nombre del stack no se conserva aquí para evitar divulgar identificadores
internos. Los tipos y estado no bastan para atribuirlo a Tangamandapio; no se
considera evidencia de despliegue del portal. En particular, la revisión no
encontró componentes de aplicación esperados en EC2/ALB/RDS/S3/SSM/Lambda/logs.

**Conclusión:** las credenciales son válidas y el lab tiene recursos de su
propio entorno, pero el portal no está demostrado como levantado en AWS en esta
región al corte. No se reinició el lab y no se cambió ningún recurso.

## Revalidación y recuperación — 12/10/2026, aproximadamente 21:37 America/Chicago

El perfil local `default` contiene la terna entregada por el usuario y STS
volvió a aceptarla (identidad suprimida). Esto no implica que el laboratorio
siga activo: la consola AWS Academy mostró `Lab terminated` y `No running
instance`. La llamada RDS más reciente fue denegada explícitamente por la
política `voc-cancel-cred`; por eso la falla es de estado/permisos del lab, no
de una terna mal copiada. La consola aún mostraba el mismo juego de credenciales
anterior, no un token nuevo.

Se invocó la prueba de restauración temporal con opt-in, pero quedó bloqueada
por `AccessDenied` antes de validar una restauración. No se modificó el snapshot
fuente ni se pudo confirmar un round-trip de datos; el script no informó una
limpieza pendiente. Las consultas posteriores de RDS también fueron denegadas,
por lo que no se presenta un inventario posterior como si estuviera verificado.

No se pudo iniciar el lab desde esta sesión: la protección de control del
navegador detuvo la automatización al no poder validar la URL actual. Por ello
no se obtuvo ni guardó un token nuevo. La siguiente verificación requiere que
AWS Academy vuelva a mostrar el lab activo y que se copie la terna recién
generada a `default`; no reutilizar la credencial anterior como renovación.
