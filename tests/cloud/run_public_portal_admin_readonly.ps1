param(
  [string]$Profile = 'default',
  [ValidateSet('https', 'alb-origin-https')]
  [string]$PortalTarget = 'https'
)

$ErrorActionPreference = 'Stop'
$region = 'us-east-1'
$acknowledgement = 'I_ACKNOWLEDGE_PUBLIC_ADMIN_READONLY_LOGIN'
if ($env:RUN_PUBLIC_PORTAL_ADMIN_READONLY -cne $acknowledgement) {
  throw 'Refused: set RUN_PUBLIC_PORTAL_ADMIN_READONLY to the documented value before checking the live public portal.'
}

$workspacePath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pythonPath = Join-Path $workspacePath 'app\.venv\Scripts\python.exe'
$testPath = Join-Path $PSScriptRoot 'live_aws_portal_azure_e2e.py'
if (-not (Test-Path -LiteralPath $pythonPath)) {
  throw "No se encontro el entorno Python del proyecto: $pythonPath"
}

$modifiedEnvironmentNames = @(
  'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
  'AWS_SECURITY_TOKEN', 'AWS_PROFILE', 'AWS_REGION', 'AWS_DEFAULT_REGION',
  'LIVE_E2E_TARGET', 'LIVE_E2E_MODE', 'RUN_LIVE_DEPLOYED_E2E'
)
$previousEnvironment = @{}
foreach ($name in $modifiedEnvironmentNames) {
  $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
  foreach ($name in @('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN')) {
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
  }
  $env:AWS_PROFILE = $Profile
  $env:AWS_REGION = $region
  $env:AWS_DEFAULT_REGION = $region

  $identity = aws sts get-caller-identity --profile $Profile --query '[Account,Arn]' --output text --region $region
  $identityExitCode = $LASTEXITCODE
  $identityParts = @($identity -split '\s+')
  if ($identityExitCode -ne 0 -or $identityParts.Count -lt 2 -or
      $identityParts[0] -ne '841113066612' -or $identityParts[1] -notmatch 'assumed-role/voclabs/') {
    throw 'Refused: AWS credentials are not an active Academy VocLabs session for the expected account.'
  }

  $env:LIVE_E2E_TARGET = $PortalTarget
  $env:LIVE_E2E_MODE = 'admin-readonly'
  $env:RUN_LIVE_DEPLOYED_E2E = 'I_ACKNOWLEDGE_LIVE_ADMIN_READONLY_CHECK'
  & $pythonPath $testPath
  $exitCode = $LASTEXITCODE
} finally {
  foreach ($name in $modifiedEnvironmentNames) {
    [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
  }
  Remove-Item Env:LIVE_E2E_TARGET -ErrorAction SilentlyContinue
  Remove-Item Env:LIVE_E2E_MODE -ErrorAction SilentlyContinue
  Remove-Item Env:RUN_LIVE_DEPLOYED_E2E -ErrorAction SilentlyContinue
}

if ($exitCode -ne 0) {
  throw 'The public read-only portal smoke did not pass; inspect the safe diagnostic and do not retry automatically.'
}
