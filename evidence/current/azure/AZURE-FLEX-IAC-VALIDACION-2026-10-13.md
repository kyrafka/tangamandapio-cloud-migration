# Preparación de Function Flex privada — 13/10/2026, 12:46 America/Chicago

## Resultado

Se preparó localmente una migración blue-green para una Function Azure Flex,
sin reemplazar la Function actual `tangama-wms-261008` (Linux Consumption Y1).
La implementación está en `iac/environments/azure-flex-private`; no se aplicó
Terraform y no se crearon recursos Azure.

La validación local confirmó:

- Terraform 1.16.2 + AzureRM 4.79.0: `init`, `validate` y formato correctos.
- `terraform test`: 3/3 escenarios aprobados. Se prueba el cierre por defecto
  de recursos facturables, networking privado en estado final y el acuse
  explícito requerido para permitir bootstrap público temporal.
- Quality gate completo: 94/94 pruebas de aplicación, dependencias limpias,
  build frontend, lint CloudFormation y formato/validación Terraform.
- Preflight de VPN AWS: 13 escenarios mock, incluidos parámetros DNS incompletos,
  IP fuera de la subnet y envío correcto de FQDN/IP a CloudFormation.

La configuración blue-green declara plan Flex FC1, identidad administrada,
package deployment en contenedor Blob privado, Application Insights con Entra,
Private Endpoint, Private DNS `privatelink.azurewebsites.net` y subnet de
integración dedicada `/27`. La Function queda sin ingreso público por defecto.
El primer publish ZIP puede habilitarse solo con dos variables y aprobación de
costo; luego debe cerrarse el acceso y verificarse desde AWS antes del cutover.

Se corrigió un error importante detectado durante la validación: Flex espera la
URL Blob del contenedor de paquetes, no el ID ARM del contenedor. La plantilla
arma el endpoint con `primary_blob_endpoint` y el nombre del contenedor, según
el [quickstart oficial de Terraform para Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-terraform).

CloudFormation ahora permite de forma opcional crear una zona Route 53 privada
acotada al hostname exacto de la Function y un registro A hacia el Private
Endpoint. No crea una zona amplia `azurewebsites.net`, evitando interceptar
otras Function Apps. El parámetro solo se activa con el par hostname/IP válido;
el despliegue queda sujeto al gate de costo ya existente. Esta pieza está sin
aplicar y no crea dominio público ni certificado HTTPS.

## Bloqueos y estado real

- La suscripción Azure for Students figura `Enabled`, pero el grupo
  `rg-tangama-private-network` no existía cuando se consultó a las 12:46.
  Faltan la VNet y subnets desplegadas; no se pudo hacer un plan Azure real.
- AWS STS aceptó la credencial del perfil local `default` para la cuenta
  `841113066612`. Las consultas de inventario de CloudFormation, VPC/EC2, ELB,
  RDS y VPN recibieron denegaciones explícitas de `voc-cancel-cred`. No se
  hicieron operaciones de escritura.
- La Function viva sigue siendo la verificada a las 12:06: Y1, pública y con
  `/api/health` HTTP 200. El E2E compensado de las 12:16 fue local→Azure y usó
  inventario ficticio (24→23→24); no pasó por EC2 ni demuestra la VPN.
- La puntuación autoestimada de la rúbrica no se elevó: esta mejora es IaC
  validada, no infraestructura aplicada o conexión multinube probada.

## Referencias

- [Networking options for Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Manage Flex Consumption function apps](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)
- [Azure Functions Terraform quickstart](https://learn.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-terraform)
- [Terraform provider mocking](https://developer.hashicorp.com/terraform/language/tests/mocking)
