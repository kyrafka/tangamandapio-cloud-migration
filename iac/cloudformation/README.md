# AWS CloudFormation — portal y reconstrucción

CloudFormation es la definición de reconstrucción del portal AWS. **Corte vigente: 15/10/2026 00:34 UTC.** El stack `tangamandapio-live-20261013` está en `UPDATE_COMPLETE`; drift `IN_SYNC`. El release `20261014-landing-loading-v11-python312` está en las dos instancias `InService`, confirmado por SSM; ambas devolvieron servicio activo y health local 200. El ALB tiene exactamente dos destinos `healthy` y `/`, `/health` y `/ready` responden HTTP 200. El ASG está mínimo/deseado 2, máximo 5, sin instancias terminando. La VPC separa ALB público, app privada con NAT y RDS aislada; security groups limitan ALB:80→app:8080→PostgreSQL:5432 y bloquean ingreso directo a EC2/RDS. RDS quedó fuera del cambio y continúa `available`, privada y cifrada, Single-AZ con un día de backup. El listener continúa HTTP: dominio/HTTPS quedan pendientes. La secuencia y los fallos intermedios están en el [registro v11](../../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md).

Históricamente, el stack se eliminó el 08/10 y se reconstruyó el 09/10. Los snapshots y restauraciones anotados en los cortes anteriores no determinan el estado de hoy. `rebuild.sh` solo debe ejecutarse después de verificar el nombre exacto del stack, el snapshot y los secretos requeridos, reconciliar la plantilla con el inventario y aprobar el costo; ahora exige un `STACK_NAME` explícito.

CloudFormation es la única herramienta que administra el portal AWS. `iac/environments/demo` es una red Terraform separada y no debe aplicarse sobre el entorno vivo.

El stack de grabaciones es independiente y su definición permanece en `voice-recordings.yaml`. El bucket reconstruido está vacío; no se migraron grabaciones previas. Como el template conserva `DeletionPolicy: Retain`, usa `destroy.sh` para borrar también el bucket retenido.

## Preparar un despliegue

La secuencia de `deploy.sh` exige un `STACK_NAME` explícito con el nombre exacto del inventario actual, valida que el stack esté estable y sin drift, y genera un change set `UPDATE`. Rechaza nombres ausentes, nombres genéricos y el default histórico para no modificar accidentalmente otro stack. Mantiene todos los parámetros actuales con `UsePreviousValue=true`, incluidos los secretos `NoEcho`; no restablece Multi-AZ, WAF, Backup ni certificados a los valores por defecto del template. No ejecuta el change set a menos que se solicite explícitamente.

El preflight HTTPS se prueba localmente con respuestas ACM simuladas: exige ambos valores, nombre DNS válido, misma región que el ALB, certificado `ISSUED` y SAN exacto o wildcard de un único nivel. La propia plantilla de CloudFormation también rechaza labels DNS vacíos, con guiones en los extremos o de más de 63 caracteres, incluso si se inicia desde la consola. Entradas inválidas se detienen antes de validar el template o crear un change set. La prueba no contacta AWS ni crea recursos.

### Activación final de dominio y HTTPS

La plantilla conserva HTTP hasta tener un dominio propio. Cuando se compre o
autorice el DNS, solicita en ACM (región `us-east-1`) un certificado público
para un subdominio como `portal.ejemplo.com`, usando validación DNS. Copia en
el proveedor DNS los CNAME de validación que muestra ACM y espera el estado
`ISSUED`. El despliegue verifica que el ARN sea regional y que el certificado
cubra exactamente el hostname (o un wildcard de un solo nivel), antes de
crear el listener HTTPS 443. Con ambos valores, `deploy.sh` cambia el listener
80 a redirección permanente HTTPS y la salida `ApplicationURL` usa el hostname,
no el DNS interno `elb.amazonaws.com`.

```bash
STACK_NAME=tangamandapio-live-20261013 \
AWS_REGION=us-east-1 \
PORTAL_DOMAIN_NAME='<hostname>' \
CERTIFICATE_ARN='<arn:aws:acm:us-east-1:...:certificate/...>' \
./deploy.sh
```

Primero se revisa el change set; para aplicarlo se repite con `APPLY_CHANGE_SET=true`
y `CONFIRM_STACK_NAME` igual al stack verificado. Después, crea en el proveedor
DNS el registro CNAME/ALIAS del hostname al output `LoadBalancerDNS`, confirma
HTTPS sin advertencias, redirección HTTP→HTTPS y cookie `Secure`. Esta fase
queda preparada en IaC, pero aún no activada en el release AWS v9.

Si el DNS está en Route 53, usa un alias A/AAAA al ALB; en otro proveedor, un
CNAME del subdominio `portal` al valor `LoadBalancerDNS`. El registro público
del portal se configura después de que el change set aplique el listener. La
validación del certificado de ACM va primero y usa sus CNAME independientes.

```bash
cd iac/cloudformation
STACK_NAME=tangamandapio-live-YYYYMMDD AWS_REGION=us-east-1 ./deploy.sh
```

Reemplaza `YYYYMMDD` únicamente por el sufijo que acabas de verificar en AWS; el ejemplo no es un nombre literal para ejecutar. El script no tiene stack predeterminado.

Revisar cuidadosamente la tabla de cambios. Para ejecutar, repetir con `APPLY_CHANGE_SET=true`, `CONFIRM_STACK_NAME` idéntico al stack recién verificado y escribir `APPLY` cuando lo solicite. No pasar contraseñas por argumentos ni reemplazar parámetros secretos; el script conserva sus valores previos.

Solo para publicar un artefacto nuevo, establecer juntos `APPLICATION_ARTIFACT_KEY` y `APPLICATION_ARTIFACT_REVISION` después de correr pruebas y subir el objeto versionado al bucket. El script no empaqueta ni sube código por sí mismo.

## Reconstrucción tras eliminar el stack

`aws-lab.yaml` incorpora `BootstrapMode`, cuyo valor por defecto `false` define la capacidad normal del template. En `true`, CloudFormation crea la infraestructura con el Auto Scaling Group en cero para evitar que EC2 intente arrancar antes de que exista el artefacto. La aplicación ya no guarda la contraseña RDS dentro de `DATABASE_URL`: recibe el ARN, obtiene el JSON del secreto en tiempo de conexión, lo cachea cinco minutos y fuerza una lectura nueva si PostgreSQL reporta `28P01` (credencial rotada). `DATABASE_NAME` queda como parámetro explícito. `rebuild.sh` no elige una pila histórica por defecto: exige que se indique explícitamente un nombre `tangamandapio-live-YYYYMMDD` verificado. La consulta de existencia es fail-closed: solo continúa cuando CloudFormation devuelve `ValidationError` con “Stack with id <nombre indicado> does not exist”. `AccessDenied`, `ExpiredToken`, errores de red u otros fallos detienen la reconstrucción antes de validar o crear recursos; `tests/aws/stack_name_guard_test.sh` cubre esos casos con mocks y sin escrituras a AWS.

`package_portal_artifact.sh` empaqueta la versión vigente desde `app/aws_release/current`, incluidas migraciones, estáticos, la revisión y `requirements.lock`. El bootstrap instala Python 3.12 en un virtualenv y únicamente paquetes con versión y hashes (`pip --require-hashes`); no altera el Python 3.9 que AL2023 reserva al sistema. El lock de release se mantiene alineado con CI y se prueba con pip-audit y un dry-run para CPython 3.12/Linux. Sin argumentos, el empaquetador crea un archivo local en `artifacts/`; con bucket y clave lo sube a S3. `rebuild.sh` calcula el SHA-256 antes de crear el stack, usa una clave S3 que incorpora el hash completo y lo pasa como parámetro; las instancias verifican los bytes descargados antes de extraerlos. La clave inmutable permite que un Launch Template anterior vuelva a descargar su paquete en un rollback. Para un release sobre un stack existente, publica primero el objeto privado en una clave que incluya el SHA-256 completo y define juntos `APPLICATION_ARTIFACT_KEY`, `APPLICATION_ARTIFACT_REVISION` y `APPLICATION_ARTIFACT_SHA256` al preparar el change set. El release v5 fue verificado en `tangamandapio-live-20261013` a las 00:24 del 14/10; es un registro histórico, no una confirmación del estado actual. Antes de otro despliegue, vuelve a verificar el inventario y conserva el artefacto anterior para rollback.

`InternalErpEnabled` mantiene habilitado el módulo interno por defecto. Sus
tablas se agregan a PostgreSQL; no se crean bases ni servicios SMTP separados.
El paquete incluye `erp_service.py`, `/erp` y sus recursos estáticos. El grupo
de Auto Scaling rota una instancia por vez durante la actualización.

Primero recrea Azure con `environments/azure-rebuild`, luego crea/actualiza en Secrets Manager el secreto con la clave nueva de la Function (sin escribirla en Git, historial de consola ni chat). Después publica AWS:

```bash
AZURE_FULFILLMENT_URL="https://<function-app>.azurewebsites.net" \
AZURE_FUNCTION_KEY_SECRET="<nombre-del-secreto-en-Secrets-Manager>" \
bash ./rebuild.sh
```

El script solo crea un stack ausente. Solicita confirmación, crea con cero EC2, sube el artefacto, detecta drift para registrar la línea base `IN_SYNC` y luego habilita dos instancias mediante un change set. Los secretos del administrador del portal y los secretos RDS gestionados externamente se conservan; una restauración de snapshot sin credencial permite únicamente la fase `BootstrapMode=true`, sin instancias. Tras restaurar PostgreSQL, habilita el secreto administrado por RDS, pasa su ARN con `ExistingDatabaseSecretArn` y actualiza `ManageDatabaseMasterPassword=true` antes de habilitar EC2. Para el admin, usa el secreto original o `RESET_ADMINISTRATOR_ON_RESTORE=true`; este último restablece una sola vez por versión, revoca sesiones e impone cambio de clave. Mantén el indicador en `false` fuera de una restauración autorizada. Por defecto desactiva Multi-AZ, WAF y AWS Backup, y deja un día de retención automática RDS; se pueden habilitar con `DATABASE_MULTI_AZ=true`, `ENABLE_WAF=true`, `ENABLE_AWS_BACKUP=true` y ajustar `DATABASE_BACKUP_RETENTION_DAYS`. No configura dominio ni certificado; HTTPS confiable queda pendiente.

## Cierre HTTPS cuando se tenga el dominio

La plantilla y `deploy.sh` ya están preparados, pero todavía no existe un FQDN
ni se debe crear un certificado para un nombre que no se controla. Cuando se
elija el dominio:

1. Confirma que puedes administrar su DNS y elige el hostname exacto (por
   ejemplo, un subdominio dedicado al portal). Si usarás Cloudflare, deja el
   registro en modo DNS-only durante la validación inicial.
2. En ACM de `us-east-1`, solicita un certificado público para ese hostname con
   validación DNS. Publica el CNAME de validación en el proveedor DNS y espera
   a que ACM indique `ISSUED`. Solicita nombres adicionales solo si realmente
   se usarán.
3. Obtén de CloudFormation el nombre actual del stack estable y su
   `LoadBalancerDNS`; no uses un stack supuesto ni modifiques RDS. Primero
   prepara y revisa el change set, sin aplicarlo:

   ```bash
   cd iac/cloudformation
   STACK_NAME='tangamandapio-live-YYYYMMDD' \
   AWS_REGION='us-east-1' \
   PORTAL_DOMAIN_NAME='portal.tu-dominio' \
   CERTIFICATE_ARN='arn:aws:acm:us-east-1:CUENTA:certificate/UUID' \
   bash ./deploy.sh
   ```

   Antes, confirma `aws sts get-caller-identity` y que la cuenta sea la del
   laboratorio correcto. Reemplaza los valores de ejemplo por datos verificados.
   El preflight exige stack estable y sin drift, certificado `ISSUED`,
   región correcta y SAN que cubra el FQDN. El primer paso solo crea/imprime un
   change set: revisar especialmente que no haya reemplazo de RDS, VPC, ALB o
   recursos con datos.
4. Para aplicar, repetir el comando agregando `APPLY_CHANGE_SET=true` y
   `CONFIRM_STACK_NAME` con exactamente el mismo nombre. El script prepara un
   change set nuevo, muestra sus cambios y pide escribir `APPLY`; revisar esa
   segunda lista antes de confirmar. Después crear el registro DNS del hostname
   apuntando al ALB (Alias/flattening para apex; CNAME para un subdominio, según
   proveedor). El comando de aplicación es:

   ```bash
   STACK_NAME='tangamandapio-live-YYYYMMDD' \
   AWS_REGION='us-east-1' \
   PORTAL_DOMAIN_NAME='portal.tu-dominio' \
   CERTIFICATE_ARN='arn:aws:acm:us-east-1:CUENTA:certificate/UUID' \
   APPLY_CHANGE_SET=true \
   CONFIRM_STACK_NAME='tangamandapio-live-YYYYMMDD' \
   bash ./deploy.sh
   ```

   Sustituye todos los ejemplos por los valores del primer preview. No pegues
   access keys en el repo ni en el comando.
5. Verificar desde fuera del portal que HTTP redirige a HTTPS, el certificado
   es confiable y cubre el hostname, `/health` y `/ready` responden 200, el
   login funciona y la cookie de sesión lleva `Secure`. Mantener rollback al
   release anterior disponible.

No hacen falta cambios de Azure para el TLS del portal: el listener HTTPS vive
en el ALB de AWS. La VPN privada AWS–Azure es una tarea separada y no se
habilita al configurar el dominio.

`tests/aws/pt-dr-snapshot-restore.ps1 -ConfirmCostlyTest` es una prueba temporal con costo: restaura el último snapshot manual, valida que la copia esté cifrada/privada y que RDS active un secreto maestro administrado; destruye únicamente la instancia y subnet group temporales. El secreto no se imprime ni se persiste. Esta prueba **no** acredita integridad de filas hasta ejecutar además una sonda SQL dentro de la VPC; no sustituye la recuperación final del servicio.

En Windows/WSL, si Bash no encuentra la CLI de Windows, define antes de ejecutar:

```bash
export AWS_CLI='/mnt/c/Program Files/Amazon/AWSCLIV2/aws.exe'
```

En Git Bash puede usarse `AWS_CLI='/c/Program Files/Amazon/AWSCLIV2/aws.exe'`; `rebuild.sh` y `deploy.sh` normalizan rutas `file:///c/...` para el CLI nativo de Windows.

## Lo que esta plantilla no demuestra

- El listener actual es HTTP, por lo que no demuestra TLS confiable. El release v9 devuelve en `/health` solo estado agregado y timestamp; esto no demuestra TLS.
- No se verificó un dominio propio ni certificados confiables del navegador.
- La Function de Azure usa inventario simulado; un pedido AWS sin SKU/cantidades fue aceptado como evento y concluyó `awaiting_items`, sin modificar stock.
- El paquete incluye envío opcional por SMTP, pero el template no aprovisiona ni configura relay, dominio, destinatarios o buzones; el correo interno del portal no equivale a SMTP corporativo.
- `InternalErpEnabled=false` desactiva las rutas ERP.

`destroy.sh` bloquea por defecto y no tiene `STACK_NAME` predeterminado. Requiere un nombre verificado con formato `tangamandapio-live-YYYYMMDD`, `CONFIRM_DELETE_DATA=true` y que `CONFIRM_STACK_NAME` coincida exactamente con `STACK_NAME`. Antes de tocar buckets u otros stacks, inspecciona el template realmente desplegado y se niega a continuar si RDS no tiene `DeletionPolicy: Snapshot` y `UpdateReplacePolicy: Snapshot`, o si los secretos de RDS/admin no tienen `DeletionPolicy` y `UpdateReplacePolicy: Retain`. CloudFormation conserva un snapshot final al retirar la base; `PRESERVE_RDS_SNAPSHOT=true` además crea un snapshot manual previo. El script **nunca elimina snapshots manuales**. El apagado sí borra versiones de buckets, el stack de grabaciones y su bucket retenido, y la clave Azure externa de Secrets Manager/SSM; revisa y archiva los objetos que deban conservarse antes de confirmar. La plantilla configura `DeleteAutomatedBackups: true` para las reconstrucciones. Los pedidos y cuentas quedan dentro del snapshot, no disponibles en línea.

## Último release sano confirmado antes del despliegue final v11 — histórico

El último corte sano confirmado fue v10, con CloudFormation `UPDATE_COMPLETE`,
drift `IN_SYNC` y dos destinos saludables. Ese estado es anterior al intento
v11 y no prueba que v10 se haya restaurado. El artefacto v11 legado
(`2a834...`) se publicó y su actualización quedó sin resultado final
verificable; el artefacto portable candidato (`ef3ffe...`) y la política de
Instance Refresh reforzada son locales, aún no publicados. Mantén la
[evidencia detallada v11](../../evidence/current/aws/AWS-DESPLIEGUE-V11-2026-10-14.md)
como fuente de estado más reciente. La evidencia de v9/v10 describe cortes
históricos; no la uses como prueba de salud actual.
