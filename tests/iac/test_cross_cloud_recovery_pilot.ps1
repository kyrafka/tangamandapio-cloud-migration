$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path $PSScriptRoot '..\..\iac\scripts\cross_cloud_recovery_pilot.ps1'
. $scriptPath

$work = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
  $source = Join-Path $work 'source.json'
  $restored = Join-Path $work 'restored.json'
  $different = Join-Path $work 'different.json'
  Set-Content -Path $source -Value '{"kind":"synthetic","count":2}' -Encoding utf8
  Copy-Item -Path $source -Destination $restored
  Set-Content -Path $different -Value '{"kind":"synthetic","count":3}' -Encoding utf8

  $match = Assert-CrossCloudBackupIntegrity -SourcePath $source -RestoredPath $restored
  if (-not $match.Matches -or $match.SourceSha256 -ne $match.RestoredSha256) {
    throw 'Matching backup and restored files must pass SHA-256 verification.'
  }

  $rejected = $false
  try {
    $null = Assert-CrossCloudBackupIntegrity -SourcePath $source -RestoredPath $different
  } catch {
    $rejected = $true
  }
  if (-not $rejected) {
    throw 'A restored file with different content must be rejected.'
  }

  Write-Output 'PASS: matching files are accepted and mismatched restores are rejected.'
} finally {
  Remove-Item -LiteralPath $work -Recurse -Force
}
