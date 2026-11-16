$ErrorActionPreference = 'Stop'

$server = Join-Path $PSScriptRoot '.venv\Scripts\moto_server.exe'
$runtime = Join-Path $env:TEMP 'tangamandapio-moto'
$pidFile = Join-Path $runtime 'server.pid'
$stdout = Join-Path $runtime 'server.log'
$stderr = Join-Path $runtime 'server-error.log'
$port = 5000

if (-not (Test-Path $server)) {
    & (Join-Path $PSScriptRoot 'install.ps1')
}

New-Item -ItemType Directory -Path $runtime -Force | Out-Null

if (Test-Path $pidFile) {
    $savedPid = 0
    [void][int]::TryParse((Get-Content $pidFile -Raw), [ref]$savedPid)
    if ($savedPid -gt 0) {
        $existing = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
        if ($existing -and $existing.Path -eq $server) {
            try {
                $null = Invoke-WebRequest -Uri "http://127.0.0.1:$port/" -TimeoutSec 2
                Write-Host "Moto ya está disponible en http://127.0.0.1:$port"
                return
            } catch {
                # El proceso existe pero el servicio no responde; no se mata automáticamente.
                throw "El proceso de Moto ($savedPid) existe, pero no responde. Revisa $stderr antes de detenerlo."
            }
        }
    }
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    throw "El puerto local $port ya está ocupado por otro proceso. No se modificó ni cerró."
}

$process = Start-Process -FilePath $server -ArgumentList @('-H', '127.0.0.1', '-p', "$port") `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -Path $pidFile -Value $process.Id -NoNewline

$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($process.HasExited) { break }
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        $ready = $connect.AsyncWaitHandle.WaitOne(250) -and $client.Connected
        if ($ready) { break }
    } catch {
        # Sigue esperando hasta 10 segundos.
    } finally {
        $client.Dispose()
    }
}

if (-not $ready) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    if ($process.HasExited) {
        throw "Moto terminó al arrancar. Revisa el registro local: $stderr"
    }
    throw "Moto no abrió el puerto en 10 segundos. Revisa el registro local: $stderr"
}

Write-Host "Moto está activo únicamente en http://127.0.0.1:$port"
Write-Host 'Usa .\iac\local-emulator\smoke.ps1 para verificar S3, Secrets Manager y SQS.'
Write-Host 'Usa .\iac\local-emulator\stop.ps1 para detenerlo.'
