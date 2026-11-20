# Estado operativo al 20/11/2026

## Portal y roles

`20261120-erp-mail-by-role` está desplegado en AWS Ohio en ambas instancias del
Auto Scaling Group. El portal completó 297 comprobaciones reales en diez
sesiones. Comercial envió un mensaje, Almacén lo abrió y el contador de mensajes
pendientes se actualizó. Las pruebas incluyeron módulos permitidos, accesos
denegados y visibilidad del mensaje restringida a sus participantes. La entrega
de correo del ERP opera dentro del portal. El chequeo al WMS privado devolvió
`ok`. [Evidencia de correo, roles y despliegue](../evidence/current/aws/AWS-ERP-MAIL-ROLES-2026-11-20.json).

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
y a ese corte, con un pedido y un evento outbox posteriores. La revisión de
mínimo privilegio SQL y la confirmación de revocación de credenciales expuestas
en las cuentas anteriores siguen abiertas.

[Inventario de red, WAF, costos y pruebas del 19/11](ESTADO_REAL_2026-11-19.md) ·
[Matriz y evidencias para la defensa](../core/04_matriz_rubrica.md).
