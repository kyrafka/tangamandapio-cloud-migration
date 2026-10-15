# Azure Functions Flex — migración blue-green privada

Este entorno crea una Function Flex nueva, sin reemplazar la Function `Y1`
activa. La versión verde usa la subnet `snet-flex-functions` delegada a
`Microsoft.App/environments`, identidad administrada para host/deployment
storage, Application Insights con Entra ID, un Private Endpoint en
`snet-private-endpoints` y la zona privada `privatelink.azurewebsites.net`.
La integración de la subnet es salida; el Private Endpoint habilita ingreso
privado.

El estado final de Terraform bloquea el acceso público. La única excepción es
el primer despliegue del paquete: Azure CLI necesita llegar al endpoint de
deployment/SCM. Para esa fase se exige habilitar dos variables explícitas; una
vez publicado el paquete y probado el endpoint privado desde AWS, se reaplica
con `bootstrap_public_access_enabled=false`. No se configura un `WEBSITE_RUN_FROM_PACKAGE`
externo: Flex usa package deployment y un contenedor privado exclusivo para
esta Function; `storage_container_endpoint` se construye con el endpoint HTTPS
del Blob Account y el nombre del contenedor, no con el ID ARM del contenedor.

## Dependencias y límites

1. `iac/environments/aws-azure-vpn` debe haber creado la VNet, la subnet Flex y
   la subnet de Private Endpoints. Su gateway VPN es billable y usa su propia
   compuerta de costo.
2. El Resource Group de operaciones, Storage Account, contenedor de auditoría,
   colas y Application Insights deben existir. Se consultan como datos; este
   entorno no los reemplaza ni cambia el app `Y1`.
3. El paquete reproducible se genera con
   `iac/scripts/package_azure_function.ps1`. El artefacto se publica con Azure
   CLI; no se despliega código durante `terraform apply`.
4. La zona DNS privada solo se enlaza a la VNet Azure. El CloudFormation AWS
   ofrece una zona privada Route 53 opcional para mapear el hostname exacto del
   Flex App a `function_private_endpoint_ip`, conservando el SNI HTTPS. Requiere
   pasar juntos ambos valores al script de despliegue; está apagada por defecto
   y no equivale a un dominio público.
5. El cutover del secreto `AZURE_FUNCTION_KEY` en AWS y la prueba desde EC2
   requieren que AWS Academy permita leer y actualizar Secrets Manager, además
   de la VPN operativa. No se debe retirar la Function `Y1` hasta que esas
   comprobaciones pasen.

Microsoft confirma que Consumption no ofrece Private Endpoint ni VNet
integration; Flex sí. Para Flex, la subred debe ser dedicada, delegada a
`Microsoft.App/environments` y como mínimo `/27`. El paquete solo puede
publicarse desde una máquina con conectividad y DNS hacia el endpoint SCM si el
acceso público ya está cerrado.

Referencias oficiales:

- [Azure Functions networking options](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Manage Flex Consumption function apps](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)
- [Function package deployment](https://learn.microsoft.com/en-us/azure/azure-functions/deployment-zip-push)
- [Identity-based storage connections](https://learn.microsoft.com/en-us/azure/azure-functions/manage-connections)
- [AzureRM Flex Consumption resource](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_flex_consumption)

## Validación y despliegue en dos etapas

No versionar state, plan, tfvars ni claves. La suscripción se proporciona al
invocar Terraform; puede leerse desde el Azure CLI autenticado sin imprimir
tokens. La primera validación y las pruebas mock no acceden a Azure:

```powershell
terraform -chdir=iac/environments/azure-flex-private init
terraform -chdir=iac/environments/azure-flex-private validate
terraform -chdir=iac/environments/azure-flex-private test
```

Revisar siempre el plan guardado y confirmar que no elimine o reemplace el app
actual ni sus datos. El primer apply requiere
`deployment_approved=true`, `bootstrap_public_access_enabled=true` y
`bootstrap_public_access_acknowledged=true`; publicar el ZIP con Azure CLI,
validar salud, modo `demo-inventory-ledger`, colas e idempotencia. La clave de
Function se obtiene y sincroniza con AWS Secrets Manager fuera de Terraform y
sin imprimirla.

Después de establecer VPN/BGP y la resolución privada desde la VPC, probar el
flujo desde EC2 y verificar desde fuera que el acceso público falla. Solo
entonces aplicar con `bootstrap_public_access_enabled=false` y
`bootstrap_public_access_acknowledged=false`. Ejecutar un plan final y
comprobar que no haya cambios ni drift. Esta guía no afirma que la migración,
la VPN o el cutover ya estén desplegados.

## Costos y limpieza

`deployment_approved` bloquea por defecto toda creación. El Function Flex tiene
cobro por ejecución/recursos; Private Endpoint, zona DNS Azure, zona privada
Route 53 y VPN pueden generar cargos continuos. Revisar el estimador y el saldo del laboratorio antes de
aprobar. Para limpieza, primero volver a la Function `Y1` solo si el cutover
falló y requiere rollback, preservar blobs de auditoría/paquetes, verificar el
plan y luego destruir únicamente los recursos verdes. La VPN tiene una guía de
limpieza independiente; su destrucción no debe quitar el portal AWS ni RDS.
