# EVID-010 — Despliegue controlado AWS

| Campo | Registro verificable |
|---|---|
| Nube / región | AWS Academy / us-east-1 |
| Identificador propio | `tangamandapio-live-20260925` |
| Inventario previo | Se detectaron 3 EC2 y una pila de Academy ajenos al proyecto; no se modificaron. |
| Validación IaC | `aws cloudformation validate-template` devolvió la descripción `Tangamandapio S.A.C. - laboratorio AWS controlado`. |
| Inicio | `aws cloudformation create-stack` aceptó la pila y devolvió su identificador. |
| Estado al registrar | `CREATE_IN_PROGRESS`. Recursos confirmados: `AppSG`, `AppTargetGroup` y ruta pública en `CREATE_COMPLETE`; ALB en creación. |
| Componentes solicitados | VPC, 2 subredes en AZ distintas, ALB, Auto Scaling (2 EC2), PostgreSQL RDS no público/cifrado, S3 cifrado/versionado y dashboard CloudWatch. |
| Incidente y contención | El primer intento falló por JSON no válido en el recurso `AWS::CloudWatch::Dashboard`. `--on-failure DELETE` inició la limpieza automática; no se ejecutó borrado manual. La plantilla de laboratorio fue corregida y volvió a validar correctamente. |
| Segundo intento | Pila `tangamandapio-live-20260925b` aceptada por CloudFormation. Se verificaron `DocumentsBucket`, `AppSG`, `AppTargetGroup`, `AppLaunchTemplate` y `AppAutoScalingGroup` en `CREATE_COMPLETE`. |
| Prueba funcional real | El ALB respondió HTTP `200` y el target group reportó dos destinos `healthy`. |
| Seguridad RDS verificada | PostgreSQL reportó `PubliclyAccessible=False` y `StorageEncrypted=True`. Al cierre de este registro aún estaba en fase de configuración, por lo que no se declara una conexión SQL de aplicación. |
| Cierre de primer intento | La pila `tangamandapio-live-20260925` alcanzó `DELETE_COMPLETE` mediante la limpieza automática configurada. |
| Cierre de segundo intento | Tras la autorización del responsable, se emitió `delete-stack` para `tangamandapio-live-20260925b`. La consulta posterior de recursos devolvió `ValidationError: Stack ... does not exist`, confirmando que ya no existe. |
| Inventario propio final | `length` de instancias PostgreSQL: `0`; `length` de instancias de Auto Scaling cuyo grupo contiene `tangamandapio`: `0`. No se modificaron las 3 EC2 ni la pila Academy encontradas antes del despliegue. |
| Laboratorio | AWS Academy mostró `AWS Status: Terminated`, temporizador `00:00` y mensaje `Lab terminated`. |
| Cierre preventivo posterior | Por instrucción expresa del responsable, las tres EC2 preexistentes detectadas en `running` recibieron `stop-instances` y AWS informó transición a `stopping`. No se eliminaron; el laboratorio se terminó nuevamente y mostró `AWS Status: Terminated`, `00:00`. |

Resultado honesto: se obtuvo una prueba funcional real del balanceador (HTTP `200` y dos destinos healthy) y una verificación de postura de la base de datos. El despliegue se canceló de forma controlada antes de que PostgreSQL quedara disponible, por lo que no se declara una conexión SQL ni un `CREATE_COMPLETE` de la pila.
