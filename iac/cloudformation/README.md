# AWS CloudFormation — portal y recuperación

**Entorno verificado el 22/11/2026.** El stack activo es `tangamandapio-live-20261116` en `us-east-2`.
El portal tiene dos destinos sanos, RDS Multi-AZ está disponible con un día de
retención, la VPN Tailscale transporta los eventos privados y la copia diaria
cifrada de Blob permitió recuperar el ERP. El parámetro `DatabaseMultiAZ` del
stack es `true`. [Verificación operativa del 22/11](../../Proyecto_Cloud_Tangamandapio/06_Pruebas/Verificacion_Operativa_2026-11-22.json).

## Qué administra

`aws-lab.yaml` es la plantilla principal del portal. Define su red, ALB, EC2/Auto Scaling, PostgreSQL RDS, almacenamiento, seguridad, alarmas y salidas. La plantilla incluye el escalado por carga del ALB y por CPU; un umbral definido en código no demuestra que el ASG haya escalado bajo una carga real.

Plantillas auxiliares:

- `voice-recordings.yaml`: bucket y políticas para grabaciones consentidas; es un stack separado.
- `aws-azure-vpn.yaml`: diseño de AWS Site-to-Site administrada. La cuenta AWS Academy denegó crear el Customer Gateway; no se debe afirmar que está desplegada.
- `aws-azure-p2s-router.yaml`: infraestructura base para el router EC2 de la alternativa Azure P2S. Requiere configurar el perfil y certificados OpenVPN fuera del repositorio; crear la instancia no crea por sí solo un túnel funcional.
- Los prototipos locales de IPsec/WireGuard no están validados de extremo a extremo y no forman parte de la IaC publicada.

## Preparar un cambio

1. Verifica la sesión, la cuenta y la región con credenciales temporales de la cuenta de destino; nunca copies el token al repo ni a comandos guardados.
2. Obtén el nombre exacto del stack vivo. No uses un nombre de ejemplo ni supongas que el stack existe.
3. Ejecuta `deploy.sh` para generar/revisar el change set. El primer paso no lo aplica. Comprueba especialmente reemplazos de RDS, VPC, ALB, almacenamiento o recursos con datos.
4. Para aplicar, repite solo después de revisar el plan, con `APPLY_CHANGE_SET=true`, `CONFIRM_STACK_NAME` idéntico y la confirmación interactiva solicitada por el script.
5. Comprueba salud externa, destinos del ALB, actividad del ASG, RDS y alarmas después del cambio.

Para una reconstrucción equivalente a producción, configura
`DATABASE_MULTI_AZ=true`. El valor predeterminado del laboratorio permite
ensayos con una sola zona y menor consumo. Tras crear el stack de producción,
aplica [la política de protección de RDS](production-database-stack-policy.json)
con `aws cloudformation set-stack-policy`. La política impide el reemplazo o
retiro de `Database` durante actualizaciones del stack. El borrado del stack
tiene controles independientes. [Políticas de stack de CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/protect-stack-resources.html).

```powershell
aws cloudformation set-stack-policy --stack-name tangamandapio-live-20261116 --profile main --region us-east-2 --stack-policy-body file://iac/cloudformation/production-database-stack-policy.json
```

### Separar los permisos de PostgreSQL

1. Crea el stack de secretos con [postgres-runtime-credentials.yaml](postgres-runtime-credentials.yaml). Conserva los `RuntimeSecretArn` y `BackupSecretArn` de las salidas. Secrets Manager genera ambos valores. El secreto propietario queda disponible para aplicar migraciones con autorización de operación.
2. Desde un host autorizado en la VPC, aplica las migraciones y prepara las tablas ERP con la cuenta propietaria. En una instalación vacía, el modo inicial del portal usa `DATABASE_SCHEMA_MODE=migrate`. Luego ejecuta [provision_postgres_runtime.py](../scripts/provision_postgres_runtime.py) con la cuenta, región, hostname de RDS y los tres ARNs. El script exige las migraciones previas, aplica `0010`, crea los dos roles, registra sus permisos y comprueba conexiones con TLS `verify-full`. Ejecuta primero en modo de inspección y repite con `--apply`.
3. Publica una copia del paquete del exportador que ya contiene `postgres_blob_export.py` con soporte para `DB_BACKUP_SECRET_ARN`. Actualiza su hash y clave en `aws-azure-postgres-backup.yaml`. Verifica la versión predeterminada del documento SSM antes del recambio de aplicaciones.
4. En el cambio del stack del portal, pasa `DATABASE_RUNTIME_SECRET_ARN` y `DATABASE_BACKUP_SECRET_ARN` a `deploy.sh`. Si estás reemplazando una flota que sigue usando el propietario, pasa además `RETAIN_LEGACY_DATABASE_SECRET_ACCESS=true`. Este permiso transitorio conserva las EC2 anteriores mientras se verifica el reemplazo. Confirma ambas instancias, sus módulos y el exportador con el lector dedicado.
5. Retira el permiso transitorio mediante un segundo cambio con `RETAIN_LEGACY_DATABASE_SECRET_ACCESS=false`. Revisa que el plan afecte únicamente a IAM. Comprueba que el rol de las EC2 pueda leer los secretos de ejecución y copia y reciba acceso denegado al propietario. Tras una migración posterior, vuelve a aplicar [los permisos SQL vigentes](../scripts/postgres_runtime_privileges.sql) para que las nuevas tablas y secuencias tengan sus permisos antes del despliegue.

```powershell
python iac/scripts/provision_postgres_runtime.py --account $account --region us-east-2 --host $rdsEndpoint --database tangamandapio --owner $ownerSecretArn --runtime $runtimeSecretArn --backup $backupSecretArn --migrations app/aws_release/current/migrations/postgres --privileges iac/scripts/postgres_runtime_privileges.sql --apply
```

El operador de este comando debe poder leer los tres secretos durante el
aprovisionamiento. Para la ejecución diaria, el ERP verifica el registro de
migraciones y trabaja con permisos de datos. El exportador usa el lector SQL
dedicado. [Privilegios en PostgreSQL](https://www.postgresql.org/docs/18/sql-grant.html) ·
[Verificación TLS de Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html).

El script conserva parámetros existentes con `UsePreviousValue` y tiene preflight para nombre del stack y HTTPS. Los overrides de Multi-AZ, días de backup, WAF y AWS Backup pueden cambiar costos; revisa el change set y la factura del laboratorio antes de usarlos.

## Reconstruir

`rebuild.sh` requiere un nombre nuevo explícito y se detiene ante errores de autenticación, red o permisos. La plantilla usa `BootstrapMode` para crear primero la infraestructura sin instancias. Publica el paquete versionado antes de habilitar EC2. `package_portal_artifact.sh` crea el release localmente o lo publica en el bucket indicado.

El valor predeterminado para un laboratorio sigue siendo Single-AZ y un día de retención. El RDS en producción ya usa Multi-AZ y conserva un día de retención. Usar `DATABASE_MULTI_AZ=true` en el próximo conjunto de cambios del stack de producción y revisar las acciones antes de ejecutarlo. Revisa que el conjunto de cambios conserve Multi-AZ y las suscripciones SNS requeridas.

Para recuperar **Administración → Respaldos**, pasa
`ADMIN_AZURE_BACKUP_ACCOUNT=sttangama261030r` y, si cambia el nombre por
defecto, `ADMIN_AZURE_BACKUP_CONTAINER=tangama-postgres-backups`. Restaura el
permiso de lectura fuera de CloudFormation en el parámetro cifrado
`/tangamandapio/dr/blob-read/portal`. La escritura diaria usa otra
autorización y la [pila de respaldo programado](aws-azure-postgres-backup.yaml).

El [índice de operación](../../Proyecto_Cloud_Tangamandapio/04_IaC/cloudformation/README.md) identifica el stack vigente y los pasos actuales. Empaqueta y verifica el SHA-256 del artefacto antes de habilitar EC2.

La IaC no contiene datos ni todos los insumos de recuperación. Antes de reconstruir:

- Identifica y valida el snapshot de RDS que debe conservarse; prepara una restauración aislada y comprueba sus datos.
- Recupera o vuelve a crear de forma segura los secretos del administrador, RDS y Azure Function. No restablezcas credenciales accidentalmente.
- Genera un paquete del portal y paquetes de Functions con versiones fijadas.
- Reemite certificados privados del piloto VPN y configúralos fuera de Git.
- Valida el certificado ACM, el DNS y el listener HTTPS para el hostname que se usará.

No se ha demostrado una reconstrucción integral desde una cuenta limpia. El fixture S3→Blob no reemplaza backup ni restauración de RDS.

### Lanzador guiado de ciclo de vida

`lifecycle.sh` comprueba la cuenta AWS esperada antes de delegar en `rebuild.sh` o `destroy.sh`. Ejecuta desde Git Bash/WSL con el perfil temporal ya cargado; no guarda credenciales. El aviso del comando aclara el límite: AWS en una región; no despliega la VPN, la recuperación regional, las raíces Azure ni finaliza el laboratorio Academy. No es un lanzador multinube integral. Ejemplos:

```bash
AWS_REGION=us-east-2 EXPECTED_AWS_ACCOUNT_ID=123456789012 STACK_NAME=tangamandapio-ensayo \
  AZURE_FULFILLMENT_URL=https://your-function.azurewebsites.net \
  AZURE_FUNCTION_KEY_SECRET=tangamandapio/azure/function-key \
  CERTIFICATE_ARN=arn:aws:acm:us-east-2:123456789012:certificate/00000000-0000-0000-0000-000000000000 \
  PORTAL_DOMAIN_NAME=portal.example.com \
  ALARM_NOTIFICATION_EMAIL_PRIMARY=operador@example.com \
  ALARM_NOTIFICATION_EMAIL_ALTERNATE=alterno@example.com \
  bash iac/cloudformation/lifecycle.sh up
```

```bash
AWS_REGION=us-east-2 EXPECTED_AWS_ACCOUNT_ID=123456789012 STACK_NAME=tangamandapio-ensayo \
  CONFIRM_STACK_NAME=tangamandapio-ensayo CONFIRM_DELETE_DATA=true PURGE_PROJECT_RESOURCES=true \
  bash iac/cloudformation/lifecycle.sh down
```

`up` crea un stack ausente y requiere la confirmación `CREATE <stack>`. Para HTTPS, el certificado y el dominio deben proporcionarse juntos: el script comprueba región, estado `ISSUED` y cobertura del nombre antes de crear el stack. Sin ambos parámetros el ALB queda solo con HTTP. El ARN puede cambiar tras un reinicio de cuenta. Los correos SNS son opcionales y no se guardan en el código: cada suscripción nueva requiere confirmar el mensaje de AWS. Las dos suscripciones actuales se crearon directamente en SNS y no son parámetros de la pila actual; una pila recreada debe recibir los correos para volver a registrarlas. También exige `RDS_SNAPSHOT_IDENTIFIER`, salvo que definas `ALLOW_EMPTY_DATABASE=true` y aceptes explícitamente una base vacía. `down` requiere `DELETE ALL <stack>` además de las confirmaciones de borrado; elimina snapshots y recovery points del proyecto, vacía los buckets del portal/grabaciones y conserva Secrets Manager/SSM por defecto. Para borrar credenciales, define `PURGE_PROJECT_SECRETS=true`, `CONFIRM_PURGE_PROJECT_SECRETS=<stack>` y confirma `DELETE ALL INCLUDING SECRETS <stack>`. No elimina recursos de Azure ni stacks ajenos.

El borrado necesita Python 3 con PyYAML para comprobar las políticas del template antes de tocar recursos. Usa `TANGAMA_PYTHON` si el intérprete no está en el PATH; en esta máquina, desde Git Bash, puede usarse `TANGAMA_PYTHON='/c/Program Files/Microsoft SDKs/Azure/CLI2/python.exe'`. El script se detiene si no puede cargar PyYAML.

## Destruir de forma controlada

`destroy.sh` bloquea por defecto, exige `EXPECTED_AWS_ACCOUNT_ID`, `STACK_NAME` explícito y confirmaciones coincidentes. Verifica que la base tenga políticas de snapshot y los secretos estén retenidos durante el borrado del stack. Si la deriva aún está `NOT_CHECKED`, inicia una detección y espera el resultado; cualquier estado distinto a `IN_SYNC` detiene el proceso antes de vaciar buckets. Luego purga snapshots y backups; las credenciales de Secrets Manager/SSM se conservan salvo que `PURGE_PROJECT_SECRETS=true` y una confirmación independiente identifique exactamente el stack.

No destruyas una cuenta si el snapshot, artefacto, DNS, secretos y procedimiento de reconstrucción no están comprobados. El token temporal de AWS Academy no es un respaldo y puede expirar o perder permisos.

## Dominio y HTTPS

El entorno operativo usa HTTPS en Ohio. Los CNAME de validación ACM permanecen DNS-only.

Para otro hostname, solicita en ACM us-east-2 un certificado para el nombre exacto, publica el CNAME de validación DNS-only, espera `ISSUED`, genera y revisa un change set que conecte el listener HTTPS y solo entonces configura el CNAME del subdominio hacia el DNS del ALB. Conserva intactos nombres que ya use otro proyecto.

## Validación local de plantillas

Las plantillas se pueden revisar con CloudFormation Linter/`validate-template` y los roots Terraform con `fmt`, `init`, `validate` y tests con mocks. Estas verificaciones no despliegan recursos ni sustituyen un change set, un plan contra el estado correcto o una prueba viva. No se ejecutó `apply` durante esta actualización documental.
