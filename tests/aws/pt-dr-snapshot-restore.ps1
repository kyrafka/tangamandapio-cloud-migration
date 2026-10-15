param(
  [switch]$ConfirmCostlyTest,
  [ValidateRange(5, 60)]
  [int]$MaxWaitMinutes = 30,
  [string]$Region = 'us-east-1'
)

$ErrorActionPreference = 'Stop'
if (-not $ConfirmCostlyTest) {
  throw 'Cancelado: requiere -ConfirmCostlyTest porque crea temporalmente una instancia RDS facturable.'
}

$profilePath = Join-Path $env:USERPROFILE '.aws\credentials'
$configPath = Join-Path $env:USERPROFILE '.aws\config'
$envNames = @('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_PROFILE', 'AWS_SHARED_CREDENTIALS_FILE', 'AWS_CONFIG_FILE')
$oldEnv = @{}
foreach ($name in $envNames) {
  $oldEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$env:AWS_SHARED_CREDENTIALS_FILE = $profilePath
$env:AWS_CONFIG_FILE = $configPath
foreach ($name in @('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_PROFILE')) {
  [Environment]::SetEnvironmentVariable($name, $null, 'Process')
}

$restoreId = $null
$subnetGroupName = $null
$restoreCreated = $false
$subnetGroupCreated = $false
$passed = $false
$cleanupPassed = $true
$managedSecretEnabled = $false
$managedSecretArn = $null
$failureClass = 'none'
$lastAwsOperation = 'none'
$failedOperation = 'none'

function Invoke-AwsText {
  param([string[]]$AwsArgs, [switch]$AllowMissing)
  if ($AwsArgs.Count -ge 2) {
    $script:lastAwsOperation = "$($AwsArgs[0]) $($AwsArgs[1])"
  } elseif ($AwsArgs.Count -eq 1) {
    $script:lastAwsOperation = [string]$AwsArgs[0]
  }
  $output = & aws @AwsArgs --region $Region --profile default --cli-connect-timeout 10 --cli-read-timeout 20 2>&1
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    $joined = $output -join ' '
    if ($AllowMissing -and $joined -match 'DBInstanceNotFound|DBSubnetGroupNotFound') { return 'None' }
    if ($joined -match 'ExpiredToken|InvalidClientTokenId') { throw 'AWS credentials rejected or expired.' }
    if ($joined -match 'AccessDenied|UnauthorizedOperation') { throw 'AWS authorization denied.' }
    throw "AWS CLI request failed (exit $exitCode)."
  }
  return ($output -join [Environment]::NewLine)
}

function Invoke-AwsJson {
  param([string[]]$AwsArgs)
  return (Invoke-AwsText -AwsArgs $AwsArgs) | ConvertFrom-Json
}

try {
  $null = Invoke-AwsText -AwsArgs @('sts', 'get-caller-identity', '--query', 'Account', '--output', 'text')

  $snapshotResponse = Invoke-AwsJson -AwsArgs @(
    'rds', 'describe-db-snapshots', '--db-instance-identifier', 'tangamandapio-postgres',
    '--snapshot-type', 'manual', '--query', 'DBSnapshots[?Status==`available`]|sort_by(@, &SnapshotCreateTime)[-1].{id:DBSnapshotIdentifier,status:Status,encrypted:Encrypted,engine:Engine,created:SnapshotCreateTime}', '--output', 'json'
  )
  if (-not $snapshotResponse -or $snapshotResponse.status -ne 'available' -or $snapshotResponse.encrypted -ne $true -or $snapshotResponse.engine -ne 'postgres') {
    throw 'No existe un snapshot manual PostgreSQL disponible y cifrado del proyecto.'
  }
  $snapshotId = [string]$snapshotResponse.id

  $vpcId = [string](Invoke-AwsText -AwsArgs @('ec2', 'describe-vpcs', '--filters', 'Name=is-default,Values=true', '--query', 'Vpcs[0].VpcId', '--output', 'text'))
  if ([string]::IsNullOrWhiteSpace($vpcId) -or $vpcId -eq 'None') {
    throw 'No existe una VPC predeterminada para ubicar la copia de prueba.'
  }
  $subnets = Invoke-AwsJson -AwsArgs @('ec2', 'describe-subnets', '--filters', "Name=vpc-id,Values=$vpcId", '--query', 'Subnets[].{id:SubnetId,az:AvailabilityZone}', '--output', 'json')
  $twoAzSubnets = @($subnets | Group-Object az | ForEach-Object { $_.Group[0] } | Select-Object -First 2)
  if ($twoAzSubnets.Count -lt 2) {
    throw 'La VPC predeterminada no tiene subredes en dos zonas para el DB subnet group.'
  }

  $securityGroups = Invoke-AwsJson -AwsArgs @('ec2', 'describe-security-groups', '--filters', "Name=vpc-id,Values=$vpcId", 'Name=group-name,Values=default', '--query', 'SecurityGroups[].{id:GroupId,ipv4:IpPermissions[].IpRanges[].CidrIp,ipv6:IpPermissions[].Ipv6Ranges[].CidrIpv6,peers:IpPermissions[].UserIdGroupPairs[].GroupId}', '--output', 'json')
  if (@($securityGroups).Count -ne 1) { throw 'No se encontró exactamente un security group predeterminado.' }
  $securityGroup = $securityGroups[0]
  $publicIngress = @($securityGroup.ipv4 | Where-Object { $_ -eq '0.0.0.0/0' }).Count + @($securityGroup.ipv6 | Where-Object { $_ -eq '::/0' }).Count
  $foreignPeers = @($securityGroup.peers | Where-Object { $_ -and $_ -ne $securityGroup.id }).Count
  if ($publicIngress -gt 0 -or $foreignPeers -gt 0) { throw 'El security group predeterminado permite ingreso que no es estrictamente local.' }

  $stamp = Get-Date -Format 'yyyyMMddHHmmss'
  $subnetGroupName = "tng-drtest-$stamp"
  $restoreId = "tng-drrestore-$stamp"
  $subnetIds = @($twoAzSubnets | ForEach-Object { [string]$_.id })

  $subnetGroupCreated = $true
  $null = Invoke-AwsText -AwsArgs (@('rds', 'create-db-subnet-group', '--db-subnet-group-name', $subnetGroupName, '--db-subnet-group-description', 'Temporary isolated subnet group for Tangamandapio snapshot restore test', '--subnet-ids') + $subnetIds + @('--tags', 'Key=Project,Value=tangamandapio', 'Key=Purpose,Value=temporary-dr-restore', '--output', 'json'))

  $restoreCreated = $true
  $null = Invoke-AwsText -AwsArgs @('rds', 'restore-db-instance-from-db-snapshot', '--db-instance-identifier', $restoreId, '--db-snapshot-identifier', $snapshotId, '--db-instance-class', 'db.t3.micro', '--db-subnet-group-name', $subnetGroupName, '--vpc-security-group-ids', $securityGroup.id, '--no-publicly-accessible', '--backup-retention-period', '0', '--tags', 'Key=Project,Value=tangamandapio', 'Key=Purpose,Value=temporary-dr-restore', '--output', 'json')

  $deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
  $status = 'creating'
  while ((Get-Date) -lt $deadline) {
    $status = [string](Invoke-AwsText -AwsArgs @('rds', 'describe-db-instances', '--db-instance-identifier', $restoreId, '--query', 'DBInstances[0].DBInstanceStatus', '--output', 'text'))
    if ($status -eq 'available') { break }
    if ($status -in @('failed', 'incompatible-restore', 'incompatible-parameters', 'storage-full')) {
      throw "Snapshot restore reached terminal status: $status."
    }
    Start-Sleep -Seconds 30
  }
  if ($status -ne 'available') { throw 'Snapshot restore exceeded the configured wait limit.' }

  $restored = Invoke-AwsJson -AwsArgs @('rds', 'describe-db-instances', '--db-instance-identifier', $restoreId, '--query', 'DBInstances[0].{status:DBInstanceStatus,public:PubliclyAccessible,encrypted:StorageEncrypted,engine:Engine,subnet:DBSubnetGroup.DBSubnetGroupName,backupDays:BackupRetentionPeriod}', '--output', 'json')
  if ($restored.status -ne 'available' -or $restored.public -ne $false -or $restored.encrypted -ne $true -or $restored.engine -ne 'postgres' -or $restored.subnet -ne $subnetGroupName -or $restored.backupDays -ne 0) {
    throw 'Restored instance did not meet the private, encrypted, no-extra-backup test invariants.'
  }

  # Restoring a PostgreSQL snapshot cannot create an RDS-managed secret in the
  # restore request. Enable it after the copy is available, then verify only
  # metadata/status; never print or persist the secret value.
  $null = Invoke-AwsText -AwsArgs @('rds', 'modify-db-instance', '--db-instance-identifier', $restoreId, '--manage-master-user-password', '--apply-immediately', '--output', 'json')
  $secretDeadline = (Get-Date).AddMinutes($MaxWaitMinutes)
  $managedStatus = 'pending'
  while ((Get-Date) -lt $secretDeadline) {
    $managed = Invoke-AwsJson -AwsArgs @('rds', 'describe-db-instances', '--db-instance-identifier', $restoreId, '--query', 'DBInstances[0].{status:DBInstanceStatus,secretStatus:MasterUserSecret.SecretStatus,secretArn:MasterUserSecret.SecretArn}', '--output', 'json')
    $managedStatus = [string]$managed.secretStatus
    if ($managed.status -eq 'available' -and $managedStatus -eq 'active' -and -not [string]::IsNullOrWhiteSpace([string]$managed.secretArn)) {
      $managedSecretArn = [string]$managed.secretArn
      $managedSecretEnabled = $true
      break
    }
    if ($managed.status -in @('failed', 'incompatible-restore', 'incompatible-parameters', 'storage-full')) {
      throw "Managed-secret activation reached terminal database status: $($managed.status)."
    }
    Start-Sleep -Seconds 20
  }
  if (-not $managedSecretEnabled) { throw "RDS-managed master secret did not become active (status=$managedStatus)." }

  $passed = $true
}
catch {
  $failedOperation = $lastAwsOperation
  $failureClass = switch -Regex ($_.Exception.Message) {
    'credentials rejected|expired' { 'credentials' ; break }
    'authorization denied' { 'access_denied' ; break }
    'terminal status|wait limit' { 'restore_failed_or_timeout' ; break }
    default { 'preflight_or_validation' }
  }
}
finally {
  if ($restoreCreated) {
    try {
      $deleteResult = Invoke-AwsText -AwsArgs @('rds', 'delete-db-instance', '--db-instance-identifier', $restoreId, '--skip-final-snapshot', '--delete-automated-backups', '--output', 'json') -AllowMissing
      $deleted = $deleteResult -eq 'None'
      if (-not $deleted) {
        $deleteDeadline = (Get-Date).AddMinutes(20)
        while ((Get-Date) -lt $deleteDeadline) {
          $state = Invoke-AwsText -AwsArgs @('rds', 'describe-db-instances', '--db-instance-identifier', $restoreId, '--query', 'DBInstances[0].DBInstanceStatus', '--output', 'text') -AllowMissing
          if ($state -eq 'None') { $deleted = $true; break }
          Start-Sleep -Seconds 20
        }
      }
      if (-not $deleted) { $cleanupPassed = $false }
    }
    catch { $cleanupPassed = $false }
  }
  if ($subnetGroupCreated) {
    try { $null = Invoke-AwsText -AwsArgs @('rds', 'delete-db-subnet-group', '--db-subnet-group-name', $subnetGroupName) -AllowMissing }
    catch { $cleanupPassed = $false }
  }
  foreach ($name in $envNames) {
    [Environment]::SetEnvironmentVariable($name, $oldEnv[$name], 'Process')
  }
}

if (-not $cleanupPassed) {
  throw "CLEANUP_INCOMPLETE: inspect only the temporary test resources $restoreId and $subnetGroupName; the source snapshot was not targeted."
}
if (-not $passed) {
  throw "SNAPSHOT_RESTORE_FAILED: category=$failureClass; operation=$failedOperation; source snapshot was preserved and temporary resources were cleaned."
}

Write-Output 'PT-DR-SNAPSHOT-RESTORE=PASSED'
Write-Output 'restored_database=available,encrypted,non_public'
Write-Output 'rds_managed_master_secret=active_during_test,value_not_exported'
Write-Output 'source_snapshot=preserved'
Write-Output 'temporary_database_and_subnet_group=deleted'
Write-Output 'data_integrity=not_verified (no SQL probe executed inside the isolated VPC)'
