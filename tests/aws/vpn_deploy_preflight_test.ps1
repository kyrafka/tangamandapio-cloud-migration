$ErrorActionPreference = 'Stop'
$deployScript = Join-Path $PSScriptRoot '..\..\iac\scripts\deploy_aws_vpn.ps1'
$deployScript = [System.IO.Path]::GetFullPath($deployScript)
$savedAwsFunction = Get-Item Function:\global:aws -ErrorAction SilentlyContinue
$savedAzFunction = Get-Item Function:\global:az -ErrorAction SilentlyContinue
$savedLastExitCode = $global:LASTEXITCODE
$global:VpnMockMode = 'AccessDenied'
$global:VpnMockDeployCalls = 0
$global:VpnMockAwsCalls = 0
$global:VpnMockAzCalls = 0
$global:VpnMockDeployArguments = @()
$global:VpnMockAwsCidr = '10.10.0.0/16'
$global:VpnMockAzureAsn = 65515
$global:VpnMockAzureGatewayIpIds = @(
  '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-tangama-vpn-a',
  '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-tangama-vpn-b'
)

function global:aws {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
  $global:VpnMockAwsCalls++
  $global:LASTEXITCODE = 0
  if ($AwsArgs[0] -eq 'sts' -and $AwsArgs[1] -eq 'get-caller-identity') {
    return '{"Account":"000000000000"}'
  }
  if ($AwsArgs[0] -eq 'cloudformation' -and $AwsArgs[1] -eq 'describe-stacks') {
    $stackIndex = [array]::IndexOf($AwsArgs, '--stack-name')
    $stackName = $AwsArgs[$stackIndex + 1]
    if ($stackName -eq 'tangamandapio-live-20261013') {
      return (@{ Stacks = @(@{
        StackStatus = 'UPDATE_COMPLETE'
        Outputs = @(
          @{ OutputKey = 'VpcId'; OutputValue = 'vpc-test1234' },
          @{ OutputKey = 'VpcCidr'; OutputValue = $global:VpnMockAwsCidr },
          @{ OutputKey = 'AppRouteTableId'; OutputValue = 'rtb-test1234' }
        )
      }) } | ConvertTo-Json -Depth 6 -Compress)
    }
    switch ($global:VpnMockMode) {
      'AccessDenied' {
        $global:LASTEXITCODE = 254
        return 'An error occurred (AccessDenied) when calling DescribeStacks.'
      }
      'NotFound' {
        $global:LASTEXITCODE = 255
        return "An error occurred (ValidationError) when calling the DescribeStacks operation: Stack with id $stackName does not exist"
      }
      'Changed' {
        return (@{ Stacks = @(@{
          StackStatus = 'UPDATE_COMPLETE'
          Parameters = @(@{ ParameterKey = 'VpcId'; ParameterValue = 'vpc-old1234' })
        }) } | ConvertTo-Json -Depth 6 -Compress)
      }
      default { throw 'Unexpected VPN-stack mock mode.' }
    }
  }
  if ($AwsArgs[0] -eq 'ec2' -and $AwsArgs[1] -eq 'describe-route-tables') {
    return 'vpc-test1234'
  }
  if ($AwsArgs[0] -eq 'cloudformation' -and $AwsArgs[1] -eq 'deploy') {
    $global:VpnMockDeployCalls++
    $global:VpnMockDeployArguments = @($AwsArgs)
    return ''
  }
  throw "Unexpected mocked AWS operation: $($AwsArgs[0..([Math]::Min(1, $AwsArgs.Count - 1))] -join ' ')"
}

function global:az {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AzArgs)
  $global:LASTEXITCODE = 0
  $global:VpnMockAzCalls++
  if ($AzArgs[0] -eq 'account' -and $AzArgs[1] -eq 'show') {
    return '{"id":"subscription-mock"}'
  }
  if ($AzArgs[0] -eq 'network' -and $AzArgs[1] -eq 'vnet' -and $AzArgs[2] -eq 'show') {
    return '{"id":"/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private","addressSpace":{"addressPrefixes":["10.20.0.0/16"]}}'
  }
  if ($AzArgs[0] -eq 'network' -and $AzArgs[1] -eq 'vnet-gateway' -and $AzArgs[2] -eq 'show') {
    return (@{
      state = 'Succeeded'
      bgp = $true
      asn = $global:VpnMockAzureAsn
      active = $true
      subnetIds = @(
        '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private/subnets/GatewaySubnet',
        '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/virtualNetworks/vnet-tangama-private/subnets/GatewaySubnet'
      )
      publicIpIds = $global:VpnMockAzureGatewayIpIds
    } | ConvertTo-Json -Depth 4 -Compress)
  }
  if ($AzArgs[0] -eq 'network' -and $AzArgs[1] -eq 'public-ip' -and $AzArgs[2] -eq 'show') {
    $nameIndex = [array]::IndexOf($AzArgs, '--name')
    $name = $AzArgs[$nameIndex + 1]
    if ($name -in @('pip-tangama-vpn-a', 'pip-tangama-vpn-b')) {
      $suffix = if ($name -eq 'pip-tangama-vpn-a') { '10' } else { '11' }
      return (@{
        id = "/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/$name"
        address = "198.51.100.$suffix"
      } | ConvertTo-Json -Compress)
    }
  }
  throw "Unexpected mocked Azure operation: $($AzArgs[0..([Math]::Min(2, $AzArgs.Count - 1))] -join ' ')"
}

function Invoke-MockedVpnDeploy {
  param(
    [switch]$ApproveUpdate,
    [switch]$AwsPreflightOnly,
    [string]$RouteTableId = 'rtb-test1234',
    [string]$FunctionHost = '',
    [string]$FunctionPrivateIp = ''
  )
  $arguments = @{
    PortalStackName                  = 'tangamandapio-live-20261013'
    AppRouteTableId                  = $RouteTableId
    AzureFunctionPrivateHostname     = $FunctionHost
    AzureFunctionPrivateEndpointIp   = $FunctionPrivateIp
  }
  if (-not $AwsPreflightOnly) { $arguments.ApproveRecurringCost = $true }
  if ($ApproveUpdate) { $arguments.ApproveStackUpdate = $true }
  if ($AwsPreflightOnly) { $arguments.AwsPreflightOnly = $true }
  & $deployScript @arguments | Out-Null
}

try {
  # An AWS authorization/network error must not be mistaken for stack absence.
  $global:VpnMockMode = 'AccessDenied'
  $global:VpnMockDeployCalls = 0
  $global:VpnMockAzCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0 -or $global:VpnMockAzCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: an unreadable AWS stack was not rejected before Azure or deployment.'
  }

  # The read-only AWS preflight must run before any Azure command and cost approval.
  $global:VpnMockMode = 'NotFound'
  $global:VpnMockDeployCalls = 0
  $global:VpnMockAzCalls = 0
  Invoke-MockedVpnDeploy -AwsPreflightOnly
  if ($global:VpnMockDeployCalls -ne 0 -or $global:VpnMockAzCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: AWS-only preflight touched Azure or attempted a deployment.'
  }

  # Creation is allowed only for AWS's explicit ValidationError/not-found case.
  $global:VpnMockMode = 'NotFound'
  $global:VpnMockDeployCalls = 0
  Invoke-MockedVpnDeploy
  if ($global:VpnMockDeployCalls -ne 1) {
    throw 'VPN_PREFLIGHT_FAILED: an explicitly absent stack was not deployable.'
  }

  # Existing stacks with changed parameters require a second explicit approval.
  $global:VpnMockMode = 'Changed'
  $global:VpnMockDeployCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: a changed stack did not require update approval.'
  }
  Invoke-MockedVpnDeploy -ApproveUpdate
  if ($global:VpnMockDeployCalls -ne 1) {
    throw 'VPN_PREFLIGHT_FAILED: explicit update approval was not honored.'
  }

  # A mismatched AWS VPC CIDR must fail before any VPN-stack mutation.
  $global:VpnMockMode = 'NotFound'
  $global:VpnMockAwsCidr = '10.99.0.0/16'
  $global:VpnMockDeployCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: an unexpected AWS CIDR was not rejected.'
  }

  # Only the portal's exact app route table may receive BGP-propagated routes.
  $global:VpnMockAwsCidr = '10.10.0.0/16'
  $global:VpnMockDeployCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy -RouteTableId 'rtb-wrong1234' } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: a route table other than AppRouteTableId was accepted.'
  }

  # A gateway with a mismatched BGP ASN cannot establish the planned peers.
  $global:VpnMockAzureAsn = 65123
  $global:VpnMockDeployCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: an unexpected Azure BGP ASN was accepted.'
  }

  # Both public IP resources must be the exact two attached to the gateway.
  $global:VpnMockAzureAsn = 65515
  $global:VpnMockAzureGatewayIpIds = @(
    '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-unattached',
    '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-tangama-vpn-b'
  )
  $global:VpnMockDeployCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockDeployCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: unattached Azure public IP resources were accepted.'
  }

  # Azure private DNS must be opt-in and receive both values before any cloud read.
  $global:VpnMockMode = 'NotFound'
  $global:VpnMockAzureGatewayIpIds = @(
    '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-tangama-vpn-a',
    '/subscriptions/mock/resourceGroups/rg-tangama-private-network/providers/Microsoft.Network/publicIPAddresses/pip-tangama-vpn-b'
  )
  $global:VpnMockAwsCalls = 0
  $global:VpnMockAzCalls = 0
  $failedClosed = $false
  try { Invoke-MockedVpnDeploy -FunctionHost 'tangama-wms-flex.azurewebsites.net' } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockAwsCalls -ne 0 -or $global:VpnMockAzCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: a partial Azure private DNS mapping was not rejected before cloud access.'
  }

  # The private endpoint address must be assignable inside the pinned /27 subnet.
  $failedClosed = $false
  try {
    Invoke-MockedVpnDeploy -FunctionHost 'tangama-wms-flex.azurewebsites.net' -FunctionPrivateIp '10.20.2.31'
  } catch { $failedClosed = $true }
  if (-not $failedClosed -or $global:VpnMockAwsCalls -ne 0 -or $global:VpnMockAzCalls -ne 0) {
    throw 'VPN_PREFLIGHT_FAILED: a reserved/out-of-range Private Endpoint IP was accepted.'
  }

  # The record is passed only when an exact Function host and usable private IP are supplied.
  $global:VpnMockAwsCalls = 0
  $global:VpnMockDeployCalls = 0
  $global:VpnMockDeployArguments = @()
  Invoke-MockedVpnDeploy `
    -FunctionHost 'tangama-wms-flex.azurewebsites.net' `
    -FunctionPrivateIp '10.20.2.5'
  if ($global:VpnMockDeployCalls -ne 1 -or
      $global:VpnMockDeployArguments -notcontains 'AzureFunctionPrivateHostname=tangama-wms-flex.azurewebsites.net' -or
      $global:VpnMockDeployArguments -notcontains 'AzureFunctionPrivateEndpointIp=10.20.2.5') {
    throw 'VPN_PREFLIGHT_FAILED: a valid private DNS mapping was not passed to CloudFormation.'
  }

  Write-Output 'VPN_DEPLOY_PREFLIGHT=13_MOCK_SCENARIOS_PASSED (no cloud calls)'
}
finally {
  if ($null -eq $savedAwsFunction) { Remove-Item Function:\global:aws -ErrorAction SilentlyContinue }
  else { Set-Item Function:\global:aws -Value $savedAwsFunction.ScriptBlock }
  if ($null -eq $savedAzFunction) { Remove-Item Function:\global:az -ErrorAction SilentlyContinue }
  else { Set-Item Function:\global:az -Value $savedAzFunction.ScriptBlock }
  if ($null -eq $savedLastExitCode) { Remove-Variable LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue }
  else { $global:LASTEXITCODE = $savedLastExitCode }
  Remove-Variable VpnMockMode, VpnMockDeployCalls, VpnMockAwsCalls, VpnMockAzCalls, VpnMockDeployArguments, VpnMockAwsCidr, VpnMockAzureAsn, VpnMockAzureGatewayIpIds -Scope Global -ErrorAction SilentlyContinue
}
