# Terraform para Azure y conectividad

| Raíz | Administra |
|---|---|
| [azure-rebuild](../../../iac/environments/azure-rebuild) | Servicios compartidos del WMS, Storage, Queue, Key Vault y Application Insights. La Function Consumption anterior queda deshabilitada en esta raíz. |
| [azure-private-network](../../../iac/environments/azure-private-network) | VNet, subredes y Key Vault de red. |
| [azure-flex-private](../../../iac/environments/azure-flex-private) | Function Flex, identidad administrada, Private Endpoint y DNS privado. |
| [aws-azure-tailscale](../../../iac/environments/aws-azure-tailscale) | Routers, conectividad y dependencias que pertenezcan a este estado. |

## Validar una raíz

Desde la raíz del repositorio, en una copia de trabajo para validación:

~~~powershell
terraform -chdir=iac/environments/azure-flex-private init -backend=false
terraform -chdir=iac/environments/azure-flex-private validate
~~~

## Revisar un cambio antes de aplicar

1. Confirma la suscripción y el backend. Para ensayos, usa un estado independiente y nombres de recursos propios.
2. Inicializa la raíz con su backend configurado y genera un plan con las variables autorizadas. Revisa deployment_approved y los controles de costo de la raíz.
3. Comprueba cambios y reemplazos de Storage, VNet, Key Vault y Private Endpoints. Mantén estados, planes y variables privadas fuera de Git.
4. Sigue la [guía de publicación de Flex](../../../iac/environments/azure-flex-private/README.md#publicar-en-la-function-privada) para generar el ZIP y publicarlo con [OneDeploy](../../../iac/environments/azure-flex-private/onedeploy.json).
5. Sincroniza la clave del WMS en Secrets Manager y verifica HTTPS privado desde ambas EC2. Continúa según el [orden de reconstrucción](../README.md#orden-de-reconstrucción).
