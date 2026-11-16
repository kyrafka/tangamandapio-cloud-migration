$ErrorActionPreference = 'Stop'

$server = Join-Path $PSScriptRoot '.venv\Scripts\moto_server.exe'
$pidFile = Join-Path $env:TEMP 'tangamandapio-moto\server.pid'

if (-not (Test-Path $pidFile)) {
    Write-Host 'No hay un proceso de Moto registrado para detener.'
    return
}

$serverPid = 0
if (-not [int]::TryParse((Get-Content $pidFile -Raw), [ref]$serverPid) -or $serverPid -le 0) {
    throw 'El archivo local de proceso no es válido; no se detuvo ningún proceso.'
}

$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if (-not $process) {
    Remove-Item $pidFile -Force
    Write-Host 'Moto ya estaba detenido.'
    return
}

if ($process.Path -ne $server) {
    throw "El PID $serverPid ya pertenece a otro proceso; no se detuvo."
}

Stop-Process -Id $serverPid
Remove-Item $pidFile -Force
Write-Host 'Moto quedó detenido. No se tocó ningún proceso de AWS ni Azure.'
