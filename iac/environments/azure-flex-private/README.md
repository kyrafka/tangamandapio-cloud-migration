# Azure Functions Flex privada

Este entorno define la Function Flex privada `tangama-flex-261104` y el
almacenamiento vigente `sttangama261030r`. Usa la subnet `snet-flex-functions` delegada a
`Microsoft.App/environments`, identidad administrada para host/deployment
storage, Application Insights con Entra ID, un Private Endpoint en
`snet-private-endpoints` y la zona privada `privatelink.azurewebsites.net`.
La integración de la subnet es salida; el Private Endpoint habilita ingreso
privado.

Terraform bloquea el acceso público por defecto y configura el contenedor
privado de paquetes con identidad administrada. Usa el endpoint HTTPS del
contenedor como `storage_container_endpoint`. Flex ejecuta el paquete
publicado mediante OneDeploy.

## Dependencias y límites

1. La VNet, la subnet Flex y la subnet de Private Endpoints deben existir.
   Consulta [la raíz de red privada](../azure-private-network) y usa los
   valores esperados por esta raíz.
2. El Resource Group de operaciones, Storage Account, contenedor de auditoría,
   colas y Application Insights deben existir. Se consultan como datos; este
   entorno no los reemplaza ni cambia el app `Y1`.
3. El paquete reproducible se genera con
   `iac/scripts/package_azure_function.ps1`. Publica el artefacto mediante
   OneDeploy después de revisar la infraestructura.
4. La zona DNS privada solo se enlaza a la VNet Azure. El CloudFormation AWS
   ofrece una zona privada Route 53 opcional para mapear el hostname exacto del
   Flex App a `function_private_endpoint_ip`, conservando el SNI HTTPS. Requiere
   pasar juntos ambos valores al script de despliegue; está apagada por defecto
   y no equivale a un dominio público.
5. La prueba desde EC2 necesita la VPN y la Function key sincronizada en
   Secrets Manager. Guarda la clave fuera de Terraform.

Microsoft confirma que Consumption no ofrece Private Endpoint ni VNet
integration; Flex sí. Para Flex, la subred debe ser dedicada, delegada a
`Microsoft.App/environments` y como mínimo `/27`.

Referencias oficiales:

- [Azure Functions networking options](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Manage Flex Consumption function apps](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)
- [Function package deployment](https://learn.microsoft.com/en-us/azure/azure-functions/deployment-zip-push)
- [Identity-based storage connections](https://learn.microsoft.com/en-us/azure/azure-functions/manage-connections)
- [AzureRM Flex Consumption resource](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/function_app_flex_consumption)

## Validación de infraestructura

No versionar state, plan, tfvars ni claves. La suscripción se proporciona al
invocar Terraform; puede leerse desde el Azure CLI autenticado sin imprimir
tokens. La primera validación y las pruebas mock no acceden a Azure:

```powershell
terraform -chdir=iac/environments/azure-flex-private init
terraform -chdir=iac/environments/azure-flex-private validate
terraform -chdir=iac/environments/azure-flex-private test
```

Para operar sobre Azure, inicializa el backend de la suscripción correcta y
revisa qué recursos administra antes de preparar un plan. Para una
reconstrucción aislada usa un estado independiente, una Function con nombre
globalmente único y sus dependencias propias. El plan aprobado necesita
`deployment_approved=true`. Usa los valores de acceso público
predeterminados para publicar mediante ARM.

## Publicar en la Function privada

1. Genera `released-package.zip` con
   `iac/scripts/package_azure_function.ps1 -OutputPath <ruta>/released-package.zip`.
   Calcula su SHA-256 y súbelo al contenedor de despliegue con una identidad
   autorizada. Usa un prefijo versionado como `source/<revisión>/`.
2. Genera una URL HTTPS de lectura para ese blob, con caducidad corta y
   permiso `r`. El servicio Azure debe poder leer ese origen y el contenedor de
   despliegue. Guarda la URL en un archivo local temporal de parámetros ARM
   fuera del repositorio. El mapa `parameters` debe incluir
   `functionAppName`, `location` y `packageUri`, cada uno con un objeto
   `{"value":"..."}`. El formato es
   [parámetros ARM](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/parameter-files).
3. Desde este directorio, con la suscripción y el grupo verificados, ejecuta
   el despliegue incremental. Borra el archivo de parámetros al terminar.

   ```powershell
   $parameterFile = Join-Path $env:TEMP 'wms-release.parameters.json'
   az deployment group create --resource-group rg-tangamandapio-rebuild-wus `
     --mode Incremental --name wms-release-20261119 `
     --template-file onedeploy.json --parameters "@$parameterFile" `
     --query properties.provisioningState --output tsv
   ```

4. Desde una EC2 con DNS privado y VPN, comprueba inventario y colas con la
   Function key cargada en memoria. Las salidas Terraform
   `fulfillment_event_url` y `wms_queue_status_url` preservan el hostname
   Azure para TLS. Crea un pedido sintético y sigue su identificador hasta
   Queue, Blob y Application Insights. El [registro operativo](../../ESTADO_REAL_2026-11-19.md)
   contiene el paquete y la evidencia del despliegue privado.

## Costos y limpieza

`deployment_approved` bloquea por defecto toda creación. El Function Flex tiene
cobro por ejecución/recursos; Private Endpoint, zona DNS Azure, zona privada
Route 53 y VPN pueden generar cargos continuos. Revisar el estimador y el saldo del laboratorio antes de
aprobar. Para limpieza, primero volver a la Function `Y1` solo si el cutover
falló y requiere rollback, preservar blobs de auditoría/paquetes, verificar el
plan y luego destruir únicamente los recursos verdes. La VPN tiene una guía de
limpieza independiente; su destrucción no debe quitar el portal AWS ni RDS.
