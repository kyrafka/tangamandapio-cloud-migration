# AWS CloudFormation — portal y recuperación

**Corte vigente 16/11/2026:** la cuenta activa es `481056890449`, región `us-east-2`; CloudFormation administra el portal y ASG en estado sano. La prueba de carga llegó a 5 instancias y volvió automáticamente a 2, aunque el ensayo largo registró 1,47% de errores. RDS está disponible, cifrada, Single-AZ y con retención de 1 día. No está implementado el respaldo automático cifrado PostgreSQL→Azure Blob ni una restauración aislada. La ruta privada AWS→Azure y el failover desde AWS siguen pendientes. SNS todavía requiere confirmación del correo; ACM espera el CNAME que el usuario pidió dejar para después. Ver el [estado real completo](../ESTADO_REAL_2026-11-16.md). Los párrafos fechados de octubre y principios de noviembre que aparecen más abajo son registros históricos, no estado actual.

## Qué administra

`aws-lab.yaml` es la plantilla principal del portal. Define su red, ALB, EC2/Auto Scaling, PostgreSQL RDS, almacenamiento, seguridad, alarmas y salidas. La plantilla incluye el escalado por carga del ALB y por CPU; un umbral definido en código no demuestra que el ASG haya escalado bajo una carga real.

Plantillas auxiliares:

- `voice-recordings.yaml`: bucket y políticas para grabaciones consentidas; es un stack separado.
- `aws-azure-vpn.yaml`: diseño de AWS Site-to-Site administrada. La cuenta AWS Academy denegó crear el Customer Gateway; no se debe afirmar que está desplegada.
- `aws-azure-p2s-router.yaml`: infraestructura base para el router EC2 de la alternativa Azure P2S. Requiere configurar el perfil y certificados OpenVPN fuera del repositorio; crear la instancia no crea por sí solo un túnel funcional.
- Los prototipos locales de IPsec/WireGuard no están validados de extremo a extremo y no forman parte de la IaC publicada.

## Estado operativo conocido

La verificación viva del 16/11 consultó la cuenta `481056890449` con el perfil `main`. El stack principal figura `UPDATE_COMPLETE`; el ASG tiene dos instancias y dos destinos saludables, con capacidad min 2 / desired 2 / max 5. RDS está disponible, cifrada, Single-AZ y con un día de retención. El escalado 2→4→5 y el scale-in 5→4→3→2 fueron automáticos. La prueba de 300.000 solicitudes tuvo 1,47% de errores; el postcheck de 3.000 tuvo cero. CloudFormation drift quedó `IN_SYNC` con cero recursos desviados. Esto no demuestra ruta privada hacia Azure, recuperación regional ni restore de RDS desde Blob.

## Preparar un cambio

1. Verifica la sesión, la cuenta y la región con credenciales temporales del laboratorio; nunca copies el token al repo ni a comandos guardados.
2. Obtén el nombre exacto del stack vivo. No uses un nombre de ejemplo ni supongas que el stack existe.
3. Ejecuta `deploy.sh` para generar/revisar el change set. El primer paso no lo aplica. Comprueba especialmente reemplazos de RDS, VPC, ALB, almacenamiento o recursos con datos.
4. Para aplicar, repite solo después de revisar el plan, con `APPLY_CHANGE_SET=true`, `CONFIRM_STACK_NAME` idéntico y la confirmación interactiva solicitada por el script.
5. Comprueba salud externa, destinos del ALB, actividad del ASG, RDS y alarmas después del cambio.

El script conserva parámetros existentes con `UsePreviousValue` y tiene preflight para nombre del stack y HTTPS. Los overrides de Multi-AZ, días de backup, WAF y AWS Backup pueden cambiar costos; revisa el change set y la factura del laboratorio antes de usarlos.

## Reconstruir

`rebuild.sh` requiere un nombre nuevo explícito y se detiene ante errores de autenticación, red o permisos. La plantilla usa `BootstrapMode` para crear primero la infraestructura sin instancias. Publica el paquete versionado antes de habilitar EC2. `package_portal_artifact.sh` crea el release localmente o lo publica en el bucket indicado.

El valor predeterminado para un laboratorio sigue siendo Single-AZ y un día de retención. El RDS en producción ya usa Multi-AZ y conserva un día de retención. Usar `DATABASE_MULTI_AZ=true` en el próximo conjunto de cambios del stack de producción y revisar las acciones antes de ejecutarlo. La conversión directa quedó completa. El conjunto de cambios que intentó adoptar el estado también propuso reemplazos de red y cambios en SNS, por lo que la sincronización del parámetro del stack sigue pendiente.

Para recuperar **Administración → Respaldos**, pasa
`ADMIN_AZURE_BACKUP_ACCOUNT=sttangama261030r` y, si cambia el nombre por
defecto, `ADMIN_AZURE_BACKUP_CONTAINER=tangama-postgres-backups`. Restaura el
permiso de lectura fuera de CloudFormation en el parámetro cifrado
`/tangamandapio/dr/blob-read/portal`. La escritura diaria usa otra
autorización y la [pila de respaldo programado](aws-azure-postgres-backup.yaml).

La revisión activa registrada es `20261119-order-tracking-and-contingency`.
El [registro operativo](../ESTADO_REAL_2026-11-19.md) enlaza el paquete y la
prueba del pedido privado. La reconstrucción empaqueta el código versionado
del repositorio y calcula el SHA-256 antes de habilitar EC2.

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
EXPECTED_AWS_ACCOUNT_ID=123456789012 STACK_NAME=tangamandapio-live-20261104 \
  AZURE_FULFILLMENT_URL=https://your-function.azurewebsites.net \
  AZURE_FUNCTION_KEY_SECRET=tangamandapio/azure/function-key \
  CERTIFICATE_ARN=arn:aws:acm:us-east-1:123456789012:certificate/00000000-0000-0000-0000-000000000000 \
  PORTAL_DOMAIN_NAME=portal.example.com \
  ALARM_NOTIFICATION_EMAIL_PRIMARY=operador@example.com \
  ALARM_NOTIFICATION_EMAIL_ALTERNATE=alterno@example.com \
  bash iac/cloudformation/lifecycle.sh up
```

```bash
EXPECTED_AWS_ACCOUNT_ID=123456789012 STACK_NAME=tangamandapio-live-20261104 \
  CONFIRM_STACK_NAME=tangamandapio-live-20261104 CONFIRM_DELETE_DATA=true PURGE_PROJECT_RESOURCES=true \
  bash iac/cloudformation/lifecycle.sh down
```

`up` crea un stack ausente y requiere la confirmación `CREATE <stack>`. Para HTTPS, el certificado y el dominio deben proporcionarse juntos: el script comprueba región, estado `ISSUED` y cobertura del nombre antes de crear el stack. Sin ambos parámetros el ALB queda solo con HTTP. El ARN puede cambiar tras un reinicio de cuenta. Los correos SNS son opcionales y no se guardan en el código: cada suscripción nueva requiere confirmar el mensaje de AWS. Las dos suscripciones actuales se crearon directamente en SNS y no son parámetros de la pila actual; una pila recreada debe recibir los correos para volver a registrarlas. También exige `RDS_SNAPSHOT_IDENTIFIER`, salvo que definas `ALLOW_EMPTY_DATABASE=true` y aceptes explícitamente una base vacía. `down` requiere `DELETE ALL <stack>` además de las confirmaciones de borrado; elimina snapshots y recovery points del proyecto, vacía los buckets del portal/grabaciones y conserva Secrets Manager/SSM por defecto. Para borrar credenciales, define `PURGE_PROJECT_SECRETS=true`, `CONFIRM_PURGE_PROJECT_SECRETS=<stack>` y confirma `DELETE ALL INCLUDING SECRETS <stack>`. No elimina recursos de Azure ni stacks ajenos.

El borrado necesita Python 3 con PyYAML para comprobar las políticas del template antes de tocar recursos. Usa `TANGAMA_PYTHON` si el intérprete no está en el PATH; en esta máquina, desde Git Bash, puede usarse `TANGAMA_PYTHON='/c/Program Files/Microsoft SDKs/Azure/CLI2/python.exe'`. El script se detiene si no puede cargar PyYAML.

## Destruir de forma controlada

`destroy.sh` bloquea por defecto, exige `EXPECTED_AWS_ACCOUNT_ID`, `STACK_NAME` explícito y confirmaciones coincidentes. Verifica que la base tenga políticas de snapshot y los secretos estén retenidos durante el borrado del stack. Si la deriva aún está `NOT_CHECKED`, inicia una detección y espera el resultado; cualquier estado distinto a `IN_SYNC` detiene el proceso antes de vaciar buckets. Luego purga snapshots y backups; las credenciales de Secrets Manager/SSM se conservan salvo que `PURGE_PROJECT_SECRETS=true` y una confirmación independiente identifique exactamente el stack.

En la revisión histórica del 04/11/2026 el inventario inicial mostró el stack `tangamandapio-live-20261104` con 49 recursos, grabaciones activas, ASG en 0, RDS disponible/Multi-AZ y WAF asociado. Después se recuperaron dos instancias; una prueba de 10.000 solicitudes a `/health` obtuvo 200 pero no escaló y sí consultó RDS. En ese momento no se encontró un túnel privado; el piloto Tailscale se verificó posteriormente. `us-west-2` no tenía una pila Tangamandapio. El registro de borrado previo fue seguido por esta nueva reconstrucción, así que no prueba apagado actual. No existe un ciclo integral probado que levante y elimine también VPN y recuperación regional.

No destruyas una cuenta si el snapshot, artefacto, DNS, secretos y procedimiento de reconstrucción no están comprobados. El token temporal de AWS Academy no es un respaldo y puede expirar o perder permisos.

## Dominio y HTTPS

El dominio `tangamandapio.kendellnm.me` respondió HTTPS 200 en `/` y `/health` el 29/10/2026. El certificado y la respuesta pública funcionaron; por la denegación de inventario AWS no se pudo comprobar desde AWS el listener, los destinos ni el certificado ACM. No cambies Cloudflare mientras no haya permiso de solo lectura. El DNS proxied no debe apuntar a una IP fija del borde. Los CNAME de validación ACM permanecen DNS-only.

Para otro hostname, solicita en ACM `us-east-1` un certificado para el nombre exacto, publica el CNAME de validación DNS-only, espera `ISSUED`, genera y revisa un change set que conecte el listener HTTPS y solo entonces configura el CNAME del subdominio hacia el DNS del ALB. Conserva intactos nombres que ya use otro proyecto.

## Validación local de plantillas

Las plantillas se pueden revisar con CloudFormation Linter/`validate-template` y los roots Terraform con `fmt`, `init`, `validate` y tests con mocks. Estas verificaciones no despliegan recursos ni sustituyen un change set, un plan contra el estado correcto o una prueba viva. No se ejecutó `apply` durante esta actualización documental.
