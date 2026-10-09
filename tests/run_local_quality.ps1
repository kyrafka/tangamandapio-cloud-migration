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
  try {
    $output = & $pythonPath -m unittest discover -s $TestDirectory -v 2>&1
    $exitCode = $LASTEXITCODE
  } finally {
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

Invoke-UnitSuite -Name 'API base' -WorkingDirectory $appPath -TestDirectory 'tests'
Invoke-UnitSuite -Name 'Azure Functions' -WorkingDirectory $workspacePath -TestDirectory 'app\azure_function_tests'
Invoke-UnitSuite -Name 'Release AWS' -WorkingDirectory (Join-Path $appPath 'aws_release') -TestDirectory 'tests'

if (Test-Path -LiteralPath $auditPath) {
  if (-not (Test-Path -LiteralPath $pythonLockPath)) {
    throw "No se encontro el lock reproducible de Python: $pythonLockPath"
  }
  & $pythonPath (Join-Path $PSScriptRoot 'check_python_lock.py')
  if ($LASTEXITCODE -ne 0) { throw 'El lock Python no satisface todos los manifiestos' }
  & $auditPath -r $pythonLockPath --progress-spinner off
  if ($LASTEXITCODE -ne 0) { throw 'La auditoría de dependencias Python detectó problemas' }
  Write-Host 'PYTHON_DEPENDENCY_AUDIT=APROBADA'
} else {
  Write-Host 'PYTHON_DEPENDENCY_AUDIT=OMITIDA (instale pip-audit en app/.venv; se omite también la comprobación del lock)'
}

if (Test-Path -LiteralPath $cfnLintPath) {
  & $cfnLintPath (Join-Path $workspacePath 'iac\cloudformation\aws-lab.yaml') `
    (Join-Path $workspacePath 'iac\cloudformation\voice-recordings.yaml')
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
      'iac\environments\azure-demo'
    )) {
    & $terraformPath fmt -check -recursive (Join-Path $workspacePath $relativePath)
    if ($LASTEXITCODE -ne 0) { throw "Terraform fmt fallo en $relativePath" }
  }

  foreach ($relativePath in @('iac\environments\demo', 'iac\environments\azure-demo')) {
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
  Write-Host 'TERRAFORM=FORMATO_Y_VALIDACION_APROBADOS (sin aplicar recursos)'
} else {
  Write-Host 'TERRAFORM=NO_EJECUTADO (use -ValidateTerraform para validar IaC sin desplegar)'
}

Write-Host "QUALITY_GATE=APROBADA ($script:passedTests pruebas unitarias; sin operaciones de nube)"
