param(
  [switch]$ValidateTerraform
)

$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $workspacePath 'app\.venv\Scripts\python.exe'
$terraformPath = Join-Path $workspacePath 'tools\terraform-1.16.0\terraform.exe'
$terraformDirectory = Join-Path $workspacePath 'iac\environments\azure-demo'
$terraformChdir = "-chdir=$terraformDirectory"

if (-not (Test-Path -LiteralPath $pythonPath)) { throw "No se encontro el entorno Python: $pythonPath" }
Push-Location (Join-Path $workspacePath 'app')
try { & $pythonPath -m unittest discover -s tests -v } finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas unitarias' }

if ($ValidateTerraform) {
  if (-not (Test-Path -LiteralPath $terraformPath)) { throw "No se encontro Terraform: $terraformPath" }
  & $terraformPath $terraformChdir fmt -check -recursive
  if ($LASTEXITCODE -ne 0) { throw 'Terraform fmt fallo' }
  & $terraformPath $terraformChdir init -backend=false -input=false
  if ($LASTEXITCODE -ne 0) { throw 'Terraform init fallo' }
  & $terraformPath $terraformChdir validate
  if ($LASTEXITCODE -ne 0) { throw 'Terraform validate fallo' }
  Write-Host 'TERRAFORM_AZURE=VALIDADO'
} else {
  Write-Host 'TERRAFORM_AZURE=PENDIENTE (ejecute con -ValidateTerraform cuando la dependencia de proveedor este disponible)'
}

Write-Host 'QUALITY_GATE=APROBADA (pruebas unitarias completadas)'
