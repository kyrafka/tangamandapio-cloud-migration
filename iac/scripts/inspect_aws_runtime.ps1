[CmdletBinding()]
param(
  [string] $Region = 'us-east-1',
  [string] $StackName = 'tangamandapio-live-20261013'
)

$ErrorActionPreference = 'Continue'
$checks = [System.Collections.Generic.List[object]]::new()
$script:awsReadCalls = 0

function Get-AwsErrorCategory {
  param([string] $Message)
  if ($Message -match 'explicit deny|AccessDenied|UnauthorizedOperation') { return 'access_denied' }
  if ($Message -match 'ExpiredToken|InvalidClientTokenId|UnrecognizedClientException') { return 'invalid_or_expired_credentials' }
  if ($Message -match 'could not connect|timed out|Could not connect to the endpoint URL') { return 'network_error' }
  return 'aws_cli_error'
}

function Invoke-AwsReadOnlyJson {
  param(
    [Parameter(Mandatory)] [string] $Name,
    [Parameter(Mandatory)] [string[]] $Arguments
  )

  $script:awsReadCalls++
  $commandArguments = @($Arguments) + @('--region', $Region, '--output', 'json')
  try {
    $output = @(& aws @commandArguments 2>&1)
    $exitCode = $LASTEXITCODE
  } catch {
    return [pscustomobject]@{ name = $Name; status = 'error'; error = 'aws_cli_unavailable'; data = $null }
  }

  $text = ($output | ForEach-Object { [string]$_ }) -join "`n"
  if ($exitCode -ne 0) {
    return [pscustomobject]@{
      name = $Name
      status = 'error'
      error = Get-AwsErrorCategory -Message $text
      data = $null
    }
  }

  try {
    $data = $text | ConvertFrom-Json -ErrorAction Stop
  } catch {
    return [pscustomobject]@{ name = $Name; status = 'error'; error = 'invalid_json_response'; data = $null }
  }
  return [pscustomobject]@{ name = $Name; status = 'ok'; error = $null; data = $data }
}

function Get-SafeAwsData {
  param([Parameter(Mandatory)] $Result)
  if ($Result.status -ne 'ok') { return $null }

  switch -Regex ($Result.name) {
    '^identity$' {
      return [pscustomobject]@{ account = $Result.data.Account }
    }
    '^stack$' {
      return @($Result.data.Stacks | ForEach-Object {
        [pscustomobject]@{ name = $_.StackName; status = $_.StackStatus }
      })
    }
    '^load_balancers$' {
      return @($Result.data.LoadBalancers | ForEach-Object {
        [pscustomobject]@{
          name = $_.LoadBalancerName
          state = $_.State.Code
          scheme = $_.Scheme
          arn = $_.LoadBalancerArn
          dns_name = $_.DNSName
        }
      })
    }
    '^target_groups/' {
      return @($Result.data.TargetGroups | ForEach-Object {
        [pscustomobject]@{ name = $_.TargetGroupName; arn = $_.TargetGroupArn }
      })
    }
    '^target_health/' {
      return @($Result.data.TargetHealthDescriptions | ForEach-Object {
        [pscustomobject]@{ state = $_.TargetHealth.State; reason = $_.TargetHealth.Reason }
      })
    }
    '^auto_scaling$' {
      return @($Result.data.AutoScalingGroups | ForEach-Object {
        [pscustomobject]@{
          name = $_.AutoScalingGroupName
          desired = $_.DesiredCapacity
          min = $_.MinSize
          max = $_.MaxSize
          in_service = @($_.Instances | Where-Object LifecycleState -eq 'InService').Count
        }
      })
    }
    '^instances$' {
      return @($Result.data.Reservations | ForEach-Object { $_.Instances } | ForEach-Object {
        $nameTag = $_.Tags | Where-Object Key -eq 'Name' | Select-Object -First 1
        [pscustomobject]@{ id = $_.InstanceId; name = $nameTag.Value; state = $_.State.Name; type = $_.InstanceType }
      })
    }
    '^databases$' {
      return @($Result.data.DBInstances | ForEach-Object {
        [pscustomobject]@{
          id = $_.DBInstanceIdentifier
          status = $_.DBInstanceStatus
          multi_az = $_.MultiAZ
          backup_retention_days = $_.BackupRetentionPeriod
          encrypted = $_.StorageEncrypted
          public = $_.PubliclyAccessible
        }
      })
    }
    default { return $null }
  }
}

function Add-AwsCheck {
  param(
    [Parameter(Mandatory)] [string] $Name,
    [Parameter(Mandatory)] [string[]] $Arguments
  )
  $result = Invoke-AwsReadOnlyJson -Name $Name -Arguments $Arguments
  $checks.Add([pscustomobject]@{
    name = $result.name
    status = $result.status
    error = $result.error
    data = Get-SafeAwsData -Result $result
  })
  return $result
}

$identity = Add-AwsCheck -Name 'identity' -Arguments @('sts', 'get-caller-identity')
[void](Add-AwsCheck -Name 'stack' -Arguments @('cloudformation', 'describe-stacks', '--stack-name', $StackName))
$loadBalancers = Add-AwsCheck -Name 'load_balancers' -Arguments @('elbv2', 'describe-load-balancers')
if ($loadBalancers.status -eq 'ok') {
  foreach ($loadBalancer in @($loadBalancers.data.LoadBalancers)) {
    $lbLabel = [string]$loadBalancer.LoadBalancerName
    $targetGroups = Add-AwsCheck -Name "target_groups/$lbLabel" -Arguments @(
      'elbv2', 'describe-target-groups', '--load-balancer-arn', [string]$loadBalancer.LoadBalancerArn
    )
    if ($targetGroups.status -eq 'ok') {
      foreach ($targetGroup in @($targetGroups.data.TargetGroups)) {
        [void](Add-AwsCheck -Name "target_health/$($targetGroup.TargetGroupName)" -Arguments @(
          'elbv2', 'describe-target-health', '--target-group-arn', [string]$targetGroup.TargetGroupArn
        ))
      }
    }
  }
}
[void](Add-AwsCheck -Name 'auto_scaling' -Arguments @('autoscaling', 'describe-auto-scaling-groups'))
[void](Add-AwsCheck -Name 'instances' -Arguments @('ec2', 'describe-instances'))
[void](Add-AwsCheck -Name 'databases' -Arguments @('rds', 'describe-db-instances'))

$hasErrors = @($checks | Where-Object status -ne 'ok').Count -gt 0
$targetStates = @($checks | Where-Object name -like 'target_health/*' | ForEach-Object { $_.data } | ForEach-Object { $_.state })
$dbStates = @($checks | Where-Object name -eq 'databases' | ForEach-Object { $_.data } | ForEach-Object { $_.status })
$instanceStates = @($checks | Where-Object name -eq 'instances' | ForEach-Object { $_.data } | ForEach-Object { $_.state })
$readiness = 'unknown'
if ($hasErrors) {
  $readiness = 'incomplete'
} elseif ($targetStates.Count -gt 0 -and $dbStates.Count -gt 0 -and $instanceStates.Count -gt 0) {
  if (@($targetStates | Where-Object { $_ -ne 'healthy' }).Count -eq 0 -and
      @($dbStates | Where-Object { $_ -ne 'available' }).Count -eq 0 -and
      @($instanceStates | Where-Object { $_ -ne 'running' }).Count -eq 0) {
    $readiness = 'healthy'
  } else {
    $readiness = 'degraded'
  }
}

[pscustomobject]@{
  read_only = $true
  region = $Region
  stack_name = $StackName
  aws_read_calls = $script:awsReadCalls
  identity = if ($identity.status -eq 'ok') { $identity.data.Account } else { $null }
  access_status = if ($hasErrors) { 'partial' } else { 'complete' }
  readiness = $readiness
  checks = @($checks)
} | ConvertTo-Json -Depth 8
