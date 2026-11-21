# Estado operativo al 20/11/2026

## Portal y roles

`20261120-erp-db-runtime` está desplegado en AWS Ohio en ambas instancias del
Auto Scaling Group. El portal completó 297 comprobaciones reales en diez
sesiones. Comercial envió un mensaje, Almacén lo abrió y el contador de mensajes
pendientes se actualizó. Las pruebas incluyeron módulos permitidos, accesos
denegados y visibilidad del mensaje restringida a sus participantes. La entrega
de correo del ERP opera dentro del portal. El chequeo al WMS privado devolvió
`ok`. [Verificación de la versión vigente](../evidence/current/aws/AWS-ERP-SQL-ACCESS-2026-11-20.json) ·
[Corrección inicial del buzón](../evidence/current/aws/AWS-ERP-MAIL-ROLES-2026-11-20.json).

## AWS y CloudFormation

La pila `tangamandapio-live-20261116` completó la actualización a las 18:10:40
de Lima. `DatabaseMultiAZ=true` coincide con RDS disponible en `us-east-2b` y
`us-east-2a`. Se conservó la misma base física, la retención de un día y la salud
2/2 del ASG. La comprobación de deriva del recurso RDS quedó `IN_SYNC`. La pila
tiene una política que protege `Database` de reemplazo o retiro durante
actualizaciones. [Plan y verificación posteriores](../evidence/current/aws/AWS-RDS-IAC-RECONCILIATION-2026-11-20.json).

La detección completa del stack reportó dos diferencias. SNS muestra la
suscripción Gmail confirmada entre las propiedades reales del tema. IAM muestra
la política de respaldo `tangamandapio-scheduled-blob-backup` que agrega la pila
`tangamandapio-azure-postgres-backup`. Conserva ambas al preparar cambios de la
pila principal. La suscripción UPeU aún muestra `PendingConfirmation`. Para
activarla, abre en Outlook institucional el mensaje de AWS Notifications de
`tangamandapio-alarms`, pulsa **Confirm subscription** y verifica el estado en
SNS → Topics → `tangamandapio-alarms` → Subscriptions en Ohio.

El ERP valida las migraciones y ejecuta sus operaciones con
`tangama_app_runtime`. El exportador usa `tangama_backup_reader` con lectura de
tablas y secuencias. Ambas EC2 demostraron acceso a RDS y `pg_dump` con el
lector. Tras el recambio, el rol de instancia perdió acceso al secreto maestro.
Secrets Manager devolvió acceso denegado desde ambas EC2. `/ready` respondió
HTTP 200 en las 35 muestras del recambio. El stack independiente de los
secretos mantuvo sus dos recursos y protección contra eliminación del stack.
[Pruebas de permisos y despliegue](../evidence/current/aws/AWS-ERP-SQL-ACCESS-2026-11-20.json).

La primera ronda posterior al despliegue pasó 296 de 297 comprobaciones. El
GET de datos maestros de Almacén a las 19:06:39 recibió un 502 del ALB. La traza
mostró `ALLOW` en WAF, `waf,forward` en el ALB y `target_status_code=-`. La
repetición pasó 297 de 297, incluido el 403 esperado para Almacén. Se observó
una espera de conexión persistente de 2 s en Gunicorn y un tiempo de inactividad
de 60 s en el ALB. Esa diferencia es una causa compatible con el registro y
queda por probar mediante un ensayo controlado. [Diagnóstico de HTTP 502 en ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html#http-502-issues).

## Recuperación desde Azure

La copia diaria de las 03:01:07 de Lima se descargó desde Blob y se descifró
con la clave versionada de Azure Key Vault. Se comprobaron las dos huellas del
manifiesto de respaldo, copiado de S3 antes de la prueba. El PostgreSQL local
aislado recuperó 20 tablas, dos pedidos y dos eventos outbox. El ERP inició
sobre esa base, mostró los dos pedidos y pasó 19 comprobaciones HTTP, incluidas
sesiones de Administración y Almacén, permisos y correo interno. Los ensayos
duraron 14,546, 12,750 y 13,625 s, medidos desde la descarga hasta completar la
última comprobación. El tercero reutilizó el manifiesto publicado. El clúster
local se eliminó al terminar cada prueba. El origen era PostgreSQL 18.3 y el
destino local 17.5. [Registro de recuperación](../evidence/current/azure/AZURE-ERP-RECOVERY-2026-11-20.json).

Para una recuperación regional completa aún se requiere un destino autorizado
por AWS Organizations o una cuenta secundaria aprobada, infraestructura de red
y DNS, y repetir el ensayo con PostgreSQL 18. Queda pendiente el ensayo de
conmutación administrada de RDS. El RPO medido el 19/11 correspondió a esa copia
y a ese corte, con un pedido y un evento outbox posteriores. La confirmación
de revocación de credenciales expuestas en las cuentas anteriores sigue
abierta.

El ensayo con los usuarios SQL dedicados sobre la copia de Blob completó 25
comprobaciones HTTP en 16,078 s. Incluyó venta, compra, recepción en el outbox,
gasto, liquidación y correo. Se verificó que el usuario del ERP no puede crear
tablas o modificar el registro de migraciones y que el lector puede exportar
la base sin escribir. [Evidencia desde la copia de Azure](../evidence/current/azure/AZURE-ERP-RESTRICTED-DB-2026-11-20.json).

## Revisión Terraform de Azure

El plan de `azure-flex-private` proponía retirar una etiqueta que Azure agrega
para vincular la Function con Application Insights. Terraform ahora preserva
esa etiqueta. Se sincronizaron tres salidas en el backend sin cambiar recursos
en Azure y el plan posterior devolvió `No changes`. El plan de solo refresco de
`azure-rebuild` registró siete recursos con diferencias y quedó en modo lectura.
[Diferencias y alcance](../evidence/current/azure/AZURE-TERRAFORM-DRIFT-2026-11-20.md).

La consulta de presupuestos de las 18:54 de Lima registró USD 16,75 de 200 en
AWS y USD 9,75 de 25 en Azure. [Lecturas y desglose del día](../evidence/current/COSTOS-2026-11-20.md).

[Inventario de red, WAF, costos y pruebas del 19/11](ESTADO_REAL_2026-11-19.md) ·
[Matriz y evidencias para la defensa](../core/04_matriz_rubrica.md).
