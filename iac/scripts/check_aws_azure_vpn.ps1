param(
  [Parameter(Mandatory)] [string] $AwsVpnStackName,
  [Parameter(Mandatory)] [string] $AzureResourceGroup,
  [Parameter(Mandatory)] [string] $AwsRegion = 'us-east-1'
)

$ErrorActionPreference = 'Stop'
$output = & aws cloudformation describe-stacks --stack-name $AwsVpnStackName --region $AwsRegion --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'No fue posible leer el stack VPN de AWS.' }
$stack = $output | ConvertFrom-Json
$keys = @('AzureVpnConnectionAId', 'AzureVpnConnectionBId')
$vpnIds = foreach ($key in $keys) {
  ($stack.Stacks[0].Outputs | Where-Object OutputKey -eq $key).OutputValue
}
if ($vpnIds.Count -ne 2 -or -not $vpnIds[0] -or -not $vpnIds[1]) { throw 'El stack no contiene las dos conexiones VPN esperadas.' }

$awsOutput = & aws ec2 describe-vpn-connections --vpn-connection-ids $vpnIds[0] $vpnIds[1] --region $AwsRegion --query 'VpnConnections[].{id:VpnConnectionId,state:State,tunnels:VgwTelemetry[].{outside:OutsideIpAddress,status:Status,acceptedRoutes:AcceptedRouteCount}}' --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'No fue posible consultar el estado de túneles AWS.' }
$azureOutput = & az network vpn-connection list --resource-group $AzureResourceGroup --query "[?starts_with(name, 'conn-tangama-aws-')].{name:name,state:connectionStatus,provisioning:provisioningState,in:ingressBytesTransferred,out:egressBytesTransferred}" --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'No fue posible consultar el estado de conexiones Azure.' }

$awsConnections = @($awsOutput | ConvertFrom-Json)
$azureConnections = @($azureOutput | ConvertFrom-Json)
$upTunnels = @($awsConnections | ForEach-Object { $_.tunnels } | Where-Object status -eq 'UP').Count
$connected = @($azureConnections | Where-Object state -eq 'Connected').Count
$result = [pscustomobject]@{
  aws_connections          = $awsConnections.Count
  aws_tunnels_up           = $upTunnels
  azure_connections        = $azureConnections.Count
  azure_connections_up     = $connected
  tunnel_status            = $awsConnections
  connection_status        = $azureConnections
  verification             = if ($upTunnels -eq 4 -and $connected -eq 4) { 'ALL_TUNNELS_CONNECTED' } else { 'INCOMPLETE' }
}
$result | ConvertTo-Json -Depth 6
if ($result.verification -ne 'ALL_TUNNELS_CONNECTED') { exit 2 }
