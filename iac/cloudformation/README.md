# AWS CloudFormation — portal y recuperación

## Qué administra

`aws-lab.yaml` es la plantilla principal del portal. Define su red, ALB, EC2/Auto Scaling, PostgreSQL RDS, almacenamiento, seguridad, alarmas y salidas. La plantilla incluye el escalado por carga del ALB y por CPU; un umbral definido en código no demuestra que el ASG haya escalado bajo una carga real.

Plantillas auxiliares:

- `voice-recordings.yaml`: bucket y políticas para grabaciones consentidas; es un stack separado.
- `aws-azure-vpn.yaml`: diseño de AWS Site-to-Site administrada. La cuenta AWS Academy denegó crear el Customer Gateway; no se debe afirmar que está desplegada.
- `aws-azure-p2s-router.yaml`: infraestructura base para el router EC2 de la alternativa Azure P2S. Requiere configurar el perfil y certificados OpenVPN fuera del repositorio; crear la instancia no crea por sí solo un túnel funcional.
- Los prototipos locales de IPsec/WireGuard no están validados de extremo a extremo y no forman parte de la IaC publicada.

## Estado operativo conocido

El último inventario documentado (27/10/2026) registra ALB/HTTPS, WAF asociado, dos instancias deseadas en un ASG de máximo cinco y RDS Multi-AZ cifrado con siete días de retención. En el reintento del 29/10, STS autenticó en una cuenta distinta del inventario histórico, pero la política explícita `voc-cancel-cred` bloqueó el inventario. En la comprobación pública, `/` y `/health` devolvieron HTTP 200; esto confirma respuesta del endpoint, no el estado de RDS, ALB targets, ASG ni WAF. No se aplicó infraestructura.

## Preparar un cambio

1. Verifica la sesión, la cuenta y la región con credenciales temporales del laboratorio; nunca copies el token al repo ni a comandos guardados.
2. Obtén el nombre exacto del stack vivo. No uses un nombre de ejemplo ni supongas que el stack existe.
3. Ejecuta `deploy.sh` para generar/revisar el change set. El primer paso no lo aplica. Comprueba especialmente reemplazos de RDS, VPC, ALB, almacenamiento o recursos con datos.
4. Para aplicar, repite solo después de revisar el plan, con `APPLY_CHANGE_SET=true`, `CONFIRM_STACK_NAME` idéntico y la confirmación interactiva solicitada por el script.
5. Comprueba salud externa, destinos del ALB, actividad del ASG, RDS y alarmas después del cambio.

El script conserva parámetros existentes con `UsePreviousValue` y tiene preflight para nombre del stack y HTTPS. Los overrides de Multi-AZ, días de backup, WAF y AWS Backup pueden cambiar costos; revisa el change set y la factura del laboratorio antes de usarlos.

## Reconstruir

`rebuild.sh` requiere un nombre nuevo explícito y se detiene ante errores de autenticación, red o permisos. La plantilla usa `BootstrapMode` para crear primero la infraestructura sin instancias; publica el paquete versionado antes de habilitar la capacidad de EC2. `package_portal_artifact.sh` crea el release localmente o lo publica en un bucket cuando se le proporcionan parámetros explícitos.

La IaC no contiene datos ni todos los insumos de recuperación. Antes de reconstruir:

- Identifica y valida el snapshot de RDS que debe conservarse; prepara una restauración aislada y comprueba sus datos.
- Recupera o vuelve a crear de forma segura los secretos del administrador, RDS y Azure Function. No restablezcas credenciales accidentalmente.
- Genera un paquete del portal y paquetes de Functions con versiones fijadas.
- Reemite certificados privados del piloto VPN y configúralos fuera de Git.
- Valida el certificado ACM, el DNS y el listener HTTPS para el hostname que se usará.

No se ha demostrado una reconstrucción integral desde una cuenta limpia. El fixture S3→Blob no reemplaza backup ni restauración de RDS.

## Destruir de forma controlada

`destroy.sh` bloquea por defecto, exige `STACK_NAME` explícito y confirmaciones coincidentes. Verifica que la base tenga políticas de snapshot y que los secretos se retengan; puede crear un snapshot manual previo cuando se solicita. No borra snapshots manuales. Sin embargo, eliminar stacks puede borrar versiones de buckets, instancias, rutas y recursos auxiliares; archiva primero los artefactos necesarios y revisa cada acción.

No destruyas una cuenta si el snapshot, artefacto, DNS, secretos y procedimiento de reconstrucción no están comprobados. El token temporal de AWS Academy no es un respaldo y puede expirar o perder permisos.

## Dominio y HTTPS

El dominio `tangamandapio.kendellnm.me` respondió HTTPS 200 en `/` y `/health` el 29/10/2026. El certificado y la respuesta pública funcionaron; por la denegación de inventario AWS no se pudo comprobar desde AWS el listener, los destinos ni el certificado ACM. No cambies Cloudflare mientras no haya permiso de solo lectura. El DNS proxied no debe apuntar a una IP fija del borde. Los CNAME de validación ACM permanecen DNS-only.

Para otro hostname, solicita en ACM `us-east-1` un certificado para el nombre exacto, publica el CNAME de validación DNS-only, espera `ISSUED`, genera y revisa un change set que conecte el listener HTTPS y solo entonces configura el CNAME del subdominio hacia el DNS del ALB. Conserva intactos nombres que ya use otro proyecto.

## Validación local de plantillas

Las plantillas se pueden revisar con CloudFormation Linter/`validate-template` y los roots Terraform con `fmt`, `init`, `validate` y tests con mocks. Estas verificaciones no despliegan recursos ni sustituyen un change set, un plan contra el estado correcto o una prueba viva. No se ejecutó `apply` durante esta actualización documental.
