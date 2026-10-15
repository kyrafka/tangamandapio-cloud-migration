# Red privada AWS–Azure (BGP, dos gateways activos)

Este entorno crea una VNet Azure no solapada (`10.20.0.0/16`), subred de
workloads, subred para Private Endpoints, una subred Flex Consumption delegada
(`/27`, `Microsoft.App/environments`) y un gateway VPN RouteBased `VpnGw1AZ`
con BGP y dos IP públicas activas. Azure rechazó la SKU no zonal `VpnGw1` en
la suscripción de prueba; Microsoft ya no admite crear gateways nuevos con
esas SKU, por lo que este entorno fija la variante AZ. El lado AWS se define por separado en
`iac/cloudformation/aws-azure-vpn.yaml`: se adjunta un Virtual Private Gateway
a la VPC existente y se propagan rutas solo a la tabla de las subredes de
aplicación. La tabla aislada de RDS y sus grupos de seguridad no cambian.

Se usan dos conexiones VPN AWS y cuatro túneles IPsec en total. Los túneles
usan `169.254.21.0/30`, `169.254.22.0/30`, `169.254.21.4/30` y
`169.254.22.4/30`. Las dos primeras redes corresponden a la instancia A del
gateway Azure (peers `.21.2` y `.22.2`); las dos últimas a la instancia B
(peers `.21.6` y `.22.6`). Cada conexión Azure se fija al ID de la
configuración IP de su instancia activa-activa; BGP no queda implícito ni se
deja a selección automática.

## Orden de despliegue

Los gateways y las IP públicas son recursos con cargo recurrente. El recurso
Terraform `terraform_data.vpn_cost_gate` bloquea la creación de todo el grupo
de red, incluidos esos componentes facturables, hasta establecer
`deployment_approved=true`. La prueba mock en `tests/cost_gate.tftest.hcl`
verifica tanto el rechazo por defecto como el plan del gateway activo-activo;
no crea recursos reales. No aprobar ni aplicar si el laboratorio no está
vigente o no se revisó el saldo y el costo regional.

1. Antes de crear recursos de red en Azure, ejecutar el preflight AWS de solo
   lectura desde la raíz del proyecto, con el nombre del stack del portal y el
   output `AppRouteTableId`:

   ```powershell
   .\iac\scripts\deploy_aws_vpn.ps1 `
     -PortalStackName tangamandapio-live-20261013 `
     -AppRouteTableId <APP_ROUTE_TABLE_ID> `
     -AwsPreflightOnly
   ```

   Debe devolver `AWS_READ_PREFLIGHT_PASSED`; ante `AccessDenied`, sesión
   inválida o stack no estable, detenerse y no aplicar Terraform en Azure. Este
   preflight evita pagar el gateway Azure cuando ni siquiera se puede leer la
   red AWS necesaria. Es solo lectura: no garantiza permisos de creación; la
   operación CloudFormation continúa siendo la comprobación autoritativa.
2. Confirmar que la VPC AWS sea `10.10.0.0/16`, que la VNet Azure sea
   `10.20.0.0/16` y que no exista ninguna ruta CIDR solapada.
3. Generar y revisar el plan del gateway Azure en este directorio. El `apply`
   solo procede con `deployment_approved=true` después de revisar el costo.
   El gateway puede tardar decenas de minutos en aprovisionar.
4. Ejecutar `iac/scripts/deploy_aws_vpn.ps1` con el stack del portal, la tabla
   de rutas app y `-ApproveRecurringCost`. El preflight compara VPC/VNet CIDR,
   confirma que la tabla pertenece a la VPC y que las dos IP configurations del
   gateway están en su `GatewaySubnet`; no reemplaza ni importa la VPC desde
   Terraform. Si no puede leer el stack VPN existente, aborta en vez de asumir
   que no existe. Si ya existe con parámetros distintos, requiere además
   `-ApproveStackUpdate` tras revisar el cambio.
5. Ejecutar `iac/scripts/connect_azure_vpn.ps1` con el stack, grupo y gateway
   Azure. El script consulta las PSK en memoria con AWS CLI, asocia las cuatro
   conexiones Azure a su APIPA/configuración IP y valida el mapeo. No guarda
   PSK en archivos, salida o Terraform state.
6. Ejecutar `iac/scripts/check_aws_azure_vpn.ps1`. Para aprobar se requieren
   2 conexiones AWS, 4/4 túneles AWS `UP` y 4/4 conexiones Azure `Connected`.
   Guardar capturas solo después; no capturar el JSON/configuración de túneles
   que incluye PSK.

Las sesiones de AWS CLI y Azure CLI deben apuntar a las suscripciones/cuenta y
región correctas. Las plantillas no crean redes hasta un `apply`/despliegue
explícito. Los estados locales se quedan fuera de Git; no activar transcript,
debug HTTP ni volcados de salida durante el intercambio de PSK.

## Alcance real y desmontaje

La VPN enruta entre la VPC AWS y la VNet Azure; las rutas llegan a subredes de
aplicación AWS y workloads Azure. RDS se mantiene sin ruta propagada y con
ingreso limitado a la security group de aplicación. El WMS existente sigue en
Azure Consumption (`Y1`) con endpoint HTTPS público: **esta VPN por sí sola no
hace que la Function atienda por red privada ni prueba que el flujo del portal
cruce el túnel**. Microsoft no admite Private Endpoint ni VNet integration en
el plan Consumption; Flex Consumption soporta ambos. La VNet integration es
solo salida: el ingreso privado requiere un Private Endpoint y DNS que resuelva
el hostname del WMS a su IP privada. El diseño objetivo debe migrar la Function
a Flex Consumption; este stack ya define `snet-flex-functions` (`10.20.2.0/27`)
delegada a `Microsoft.App/environments` y expone `flex_integration_subnet_id`.
Todavía falta desplegar la Function Flex, Private Endpoint/Private DNS y
resolver ese DNS desde AWS a través del túnel antes de cambiar el endpoint del
portal. La definición blue-green está en `../azure-flex-private`; el
CloudFormation de esta conexión incluye una zona privada Route 53 optativa para
el FQDN exacto de Flex. Ninguna de esas definiciones se aplicó y la opción de
DNS permanece desactivada. Flex Consumption con VNet
integration y Private Endpoint es una capacidad del plan, no prueba de que esté
desplegada en este proyecto. Estas restricciones y subnet minima siguen la
[guía oficial de redes de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
y la [guía oficial de Flex Consumption](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to).
La migración y los endpoints DNS agregan costo y requieren un plan de corte; se
deja explícito para no presentar una ruta disponible como tráfico de aplicación
ya migrado. El stack de red únicamente prepara la subred delegada y la expone
como output; no crea ni migra la Function Flex ni configura el Private Endpoint
o la resolución DNS. Las plantillas locales de esos componentes ya existen,
pero la VNet `rg-tangama-private-network` tampoco existe en el corte del
13/10/2026 12:46. Hacen falta permisos/inventario AWS y aprobación de costos
antes de desplegar y probar el flujo de extremo a extremo.

Al terminar la evidencia, ejecutar `iac/scripts/disconnect_azure_vpn.ps1`
con `CONFIRM_TANGAMA_VPN_CLEANUP=YES`; elimina las cuatro conexiones Azure,
sus Local Network Gateways y el stack VPN AWS, pero no toca el gateway/VNet
administrados por este entorno. Después ejecutar `terraform destroy` aquí.
Verificar que no
quede gateway VPN en ninguna nube; apagar el laboratorio AWS no necesariamente
elimina recursos facturables mientras el laboratorio se encuentre activo.

## Referencias oficiales

- [Microsoft: conectar AWS y Azure con BGP](https://learn.microsoft.com/en-us/azure/vpn-gateway/vpn-gateway-howto-aws-bgp) — arquitectura de 2 conexiones AWS, 4 túneles y 4 conexiones Azure; mapeo APIPA por instancia.
- [Microsoft: opciones de red de Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options) — diferencias entre Consumption, Flex Consumption, Premium y Dedicated para VNet/Private Endpoint.
- [Microsoft: precios de VPN Gateway](https://azure.microsoft.com/en-us/pricing/details/vpn-gateway/) — revisar región, SKU y cargos antes de crear el gateway.
