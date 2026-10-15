param(
  [switch]$ValidateTerraform
)

$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$appPath = Join-Path $workspacePath 'app'
$pythonPath = Join-Path $appPath '.venv\Scripts\python.exe'
$pythonLockPath = Join-Path $appPath 'requirements-ci.lock'
$terraformPath = Join-Path $workspacePath 'tools\terraform-1.16.0\terraform.exe'
$auditPath = Join-Path $appPath '.venv\Scripts\pip-audit.exe'
$cfnLintPath = Join-Path $appPath '.venv\Scripts\cfn-lint.exe'
$script:passedTests = 0

if (-not (Test-Path -LiteralPath $pythonPath)) {
  throw "No se encontro el entorno Python del proyecto: $pythonPath"
}

function Invoke-UnitSuite {
  param(
    [Parameter(Mandatory)] [string] $Name,
    [Parameter(Mandatory)] [string] $WorkingDirectory,
    [Parameter(Mandatory)] [string] $TestDirectory
  )

  Push-Location $WorkingDirectory
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $output = & $pythonPath -m unittest discover -s $TestDirectory -v 2>&1
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Pop-Location
  }

  if ($exitCode -ne 0) {
    $output | ForEach-Object { Write-Host $_ }
    throw "Fallaron las pruebas de $Name"
  }

  $summary = $output | Select-String -Pattern 'Ran (\d+) tests|^OK$'
  $runLine = $summary | Where-Object { $_.Line -match 'Ran (\d+) tests' } | Select-Object -Last 1
  if (-not $runLine -or $runLine.Line -notmatch 'Ran (\d+) tests') {
    $output | ForEach-Object { Write-Host $_ }
    throw "No se pudo leer el resumen de pruebas de $Name"
  }

  $suiteCount = [int]$Matches[1]
  $script:passedTests += $suiteCount
  Write-Host "$Name`: $suiteCount pruebas aprobadas"
}

Push-Location $appPath
try {
  & $pythonPath -m compileall -q src azure_function aws_release\current
  if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación sintáctica de Python' }
} finally {
  Pop-Location
}

& $pythonPath -m py_compile (Join-Path $workspacePath 'tests\run_live_azure_erp_smoke.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación de la prueba viva ERP→Azure' }
Invoke-UnitSuite -Name 'Azure smoke guard' -WorkingDirectory $workspacePath -TestDirectory 'tests'
Invoke-UnitSuite -Name 'Tailscale preflight' -WorkingDirectory $workspacePath -TestDirectory 'tests\cloud'
& $pythonPath -m py_compile (Join-Path $workspacePath 'iac\scripts\check_tailscale_prerequisites.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación del preflight Tailscale' }
& $pythonPath -m py_compile (Join-Path $workspacePath 'tests\aws\rds_integrity_probe.py')
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación de la sonda SQL del restore RDS' }

$powerShellScripts = @(
  'iac\scripts\estimate_cloud_costs.ps1',
  'iac\scripts\deploy_aws_vpn.ps1',
  'iac\scripts\connect_azure_vpn.ps1',
  'iac\scripts\check_aws_azure_vpn.ps1',
  'iac\scripts\disconnect_azure_vpn.ps1',
  'iac\scripts\inspect_aws_runtime.ps1'
)
foreach ($relativePath in $powerShellScripts) {
  $parseTokens = $null
  $parseErrors = $null
  $parsePath = Join-Path $workspacePath $relativePath
  [void][System.Management.Automation.Language.Parser]::ParseFile($parsePath, [ref]$parseTokens, [ref]$parseErrors)
  if ($parseErrors.Count -gt 0) {
    $parseErrors | ForEach-Object { Write-Host $_ }
    throw "Error de sintaxis PowerShell en $relativePath"
  }
}
$costScriptPath = Join-Path $workspacePath 'iac\scripts\estimate_cloud_costs.ps1'
$costEstimateOutput = & $costScriptPath | Out-String
if ($costEstimateOutput -notmatch 'Modeled AWS subtotal \(not all-in\)\s+\$\s*91\.92') {
  throw 'La estimación reproducible de costo no coincide con el subtotal base esperado de $91.92'
}
$partTimeCostOutput = & $costScriptPath `
  -ComputeHours 160 -SharedInfrastructureHours 730 -AverageAlbLcuPerHour 0.1 -NatProcessedGb 2 | Out-String
if ($partTimeCostOutput -notmatch 'Modeled AWS subtotal \(not all-in\)\s+\$\s*64\.19') {
  throw 'La estimación no mantuvo ALB/NAT/IPv4 por hora al detener solamente EC2 y RDS'
}
$deployGuardText = $null
try {
  $deployGuardText = & (Join-Path $workspacePath 'iac\scripts\deploy_aws_vpn.ps1') `
    -PortalStackName 'guard-only' -AppRouteTableId 'rtb-0123456789abcdef0' 2>&1 | Out-String
} catch {
  $deployGuardText = $_.Exception.Message
}
if ($deployGuardText -notmatch 'No se desplegó: revise el costo recurrente') {
  throw 'El script VPN AWS no bloqueó el despliegue sin aprobar el costo recurrente'
}
& (Join-Path $workspacePath 'tests\aws\vpn_deploy_preflight_test.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Fallaron los mocks de preflight del despliegue VPN AWS' }
& (Join-Path $workspacePath 'tests\aws\inspect_aws_runtime_test.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Fallaron los mocks del diagnóstico read-only AWS' }

$previousVpnCleanupOptIn = $env:CONFIRM_TANGAMA_VPN_CLEANUP
Remove-Item Env:CONFIRM_TANGAMA_VPN_CLEANUP -ErrorAction SilentlyContinue
$cleanupGuardText = $null
try {
  $cleanupGuardText = & (Join-Path $workspacePath 'iac\scripts\disconnect_azure_vpn.ps1') `
    -AzureResourceGroup 'guard-only' -AwsVpnStackName 'tangamandapio-aws-azure-vpn' 2>&1 | Out-String
} catch {
  $cleanupGuardText = $_.Exception.Message
} finally {
  if ($null -ne $previousVpnCleanupOptIn) { $env:CONFIRM_TANGAMA_VPN_CLEANUP = $previousVpnCleanupOptIn }
}
if ($cleanupGuardText -notmatch 'Desmontaje cancelado') {
  throw 'El script VPN no bloqueó el desmontaje sin confirmación explícita'
}
$connectAst = [System.Management.Automation.Language.Parser]::ParseFile(
  (Join-Path $workspacePath 'iac\scripts\connect_azure_vpn.ps1'), [ref]$parseTokens, [ref]$parseErrors
)
$ipOffsetFunction = $connectAst.Find({
  param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-IpOffset'
}, $true)
if (-not $ipOffsetFunction) { throw 'No se encontró el cálculo de peer BGP de la VPN' }
Invoke-Expression $ipOffsetFunction.Extent.Text
$peerChecks = @(
  @('169.254.21.0/30', '169.254.21.1'),
  @('169.254.22.0/30', '169.254.22.1'),
  @('169.254.21.4/30', '169.254.21.5'),
  @('169.254.22.4/30', '169.254.22.5')
)
foreach ($check in $peerChecks) {
  $actualPeer = Get-IpOffset -Cidr $check[0] -Offset 1
  if ($actualPeer -ne $check[1]) { throw "Peer BGP incorrecto para $($check[0])" }
}
$vpnTemplate = Get-Content -Raw (Join-Path $workspacePath 'iac\cloudformation\aws-azure-vpn.yaml')
$vpnTerraform = Get-Content -Raw (Join-Path $workspacePath 'iac\environments\aws-azure-vpn\main.tf')
$vpnConnector = Get-Content -Raw (Join-Path $workspacePath 'iac\scripts\connect_azure_vpn.ps1')
foreach ($mapping in @(
  @('169.254.21.0/30', '169.254.21.2', 'a'),
  @('169.254.22.0/30', '169.254.22.2', 'a'),
  @('169.254.21.4/30', '169.254.21.6', 'b'),
  @('169.254.22.4/30', '169.254.22.6', 'b')
)) {
  $cidrPattern = [regex]::Escape("TunnelInsideCidr: $($mapping[0])")
  $scriptPattern = [regex]::Escape("'$($mapping[0])' = @{ Peer = '$($mapping[1])'; Instance = '$($mapping[2])' }")
  if ($vpnTemplate -notmatch $cidrPattern -or $vpnConnector -notmatch $scriptPattern) {
    throw "El contrato CloudFormation/Azure no coincide para el túnel $($mapping[0])"
  }
  if ($vpnTerraform -notmatch [regex]::Escape("`"$($mapping[1])`"")) {
    throw "Terraform Azure no declara el peer APIPA $($mapping[1])"
  }
}
Write-Host 'POWERSHELL_INFRA_SCRIPTS=PARSE_APROBADO'

$gitBashPath = 'C:\Program Files\Git\bin\bash.exe'
if (Test-Path -LiteralPath $gitBashPath) {
  $restoreTestPath = Join-Path $workspacePath 'tests\aws\pt-dr-01-rds-restore.sh'
  $restoreTestText = Get-Content -LiteralPath $restoreTestPath -Raw
  $restoreProbeText = Get-Content -LiteralPath (Join-Path $workspacePath 'tests\aws\rds_integrity_probe.py') -Raw
  $destroyTestPath = Join-Path $workspacePath 'tests\aws\destroy_safety_test.sh'
  $stackNameGuardPath = Join-Path $workspacePath 'tests\aws\stack_name_guard_test.sh'
  $portalArtifactTestPath = Join-Path $workspacePath 'tests\aws\package_portal_artifact_test.sh'
  $pythonRuntimeGuardPath = Join-Path $workspacePath 'tests\aws\python_runtime_guard_test.sh'
  $certificatePreflightTestPath = Join-Path $workspacePath 'tests\aws\certificate_preflight_test.sh'
  $monitorRestoreTestPath = Join-Path $workspacePath 'tests\aws\pt-mon-restore_mock_test.sh'
  $storageTestPath = Join-Path $workspacePath 'tests\aws\pt-sto-01-s3.sh'
  $monitorTestPath = Join-Path $workspacePath 'tests\aws\pt-mon-01-alarm.sh'
  $destroyMockPath = Join-Path $workspacePath 'tests\aws\fixtures\mock_aws_destroy_unsafe_template.sh'
  $certificateMockPath = Join-Path $workspacePath 'tests\aws\fixtures\mock_aws_certificate_preflight.sh'
  $alarmMockPath = Join-Path $workspacePath 'tests\aws\fixtures\mock_aws_alarm_state.sh'
  & $gitBashPath -n $restoreTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash del test de restore RDS' }
  if ($restoreTestText -notmatch '(?s)RTO_START=.*?aws rds restore-db-instance-from-db-snapshot') {
    throw 'La medición RTO debe iniciar antes del restore, no durante la creación del snapshot.'
  }
  if ($restoreTestText -notmatch '(?s)aws rds restore-db-instance-from-db-snapshot.*?--backup-retention-period 0') {
    throw 'El restore temporal debe desactivar backups automáticos para evitar retención facturable adicional.'
  }
  if ($restoreTestText -notmatch 'db\["BackupRetentionPeriod"\] == 0') {
    throw 'La sonda de restore debe verificar que la retención automática quedó desactivada.'
  }
  if ($restoreTestText -notmatch 'DatabaseSecretArn' -or $restoreTestText -match 'logical-resource-id DBSecret') {
    throw 'El restore debe resolver el ARN físico exportado, también cuando RDS administra el secreto maestro.'
  }
  if ($restoreTestText -notmatch "tr -d '\\r'") {
    throw 'El parser del restore debe normalizar CRLF del Python de Windows antes del preflight.'
  }
  if ($restoreTestText -notmatch 'REMOTE_PYTHON=.*venv/bin/python' -or
      $restoreTestText -notmatch '(?s)invoke_probe .* preflight.*?PROBE_CREATED=true\s+PROBE_JSON=.*invoke_probe .* create' -or
      $restoreProbeText -notmatch 'operation == "preflight"' -or
      $restoreProbeText -notmatch 'secret_region = secret_arn\.split\(":"\)\[3\]') {
    throw 'La sonda debe verificar el runtime de aplicación por SSM antes de armar limpieza y derivar la región del ARN secreto.'
  }
  if ($restoreTestText -notmatch 'json\.dumps\(json\.loads\(sys\.stdin\.read\(\)\)\["marker_present"\]\)') {
    throw 'El restore debe comparar booleanos JSON en minúscula para Bash multiplataforma.'
  }
  & $gitBashPath -n (Join-Path $workspacePath 'iac\cloudformation\destroy.sh')
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de destroy.sh' }
  & $gitBashPath -n $destroyTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de la prueba destroy safety' }
  & $gitBashPath -n $stackNameGuardPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de la prueba de stack explícito' }
  & $gitBashPath -n $portalArtifactTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de la prueba del paquete del portal' }
  & $gitBashPath -n $monitorRestoreTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de la prueba de restauración de alarma' }
  & $gitBashPath -n $storageTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de PT-STO-01' }
  & $gitBashPath -n $monitorTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash de PT-MON-01' }
  & $gitBashPath -n $alarmMockPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica del mock de CloudWatch' }
  & $gitBashPath -n $destroyMockPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica Bash del mock AWS para destroy.sh' }
  & $gitBashPath $destroyTestPath
  if ($LASTEXITCODE -ne 0) { throw 'destroy.sh no bloqueó el borrado con políticas de recuperación inseguras' }
  Write-Host 'DESTROY_SAFETY=FAIL_CLOSED_GUARD_APPROVED (mock AWS; sin operaciones de nube)'
  & $gitBashPath $stackNameGuardPath
  if ($LASTEXITCODE -ne 0) { throw 'Los scripts CloudFormation no bloquearon nombres de stack ausentes/incorrectos' }
  $deployScriptPath = Join-Path $workspacePath 'iac\cloudformation\deploy.sh'
  $releaseParameterNames = @('STACK_NAME', 'APPLICATION_ARTIFACT_KEY', 'APPLICATION_ARTIFACT_REVISION', 'APPLICATION_ARTIFACT_SHA256')
  $previousReleaseParameters = @{}
  foreach ($name in $releaseParameterNames) {
    $previousReleaseParameters[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  }
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    # These two deploy invocations are expected to exit non-zero before any
    # AWS call. Keep PowerShell from turning the native stderr into a throw so
    # the harness can assert the exit code and guard message explicitly.
    $ErrorActionPreference = 'Continue'
    $env:STACK_NAME = 'tangamandapio-live-20261013'
    $env:APPLICATION_ARTIFACT_KEY = 'releases/tangamandapio/portal-local-test.tar.gz'
    $env:APPLICATION_ARTIFACT_REVISION = 'local-test'
    $env:APPLICATION_ARTIFACT_SHA256 = ('0' * 64)
    $artifactKeyGuardOutput = & $gitBashPath $deployScriptPath 2>&1
    $artifactKeyGuardExit = $LASTEXITCODE

    $env:APPLICATION_ARTIFACT_KEY = "releases/tangamandapio/portal-local-test-$($env:APPLICATION_ARTIFACT_SHA256).tar.gz"
    $env:APPLICATION_ARTIFACT_SHA256 = 'not-a-sha256'
    $artifactHashGuardOutput = & $gitBashPath $deployScriptPath 2>&1
    $artifactHashGuardExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    foreach ($name in $releaseParameterNames) {
      [Environment]::SetEnvironmentVariable($name, $previousReleaseParameters[$name], 'Process')
    }
  }
  if ($artifactKeyGuardExit -ne 2 -or ($artifactKeyGuardOutput -join "`n") -notmatch 'debe incluir el SHA-256 completo') {
    throw 'deploy.sh no rechazó una clave de artefacto mutable antes de consultar AWS.'
  }
  if ($artifactHashGuardExit -ne 2 -or ($artifactHashGuardOutput -join "`n") -notmatch 'debe contener exactamente 64 caracteres') {
    throw 'deploy.sh no rechazó un SHA-256 mal formado antes de consultar AWS.'
  }
  Write-Host 'ARTIFACT_RELEASE_GUARDS=SHA256_AND_IMMUTABLE_KEY_APPROVED (sin llamadas AWS)'
  & $gitBashPath $portalArtifactTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la integridad, contenido o exclusión de secretos del paquete del portal' }
  & $gitBashPath -n $pythonRuntimeGuardPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica del guard del runtime Python AWS' }
  & $gitBashPath -n $certificatePreflightTestPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica de la prueba de preflight ACM/HTTPS' }
  & $gitBashPath -n $certificateMockPath
  if ($LASTEXITCODE -ne 0) { throw 'Falló la validación sintáctica del mock ACM/CloudFormation' }
  & $gitBashPath $certificatePreflightTestPath
  if ($LASTEXITCODE -ne 0) { throw 'El preflight ACM/HTTPS no rechazó entradas inválidas o aceptó una cobertura DNS incorrecta' }
  Write-Host 'HTTPS_PREFLIGHT=ACM_REGION_STATUS_SAN_AND_WILDCARD_GUARDS_APPROVED (mock AWS; sin mutaciones)'
  & $gitBashPath $pythonRuntimeGuardPath
  if ($LASTEXITCODE -ne 0) { throw 'La plantilla no fija el runtime de Python usado por las dependencias del release' }
  & $gitBashPath $monitorRestoreTestPath
  if ($LASTEXITCODE -ne 0) { throw 'PT-MON-01 no restauró el estado original tras éxito/error' }
  $probePathWindows = Join-Path $workspacePath 'tests\aws\rds_integrity_probe.py'
  $probeDrive = $probePathWindows.Substring(0, 1).ToLowerInvariant()
  $probePathBash = '/' + $probeDrive + $probePathWindows.Substring(2).Replace('\', '/')
  $probePathBashQuoted = "'" + $probePathBash + "'"
  $probeRoundTrip = "set -o pipefail; gzip -c $probePathBashQuoted | base64 | base64 -d | gzip -d | cmp - $probePathBashQuoted"
  & $gitBashPath -c $probeRoundTrip
  if ($LASTEXITCODE -ne 0) { throw 'La sonda SQL RDS no sobrevive al empaquetado remoto gzip/Base64' }
  $previousDrOptIn = $env:CONFIRM_COSTLY_DR_TEST
  Remove-Item Env:CONFIRM_COSTLY_DR_TEST -ErrorAction SilentlyContinue
  try {
    $restoreDrive = $restoreTestPath.Substring(0, 1).ToLowerInvariant()
    $restorePathBash = '/' + $restoreDrive + $restoreTestPath.Substring(2).Replace('\', '/')
    $restorePathBashQuoted = "'" + $restorePathBash + "'"
    $guardCommand = 'unset CONFIRM_COSTLY_DR_TEST; AWS_PROFILE=tangama-guard-no-auth AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_CONFIG_FILE=/dev/null ' + $restorePathBashQuoted + ' 2>/dev/null; status=$?; printf "DR_GUARD_EXIT=%s\n" "$status"; test "$status" -eq 2'
    $guardOutput = & $gitBashPath -c $guardCommand
    $drGuardExit = $LASTEXITCODE
  } finally {
    if ($null -ne $previousDrOptIn) { $env:CONFIRM_COSTLY_DR_TEST = $previousDrOptIn }
  }
  if ($drGuardExit -ne 0 -or ($guardOutput -join "`n") -notmatch 'DR_GUARD_EXIT=2') {
    throw 'El test de restore RDS no rechazó una ejecución sin opt-in explícito'
  }
  Write-Host 'RDS_RESTORE=SYNTAX_COST_RTO_AND_RETENTION_GUARDS_APROBADOS (sin operaciones de nube)'
} else {
  Write-Host 'RDS_RESTORE=CHEQUEO_BASH_OMITIDO (instale Git for Windows para incluirlo)'
}

$previousLiveOptIn = $env:TANGAMA_LIVE_AZURE_SMOKE
Remove-Item Env:TANGAMA_LIVE_AZURE_SMOKE -ErrorAction SilentlyContinue
try {
  $liveGuardOutput = & $pythonPath (Join-Path $workspacePath 'tests\run_live_azure_erp_smoke.py') 2>&1
  $liveGuardExit = $LASTEXITCODE
} finally {
  if ($null -ne $previousLiveOptIn) { $env:TANGAMA_LIVE_AZURE_SMOKE = $previousLiveOptIn }
}
if ($liveGuardExit -ne 2 -or ($liveGuardOutput -join "`n") -notmatch 'REFUSED:') {
  $liveGuardOutput | ForEach-Object { Write-Host $_ }
  throw 'La prueba viva ERP→Azure no se protegió contra ejecución involuntaria'
}
Write-Host 'LIVE_AZURE_SMOKE=SYNTAX_AND_OPT_IN_GUARD_APPROVED (sin operaciones de nube)'

Invoke-UnitSuite -Name 'API base' -WorkingDirectory $appPath -TestDirectory 'tests'
Invoke-UnitSuite -Name 'Azure Functions' -WorkingDirectory $workspacePath -TestDirectory 'app\azure_function_tests'
Invoke-UnitSuite -Name 'Release AWS' -WorkingDirectory (Join-Path $appPath 'aws_release') -TestDirectory 'tests'

$transactionLoadPath = Join-Path $workspacePath 'tests\performance\transactional_load_test.py'
$previousErrorActionPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = 'Continue'
  $transactionLoadOutput = & $pythonPath $transactionLoadPath `
    --requests 40 --concurrency 8 --max-p95-ms 5000 2>&1
  $transactionLoadExitCode = $LASTEXITCODE
} finally {
  $ErrorActionPreference = $previousErrorActionPreference
}
if ($transactionLoadExitCode -ne 0) {
  $transactionLoadOutput | ForEach-Object { Write-Host $_ }
  throw 'Falló el flujo transaccional local concurrente y aislado (PT-PERF-02)'
}
Write-Host 'PT_PERF_02=40_TRANSACCIONES_AISLADAS_APROBADAS (sin nube ni datos persistentes)'

if (-not (Test-Path -LiteralPath $pythonLockPath)) {
  throw "No se encontro el lock reproducible de Python: $pythonLockPath"
}
& $pythonPath (Join-Path $PSScriptRoot 'check_python_lock.py')
if ($LASTEXITCODE -ne 0) { throw 'El lock Python no satisface todos los manifiestos' }
$azurePackageBuilder = Join-Path $workspacePath 'iac\scripts\package_azure_function.ps1'
$azurePackageOutput = & $azurePackageBuilder -PythonExecutable $pythonPath 6>&1
$azurePackageExitCode = $LASTEXITCODE
$azurePackageOutput | ForEach-Object { Write-Host $_ }
if ($azurePackageExitCode -ne 0) { throw 'No se pudo construir el paquete inmutable de Azure' }
$packagePathLine = $azurePackageOutput |
  ForEach-Object { $_.ToString() } |
  Where-Object { $_ -match '^PACKAGE_PATH=.+$' } |
  Select-Object -Last 1
if (-not $packagePathLine) { throw 'El empaquetador Azure no informó la ruta del ZIP generado' }
$generatedAzurePackagePath = $packagePathLine.Substring('PACKAGE_PATH='.Length)
& $pythonPath (Join-Path $PSScriptRoot 'check_azure_package.py') $generatedAzurePackagePath
if ($LASTEXITCODE -ne 0) { throw 'El ZIP configurado de Azure no coincide con el código fuente vigente' }

if (Test-Path -LiteralPath $auditPath) {
  & $auditPath -r $pythonLockPath --progress-spinner off
  if ($LASTEXITCODE -ne 0) { throw 'La auditoría de dependencias Python detectó problemas' }
  & $auditPath -r (Join-Path $workspacePath 'app\aws_release\current\requirements.lock') --progress-spinner off
  if ($LASTEXITCODE -ne 0) { throw 'La auditoría de dependencias del release AWS detectó problemas' }
  & $auditPath -r (Join-Path $workspacePath 'app\azure_function\requirements.lock') --progress-spinner off
  if ($LASTEXITCODE -ne 0) { throw 'La auditoría de dependencias Azure Function detectó problemas' }
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    # pip writes normal resolver/download progress to stderr; collect it without
    # letting PowerShell 7 treat native stderr as a terminating exception.
    $ErrorActionPreference = 'Continue'
    $awsRuntimeProbeOutput = & $pythonPath -m pip install --dry-run --ignore-installed --require-hashes --only-binary=:all: --python-version 3.12 --platform manylinux2014_x86_64 --implementation cp --abi cp312 -r (Join-Path $workspacePath 'app\aws_release\current\requirements.lock') 2>&1
    $awsRuntimeProbeExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($awsRuntimeProbeExit -ne 0) {
    $awsRuntimeProbeOutput | ForEach-Object { Write-Host $_ }
    throw 'El lock del release AWS no se puede instalar para Python 3.12/Linux con los hashes fijados'
  }
  Write-Host 'AWS_RUNTIME=PYTHON_3_12_LINUX_LOCK_INSTALLABLE (dry-run; sin instalar)'
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $azureRuntimeProbeOutput = & $pythonPath -m pip install --dry-run --ignore-installed --require-hashes --only-binary=:all: --python-version 3.11 --platform manylinux2014_x86_64 --implementation cp --abi cp311 -r (Join-Path $workspacePath 'app\azure_function\requirements.lock') 2>&1
    $azureRuntimeProbeExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($azureRuntimeProbeExit -ne 0) {
    $azureRuntimeProbeOutput | ForEach-Object { Write-Host $_ }
    throw 'El lock Azure no se puede instalar para Python 3.11/Linux con los hashes fijados'
  }
  Write-Host 'AZURE_RUNTIME=PYTHON_3_11_LINUX_LOCK_INSTALLABLE (dry-run; sin instalar)'
  Write-Host 'PYTHON_DEPENDENCY_AUDIT=APROBADA (CI, release AWS y Azure Function)'
} else {
  Write-Host 'PYTHON_DEPENDENCY_AUDIT=OMITIDA (instale pip-audit en app/.venv; se omite también la comprobación del lock)'
}

if (Test-Path -LiteralPath $cfnLintPath) {
  $awsTemplatePath = Join-Path $workspacePath 'iac\cloudformation\aws-lab.yaml'
  $deployScriptText = Get-Content -Raw (Join-Path $workspacePath 'iac\cloudformation\deploy.sh')
  $rebuildScriptText = Get-Content -Raw (Join-Path $workspacePath 'iac\cloudformation\rebuild.sh')
  $awsTemplateText = (Get-Content -Raw $awsTemplatePath).Replace("`r", '')
  $domainPatternContract = @'
AllowedPattern: '^$|^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$'
'@
  if (-not $awsTemplateText.Contains($domainPatternContract)) {
    throw 'CloudFormation debe rechazar labels DNS vacíos, con guiones en los extremos o de más de 63 caracteres.'
  }
  $shaParameterContract = @'
(?m)^  ApplicationArtifactSha256:
    Type: String
    Default: (?:''|[a-f0-9]{64})
    AllowedPattern: '\^\$\|\^\[a-f0-9\]\{64\}\$'
'@
  if ($awsTemplateText -notmatch $shaParameterContract) {
    throw 'CloudFormation no valida el parámetro SHA-256 del artefacto del portal.'
  }
  if ($awsTemplateText -notmatch '(?s)aws s3 cp .*?ARTIFACT_SHA256_ACTUAL=.*?if \[ -n ''\$\{ApplicationArtifactSha256\}'' \].*?tar -xzf') {
    throw 'Las instancias deben comprobar el SHA-256 antes de extraer el paquete.'
  }
  if ($deployScriptText -notmatch 'APPLICATION_ARTIFACT_KEY.*APPLICATION_ARTIFACT_REVISION.*APPLICATION_ARTIFACT_SHA256' -or
      $deployScriptText -notmatch 'ApplicationArtifactSha256' -or
      $deployScriptText -notmatch '(?s)APPLICATION_ARTIFACT_KEY.*APPLICATION_ARTIFACT_SHA256.*preservar el release previo') {
    throw 'El despliegue existente no exige una clave inmutable ni propaga el hash del artefacto.'
  }
  if ($awsTemplateText -notmatch '(?s)PortalDomainName:.*CertificateArn.*HasCertificate' -or
      $awsTemplateText -notmatch 'https://\$\{PortalDomainName\}' -or
      $deployScriptText -notmatch '(?s)HTTPS requiere definir juntos CERTIFICATE_ARN y PORTAL_DOMAIN_NAME.*CertificateArn\).*CERTIFICATE_ARN.*PortalDomainName\).*PORTAL_DOMAIN_NAME' -or
      $deployScriptText -notmatch 'Certificate\.SubjectAlternativeNames') {
    throw 'El paso HTTPS debe exigir dominio + certificado, validar cobertura DNS y emitir el dominio correcto.'
  }
  if ($rebuildScriptText -notmatch '(?s)ARTIFACT_SHA256=.*?portal-\$\{REVISION\}-\$\{ARTIFACT_SHA256\}\.tar\.gz.*?ApplicationArtifactSha256,ParameterValue=\$ARTIFACT_SHA256') {
    throw 'La reconstrucción no usa una clave de paquete inmutable y fija el hash en CloudFormation.'
  }
  & $cfnLintPath $awsTemplatePath `
    (Join-Path $workspacePath 'iac\cloudformation\voice-recordings.yaml') `
    (Join-Path $workspacePath 'iac\cloudformation\aws-azure-vpn.yaml')
  if ($LASTEXITCODE -ne 0) { throw 'cfn-lint encontró problemas en CloudFormation' }
  Write-Host 'CLOUDFORMATION=VALIDADA'
} else {
  Write-Host 'CLOUDFORMATION=OMITIDA (instale cfn-lint en app/.venv)'
}

$webPath = Join-Path $appPath 'web'
$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if ($pnpmCommand -and (Test-Path -LiteralPath (Join-Path $webPath 'node_modules'))) {
  Push-Location $webPath
  try {
    & pnpm run test:access
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas locales de navegación por rol' }
    & pnpm run test:csv
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas locales de importación CSV del catálogo' }
    & pnpm run build:check
    if ($LASTEXITCODE -ne 0) { throw 'Falló el build de producción de la web' }
    & pnpm audit --prod --audit-level high
    if ($LASTEXITCODE -ne 0) { throw 'La auditoría de dependencias frontend detectó problemas' }
  } finally {
    Pop-Location
  }
  Write-Host 'FRONTEND_BUILD=APROBADO'
} else {
  Write-Host 'FRONTEND_BUILD=OMITIDO (instale pnpm y dependencias en app/web para incluirlo)'
}

if ($ValidateTerraform) {
  if (-not (Test-Path -LiteralPath $terraformPath)) {
    throw "No se encontro Terraform: $terraformPath"
  }

  foreach ($relativePath in @(
      'iac\modules\aws_network',
      'iac\modules\azure_operations',
      'iac\environments\demo',
      'iac\environments\azure-demo',
      'iac\environments\azure-rebuild',
      'iac\environments\aws-azure-vpn',
      'iac\environments\azure-flex-private'
    )) {
    & $terraformPath fmt -check -recursive (Join-Path $workspacePath $relativePath)
    if ($LASTEXITCODE -ne 0) { throw "Terraform fmt fallo en $relativePath" }
  }

  foreach ($relativePath in @(
      'iac\environments\demo',
      'iac\environments\azure-demo',
      'iac\environments\azure-rebuild',
      'iac\environments\aws-azure-vpn',
      'iac\environments\azure-flex-private'
    )) {
    Push-Location (Join-Path $workspacePath $relativePath)
    try {
      & $terraformPath init -backend=false -input=false -lockfile=readonly -no-color
      if ($LASTEXITCODE -ne 0) { throw "Terraform init fallo en $relativePath" }
      & $terraformPath validate -no-color
      if ($LASTEXITCODE -ne 0) { throw "Terraform validate fallo en $relativePath" }
    } finally {
      Pop-Location
    }
  }
  Push-Location (Join-Path $workspacePath 'iac\environments\aws-azure-vpn')
  try {
    & $terraformPath test -no-color
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas mock del bloqueo de costo de la VPN.' }
  } finally {
    Pop-Location
  }
  Write-Host 'VPN_COST_GATE=MOCK_TESTS_APROBADOS (sin credenciales ni recursos cloud)'
  Push-Location (Join-Path $workspacePath 'iac\environments\azure-flex-private')
  try {
    & $terraformPath test -no-color
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas mock de Flex privado y su compuerta de costo.' }
  } finally {
    Pop-Location
  }
  Write-Host 'AZURE_FLEX_PRIVATE=COST_GATE_AND_NETWORKING_TESTS_APROBADOS (sin recursos cloud)'
  Write-Host 'TERRAFORM=FORMATO_Y_VALIDACION_APROBADOS (sin aplicar recursos)'
} else {
  Write-Host 'TERRAFORM=NO_EJECUTADO (use -ValidateTerraform para validar IaC sin desplegar)'
}

Write-Host "QUALITY_GATE=APROBADA ($script:passedTests pruebas unitarias; sin operaciones de nube)"
