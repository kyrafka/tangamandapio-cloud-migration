$ErrorActionPreference = 'Stop'

$venv = Join-Path $PSScriptRoot '.venv'
$python = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $python)) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        throw 'No se encontró Python. Instala Python 3.10 o posterior y vuelve a intentarlo.'
    }
    & $systemPython.Source -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno local de Moto.' }
}

& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar Moto desde PyPI.' }

Write-Host 'Moto quedó instalado dentro de iac/local-emulator/.venv.'
