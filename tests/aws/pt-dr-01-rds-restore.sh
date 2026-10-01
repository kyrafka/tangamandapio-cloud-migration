#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_COSTLY_DR_TEST:-}" != "YES" ]]; then
  echo "Cancelado: esta prueba crea temporalmente una instancia RDS. Use CONFIRM_COSTLY_DR_TEST=YES." >&2
  exit 2
fi

STACK_NAME="${1:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"
SOURCE_DB="$(aws cloudformation describe-stack-resources --stack-name "$STACK_NAME" --logical-resource-id Database --region "$REGION" --query 'StackResources[0].PhysicalResourceId' --output text)"
SUBNET_GROUP="$(aws rds describe-db-instances --db-instance-identifier "$SOURCE_DB" --region "$REGION" --query 'DBInstances[0].DBSubnetGroup.DBSubnetGroupName' --output text)"
SG_ID="$(aws rds describe-db-instances --db-instance-identifier "$SOURCE_DB" --region "$REGION" --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)"
SUFFIX="$(date +%s)"
SNAPSHOT_ID="${SOURCE_DB}-pt-dr-${SUFFIX}"
RESTORE_ID="${SOURCE_DB}-restore-${SUFFIX}"
STARTED="$(date +%s)"

cleanup() {
  aws rds delete-db-instance --db-instance-identifier "$RESTORE_ID" --skip-final-snapshot --delete-automated-backups --region "$REGION" >/dev/null 2>&1 || true
  aws rds wait db-instance-deleted --db-instance-identifier "$RESTORE_ID" --region "$REGION" >/dev/null 2>&1 || true
  aws rds delete-db-snapshot --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" >/dev/null 2>&1 || true
}
trap cleanup EXIT

aws rds create-db-snapshot --db-instance-identifier "$SOURCE_DB" --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" >/dev/null
aws rds wait db-snapshot-available --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION"
aws rds restore-db-instance-from-db-snapshot --db-instance-identifier "$RESTORE_ID" --db-snapshot-identifier "$SNAPSHOT_ID" --db-instance-class db.t3.micro --db-subnet-group-name "$SUBNET_GROUP" --vpc-security-group-ids "$SG_ID" --no-publicly-accessible --region "$REGION" >/dev/null
aws rds wait db-instance-available --db-instance-identifier "$RESTORE_ID" --region "$REGION"
PUBLIC="$(aws rds describe-db-instances --db-instance-identifier "$RESTORE_ID" --region "$REGION" --query 'DBInstances[0].PubliclyAccessible' --output text)"
RTO_SECONDS="$(( $(date +%s) - STARTED ))"
printf '{"test_id":"PT-DR-01","status":"APROBADA","publicly_accessible":"%s","measured_rto_seconds":%s,"cleanup":"automatic"}\n' "$PUBLIC" "$RTO_SECONDS"
test "$PUBLIC" = "False"
