# Revalidación de credenciales AWS — 12/10/2026

## Renovación más reciente del usuario — 23:45 America/Chicago

Los tres campos temporales fueron guardados en el perfil local `default` y
`aws sts get-caller-identity --profile default` terminó correctamente. No se
registraron valores de credencial. Lecturas posteriores confirmaron que no hay
instancias RDS del portal en línea y que el snapshot manual cifrado sigue
disponible. Una comprobación de `rds:ModifyDBInstance` contra un identificador
que no existía devolvió `AccessDenied`; no se creó recurso. Esta actualización
local no inició ni detuvo recursos cloud.

## Terna nueva proporcionada por el usuario — 22:52 America/Chicago

Se actualizaron los tres campos del perfil local `default` con la terna más
reciente, sin copiar sus valores a archivos de evidencia ni a la salida. STS
aceptó la sesión y las consultas de solo lectura a CloudFormation, EC2, ELBv2,
RDS, VPC, S3, SQS, Lambda y ECS respondieron. El inventario actualizado se
documenta en [AWS-INVENTARIO-2026-10-12.md](AWS-INVENTARIO-2026-10-12.md).

Esto confirma que la sesión AWS está operativa; no equivale a que el portal esté
desplegado. No se modificó ningún recurso cloud.

**Resultado:** autenticación aceptada por AWS STS a las 21:03 (America/Chicago).

Se reescribieron los tres campos del perfil local `default` con los valores
suministrados por el usuario y se compararon en memoria, campo por campo. La
comparación fue exacta (`saved_values_match=true`). Después,
`aws sts get-caller-identity --profile default` terminó correctamente. La
identidad y los valores de credencial no se imprimieron ni se copiaron a este
registro.

El proceso fijó las rutas de los archivos locales de configuración y
credenciales, porque la invocación inicial del CLI encontró una ruta de
configuración vacía. La revalidación posterior resolvió esa configuración y
confirmó tanto la comparación local como la aceptación del token por STS.

Este control **solo demuestra autenticación**. No se consultó el inventario de
AWS, CloudFormation, EC2, ALB ni RDS, y no se ejecutó ninguna operación de
lectura de recursos ni escritura cloud. No se reinició el Learner Lab porque la
credencial pasó la prueba STS. El registro previo
[`AWS-AUTENTICACION-RECHAZADA-2026-10-12.md`](AWS-AUTENTICACION-RECHAZADA-2026-10-12.md)
describe el fallo anterior y debe leerse como histórico, no como estado actual.

La credencial temporal se compartió en el chat; no se reproduce aquí. Debe
rotarse al renovar el Learner Lab y nunca incluirse en capturas, commits o
documentos.

## Revalidación posterior del mismo día

STS volvió a aceptar la sesión. Las consultas de solo lectura
`ec2 describe-instances` y `cloudformation list-stacks` no pudieron listar
recursos (denegadas o no disponibles); por tanto, la CLI no confirma si quedan
instancias o stacks. La última observación directa disponible de AWS Academy
decía `Lab terminated` / `No running instance`. El control del navegador se
detuvo antes de poder pulsar Start Lab; no se apagó ni inició un lab durante
esta comprobación y no se obtuvo un token nuevo.
