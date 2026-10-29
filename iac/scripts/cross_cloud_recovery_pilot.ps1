[CmdletBinding()]
param(
  [string]$SourcePath,
  [string]$Bucket = 'tangamandapio-files-654654388734-us-east-1',
  [string]$ObjectKey,
  [string]$StorageAccount = 'sttangama261008r',
  [string]$StorageResourceGroup = 'rg-tangamandapio-rebuild-wus',
  [string]$Container = 'cross-cloud-dr-pilot',
  [string]$RestorePath,
  [string]$EvidencePath
)

$ErrorActionPreference = 'Stop'

function Get-CrossCloudFileSha256 {
  param([Parameter(Mandatory)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "No existe el archivo para verificar: $Path"
  }

  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-CrossCloudBackupIntegrity {
  param(
    [Parameter(Mandatory)][string]$SourcePath,
    [Parameter(Mandatory)][string]$RestoredPath
  )

  $sourceHash = Get-CrossCloudFileSha256 -Path $SourcePath
  $restoredHash = Get-CrossCloudFileSha256 -Path $RestoredPath
  if ($sourceHash -ne $restoredHash) {
    throw 'La copia restaurada no coincide con el archivo de origen (SHA-256 distinto).'
  }

  return [pscustomobject]@{
    Matches       = $true
    SourceSha256  = $sourceHash
    RestoredSha256 = $restoredHash
  }
}

function Invoke-AzureStorageCli {
  param([Parameter(Mandatory)][string[]]$Arguments)

  $output = & $script:AzureCliPython -m azure.cli @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    # Do not surface CLI arguments: copy commands include a short-lived signed URL.
    throw "Azure CLI de Storage falló (código $exitCode)."
  }
  return ($output -join [Environment]::NewLine)
}

function Invoke-CrossCloudRecoveryPilot {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$InputPath,
    [Parameter(Mandatory)][string]$DestinationPath,
    [Parameter(Mandatory)][string]$EvidenceOutputPath,
    [Parameter(Mandatory)][string]$S3Bucket,
    [Parameter(Mandatory)][string]$S3ObjectKey,
    [Parameter(Mandatory)][string]$BlobAccount,
    [Parameter(Mandatory)][string]$BlobResourceGroup,
    [Parameter(Mandatory)][string]$BlobContainer
  )

  if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    throw 'El archivo de entrada no existe.'
  }
  try {
    $inputDocument = Get-Content -LiteralPath $InputPath -Raw | ConvertFrom-Json
  } catch {
    throw 'El respaldo de prueba debe ser JSON válido.'
  }
  if ([string]$inputDocument.data_scope -notmatch 'synthetic') {
    throw 'Este piloto acepta solo artefactos marcados explícitamente como datos sintéticos.'
  }

  $azCommand = Get-Command az -ErrorAction Stop
  if ([IO.Path]::GetExtension($azCommand.Source) -ne '.cmd') {
    throw 'Se esperaba el launcher az.cmd de Azure CLI para localizar su Python integrado.'
  }
  $cliRoot = Split-Path (Split-Path $azCommand.Source -Parent) -Parent
  $script:AzureCliPython = Join-Path $cliRoot 'python.exe'
  if (-not (Test-Path -LiteralPath $script:AzureCliPython -PathType Leaf)) {
    throw 'No se encontró Python de Azure CLI; no se inició ninguna transferencia.'
  }

  $s3Uri = "s3://$S3Bucket/$S3ObjectKey"
  $null = & aws sts get-caller-identity --query Account --output text 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw 'AWS rechazó las credenciales o no se pudo confirmar la identidad.'
  }

  $null = & aws s3 cp $InputPath $s3Uri --sse AES256 --content-type application/json --only-show-errors 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw 'No se pudo guardar el respaldo sintético en S3.'
  }

  $sourceUrl = (& aws s3 presign $s3Uri --expires-in 900 2>$null | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $sourceUrl.StartsWith('https://')) {
    throw 'No se pudo generar la URL de lectura temporal de S3.'
  }

  $storageKey = (& az storage account keys list --resource-group $BlobResourceGroup --account-name $BlobAccount --query '[0].value' -o tsv 2>$null | Out-String).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($storageKey)) {
    throw 'No se pudo obtener acceso al almacenamiento Azure desde la sesión autenticada.'
  }

  $previousStorageKey = [Environment]::GetEnvironmentVariable('AZURE_STORAGE_KEY', 'Process')
  try {
    $env:AZURE_STORAGE_KEY = $storageKey
    $null = Invoke-AzureStorageCli -Arguments @(
      'storage', 'container', 'create', '--account-name', $BlobAccount,
      '--name', $BlobContainer, '--auth-mode', 'key', '--public-access', 'off',
      '--only-show-errors', '--output', 'none'
    )

    $destinationBlob = [IO.Path]::GetFileName($S3ObjectKey)
    $null = Invoke-AzureStorageCli -Arguments @(
      'storage', 'blob', 'copy', 'start', '--account-name', $BlobAccount,
      '--destination-container', $BlobContainer, '--destination-blob', $destinationBlob,
      '--source-uri', $sourceUrl, '--auth-mode', 'key', '--only-show-errors', '--output', 'none'
    )

    $copyStatus = 'pending'
    for ($attempt = 0; $attempt -lt 40 -and $copyStatus -eq 'pending'; $attempt++) {
      Start-Sleep -Seconds 2
      $copyStatus = (Invoke-AzureStorageCli -Arguments @(
        'storage', 'blob', 'show', '--account-name', $BlobAccount,
        '--container-name', $BlobContainer, '--name', $destinationBlob,
        '--auth-mode', 'key', '--query', 'properties.copy.status', '--output', 'tsv'
      )).Trim()
    }
    if ($copyStatus -ne 'success') {
      throw "La copia servidor a servidor no finalizó correctamente (estado: $copyStatus)."
    }

    $null = Invoke-AzureStorageCli -Arguments @(
      'storage', 'blob', 'download', '--account-name', $BlobAccount,
      '--container-name', $BlobContainer, '--name', $destinationBlob,
      '--file', $DestinationPath, '--auth-mode', 'key', '--overwrite', 'true',
      '--only-show-errors'
    )

    $integrity = Assert-CrossCloudBackupIntegrity -SourcePath $InputPath -RestoredPath $DestinationPath
    $result = [ordered]@{
      timestamp_utc      = (Get-Date).ToUniversalTime().ToString('o')
      result              = 'passed'
      transfer            = 'AWS S3 -> Azure Blob server-side copy -> local restore verification'
      source_bucket       = $S3Bucket
      source_object       = $S3ObjectKey
      destination_account = $BlobAccount
      destination_container = $BlobContainer
      destination_blob    = $destinationBlob
      copy_status         = $copyStatus
      source_sha256       = $integrity.SourceSha256
      restored_sha256     = $integrity.RestoredSha256
      hashes_match        = $integrity.Matches
      data_scope          = 'Synthetic QA only; this is not an RDS dump or a production database backup.'
    }
    $parent = Split-Path -Parent $EvidenceOutputPath
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $EvidenceOutputPath -Encoding utf8
    return [pscustomobject]@{
      Result = 'passed'
      CopyStatus = $copyStatus
      HashesMatch = $integrity.Matches
      EvidencePath = $EvidenceOutputPath
      RestoredPath = $DestinationPath
    }
  } finally {
    if ($null -eq $previousStorageKey) {
      Remove-Item Env:AZURE_STORAGE_KEY -ErrorAction SilentlyContinue
    } else {
      $env:AZURE_STORAGE_KEY = $previousStorageKey
    }
    $storageKey = $null
    $sourceUrl = $null
  }
}

if ($PSBoundParameters.ContainsKey('SourcePath')) {
  $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
  if ([string]::IsNullOrWhiteSpace($ObjectKey)) {
    $ObjectKey = "cross-cloud-dr-pilot/$([IO.Path]::GetFileName($SourcePath))"
  }
  if ([string]::IsNullOrWhiteSpace($RestorePath)) {
    $RestorePath = Join-Path (Split-Path -Parent $SourcePath) "restored-$stamp.json"
  }
  if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path (Split-Path -Parent $SourcePath) "CROSS-CLOUD-DR-PILOT-$stamp.json"
  }

  $result = Invoke-CrossCloudRecoveryPilot -InputPath $SourcePath -DestinationPath $RestorePath `
    -EvidenceOutputPath $EvidencePath -S3Bucket $Bucket -S3ObjectKey $ObjectKey `
    -BlobAccount $StorageAccount -BlobResourceGroup $StorageResourceGroup -BlobContainer $Container
  $result | Format-List
}
