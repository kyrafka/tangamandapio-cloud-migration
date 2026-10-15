param(
  [Parameter(Mandatory)] [string] $AzureResourceGroup,
  [Parameter(Mandatory)] [string] $AwsVpnStackName,
  [string] $AwsRegion = 'us-east-1'
)

$ErrorActionPreference = 'Stop'
$expectedAwsStackName = 'tangamandapio-aws-azure-vpn'
if ($AwsVpnStackName -ne $expectedAwsStackName) {
  throw "Desmontaje cancelado: el stack esperado debe ser $expectedAwsStackName."
}
if ($env:CONFIRM_TANGAMA_VPN_CLEANUP -ne 'YES') {
  throw 'Desmontaje cancelado. Revise primero la evidencia y establezca CONFIRM_TANGAMA_VPN_CLEANUP=YES.'
}
$identity = & aws sts get-caller-identity --region $AwsRegion --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'AWS CLI no tiene una sesión válida; no se eliminó nada.' }
$awsStack = & aws cloudformation describe-stacks --stack-name $AwsVpnStackName --region $AwsRegion --query 'Stacks[0].StackStatus' --output text 2>$null
if ($LASTEXITCODE -ne 0 -or $awsStack -notin @('CREATE_COMPLETE', 'UPDATE_COMPLETE')) {
  throw "No se pudo verificar un stack VPN estable de AWS ($awsStack); no se eliminó nada."
}
$null = $identity

# El alcance está limitado a los cuatro nombres creados por
# connect_azure_vpn.ps1; no elimina el gateway, la VNet ni recursos ajenos.
$expectedNames = @(
  'conn-tangama-aws-a-t1', 'conn-tangama-aws-a-t2',
  'conn-tangama-aws-b-t1', 'conn-tangama-aws-b-t2'
)
$existing = & az network vpn-connection list --resource-group $AzureResourceGroup --query "[?starts_with(name, 'conn-tangama-aws-')].name" --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'No fue posible consultar las conexiones Azure; no se eliminó nada.' }
$names = @($existing | ConvertFrom-Json)
if (@($names | Where-Object { $_ -notin $expectedNames }).Count -gt 0) {
  throw 'Hay conexiones con el prefijo del proyecto que no coinciden con los cuatro nombres esperados; revise manualmente.'
}
$expectedLocalGatewayNames = @(
  'lng-tangama-aws-a-t1', 'lng-tangama-aws-a-t2',
  'lng-tangama-aws-b-t1', 'lng-tangama-aws-b-t2'
)
$existingLocalGateways = & az network local-gateway list --resource-group $AzureResourceGroup --query "[?starts_with(name, 'lng-tangama-aws-')].name" --output json 2>$null
if ($LASTEXITCODE -ne 0) { throw 'No fue posible consultar Local Network Gateways Azure; AWS no se eliminó.' }
$localGatewayNames = @($existingLocalGateways | ConvertFrom-Json)
if (@($localGatewayNames | Where-Object { $_ -notin $expectedLocalGatewayNames }).Count -gt 0) {
  throw 'Hay Local Network Gateways con el prefijo del proyecto que no coinciden con el conjunto esperado.'
}

foreach ($name in $names) {
  & az network vpn-connection delete --resource-group $AzureResourceGroup --name $name --output none 2>$null
  if ($LASTEXITCODE -ne 0) { throw "No se pudo eliminar la conexión Azure esperada $name." }
}
foreach ($name in $localGatewayNames) {
  & az network local-gateway delete --resource-group $AzureResourceGroup --name $name --output none 2>$null
  if ($LASTEXITCODE -ne 0) { throw "No se pudo eliminar el Local Network Gateway $name." }
}
$deletedConnectionCount = $names.Count

& aws cloudformation delete-stack --stack-name $AwsVpnStackName --region $AwsRegion
if ($LASTEXITCODE -ne 0) { throw 'Azure peers were removed, but AWS VPN stack deletion failed; review AWS manually.' }
& aws cloudformation wait stack-delete-complete --stack-name $AwsVpnStackName --region $AwsRegion
if ($LASTEXITCODE -ne 0) { throw 'AWS VPN stack deletion did not complete; inspect its events and remaining resources.' }
Write-Output ('{"result":"VPN_GATEWAYS_REMOVED","azure_connections":{0},"aws_stack":"DELETE_COMPLETE"}' -f $deletedConnectionCount)
