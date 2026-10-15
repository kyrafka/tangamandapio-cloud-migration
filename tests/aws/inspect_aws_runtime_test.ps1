$ErrorActionPreference = 'Stop'
$scriptPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\iac\scripts\inspect_aws_runtime.ps1'))
$savedAwsFunction = Get-Item Function:\global:aws -ErrorAction SilentlyContinue
$savedLastExitCode = $global:LASTEXITCODE
$global:AwsDiagnosticMode = 'healthy'
$global:AwsDiagnosticCalls = [System.Collections.Generic.List[string]]::new()

function global:aws {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]] $AwsArgs)
  $command = $AwsArgs[0..([array]::IndexOf($AwsArgs, '--region') - 1)] -join ' '
  $global:AwsDiagnosticCalls.Add($command)
  $global:LASTEXITCODE = 0

  if ($global:AwsDiagnosticMode -eq 'denied' -and $AwsArgs[0] -ne 'sts') {
    $global:LASTEXITCODE = 254
    return 'explicit deny in an identity-based policy'
  }

  if ($AwsArgs[0] -eq 'sts') { return '{"Account":"841113066612","Arn":"arn:aws:sts::841113066612:assumed-role/voclabs/redacted"}' }
  if ($AwsArgs[0] -eq 'cloudformation') { return '{"Stacks":[{"StackName":"tangamandapio-live-20261013","StackStatus":"UPDATE_COMPLETE"}]}' }
  if ($AwsArgs[0] -eq 'elbv2' -and $AwsArgs[1] -eq 'describe-load-balancers') {
    return '{"LoadBalancers":[{"LoadBalancerName":"portal-alb","LoadBalancerArn":"arn:aws:elasticloadbalancing:us-east-1:841113066612:loadbalancer/app/portal/abc","DNSName":"portal.example.invalid","Scheme":"internet-facing","State":{"Code":"active"}}]}'
  }
  if ($AwsArgs[0] -eq 'elbv2' -and $AwsArgs[1] -eq 'describe-target-groups') {
    return '{"TargetGroups":[{"TargetGroupName":"portal-targets","TargetGroupArn":"arn:aws:elasticloadbalancing:us-east-1:841113066612:targetgroup/portal/abc"}]}'
  }
  if ($AwsArgs[0] -eq 'elbv2' -and $AwsArgs[1] -eq 'describe-target-health') {
    $state = if ($global:AwsDiagnosticMode -eq 'unhealthy') { 'unhealthy' } else { 'healthy' }
    return (@{ TargetHealthDescriptions = @(@{ Target = @{ Id = 'i-demo' }; TargetHealth = @{ State = $state; Reason = '' } }) } | ConvertTo-Json -Depth 4 -Compress)
  }
  if ($AwsArgs[0] -eq 'autoscaling') { return '{"AutoScalingGroups":[{"AutoScalingGroupName":"portal-asg","DesiredCapacity":1,"MinSize":1,"MaxSize":2,"Instances":[{"LifecycleState":"InService"}]}]}' }
  if ($AwsArgs[0] -eq 'ec2') { return '{"Reservations":[{"Instances":[{"InstanceId":"i-demo","InstanceType":"t3.micro","State":{"Name":"running"},"Tags":[{"Key":"Name","Value":"portal"}]}]}]}' }
  if ($AwsArgs[0] -eq 'rds') { return '{"DBInstances":[{"DBInstanceIdentifier":"portal-db","DBInstanceStatus":"available","MultiAZ":false,"BackupRetentionPeriod":1,"StorageEncrypted":true,"PubliclyAccessible":false}]}' }
  throw "Unexpected mocked AWS command: $command"
}

try {
  $global:AwsDiagnosticMode = 'healthy'
  $global:AwsDiagnosticCalls.Clear()
  $healthy = (& $scriptPath -StackName 'tangamandapio-live-20261013' | ConvertFrom-Json)
  if (-not $healthy.read_only -or $healthy.access_status -ne 'complete' -or $healthy.readiness -ne 'healthy') {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: a healthy mock was not reported healthy.'
  }
  if ($healthy.checks.Count -ne 8 -or $healthy.aws_read_calls -ne 8) {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: expected identity, stack, ALB, target group, target health, ASG, EC2 and RDS reads.'
  }
  if (@($global:AwsDiagnosticCalls | Where-Object { $_ -match '\b(create|delete|modify|update|put|terminate|start|stop)\b' }).Count -gt 0) {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: a mutating AWS operation was attempted.'
  }

  $global:AwsDiagnosticMode = 'unhealthy'
  $degraded = (& $scriptPath -StackName 'tangamandapio-live-20261013' | ConvertFrom-Json)
  if ($degraded.readiness -ne 'degraded') {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: unhealthy ALB target was not reported as degraded.'
  }

  $global:AwsDiagnosticMode = 'denied'
  $global:AwsDiagnosticCalls.Clear()
  $partial = (& $scriptPath -StackName 'tangamandapio-live-20261013' | ConvertFrom-Json)
  if ($partial.access_status -ne 'partial' -or $partial.readiness -ne 'incomplete' -or
      @($partial.checks | Where-Object { $_.error -eq 'access_denied' }).Count -lt 1) {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: explicit IAM denies were not represented as incomplete.'
  }
  if (@($global:AwsDiagnosticCalls | Where-Object { $_ -match '\b(create|delete|modify|update|put|terminate|start|stop)\b' }).Count -gt 0) {
    throw 'AWS_RUNTIME_DIAGNOSTIC_FAILED: a mutating AWS operation was attempted during denied reads.'
  }
  Write-Output 'AWS_RUNTIME_DIAGNOSTIC=3_MOCK_SCENARIOS_PASSED (healthy, degraded, access-denied; no writes)'
}
finally {
  if ($null -eq $savedAwsFunction) { Remove-Item Function:\global:aws -ErrorAction SilentlyContinue }
  else { Set-Item Function:\global:aws -Value $savedAwsFunction.ScriptBlock }
  if ($null -eq $savedLastExitCode) { Remove-Variable LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue }
  else { $global:LASTEXITCODE = $savedLastExitCode }
  Remove-Variable AwsDiagnosticMode, AwsDiagnosticCalls -Scope Global -ErrorAction SilentlyContinue
}
