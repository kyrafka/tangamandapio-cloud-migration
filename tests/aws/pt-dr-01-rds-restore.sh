#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ "${CONFIRM_COSTLY_DR_TEST:-}" != "YES" ]]; then
  echo "Cancelado: requiere una instancia RDS temporal. Use CONFIRM_COSTLY_DR_TEST=YES." >&2
  exit 2
fi

STACK_NAME="${1:-}"
if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "Indique el stack exacto: $0 tangamandapio-live-YYYYMMDD" >&2
  exit 2
fi

REGION="${AWS_REGION:-us-east-1}"
MAX_WAIT_SECONDS="${DR_MAX_WAIT_SECONDS:-1800}"
for binary in aws python3; do
  command -v "$binary" >/dev/null || { echo "Falta dependencia requerida: $binary" >&2; exit 2; }
done

aws sts get-caller-identity --region "$REGION" >/dev/null
STACK_STATUS="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text)"
case "$STACK_STATUS" in
  CREATE_COMPLETE|UPDATE_COMPLETE) ;;
  *) echo "El stack no está estable ($STACK_STATUS); se cancela antes de crear recursos." >&2; exit 2 ;;
esac

SOURCE_DB="$(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-resource-id Database --region "$REGION" --query 'StackResourceDetail.PhysicalResourceId' --output text)"
# RDS-managed master secrets do not appear as a CloudFormation resource named
# DBSecret. Resolve the exported physical ARN so restore works with both the
# managed-password and Secrets Manager resource configurations.
SECRET_ARN="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue | [0]" --output text)"
ASG_NAME="$(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" --logical-resource-id AutoScalingGroup --region "$REGION" --query 'StackResourceDetail.PhysicalResourceId' --output text)"
if [[ -z "$SOURCE_DB" || "$SOURCE_DB" == None || -z "$SECRET_ARN" || "$SECRET_ARN" == None || "$SECRET_ARN" != arn:*:secretsmanager:* || -z "$ASG_NAME" || "$ASG_NAME" == None ]]; then
  echo "El stack no expone la base, secreto y ASG esperados; no se inició el restore." >&2
  exit 2
fi

SOURCE_JSON="$(aws rds describe-db-instances --db-instance-identifier "$SOURCE_DB" --region "$REGION" --output json)"
readarray -t SOURCE_PROPERTIES < <(python3 -c '
import json, sys
db = json.loads(sys.stdin.read())["DBInstances"][0]
print(db["DBInstanceStatus"])
print(db["Engine"])
print(str(db["PubliclyAccessible"]).lower())
print(str(db["StorageEncrypted"]).lower())
print(db["DBInstanceClass"])
print(db["DBSubnetGroup"]["DBSubnetGroupName"])
print(" ".join(item["VpcSecurityGroupId"] for item in db["VpcSecurityGroups"]))
print(db["DBInstanceArn"])
' <<<"$SOURCE_JSON" | tr -d '\r')
SOURCE_STATUS="${SOURCE_PROPERTIES[0]}"
ENGINE="${SOURCE_PROPERTIES[1]}"
SOURCE_PUBLIC="${SOURCE_PROPERTIES[2]}"
SOURCE_ENCRYPTED="${SOURCE_PROPERTIES[3]}"
INSTANCE_CLASS="${SOURCE_PROPERTIES[4]}"
SUBNET_GROUP="${SOURCE_PROPERTIES[5]}"
SECURITY_GROUPS="${SOURCE_PROPERTIES[6]}"
DB_ARN="${SOURCE_PROPERTIES[7]}"
if [[ "$SOURCE_STATUS" != available || "$ENGINE" != postgres || "$SOURCE_PUBLIC" != false || "$SOURCE_ENCRYPTED" != true ]]; then
  echo "Preflight falló: la fuente debe ser PostgreSQL disponible, privada y cifrada." >&2
  exit 2
fi
PROJECT_TAG="$(aws rds list-tags-for-resource --resource-name "$DB_ARN" --region "$REGION" --query 'TagList[?Key==`Project`].Value | [0]' --output text)"
if [[ "${PROJECT_TAG,,}" != tangamandapio* ]]; then
  echo "La etiqueta del recurso no identifica con seguridad el proyecto; no se crearán recursos." >&2
  exit 2
fi

# Escoge una instancia sana del ASG y comprueba SSM antes de snapshot o restore.
INSTANCE_IDS="$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$ASG_NAME" --region "$REGION" --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService` && HealthStatus==`Healthy`].InstanceId' --output text)"
SSM_INSTANCE=""
for candidate in $INSTANCE_IDS; do
  ping="$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$candidate" --region "$REGION" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
  if [[ "$ping" == Online ]]; then SSM_INSTANCE="$candidate"; break; fi
done
if [[ -z "$SSM_INSTANCE" ]]; then
  echo "No hay una instancia de aplicación saludable y en línea por SSM; no se creó snapshot ni restore." >&2
  exit 2
fi

SUFFIX="$(date -u +%Y%m%d%H%M%S)"
readonly SNAPSHOT_ID="tng-dr-snap-${SUFFIX}"
readonly RESTORE_ID="tng-dr-restore-${SUFFIX}"
readonly PROBE_TABLE="dr_probe_${SUFFIX}"
readonly PROBE_MARKER="${STACK_NAME}-${SUFFIX}"
readonly REMOTE_PROBE_B64="$(gzip -c "$SCRIPT_DIR/rds_integrity_probe.py" | base64 | tr -d '\r\n')"
SNAPSHOT_CREATED=false
RESTORE_CREATED=false
PROBE_CREATED=false
TEST_PASSED=false
CLEANUP_OK=true
RTO_START=""

invoke_probe() {
  local host="$1" operation="$2"
  local remote_command parameters_json command_id status output
  remote_command="printf '%s' '${REMOTE_PROBE_B64}' | base64 -d | gzip -d | python3 - '${SECRET_ARN}' '${host}' '${operation}' '${PROBE_TABLE}' '${PROBE_MARKER}'"
  parameters_json="$(python3 -c 'import json,sys; print(json.dumps({"commands":[sys.argv[1]]}))' "$remote_command")"
  command_id="$(aws ssm send-command --document-name AWS-RunShellScript --instance-ids "$SSM_INSTANCE" --parameters "$parameters_json" --region "$REGION" --query 'Command.CommandId' --output text)"
  local waited=0
  while (( waited < MAX_WAIT_SECONDS )); do
    status="$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$SSM_INSTANCE" --region "$REGION" --query 'Status' --output text 2>/dev/null || true)"
    case "$status" in
      Success) break ;;
      Failed|Cancelled|TimedOut|Cancelling)
        echo "La verificación SQL remota falló (SSM $status); no se imprimen secretos." >&2
        return 1
        ;;
    esac
    sleep 5
    waited=$((waited + 5))
  done
  if [[ "$status" != Success ]]; then echo "Timeout al esperar el comando SSM." >&2; return 1; fi
  output="$(aws ssm get-command-invocation --command-id "$command_id" --instance-id "$SSM_INSTANCE" --region "$REGION" --query 'StandardOutputContent' --output text)"
  printf '%s\n' "$output" | tail -n 1
}

cleanup() {
  local original_status=$?
  trap - EXIT
  if [[ "$PROBE_CREATED" == true ]]; then
    if [[ -n "${SOURCE_ENDPOINT:-}" ]] && ! invoke_probe "$SOURCE_ENDPOINT" drop >/dev/null 2>&1; then CLEANUP_OK=false; fi
    if [[ "$RESTORE_CREATED" == true && -n "${RESTORE_ENDPOINT:-}" ]]; then
      if ! invoke_probe "$RESTORE_ENDPOINT" drop >/dev/null 2>&1; then CLEANUP_OK=false; fi
    fi
  fi
  if [[ "$RESTORE_CREATED" == true ]]; then
    aws rds delete-db-instance --db-instance-identifier "$RESTORE_ID" --skip-final-snapshot --delete-automated-backups --region "$REGION" >/dev/null 2>&1 || CLEANUP_OK=false
    aws rds wait db-instance-deleted --db-instance-identifier "$RESTORE_ID" --region "$REGION" >/dev/null 2>&1 || CLEANUP_OK=false
  fi
  if [[ "$SNAPSHOT_CREATED" == true ]]; then
    if aws rds delete-db-snapshot --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" >/dev/null 2>&1; then
      aws rds wait db-snapshot-deleted --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" >/dev/null 2>&1 || CLEANUP_OK=false
    else
      CLEANUP_OK=false
    fi
  fi
  if [[ "$CLEANUP_OK" != true ]]; then
    echo "CLEANUP=INCOMPLETE; revise únicamente los recursos $RESTORE_ID / $SNAPSHOT_ID y la tabla $PROBE_TABLE." >&2
    exit 3
  fi
  if [[ "$original_status" -eq 0 && "$TEST_PASSED" == true ]]; then
    printf '{"test_id":"PT-DR-01","status":"PASSED","source_db":"%s","restore_db":"%s","measured_rto_seconds":%s,"measured_rpo_upper_bound_seconds":%s,"source_public":false,"restore_public":false,"encrypted":true,"restore_backup_retention_days":0,"data_marker_verified":true,"cleanup":"verified"}\n' \
      "$SOURCE_DB" "$RESTORE_ID" "${RTO_SECONDS:-null}" "${RPO_UPPER_BOUND_SECONDS:-null}"
  elif [[ "$original_status" -eq 0 ]]; then
    exit 1
  fi
  exit "$original_status"
}
trap cleanup EXIT

SOURCE_ENDPOINT="$(aws rds describe-db-instances --db-instance-identifier "$SOURCE_DB" --region "$REGION" --query 'DBInstances[0].Endpoint.Address' --output text)"
if [[ -z "$SOURCE_ENDPOINT" || "$SOURCE_ENDPOINT" == None ]]; then echo "La fuente no tiene endpoint." >&2; exit 2; fi

# Preflight de permisos de SQL/SSM antes de iniciar recursos facturables. Crea
# una tabla efímera y un marcador único que se elimina en el trap de salida.
# The remote command can commit the marker and then lose its SSM response;
# arm cleanup first so DROP IF EXISTS is attempted even on an ambiguous failure.
PROBE_CREATED=true
PROBE_JSON="$(invoke_probe "$SOURCE_ENDPOINT" create)"
MARKER_CREATED_AT="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["committed_at"])' <<<"$PROBE_JSON")"

aws rds create-db-snapshot --db-instance-identifier "$SOURCE_DB" --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" >/dev/null
SNAPSHOT_CREATED=true
aws rds wait db-snapshot-available --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION"
SNAPSHOT_JSON="$(aws rds describe-db-snapshots --db-snapshot-identifier "$SNAPSHOT_ID" --region "$REGION" --output json)"
SNAPSHOT_TIME="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["DBSnapshots"][0]["SnapshotCreateTime"])' <<<"$SNAPSHOT_JSON")"
RPO_UPPER_BOUND_SECONDS="$(python3 -c 'from datetime import datetime; import sys; a=datetime.fromisoformat(sys.argv[1].replace("Z","+00:00")); b=datetime.fromisoformat(sys.argv[2].replace("Z","+00:00")); print(max(0,int((b-a).total_seconds())))' "$MARKER_CREATED_AT" "$SNAPSHOT_TIME")"

# RTO is measured from the restore request until the restored database passes
# the SQL integrity probe, not from the preceding snapshot creation.
RTO_START="$(date +%s)"
read -r -a SG_ARGS <<< "$SECURITY_GROUPS"
SG_FLAGS=()
for group in "${SG_ARGS[@]}"; do SG_FLAGS+=(--vpc-security-group-ids "$group"); done
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier "$RESTORE_ID" \
  --db-snapshot-identifier "$SNAPSHOT_ID" \
  --db-instance-class "$INSTANCE_CLASS" \
  --db-subnet-group-name "$SUBNET_GROUP" \
  "${SG_FLAGS[@]}" \
  --backup-retention-period 0 \
  --no-publicly-accessible \
  --region "$REGION" >/dev/null
RESTORE_CREATED=true
aws rds wait db-instance-available --db-instance-identifier "$RESTORE_ID" --region "$REGION"
RESTORE_JSON="$(aws rds describe-db-instances --db-instance-identifier "$RESTORE_ID" --region "$REGION" --output json)"
RESTORE_ENDPOINT="$(python3 -c 'import json,sys; db=json.loads(sys.stdin.read())["DBInstances"][0]; print(db["Endpoint"]["Address"]); assert db["PubliclyAccessible"] is False; assert db["StorageEncrypted"] is True; assert db["DBInstanceStatus"] == "available"; assert db["BackupRetentionPeriod"] == 0; assert db["DBSubnetGroup"]["DBSubnetGroupName"] == sys.argv[1]; assert {x["VpcSecurityGroupId"] for x in db["VpcSecurityGroups"]} == set(sys.argv[2].split())' "$SUBNET_GROUP" "$SECURITY_GROUPS" <<<"$RESTORE_JSON")"

RESTORE_PROBE="$(invoke_probe "$RESTORE_ENDPOINT" verify)"
RESTORE_MARKER="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read())["marker_present"]))' <<<"$RESTORE_PROBE")"
if [[ "$RESTORE_MARKER" != true ]]; then echo "El restore abrió pero no contiene el marcador SQL anterior al snapshot." >&2; exit 1; fi
SOURCE_COUNTS="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read())["business_counts"], sort_keys=True))' <<<"$PROBE_JSON")"
RESTORE_COUNTS="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.stdin.read())["business_counts"], sort_keys=True))' <<<"$RESTORE_PROBE")"
if [[ "$SOURCE_COUNTS" != "$RESTORE_COUNTS" ]]; then echo "Los conteos de tablas de negocio difieren entre el checkpoint y el restore." >&2; exit 1; fi
RTO_SECONDS="$(( $(date +%s) - RTO_START ))"
TEST_PASSED=true
