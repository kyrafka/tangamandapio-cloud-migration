param(
  [Parameter(Mandatory)] [string] $PortalStackName,
  [Parameter(Mandatory)] [string] $AppRouteTableId,
  [string] $AzureResourceGroup = 'rg-tangama-private-network',
  [string] $AzureGatewayName = 'vng-tangama-aws',
  [string] $VpnStackName = 'tangamandapio-aws-azure-vpn',
  [string] $AwsRegion = 'us-east-1',
  [string] $AzureVnetName = 'vnet-tangama-private',
  [string] $AzureFunctionPrivateHostname = '',
  [string] $AzureFunctionPrivateEndpointIp = '',
  [switch] $ApproveStackUpdate,
  [switch] $ApproveRecurringCost,
  [switch] $AwsPreflightOnly
)

$ErrorActionPreference = 'Stop'
if (-not $ApproveRecurringCost -and -not $AwsPreflightOnly) {
  throw 'No se desplegó: revise el costo recurrente del gateway en ambas nubes y repita con -ApproveRecurringCost.'
}

$hasPrivateHostname = -not [string]::IsNullOrWhiteSpace($AzureFunctionPrivateHostname)
$hasPrivateEndpointIp = -not [string]::IsNullOrWhiteSpace($AzureFunctionPrivateEndpointIp)
if ($hasPrivateHostname -ne $hasPrivateEndpointIp) {
  throw 'Para habilitar DNS privado se requieren juntos el hostname de la Function y la IP del Private Endpoint.'
}
if ($hasPrivateHostname) {
  if ($AzureFunctionPrivateHostname -notmatch '^[a-z0-9][a-z0-9-]{0,58}[a-z0-9]\.azurewebsites\.net$') {
    throw 'El hostname privado debe ser el FQDN exacto de una Function Azure bajo azurewebsites.net.'
  }
  if ($AzureFunctionPrivateEndpointIp -notmatch '^10\.20\.2\.(\d{1,3})$') {
    throw 'La IP del Private Endpoint debe pertenecer a la subnet Flex fijada en 10.20.2.0/27.'
  }
  $privateEndpointOctet = [int]$Matches[1]
  if ($privateEndpointOctet -lt 4 -or $privateEndpointOctet -gt 30) {
    throw 'La IP indicada es una dirección reservada o está fuera del rango asignable 10.20.2.4–10.20.2.30.'
  }
}

$null = & aws sts get-caller-identity --region $AwsRegion --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'AWS CLI no tiene una sesión válida; no se desplegó nada.' }

$portalRaw = & aws cloudformation describe-stacks --stack-name $PortalStackName --region $AwsRegion --output json 2>&1
$portalExitCode = $LASTEXITCODE
if ($portalExitCode -ne 0) {
  throw 'No se pudo leer el stack portal AWS (incluida una posible denegación de política); no se desplegó nada.'
}
$portal = ($portalRaw -join "`n") | ConvertFrom-Json
if ($portal.Stacks[0].StackStatus -notin @('CREATE_COMPLETE', 'UPDATE_COMPLETE')) {
  throw 'El stack portal AWS no está accesible o no está estable; no se desplegó nada.'
}
$vpcId = ($portal.Stacks[0].Outputs | Where-Object OutputKey -eq 'VpcId').OutputValue
$vpcCidr = ($portal.Stacks[0].Outputs | Where-Object OutputKey -eq 'VpcCidr').OutputValue
$expectedAppRouteTableId = ($portal.Stacks[0].Outputs | Where-Object OutputKey -eq 'AppRouteTableId').OutputValue
if (-not $vpcId -or $vpcCidr -ne '10.10.0.0/16') {
  throw 'El stack portal no expone la VPC esperada (10.10.0.0/16); no se desplegó nada.'
}
if (-not $expectedAppRouteTableId -or $AppRouteTableId -ne $expectedAppRouteTableId) {
  throw 'La tabla indicada no es el output AppRouteTableId del portal; se evita propagar rutas hacia tablas públicas o de RDS.'
}
$routeTableVpc = & aws ec2 describe-route-tables --route-table-ids $AppRouteTableId --region $AwsRegion --query 'RouteTables[0].VpcId' --output text 2>$null
if ($LASTEXITCODE -ne 0 -or $routeTableVpc -ne $vpcId) { throw 'La tabla de rutas indicada no pertenece a la VPC del portal.' }

$existingRaw = & aws cloudformation describe-stacks --stack-name $VpnStackName --region $AwsRegion --output json 2>&1
$describeExitCode = $LASTEXITCODE
$existingStack = $null
$vpnStackExists = $false
if ($describeExitCode -eq 0) {
  $existingStack = ($existingRaw -join "`n") | ConvertFrom-Json
  $existingStatus = [string]$existingStack.Stacks[0].StackStatus
  if ($existingStatus -notin @('CREATE_COMPLETE', 'UPDATE_COMPLETE')) {
    throw "El stack VPN ya existe en estado $existingStatus; inspección manual requerida."
  }
  $vpnStackExists = $true
} else {
  $describeMessage = $existingRaw -join "`n"
  if ($describeMessage -notmatch '(?i)ValidationError.*Stack.*does not exist') {
    throw 'No se pudo confirmar de forma segura si el stack VPN existe; no se desplegó nada.'
  }
}

if ($AwsPreflightOnly) {
  [pscustomobject]@{
    result              = 'AWS_READ_PREFLIGHT_PASSED'
    account              = 'validated-by-sts'
    region               = $AwsRegion
    portal_stack         = $PortalStackName
    vpc_cidr             = $vpcCidr
    app_route_table      = $AppRouteTableId
    vpn_stack_exists     = $vpnStackExists
    create_permissions   = 'not-tested; CloudFormation execution remains authoritative'
    cloud_mutations      = 0
  } | ConvertTo-Json -Compress
  return
}

$azure = & az account show --output json 2>$null | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $azure.id) { throw 'Azure CLI no tiene una sesión válida; no se desplegó nada.' }

$azureVnet = & az network vnet show --resource-group $AzureResourceGroup --name $AzureVnetName --output json 2>$null | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $azureVnet.id -or '10.20.0.0/16' -notin @($azureVnet.addressSpace.addressPrefixes)) {
  throw 'La VNet Azure no existe o su CIDR no es el prefijo esperado 10.20.0.0/16; no se desplegó nada.'
}
$gateway = & az network vnet-gateway show --resource-group $AzureResourceGroup --name $AzureGatewayName --query '{state:provisioningState,bgp:enableBgp,asn:bgpSettings.asn,active:activeActive,subnetIds:ipConfigurations[].subnet.id,publicIpIds:ipConfigurations[].publicIPAddress.id}' --output json 2>$null | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $gateway.state -ne 'Succeeded' -or -not $gateway.bgp -or [int]$gateway.asn -ne 65515 -or -not $gateway.active -or @($gateway.subnetIds).Count -ne 2 -or @($gateway.publicIpIds).Count -ne 2) {
  throw 'Azure no muestra el gateway activo-activo/BGP listo; no se desplegó nada.'
}
if (@($gateway.subnetIds | Where-Object { $_ -notlike "$($azureVnet.id)/subnets/GatewaySubnet" }).Count -gt 0) {
  throw 'El gateway VPN no está en la GatewaySubnet de la VNet esperada; no se desplegó nada.'
}
$publicAJson = & az network public-ip show --resource-group $AzureResourceGroup --name 'pip-tangama-vpn-a' --query '{id:id,address:ipAddress}' --output json 2>$null
$publicAExitCode = $LASTEXITCODE
$publicBJson = & az network public-ip show --resource-group $AzureResourceGroup --name 'pip-tangama-vpn-b' --query '{id:id,address:ipAddress}' --output json 2>$null
$publicBExitCode = $LASTEXITCODE
if ($publicAExitCode -ne 0 -or $publicBExitCode -ne 0) { throw 'No se pudieron resolver las dos IP públicas Azure.' }
$publicA = $publicAJson | ConvertFrom-Json
$publicB = $publicBJson | ConvertFrom-Json
if (-not $publicA.id -or -not $publicB.id -or -not $publicA.address -or -not $publicB.address -or $publicA.id -ieq $publicB.id) {
  throw 'Azure no devolvió dos recursos de IP pública distintos y utilizables.'
}
$gatewayPublicIpIds = @($gateway.publicIpIds)
if (@($gatewayPublicIpIds | Where-Object { $_ -ieq $publicA.id }).Count -ne 1 -or
    @($gatewayPublicIpIds | Where-Object { $_ -ieq $publicB.id }).Count -ne 1) {
  throw 'Las IP públicas esperadas no son exactamente las dos asociadas al gateway Azure; no se desplegó nada.'
}

if ($describeExitCode -eq 0) {
  $expectedParameters = @{
    VpcId                  = $vpcId
    AppRouteTableId        = $AppRouteTableId
    AzureGatewayPublicIpA  = $publicA.address
    AzureGatewayPublicIpB  = $publicB.address
    AzureVnetCidr          = '10.20.0.0/16'
    AzureBgpAsn            = '65515'
    AmazonSideAsn          = '64512'
    ProjectName            = 'tangamandapio'
    AzureFunctionPrivateHostname = $AzureFunctionPrivateHostname
    AzureFunctionPrivateEndpointIp = $AzureFunctionPrivateEndpointIp
  }
  $actualParameters = @{}
  foreach ($parameter in @($existingStack.Stacks[0].Parameters)) {
    $actualParameters[[string]$parameter.ParameterKey] = [string]$parameter.ParameterValue
  }
  $changedParameters = @($expectedParameters.Keys | Where-Object { $actualParameters[$_] -ne $expectedParameters[$_] })
  if ($changedParameters.Count -gt 0 -and -not $ApproveStackUpdate) {
    throw 'El stack VPN existe con parámetros distintos; revise el cambio y repita con -ApproveStackUpdate para autorizar la actualización.'
  }
}

$template = Join-Path $PSScriptRoot '..\cloudformation\aws-azure-vpn.yaml'
$parameterOverrides = @(
  "VpcId=$vpcId"
  "AppRouteTableId=$AppRouteTableId"
  "AzureGatewayPublicIpA=$($publicA.address)"
  "AzureGatewayPublicIpB=$($publicB.address)"
  'AzureVnetCidr=10.20.0.0/16'
  'AzureBgpAsn=65515'
  'AmazonSideAsn=64512'
  'ProjectName=tangamandapio'
)
if ($hasPrivateHostname) {
  $parameterOverrides += "AzureFunctionPrivateHostname=$AzureFunctionPrivateHostname"
  $parameterOverrides += "AzureFunctionPrivateEndpointIp=$AzureFunctionPrivateEndpointIp"
}
$deployArguments = @(
  'cloudformation', 'deploy',
  '--template-file', $template,
  '--stack-name', $VpnStackName,
  '--region', $AwsRegion,
  '--parameter-overrides'
) + $parameterOverrides + @('--no-fail-on-empty-changeset')
& aws @deployArguments
if ($LASTEXITCODE -ne 0) { throw 'CloudFormation no terminó el despliegue VPN; revise el estado del stack antes de reintentar.' }
[pscustomobject]@{
  result        = 'AWS_VPN_STACK_COMPLETE'
  cidr_contract = 'validated'
  vpn_stack     = $VpnStackName
} | ConvertTo-Json -Compress
