param(
  [Parameter(Mandatory)] [string] $AwsVpnStackName,
  [Parameter(Mandatory)] [string] $AzureResourceGroup,
  [Parameter(Mandatory)] [string] $AzureGatewayName,
  [string] $AwsRegion = 'us-east-1',
  [string] $AzureLocation = 'westus'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Invoke-AwsJson {
  param([Parameter(Mandatory)] [string[]] $Arguments)
  $raw = & aws @Arguments 2>$null
  if ($LASTEXITCODE -ne 0) { throw 'AWS CLI no pudo consultar el stack o las VPN.' }
  return ($raw -join "`n") | ConvertFrom-Json
}

function Get-StackOutput {
  param([Parameter(Mandatory)] [string] $Key)
  $query = "Stacks[0].Outputs[?OutputKey=='$Key'].OutputValue | [0]"
  $raw = & aws cloudformation describe-stacks --stack-name $AwsVpnStackName `
    --region $AwsRegion --query $query --output text 2>$null
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw) -or $raw -eq 'None') {
    throw "El stack AWS no expone la salida requerida: $Key"
  }
  return $raw.Trim()
}

function Get-IpOffset {
  param([Parameter(Mandatory)] [string] $Cidr, [Parameter(Mandatory)] [int] $Offset)
  $parts = $Cidr.Split('/')
  if ($parts.Length -ne 2 -or [int]$parts[1] -ne 30) { throw 'AWS devolvió un bloque de túnel inesperado; se requiere /30.' }
  $bytes = [System.Net.IPAddress]::Parse($parts[0]).GetAddressBytes()
  [array]::Reverse($bytes)
  $number = [BitConverter]::ToUInt32($bytes, 0) + [uint32]$Offset
  $result = [BitConverter]::GetBytes($number)
  [array]::Reverse($result)
  return [System.Net.IPAddress]::new($result).ToString()
}

$createdConnections = [System.Collections.Generic.List[string]]::new()
$createdLocalGateways = [System.Collections.Generic.List[string]]::new()
$connections = [System.Collections.Generic.List[string]]::new()

try {
  $identity = Invoke-AwsJson -Arguments @('sts', 'get-caller-identity', '--region', $AwsRegion, '--output', 'json')
  $stack = Invoke-AwsJson -Arguments @('cloudformation', 'describe-stacks', '--stack-name', $AwsVpnStackName, '--region', $AwsRegion, '--output', 'json')
  if ($stack.Stacks[0].StackStatus -notin @('CREATE_COMPLETE', 'UPDATE_COMPLETE')) {
    throw 'El stack de VPN AWS no está estable; no se modificó Azure.'
  }
  $azureAccount = & az account show --output json 2>$null | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0 -or -not $azureAccount.id) { throw 'Azure CLI no tiene una sesión válida.' }

  $resourceGroup = & az group show --name $AzureResourceGroup --query name --output tsv 2>$null
  if ($LASTEXITCODE -ne 0 -or $resourceGroup -ne $AzureResourceGroup) { throw 'No se encontró el grupo de red esperado en Azure.' }
  $gatewayState = & az network vnet-gateway show --resource-group $AzureResourceGroup --name $AzureGatewayName `
    --query '{name:name,provisioningState:provisioningState,bgp:enableBgp,active:activeActive}' --output json 2>$null | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0 -or $gatewayState.provisioningState -ne 'Succeeded' -or -not $gatewayState.bgp -or -not $gatewayState.active) {
    throw 'El gateway Azure no está listo con BGP y active-active habilitados.'
  }
  $ipConfigurations = & az network vnet-gateway show --resource-group $AzureResourceGroup --name $AzureGatewayName `
    --query 'ipConfigurations[].{name:name,id:id}' --output json 2>$null | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw 'No se pudieron consultar las interfaces IP del gateway Azure.' }
  $ipConfigA = ($ipConfigurations | Where-Object name -eq 'active-active-a' | Select-Object -First 1).id
  $ipConfigB = ($ipConfigurations | Where-Object name -eq 'active-active-b' | Select-Object -First 1).id
  if (-not $ipConfigA -or -not $ipConfigB) { throw 'El gateway no expone las dos IP configurations esperadas.' }

  $vpnIds = @((Get-StackOutput -Key 'AzureVpnConnectionAId'), (Get-StackOutput -Key 'AzureVpnConnectionBId'))
  $awsCidr = Get-StackOutput -Key 'VpcCidr'
  $amazonAsn = [int](Get-StackOutput -Key 'AmazonSideAsn')
  $tunnelJson = Invoke-AwsJson -Arguments @(
    'ec2', 'describe-vpn-connections', '--vpn-connection-ids', $vpnIds[0], $vpnIds[1],
    '--region', $AwsRegion, '--output', 'json'
  )
  $vpnA = @($tunnelJson.VpnConnections | Where-Object VpnConnectionId -eq $vpnIds[0])
  $vpnB = @($tunnelJson.VpnConnections | Where-Object VpnConnectionId -eq $vpnIds[1])
  if ($vpnA.Count -ne 1 -or $vpnB.Count -ne 1) { throw 'AWS no devolvió exactamente las dos conexiones esperadas.' }

  # Azure active-active uses a distinct APIPA per tunnel and per gateway IP config.
  # The CIDRs exactly match Microsoft's AWS/Azure BGP interoperability guide.
  $apipa = @{
    '169.254.21.0/30' = @{ Peer = '169.254.21.2'; Instance = 'a' }
    '169.254.22.0/30' = @{ Peer = '169.254.22.2'; Instance = 'a' }
    '169.254.21.4/30' = @{ Peer = '169.254.21.6'; Instance = 'b' }
    '169.254.22.4/30' = @{ Peer = '169.254.22.6'; Instance = 'b' }
  }
  $expectedByVpn = @{}
  $expectedByVpn[$vpnIds[0]] = @('169.254.21.0/30', '169.254.22.0/30')
  $expectedByVpn[$vpnIds[1]] = @('169.254.21.4/30', '169.254.22.4/30')

  $connectionsList = & az network vpn-connection list --resource-group $AzureResourceGroup --output json 2>$null | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw 'No se pudieron revisar nombres de conexiones Azure antes de crear recursos.' }
  $localGatewaysList = & az network local-gateway list --resource-group $AzureResourceGroup --output json 2>$null | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw 'No se pudieron revisar nombres de gateways locales Azure antes de crear recursos.' }

  $plannedNames = [System.Collections.Generic.List[string]]::new()
  foreach ($vpn in @($vpnA[0], $vpnB[0])) {
    $suffix = if ($vpn.VpnConnectionId -eq $vpnIds[0]) { 'a' } else { 'b' }
    foreach ($tunnel in $vpn.Options.TunnelOptions) {
      if (-not $apipa.ContainsKey($tunnel.TunnelInsideCidr) -or $tunnel.TunnelInsideCidr -notin $expectedByVpn[$vpn.VpnConnectionId]) {
        throw 'El mapeo de túneles AWS no coincide con los bloques APIPA planificados.'
      }
      $index = [array]::IndexOf([array]$expectedByVpn[$vpn.VpnConnectionId], $tunnel.TunnelInsideCidr) + 1
      $plannedNames.Add("lng-tangama-aws-$suffix-t$index")
      $plannedNames.Add("conn-tangama-aws-$suffix-t$index")
    }
  }
  if ($plannedNames.Count -ne 8) { throw 'AWS no expone los cuatro túneles IPsec esperados.' }
  $existingNames = @($connectionsList | ForEach-Object name) + @($localGatewaysList | ForEach-Object name)
  $collisions = @($plannedNames | Where-Object { $_ -in $existingNames })
  if ($collisions.Count -gt 0) { throw 'Ya existen recursos Azure con nombres reservados; revise el estado antes de continuar.' }

  foreach ($vpn in @($vpnA[0], $vpnB[0])) {
    $suffix = if ($vpn.VpnConnectionId -eq $vpnIds[0]) { 'a' } else { 'b' }
    foreach ($tunnel in $vpn.Options.TunnelOptions) {
      $mapping = $apipa[$tunnel.TunnelInsideCidr]
      if ([string]::IsNullOrWhiteSpace($tunnel.PreSharedKey) -or [string]::IsNullOrWhiteSpace($tunnel.OutsideIpAddress)) {
        throw 'AWS aún no expone un túnel IPsec completo; no se pudo configurar Azure.'
      }

      # AWS is the first usable address in the /30. The peer IP is used only
      # in the transient Azure Local Network Gateway configuration.
      $awsInsidePeer = Get-IpOffset -Cidr $tunnel.TunnelInsideCidr -Offset 1
      $tunnelNumber = [array]::IndexOf([array]$expectedByVpn[$vpn.VpnConnectionId], $tunnel.TunnelInsideCidr) + 1
      $localGatewayName = "lng-tangama-aws-$suffix-t$tunnelNumber"
      $connectionName = "conn-tangama-aws-$suffix-t$tunnelNumber"
      $ipConfigurationId = if ($mapping.Instance -eq 'a') { $ipConfigA } else { $ipConfigB }

      $createdLocalGateways.Add($localGatewayName)
      & az network local-gateway create `
        --resource-group $AzureResourceGroup --location $AzureLocation --name $localGatewayName `
        --gateway-ip-address $tunnel.OutsideIpAddress --asn $amazonAsn --bgp-peering-address $awsInsidePeer `
        --output none 2>$null | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la definición local de un túnel en Azure.' }

      # Azure CLI's create command does not expose gatewayCustomBgpIpAddresses.
      # Set the connection-specific APIPA via its generic update after create.
      $createdConnections.Add($connectionName)
      & az network vpn-connection create `
        --resource-group $AzureResourceGroup --name $connectionName `
        --vnet-gateway1 $AzureGatewayName --local-gateway2 $localGatewayName `
        --enable-bgp --shared-key $tunnel.PreSharedKey --output none 2>$null | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'Azure rechazó la creación de una conexión IPsec; no se imprimieron credenciales.' }

      $customBgpJson = ConvertTo-Json -InputObject @(@{
        customBgpIpAddress = $mapping.Peer
        ipConfigurationId  = $ipConfigurationId
      }) -Compress
      & az network vpn-connection update --resource-group $AzureResourceGroup --name $connectionName `
        --set "gatewayCustomBgpIpAddresses=$customBgpJson" --output none 2>$null | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'No se pudo fijar el APIPA Azure de la conexión; revisión manual requerida.' }

      $verified = & az network vpn-connection show --resource-group $AzureResourceGroup --name $connectionName `
        --query '{bgp:enableBgp,apipa:gatewayCustomBgpIpAddresses,state:provisioningState}' --output json 2>$null | ConvertFrom-Json
      if ($LASTEXITCODE -ne 0 -or -not $verified.bgp -or $verified.state -ne 'Succeeded' -or
          $verified.apipa.Count -ne 1 -or $verified.apipa[0].customBgpIpAddress -ne $mapping.Peer -or
          $verified.apipa[0].ipConfigurationId -ne $ipConfigurationId) {
        throw 'La conexión Azure no refleja el APIPA y la IP configuration esperados.'
      }
      $connections.Add($connectionName)
    }
  }

  if ($connections.Count -ne 4) { throw 'Se esperaba configurar cuatro túneles IPsec (dos por cada instancia Azure).' }
  [pscustomobject]@{
    result                  = 'CONFIGURED'
    aws_account             = $identity.Account
    azure_subscription      = $azureAccount.id
    aws_vpn_connections     = $vpnIds.Count
    azure_ipsec_connections = $connections.Count
    secrets_written_locally = $false
  } | ConvertTo-Json -Compress
} catch {
  # The preflight rejected pre-existing names, so only this invocation's
  # resources are eligible for best-effort rollback. Keys are never emitted.
  foreach ($name in $createdConnections) {
    & az network vpn-connection delete --resource-group $AzureResourceGroup --name $name --output none 2>$null | Out-Null
  }
  foreach ($name in $createdLocalGateways) {
    & az network local-gateway delete --resource-group $AzureResourceGroup --name $name --output none 2>$null | Out-Null
  }
  Write-Error $_.Exception.Message
  exit 1
}
