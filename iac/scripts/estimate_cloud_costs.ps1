param(
  [ValidateRange(0, 744)]
  [decimal]$ComputeHours = 730,

  [ValidateRange(0, 744)]
  [decimal]$SharedInfrastructureHours = 730,

  [ValidateRange(0, 1000)]
  [decimal]$AverageAlbLcuPerHour = 1,

  [ValidateRange(0, 1000000)]
  [decimal]$NatProcessedGb = 10
)

$ErrorActionPreference = 'Stop'

# Public list-price inputs, USD. Refresh these against each provider's calculator
# before using the output as a purchase order or production budget.
$rates = [ordered]@{
  Ec2LinuxMicroPerHour = [decimal]'0.0104'
  EbsGp3PerGbMonth = [decimal]'0.08'
  RdsPostgresMicroSingleAzPerHour = [decimal]'0.018'
  RdsGp3PerGbMonth = [decimal]'0.115'
  AlbPerHour = [decimal]'0.0225'
  AlbLcuPerHour = [decimal]'0.008'
  NatGatewayPerHour = [decimal]'0.045'
  NatGatewayPerGb = [decimal]'0.045'
  PublicIpv4PerHour = [decimal]'0.005'
  SecretsManagerPerSecretMonth = [decimal]'0.40'
}

$items = @(
  [pscustomobject]@{ Name = 'EC2: 2 x t3.micro Linux'; Formula = '2 x compute-hours x rate'; Amount = 2 * $ComputeHours * $rates.Ec2LinuxMicroPerHour }
  [pscustomobject]@{ Name = 'EBS: 16 GB gp3'; Formula = '16 GB-month x rate'; Amount = 16 * $rates.EbsGp3PerGbMonth }
  [pscustomobject]@{ Name = 'RDS PostgreSQL: db.t3.micro Single-AZ'; Formula = 'compute-hours x rate'; Amount = $ComputeHours * $rates.RdsPostgresMicroSingleAzPerHour }
  [pscustomobject]@{ Name = 'RDS: 20 GB gp3'; Formula = '20 GB-month x rate'; Amount = 20 * $rates.RdsGp3PerGbMonth }
  [pscustomobject]@{ Name = 'Application Load Balancer'; Formula = 'shared-infrastructure-hours x rate'; Amount = $SharedInfrastructureHours * $rates.AlbPerHour }
  [pscustomobject]@{ Name = 'ALB capacity'; Formula = 'average LCU/hour x shared-infrastructure-hours x rate'; Amount = $AverageAlbLcuPerHour * $SharedInfrastructureHours * $rates.AlbLcuPerHour }
  [pscustomobject]@{ Name = 'NAT Gateway'; Formula = 'shared-infrastructure-hours x rate'; Amount = $SharedInfrastructureHours * $rates.NatGatewayPerHour }
  [pscustomobject]@{ Name = 'NAT processing'; Formula = 'processed GB x rate'; Amount = $NatProcessedGb * $rates.NatGatewayPerGb }
  [pscustomobject]@{ Name = 'NAT public IPv4'; Formula = 'one in-use IPv4 x shared-infrastructure-hours x rate'; Amount = $SharedInfrastructureHours * $rates.PublicIpv4PerHour }
  [pscustomobject]@{ Name = 'Secrets Manager: 2 secrets'; Formula = '2 x month x rate'; Amount = 2 * $rates.SecretsManagerPerSecretMonth }
)

$total = ($items | Measure-Object -Property Amount -Sum).Sum
'Scenario: compute/database={0} h/month; shared infrastructure={1} h/month; {2} average ALB LCU/hour; {3} GB processed through NAT' -f $ComputeHours, $SharedInfrastructureHours, $AverageAlbLcuPerHour, $NatProcessedGb
$items | ForEach-Object { '{0,-47} ${1,8:N2}  ({2})' -f $_.Name,$_.Amount,$_.Formula }
'{0,-47} ${1,8:N2}' -f 'Modeled AWS subtotal (not all-in)', $total
'Azure Functions compute/requests assumed within eligible Consumption grants; Azure storage/transactions remain variable and are not included.'
'Excluded: taxes, credits/discounts, S3/Blob capacity and operations, CloudWatch/Log Analytics ingestion, snapshots beyond included backup, outbound and cross-zone traffic, IPv4 on other resources, and actual contractual pricing.'
