# CloudFormation para AWS

La [plantilla del portal](../../../iac/cloudformation/aws-lab.yaml) administra el stack tangamandapio-live-20261116 en AWS Ohio. Sus pilas auxiliares cubren el [respaldo cifrado](../../../iac/cloudformation/aws-azure-postgres-backup.yaml), el [DNS privado del WMS](../../../iac/cloudformation/aws-private-wms-dns.yaml) y el [registro de WAF](../../../iac/cloudformation/aws-waf-logging.yaml).

## Consultar el entorno

Desde Git Bash o WSL, con AWS CLI y acceso autorizado:

~~~bash
export AWS_PROFILE=main
export AWS_REGION=us-east-2
aws sts get-caller-identity
aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name tangamandapio-live-20261116 --query 'Stacks[0].StackStatus'
~~~

## Preparar un despliegue

1. Confirma cuenta y región. Empaqueta el portal con [package_portal_artifact.sh](../../../iac/cloudformation/package_portal_artifact.sh).
2. Prepara un snapshot aprobado de RDS, dominio y certificado ACM de Ohio. Ten disponibles el hostname de la Function y el nombre de su secreto en AWS Secrets Manager.
3. Para una pila nueva, sigue la sección **Reconstruir** de la [guía del lanzador](../../../iac/cloudformation/README.md#reconstruir). La plantilla principal supera el tamaño admitido para enviarla inline. Usa el mecanismo S3 del lanzador.
4. Para una pila existente, revisa el conjunto de cambios antes de ejecutarlo. Comprueba reemplazos de RDS, red y ALB. Confirma dos destinos sanos y HTTP 200 en /ready después del cambio.

El entorno opera con DatabaseMultiAZ=true. Establece DATABASE_MULTI_AZ=true al recrear esa modalidad. Los datos, secretos, artefactos, DNS y certificado requieren pasos propios.
