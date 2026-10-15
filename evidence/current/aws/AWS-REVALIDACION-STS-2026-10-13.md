# Autenticación AWS — 13/10/2026

## Revalidación solo lectura — 18:42 America/Chicago

`aws sts get-caller-identity --profile default` autenticó la cuenta Academy
`841113066612` como rol `voclabs`; por tanto, el token usado en este corte es
válido. `cloudformation:ListStacks` continúa bloqueado por una denegación
explícita de la política `voc-cancel-cred`. Se probó además
`DescribeStacks` usando el nombre exacto conocido
`tangamandapio-live-20261013`; también recibió explicit deny sobre el ARN de ese
stack. No es solo una limitación para listar: la política impide leer el stack
conocido y por eso bloquea el preflight de despliegue. No se modificaron
recursos.

El ALB `tangamandapio-alb-1120317898.us-east-1.elb.amazonaws.com` respondió
200 en `/health` y `/ready`, pero 404 en `/administracion` y
`/api/admin/alarm-subscriptions`. El front publicado no contiene esas rutas
administrativas aunque el backend/candidato local sí las prueba. No se ejecutó
despliegue por no poder reconciliar el estado CloudFormation.

## Corte 11:33 America/Chicago

Se actualizó el perfil local `default` con la terna temporal más reciente y
`aws sts get-caller-identity` autenticó la cuenta académica `841113066612`.
Los valores de las credenciales no se registraron.

STS exitoso no habilita las demás APIs. En este corte fueron rechazadas por
denegación explícita de la política de identidad `voc-cancel-cred`:

- `cloudformation:DescribeStacks`
- `autoscaling:DescribeAutoScalingGroups`
- `ssm:DescribeInstanceInformation`

No se pudo verificar el stack, el ASG ni la conectividad SSM de las instancias.
No se modificó AWS. La última comprobación de aplicación, a las 10:43, mostró
stack `UPDATE_COMPLETE`, 2/2 instancias y destinos sanos y `/health` HTTP 200;
eso es evidencia histórica, no un estado confirmado a las 11:33.

El control visual de AWS Academy se detuvo antes de interactuar con la página:
no logró identificar de forma confiable la URL activa de Chrome. No se afirma
haber iniciado, detenido ni inspeccionado visualmente el laboratorio.

## Corte 03:19 America/Chicago

La terna temporal más reciente entregada por el usuario se aplicó al perfil
local `default`. AWS STS autenticó la cuenta del laboratorio y devolvió un rol
`voclabs`. No se registraron credenciales en este documento ni en Git.

La consola de AWS Academy muestra el laboratorio en estado `Ready`, 3 h 58 min
restantes, $22/$50 utilizados y “No running instance”. La sección AWS Details
presenta la misma terna entregada para este corte. El indicador `Ready` confirma
la sesión del laboratorio, no que existan instancias de la aplicación.

Las siguientes consultas de solo lectura fueron rechazadas por una denegación
explícita de la política de identidad `voc-cancel-cred`:

- `cloudformation:ListStacks`
- `ec2:DescribeInstances`
- `elasticloadbalancing:DescribeLoadBalancers`
- `rds:DescribeDBInstances`

La falla no es `InvalidClientTokenId`: STS aceptó la sesión. La política actual
impide verificar inventario y administrar esos servicios. En paralelo, el DNS
del ALB no resolvió durante la prueba externa de `/health`; no se puede afirmar
que el portal público esté disponible. La Function de Azure sí devolvió HTTP
200 en `/api/health`.

El anterior corte de salud y despliegue a las 02:32 está conservado como
evidencia histórica, no como estado actual. Las credenciales son temporales y
no deben copiarse a evidencias, commits o capturas.

## Corte 04:14 America/Chicago

Se actualizó el perfil local `default` con la terna temporal que el usuario
entregó para este corte. `aws sts get-caller-identity` autenticó una sesión
`voclabs`. Los valores de las credenciales no se guardaron en Git ni en este
registro.

Las consultas actuales de solo lectura volvieron a recibir denegaciones
explícitas de `voc-cancel-cred` para `cloudformation:ListStacks`,
`ec2:DescribeInstances`, `elasticloadbalancing:DescribeLoadBalancers` y
`rds:DescribeDBInstances`. No se confirmó el inventario de recursos, no se
modificó infraestructura y no se afirma que EC2, ALB o RDS estén activos o
apagados. STS aceptado no demuestra que el permiso Start Lab de AWS Academy se
haya ejecutado; la interfaz Academy no se pudo verificar en este corte.

## Corte 04:53 America/Chicago

Se verificó el perfil local `default` sin imprimir credenciales: el identificador
de clave coincide con el entregado en este corte; el secreto y el token de sesión
están presentes (40 y 772 caracteres, respectivamente). Pese a ello,
`aws sts get-caller-identity --profile default` fue rechazado por AWS como token
inválido. No se realizaron llamadas de modificación ni se cambió infraestructura.
El estado visual del laboratorio en AWS Academy no se pudo comprobar porque la
ventana de Chrome visible correspondía a WhatsApp; no se afirma que se haya
iniciado ni detenido el laboratorio. Hace falta copiar una terna nueva desde
AWS Details y volver a validar STS antes de continuar.

## Corte 05:15 America/Chicago

Se reemplazó `default` con la terna recién entregada. La comparación local
confirmó coincidencia exacta de access key, secret y session token sin
imprimirlos; AWS CLI indicó `shared-credentials-file` como origen. La consulta
`aws sts get-caller-identity --profile default` devolvió `ExpiredToken`. No se
ejecutaron llamadas que modifiquen recursos. El usuario reportó que el
laboratorio está encendido, pero la autenticación fallida impide confirmar por
API el estado del laboratorio y el inventario de AWS.

## Corte 11:52 America/Chicago

Se reemplazó el perfil local `default` con la terna temporal más reciente
entregada por el usuario. La access key del perfil coincide con la recibida y
no hay variables `AWS_*` de entorno que estén sustituyendo el perfil. STS
autenticó la cuenta académica `841113066612` como rol `voclabs`; por tanto, esta
terna sí es válida para autenticación. Los valores no se registraron.

Las consultas de solo lectura a `cloudformation:ListStacks`, `ec2:DescribeVpcs`,
`ec2:DescribeInstances`, `ec2:DescribeVpnConnections`,
`autoscaling:DescribeAutoScalingGroups`,
`elasticloadbalancing:DescribeLoadBalancers` y `rds:DescribeDBInstances` fueron
rechazadas por denegación explícita de `voc-cancel-cred`. El preflight
`-AwsPreflightOnly` confirmó que termina ante esa denegación antes de invocar
Azure. No se modificó AWS ni se pudo confirmar el estado actual del stack,
ASG, ALB o RDS. La denegación de autorización es distinta de un token vencido o
inválido. Hace falta que la política/sesión del laboratorio permita esas
lecturas antes de ejecutar el preflight completo de la VPN o afirmar un estado
de despliegue.

## Corte 12:46 America/Chicago

Se reemplazó el perfil local `default` con la terna temporal recién entregada.
`aws sts get-caller-identity` autenticó nuevamente la cuenta académica
`841113066612` con rol `voclabs`. Los secretos no se copiaron a archivos del
proyecto ni a esta evidencia.

Las consultas de solo lectura a `cloudformation:ListStacks`, `ec2:DescribeVpcs`,
`ec2:DescribeInstances`, `ec2:DescribeVpnConnections`,
`elasticloadbalancing:DescribeLoadBalancers` y `rds:DescribeDBInstances`
fallaron con denegación explícita de la política `voc-cancel-cred`. El token es
válido; la política impide inventariar los recursos. No se efectuaron
operaciones de escritura ni cambios en AWS. Los datos de despliegues anteriores
siguen siendo históricos, no una comprobación de estado presente.

## Corte 13:03 America/Chicago

El perfil local conserva la última terna del laboratorio, pero al revalidar
`aws sts get-caller-identity --profile default` AWS respondió `ExpiredToken`.
`cloudformation:ListStacks` también falló por el token vencido, por lo que no
se pudo repetir el inventario ni determinar el estado del laboratorio. No se
hicieron escrituras. La denegación explícita `voc-cancel-cred` del corte 12:46
se conserva como evidencia histórica; no se atribuye a la expiración.

Se intentó revisar AWS Academy mediante el navegador, pero la automatización
se detuvo al reportar la tecla Escape física antes de capturar o cambiar la
página. No se obtuvo una credencial nueva ni se afirma que el laboratorio esté
encendido o apagado.

## Recuperación automática confirmada — 13:15 America/Chicago

Tras el corte de 13:08, Auto Scaling completó dos reemplazos en
`us-east-1a`/`us-east-1b`. AWS reporta ambas instancias `InService` y `Healthy`,
health checks EC2 `ok` y 2/2 destinos ALB `healthy`. Ocho GET de `/health`
devolvieron HTTP 200 con `database=ok` y alternaron entre las dos instancias;
`/` y `/ready` también devolvieron 200. La recuperación la ejecutó Auto Scaling;
no se lanzaron instancias manualmente ni se hicieron escrituras en AWS.

CloudWatch muestra alarmas `OK`, pero declara que no recibió datapoints y que
los faltantes se trataron como `NonBreaching`; por ello su estado no demuestra
monitoreo sano en ese intervalo. La plantilla local se validó con AWS; un change
set para habilitar métricas del ASG y alarmar capacidad también modificaba
`LaunchTemplate` y `ScalingPolicy` con reemplazo condicional. Se eliminó el plan
sin ejecutarlo; no se modificaron recursos AWS.

## Corte vivo — 13:08 America/Chicago

Se verificó que el perfil `default` conserva la access key terminada en `CT5R`
de la terna recién proporcionada; STS autenticó la cuenta `841113066612` como
rol `voclabs`. Los valores secretos no se copiaron al repositorio ni se
imprimieron. En este corte, las lecturas de CloudFormation, EC2, Auto Scaling,
ELB, RDS y VPN sí respondieron.

El inventario encontró el stack `tangamandapio-live-20261013` en
`UPDATE_COMPLETE`, pero el ASG está sin instancias, el target group no tiene
destinos y el ALB responde 503. Los intentos de lanzamiento terminan con
`Client.InternalError`; no se pudo precisar su causa. RDS está disponible,
Single-AZ, con 1 día de retención. No se hicieron escrituras ni se modificaron
recursos AWS.
