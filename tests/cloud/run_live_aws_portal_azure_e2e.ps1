param(
    [string]$InstanceId,
    [ValidateSet('loopback', 'alb', 'https', 'alb-origin-https')]
    [string]$PortalTarget = 'loopback',
    [ValidateSet('full', 'admin-modules', 'admin-readonly', 'admin-role-matrix', 'admin-idempotency')]
    [string]$Mode = 'full'
)

$ErrorActionPreference = 'Stop'
$region = 'us-east-1'
$writeOptIn = 'I_ACKNOWLEDGE_SYNTHETIC_RDS_AND_AZURE_WRITES'
$readOnlyOptIn = 'I_ACKNOWLEDGE_LIVE_ADMIN_READONLY_CHECK'
$optInVariable = if ($Mode -eq 'admin-readonly') { 'RUN_LIVE_AWS_ERP_READONLY' } elseif ($Mode -eq 'admin-role-matrix') { 'RUN_LIVE_AWS_ERP_ROLE_MATRIX' } else { 'RUN_LIVE_AWS_ERP_E2E' }
$expectedOptIn = if ($Mode -eq 'admin-readonly') { $readOnlyOptIn } elseif ($Mode -eq 'admin-role-matrix') { 'I_ACKNOWLEDGE_TEMPORARY_ROLE_ACCOUNT_WRITES' } else { $writeOptIn }

if ([Environment]::GetEnvironmentVariable($optInVariable, 'Process') -cne $expectedOptIn) {
    throw "Refused: set $optInVariable to the documented opt-in value before running this live test."
}

$identity = aws sts get-caller-identity --query Arn --output text --region $region
if ($LASTEXITCODE -ne 0 -or $identity -notmatch 'assumed-role/voclabs/') {
    throw 'Refused: AWS credentials are not an active AWS Academy VocLabs session.'
}

$onlineIds = @(aws ssm describe-instance-information --region $region --query "InstanceInformationList[?PingStatus=='Online'].InstanceId" --output text)
if ($LASTEXITCODE -ne 0) {
    throw 'Could not verify SSM-managed instance availability.'
}
$onlineIds = @($onlineIds -split '\s+' | Where-Object { $_ -match '^i-[0-9a-f]+$' })
if ($InstanceId) {
    if ($InstanceId -notin $onlineIds) {
        throw 'The requested EC2 instance is not currently Online in Systems Manager.'
    }
    $target = $InstanceId
} elseif ($onlineIds.Count -gt 0) {
    $target = $onlineIds[0]
} else {
    throw 'No Online Systems Manager instance is available.'
}

$scriptPath = Join-Path $PSScriptRoot 'live_aws_portal_azure_e2e.py'
$scriptBytes = [System.IO.File]::ReadAllBytes($scriptPath)
$compressed = [System.IO.MemoryStream]::new()
$gzip = [System.IO.Compression.GzipStream]::new(
    $compressed,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)
$gzip.Write($scriptBytes, 0, $scriptBytes.Length)
$gzip.Dispose()
$encodedScript = [Convert]::ToBase64String($compressed.ToArray())
$compressed.Dispose()
$remoteCommand = "printf '%s' '$encodedScript' | base64 -d | gzip -d | env RUN_LIVE_DEPLOYED_E2E=$expectedOptIn LIVE_E2E_TARGET=$PortalTarget LIVE_E2E_MODE=$Mode python3 -"
$parameters = @{ commands = @($remoteCommand) } | ConvertTo-Json -Compress
$commandId = aws ssm send-command `
    --document-name AWS-RunShellScript `
    --instance-ids $target `
    --parameters $parameters `
    --region $region `
    --query Command.CommandId `
    --output text
if ($LASTEXITCODE -ne 0 -or -not $commandId -or $commandId -eq 'None') {
    throw 'Systems Manager did not accept the live synthetic smoke command.'
}

$deadline = (Get-Date).AddMinutes(4)
$status = 'Pending'
do {
    Start-Sleep -Seconds 3
    $status = aws ssm get-command-invocation `
        --command-id $commandId `
        --instance-id $target `
        --region $region `
        --query Status `
        --output text 2>$null
} while ($status -in @('Pending', 'InProgress', 'Delayed') -and (Get-Date) -lt $deadline)

if ($status -ne 'Success') {
    throw "Live synthetic smoke failed or timed out (SSM status: $status). Inspect command $commandId before retrying; do not repeat automatically."
}

$output = aws ssm get-command-invocation `
    --command-id $commandId `
    --instance-id $target `
    --region $region `
    --query StandardOutputContent `
    --output text
if ($Mode -eq 'admin-modules') {
    $expectedResult = 'LIVE_ADMIN_MODULE_SMOKE_PASSED'
} elseif ($Mode -eq 'admin-readonly') {
    $expectedResult = 'LIVE_ADMIN_READONLY_SMOKE_PASSED'
} elseif ($Mode -eq 'admin-role-matrix') {
    $expectedResult = 'LIVE_ADMIN_ERP_ROLE_MATRIX_PASSED'
} elseif ($Mode -eq 'admin-idempotency') {
    $expectedResult = 'LIVE_ADMIN_IDEMPOTENCY_SMOKE_PASSED'
} else {
    $expectedResult = 'LIVE_E2E_PASSED'
}
if ($LASTEXITCODE -ne 0 -or $output -notmatch $expectedResult) {
    throw "The remote smoke did not report success. Inspect SSM command $commandId before retrying."
}

Write-Output $output
