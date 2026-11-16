$ErrorActionPreference = 'Stop'

$endpoint = 'http://127.0.0.1:5000'
$aws = Get-Command aws -ErrorAction SilentlyContinue
if (-not $aws) { throw 'No se encontró AWS CLI. Instálalo para correr esta comprobación local.' }

try {
    $null = Invoke-WebRequest -Uri "$endpoint/" -TimeoutSec 3
} catch {
    throw 'Moto no responde en 127.0.0.1:5000. Primero ejecuta .\iac\local-emulator\start.ps1.'
}

$envNames = @(
    'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
    'AWS_DEFAULT_REGION', 'AWS_PROFILE', 'AWS_DEFAULT_PROFILE', 'AWS_CONFIG_FILE',
    'AWS_SHARED_CREDENTIALS_FILE', 'AWS_EC2_METADATA_DISABLED'
)
$oldEnv = @{}
foreach ($name in $envNames) { $oldEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

$env:AWS_ACCESS_KEY_ID = 'local-test-only'
$env:AWS_SECRET_ACCESS_KEY = 'local-test-only'
$env:AWS_SESSION_TOKEN = 'local-test-only'
$env:AWS_DEFAULT_REGION = 'us-east-2'
$env:AWS_PROFILE = $null
$env:AWS_DEFAULT_PROFILE = $null
$configFile = Join-Path $env:TEMP "tanga-local-$([Guid]::NewGuid().ToString('N')).config"
$credentialsFile = Join-Path $env:TEMP "tanga-local-$([Guid]::NewGuid().ToString('N')).credentials"
Set-Content -Path $configFile -Value '' -NoNewline
Set-Content -Path $credentialsFile -Value '' -NoNewline
$env:AWS_CONFIG_FILE = $configFile
$env:AWS_SHARED_CREDENTIALS_FILE = $credentialsFile
$env:AWS_EC2_METADATA_DISABLED = 'true'

$suffix = [Guid]::NewGuid().ToString('N').Substring(0, 12)
$bucket = "tanga-local-$suffix"
$secretId = "tangamandapio/local-emulator/$suffix"
$queueName = "tanga-local-$suffix"
$payload = "prueba local $suffix"
$objectFile = Join-Path $env:TEMP "tanga-local-$suffix.txt"
$downloadFile = Join-Path $env:TEMP "tanga-local-$suffix.download.txt"
$queueUrl = $null
$secretCreated = $false
$bucketCreated = $false
$failed = $false

function Invoke-LocalAws {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $result = & $aws.Source --no-cli-pager @Arguments
    if ($LASTEXITCODE -ne 0) { throw "AWS CLI devolvió error local: aws $($Arguments[0]) $($Arguments[1])" }
    return $result
}

try {
    Set-Content -Path $objectFile -Value $payload -NoNewline

    $null = Invoke-LocalAws @('s3api', 'create-bucket', '--bucket', $bucket, '--create-bucket-configuration', 'LocationConstraint=us-east-2', '--endpoint-url', $endpoint)
    $bucketCreated = $true
    $null = Invoke-LocalAws @('s3api', 'put-object', '--bucket', $bucket, '--key', 'smoke.txt', '--body', $objectFile, '--endpoint-url', $endpoint)
    $null = Invoke-LocalAws @('s3api', 'get-object', '--bucket', $bucket, '--key', 'smoke.txt', $downloadFile, '--endpoint-url', $endpoint)
    if ((Get-Content $downloadFile -Raw) -ne $payload) { throw 'La lectura local del objeto S3 no coincide con lo enviado.' }
    Write-Host '[OK] S3 local: escritura, lectura y comparación.'

    $null = Invoke-LocalAws @('secretsmanager', 'create-secret', '--name', $secretId, '--secret-string', 'solo-dato-ficticio-local', '--endpoint-url', $endpoint)
    $secretCreated = $true
    $readSecret = (Invoke-LocalAws @('secretsmanager', 'get-secret-value', '--secret-id', $secretId, '--query', 'SecretString', '--output', 'text', '--endpoint-url', $endpoint) | Out-String).Trim()
    if ($readSecret -ne 'solo-dato-ficticio-local') { throw 'La lectura local del secreto ficticio no coincide.' }
    $readSecret = $null
    Write-Host '[OK] Secrets Manager local: creación y lectura del valor ficticio.'

    $queueUrl = (Invoke-LocalAws @('sqs', 'create-queue', '--queue-name', $queueName, '--endpoint-url', $endpoint) | ConvertFrom-Json).QueueUrl
    $null = Invoke-LocalAws @('sqs', 'send-message', '--queue-url', $queueUrl, '--message-body', $payload, '--endpoint-url', $endpoint)
    $received = (Invoke-LocalAws @('sqs', 'receive-message', '--queue-url', $queueUrl, '--wait-time-seconds', '1', '--endpoint-url', $endpoint) | ConvertFrom-Json).Messages
    if (-not $received -or $received[0].Body -ne $payload) { throw 'El mensaje no se recuperó de la cola local.' }
    $null = Invoke-LocalAws @('sqs', 'delete-message', '--queue-url', $queueUrl, '--receipt-handle', $received[0].ReceiptHandle, '--endpoint-url', $endpoint)
    Write-Host '[OK] SQS local: envío, recepción y eliminación del mensaje de prueba.'
} catch {
    $failed = $true
    throw
} finally {
    if ($queueUrl) {
        try { $null = Invoke-LocalAws @('sqs', 'delete-queue', '--queue-url', $queueUrl, '--endpoint-url', $endpoint) } catch { Write-Warning 'No se pudo limpiar la cola local de prueba.' }
    }
    if ($secretCreated) {
        try { $null = Invoke-LocalAws @('secretsmanager', 'delete-secret', '--secret-id', $secretId, '--force-delete-without-recovery', '--endpoint-url', $endpoint) } catch { Write-Warning 'No se pudo limpiar el secreto local ficticio.' }
    }
    if ($bucketCreated) {
        try {
            $null = Invoke-LocalAws @('s3api', 'delete-object', '--bucket', $bucket, '--key', 'smoke.txt', '--endpoint-url', $endpoint)
            $null = Invoke-LocalAws @('s3api', 'delete-bucket', '--bucket', $bucket, '--endpoint-url', $endpoint)
        } catch { Write-Warning 'No se pudo limpiar el bucket local de prueba.' }
    }
    Remove-Item $objectFile, $downloadFile -Force -ErrorAction SilentlyContinue
    Remove-Item $configFile, $credentialsFile -Force -ErrorAction SilentlyContinue
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $oldEnv[$name], 'Process') }
}

if (-not $failed) { Write-Host 'Comprobación local terminada; los recursos ficticios fueron eliminados.' }
