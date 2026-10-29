# AWS — ejecución y recuperación

## Estado comprobable al 29/10/2026

La última comprobación pública del portal HTTPS devolvió HTTP 503. AWS STS autenticó la sesión del laboratorio, pero las consultas `List`/`Describe` necesarias para inventariar recursos fueron denegadas por una política explícita. Por tanto, el inventario del 27/10 —ALB, WAF, ASG con dos instancias deseadas/máximo cinco y RDS Multi-AZ cifrado con siete días de retención— es histórico, no una afirmación del estado actual.

No se aplicó ni destruyó infraestructura durante la actualización documental. Revisa el [estado integral de IaC](../iac/README.md) antes de ejecutar comandos.

## Fuente de despliegue

CloudFormation administra el portal AWS mediante [`iac/cloudformation/aws-lab.yaml`](../iac/cloudformation/aws-lab.yaml). Usa los scripts del mismo directorio:

- `deploy.sh`: valida y prepara un change set; revisar los cambios antes de aplicar.
- `package_portal_artifact.sh`: crea el paquete reproducible de la aplicación.
- `rebuild.sh`: reconstruye un stack ausente en etapas y requiere nombre explícito.
- `destroy.sh`: elimina recursos con confirmaciones y políticas de preservación de datos.

No mezcles el entorno `iac/environments/demo` de Terraform con el stack principal. No uses un nombre de stack supuesto, ni apliques cambios cuando el inventario no es legible.

## Secuencia para la próxima sesión de laboratorio

1. Iniciar el laboratorio y obtener credenciales temporales por su canal oficial; no guardarlas en Git ni en bitácoras compartidas.
2. Comprobar STS, cuenta y región. Si `List`/`Describe` falla por IAM/SCP, detener cambios y solicitar permisos o inventario por consola.
3. Inventariar CloudFormation, EC2/ASG, ALB/targets, RDS/snapshots, S3, Secrets Manager, WAF, alarmas y SNS.
4. Comparar los recursos reales con el change set de `aws-lab.yaml`. Revisar reemplazos, snapshots, artefacto, secretos y costos.
5. Desplegar solo después del preflight; verificar targets, `/health`, `/ready`, login, datos y alertas.
6. Para destruir, validar antes el snapshot de RDS y que los objetos/artefactos necesarios estén respaldados; luego comprobar el inventario final y el consumo.

## Límites de capacidad y servicios

El ASG tiene política para escalar por carga del ALB, pero el ajuste en plantilla no prueba el cambio automático 2→3. La evidencia anterior indicó que RDS saturó antes de demostrar ese cambio; repetir una carga gradual solo después de vigilar CPU, conexiones, latencia y errores de RDS.

No hay evidencia de SQS + Lambda + DLQ del proyecto. La cuenta académica había denegado crear y pasar un rol de ejecución mínimo; no se debe sustituir por `LabRole` amplio ni eludir la política. Azure Functions cubre el procesamiento serverless Azure, pero no una rúbrica que exija Lambda explícitamente.

La VPN administrada AWS Site-to-Site no está verificada. La alternativa Azure P2S + router EC2 tiene su propio runbook y no debe presentarse como S2S/BGP.
