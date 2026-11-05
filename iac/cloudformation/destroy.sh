#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() { "$AWS_CLI" "$@" | tr -d '\r'; }
fi

STACK_NAME="${STACK_NAME:-}"
REGION="${AWS_REGION:-us-east-1}"
VOICE_STACK="${VOICE_STACK_NAME:-tangamandapio-voice-recordings}"
PROJECT_NAME="${PROJECT_NAME:-tangamandapio}"
EXPECTED_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-}"

if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "Borrado bloqueado: define STACK_NAME explícitamente con el nombre del stack verificado (tangamandapio-live-YYYYMMDD)." >&2
  exit 2
fi
if [[ ! "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
  echo "Borrado bloqueado: define EXPECTED_AWS_ACCOUNT_ID con el ID de cuenta revisado." >&2
  exit 2
fi
ACTUAL_ACCOUNT_ID="$(aws sts get-caller-identity --region "$REGION" --query Account --output text)"
if [[ "$ACTUAL_ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]]; then
  echo "Borrado bloqueado: la sesión apunta a $ACTUAL_ACCOUNT_ID; se esperaba $EXPECTED_ACCOUNT_ID." >&2
  exit 2
fi

if [[ "${CONFIRM_DELETE_DATA:-}" != "true" ]]; then
  echo "Borrado bloqueado: define CONFIRM_DELETE_DATA=true solo si aceptas perder los datos de la base y los buckets del portal." >&2
  exit 2
fi
if [[ "${CONFIRM_STACK_NAME:-}" != "$STACK_NAME" ]]; then
  echo "Borrado bloqueado: define CONFIRM_STACK_NAME exactamente como STACK_NAME después de revisar el inventario." >&2
  exit 2
fi
if [[ "${PURGE_PROJECT_RESOURCES:-}" != "true" ]]; then
  echo "Borrado bloqueado: define PURGE_PROJECT_RESOURCES=true para purgar snapshots y copias de AWS Backup del proyecto." >&2
  exit 2
fi
PURGE_PROJECT_SECRETS="${PURGE_PROJECT_SECRETS:-false}"
if [[ "$PURGE_PROJECT_SECRETS" != "true" && "$PURGE_PROJECT_SECRETS" != "false" ]]; then
  echo "Borrado bloqueado: PURGE_PROJECT_SECRETS solo acepta true o false." >&2
  exit 2
fi
if [[ "$PURGE_PROJECT_SECRETS" == "true" && "${CONFIRM_PURGE_PROJECT_SECRETS:-}" != "$STACK_NAME" ]]; then
  echo "Borrado bloqueado: para eliminar credenciales, define CONFIRM_PURGE_PROJECT_SECRETS exactamente igual a STACK_NAME." >&2
  exit 2
fi

cloudformation_stack_exists() {
  local response
  if response="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$1" 2>&1)"; then
    return 0
  fi
  if [[ "$response" == *"does not exist"* ]]; then
    return 1
  fi
  echo "No se pudo comprobar el stack $1: $response" >&2
  return 2
}

# The generic teardown does not yet own the Tailscale routers or the manually
# created private DNS zone. Never orphan them by deleting the parent VPC.
for vpn_stack in tangamandapio-tailscale-pilot tangamandapio-tailscale-pilot-b; do
  if cloudformation_stack_exists "$vpn_stack"; then
    echo "Borrado bloqueado: el stack VPN $vpn_stack existe; revisa y elimina sus dependencias mediante el procedimiento específico antes de borrar la VPC." >&2
    exit 2
  else
    result=$?
    if [[ "$result" != 1 ]]; then
      echo "Borrado bloqueado: no se pudo comprobar el inventario VPN." >&2
      exit 2
    fi
  fi
done

# A manually associated private hosted zone also prevents safe VPC teardown.
# Detect all private zones associated with this stack's VPC before proceeding.
vpc_id="$(aws cloudformation describe-stack-resource --region "$REGION" --stack-name "$STACK_NAME" --logical-resource-id VPC --query 'StackResourceDetail.PhysicalResourceId' --output text)" || {
  echo 'Borrado bloqueado: no se pudo comprobar la VPC y su DNS privado.' >&2; exit 2;
}
[[ "$vpc_id" =~ ^vpc-[0-9a-f]+$ ]] || { echo 'Borrado bloqueado: no se pudo comprobar la VPC del proyecto.' >&2; exit 2; }
zone_ids="$(aws route53 list-hosted-zones-by-vpc --vpc-id "$vpc_id" --vpc-region "$REGION" --query 'HostedZoneSummaries[*].HostedZoneId' --output text)" || {
  echo 'Borrado bloqueado: no se pudo comprobar el DNS privado de la VPC.' >&2; exit 2;
}
if [[ -n "$zone_ids" && "$zone_ids" != 'None' ]]; then
  echo 'Borrado bloqueado: la VPC tiene zonas DNS privadas asociadas; revisa su propiedad y ciclo de vida antes de continuar.' >&2
  exit 2
fi

ensure_stack_in_sync() {
  local stack_name="$1"
  local drift_status detection_id detection_status

  drift_status="$(aws cloudformation describe-stacks --region "$REGION" \
    --stack-name "$stack_name" --query 'Stacks[0].DriftInformation.StackDriftStatus' --output text)"
  if [[ "$drift_status" == "NOT_CHECKED" || "$drift_status" == "NOT_CHECKED"* ]]; then
    detection_id="$(aws cloudformation detect-stack-drift --region "$REGION" \
      --stack-name "$stack_name" --query StackDriftDetectionId --output text)"
    for attempt in $(seq 1 60); do
      detection_status="$(aws cloudformation describe-stack-drift-detection-status \
        --region "$REGION" --stack-drift-detection-id "$detection_id" \
        --query DetectionStatus --output text)"
      if [[ "$detection_status" == "DETECTION_COMPLETE" ]]; then
        drift_status="$(aws cloudformation describe-stack-drift-detection-status \
          --region "$REGION" --stack-drift-detection-id "$detection_id" \
          --query StackDriftStatus --output text)"
        break
      fi
      if [[ "$detection_status" == "DETECTION_FAILED" || "$attempt" == "60" ]]; then
        echo "Borrado bloqueado: no se pudo terminar la comprobación de deriva de $stack_name ($detection_status)." >&2
        exit 2
      fi
      sleep 5
    done
  fi

  if [[ "$drift_status" != "IN_SYNC" ]]; then
    echo "Borrado bloqueado: revisa primero la deriva de $stack_name (estado: $drift_status)." >&2
    exit 2
  fi
  echo "STACK_DRIFT_VERIFIED:$stack_name:$drift_status"
}

STACK_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' --output text)"
if [[ "$STACK_STATUS" != "UPDATE_COMPLETE" && "$STACK_STATUS" != "CREATE_COMPLETE" ]]; then
  echo "Borrado bloqueado: el stack no está estable (estado: $STACK_STATUS)." >&2
  exit 2
fi

ensure_stack_in_sync "$STACK_NAME"

# Drift detection does not validate CloudFormation lifecycle attributes. Read
# the deployed template itself and refuse deletion unless the database and its
# credential secret have recoverable policies. This is intentionally before
# touching the recordings stack or any bucket.
TEMPLATE_FILE="$(mktemp)"
trap 'rm -f "$TEMPLATE_FILE"' EXIT
if [[ -n "${TANGAMA_PYTHON:-}" ]]; then
  PYTHON_BIN="$TANGAMA_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Borrado bloqueado: se necesita Python 3 con PyYAML; define TANGAMA_PYTHON si está fuera del PATH." >&2
  exit 2
fi
if ! "$PYTHON_BIN" -c 'import yaml' >/dev/null 2>&1; then
  echo "Borrado bloqueado: el Python seleccionado necesita PyYAML; define TANGAMA_PYTHON con un intérprete que lo tenga." >&2
  exit 2
fi
aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody' --output text > "$TEMPLATE_FILE"

template_policy() {
  local logical_id="$1"
  local policy_name="$2"
  "$PYTHON_BIN" - "$TEMPLATE_FILE" "$logical_id" "$policy_name" <<'PY'
import sys
import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


class CloudFormationLoader(yaml.SafeLoader):
    pass


def construct_intrinsic(loader, tag_suffix, node):
    if isinstance(node, ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, MappingNode):
        return loader.construct_mapping(node)
    raise yaml.constructor.ConstructorError(None, None, "unsupported CloudFormation node", node.start_mark)


CloudFormationLoader.add_multi_constructor("!", construct_intrinsic)
with open(sys.argv[1], encoding="utf-8") as template_file:
    template = yaml.load(template_file, Loader=CloudFormationLoader)
resource = template.get("Resources", {}).get(sys.argv[2], {})
print(resource.get(sys.argv[3], "None"))
PY
}

DB_DELETION_POLICY="$(template_policy Database DeletionPolicy)"
DB_REPLACE_POLICY="$(template_policy Database UpdateReplacePolicy)"
DB_SECRET_POLICY="$(template_policy DBSecret DeletionPolicy)"
DB_SECRET_REPLACE_POLICY="$(template_policy DBSecret UpdateReplacePolicy)"
ADMIN_SECRET_POLICY="$(template_policy PortalAdminSecret DeletionPolicy)"
ADMIN_SECRET_REPLACE_POLICY="$(template_policy PortalAdminSecret UpdateReplacePolicy)"
if [[ "$DB_DELETION_POLICY" != "Snapshot" || "$DB_REPLACE_POLICY" != "Snapshot" || \
  "$DB_SECRET_POLICY" != "Retain" || "$DB_SECRET_REPLACE_POLICY" != "Retain" || \
  "$ADMIN_SECRET_POLICY" != "Retain" || "$ADMIN_SECRET_REPLACE_POLICY" != "Retain" ]]; then
  echo "Borrado bloqueado: el template desplegado no demuestra Snapshot/Snapshot/Retain para la base y retención del secreto DB/admin (obtenido: $DB_DELETION_POLICY/$DB_REPLACE_POLICY/$DB_SECRET_POLICY/$DB_SECRET_REPLACE_POLICY/$ADMIN_SECRET_POLICY/$ADMIN_SECRET_REPLACE_POLICY)." >&2
  exit 2
fi
echo "El template conserva RDS/secrets durante el borrado del stack; el script elimina después snapshots/backups. Secrets Manager y SSM se conservan salvo PURGE_PROJECT_SECRETS=true con confirmación independiente."

DB_IDENTIFIER="$(aws cloudformation describe-stack-resources \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "StackResources[?LogicalResourceId=='Database'].PhysicalResourceId" \
  --output text)"
if [[ -z "$DB_IDENTIFIER" || "$DB_IDENTIFIER" == "None" ]]; then
  echo "Borrado bloqueado: el stack no devolvió el identificador de RDS esperado." >&2
  exit 2
fi
AZURE_FUNCTION_KEY_SECRET="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Parameters[?ParameterKey=='AzureFunctionKeySecret'].ParameterValue" \
  --output text)"
DATABASE_SECRET_ARN="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" --output text)"
PORTAL_ADMIN_SECRET_ARN="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='PortalAdminSecretArn'].OutputValue" --output text)"
BACKUP_PLAN_ID="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='BackupPlanId'].OutputValue" --output text)"

if [[ "${PRESERVE_RDS_SNAPSHOT:-false}" == "true" ]]; then
  echo "Borrado bloqueado: PURGE_PROJECT_RESOURCES=true no puede conservar un snapshot RDS." >&2
  exit 2
fi

delete_project_secret() {
  local secret_id="$1"
  local expected_name="$2"
  [[ -n "$secret_id" && "$secret_id" != "None" ]] || return 0

  local secret_name secret_project
  if ! secret_name="$(aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$secret_id" --query Name --output text 2>&1)"; then
    if [[ "$secret_name" == *"ResourceNotFoundException"* ]]; then return 0; fi
    echo "No se pudo verificar el secreto $secret_id: $secret_name" >&2
    exit 2
  fi
  secret_project="$(aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$secret_id" --query "Tags[?Key=='Project'].Value | [0]" --output text)"
  if [[ "$secret_name" != "$expected_name" || "$secret_project" != "$PROJECT_NAME" ]]; then
    echo "Borrado bloqueado: el secreto $secret_id no acredita nombre y etiqueta del proyecto." >&2
    exit 2
  fi
  aws secretsmanager delete-secret --region "$REGION" \
    --secret-id "$secret_id" --force-delete-without-recovery >/dev/null
  echo "PROJECT_SECRET_DELETED:$secret_name"
}

# Remove the known project VPN stacks before deleting their shared VPC.
for VPN_STACK in "${VPN_STACK_NAME:-tangamandapio-aws-azure-vpn}" "${ROUTER_STACK_NAME:-tangamandapio-aws-azure-p2s-router}"; do
  if cloudformation_stack_exists "$VPN_STACK"; then
    VPN_STATUS="$(aws cloudformation describe-stacks --region "$REGION" \
      --stack-name "$VPN_STACK" --query 'Stacks[0].StackStatus' --output text)"
    if [[ "$VPN_STATUS" != "CREATE_COMPLETE" && "$VPN_STATUS" != "UPDATE_COMPLETE" ]]; then
      echo "Borrado bloqueado: el stack VPN $VPN_STACK no está estable ($VPN_STATUS)." >&2
      exit 2
    fi
    aws cloudformation delete-stack --region "$REGION" --stack-name "$VPN_STACK"
    aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$VPN_STACK"
    echo "VPN_STACK_DELETED:$VPN_STACK"
  else
    stack_probe_status=$?
    [[ "$stack_probe_status" == "1" ]] || exit "$stack_probe_status"
  fi
done

# The project backup vault is optional. When the main stack says AWS Backup is
# enabled, verify its project tag and empty its recovery points before teardown.
if [[ -n "$BACKUP_PLAN_ID" && "$BACKUP_PLAN_ID" != "None" ]]; then
  BACKUP_VAULT="${PROJECT_NAME}-vault"
  BACKUP_PROJECT="$(aws backup describe-backup-vault --region "$REGION" \
    --backup-vault-name "$BACKUP_VAULT" --query 'BackupVaultTags.Project' --output text)"
  if [[ "$BACKUP_PROJECT" != "$PROJECT_NAME" ]]; then
    echo "Borrado bloqueado: el vault $BACKUP_VAULT no confirma Project=$PROJECT_NAME." >&2
    exit 2
  fi
  RECOVERY_POINTS="$(aws backup list-recovery-points-by-backup-vault --region "$REGION" \
    --backup-vault-name "$BACKUP_VAULT" --query 'RecoveryPoints[].RecoveryPointArn' --output text)"
  for recovery_point in $RECOVERY_POINTS; do
    [[ -n "$recovery_point" && "$recovery_point" != "None" ]] || continue
    aws backup delete-recovery-point --region "$REGION" \
      --backup-vault-name "$BACKUP_VAULT" --recovery-point-arn "$recovery_point"
  done
  for attempt in $(seq 1 60); do
    remaining_recovery_points="$(aws backup list-recovery-points-by-backup-vault --region "$REGION" \
      --backup-vault-name "$BACKUP_VAULT" --query 'RecoveryPoints[].RecoveryPointArn' --output text)"
    if [[ -z "$remaining_recovery_points" || "$remaining_recovery_points" == "None" ]]; then
      break
    fi
    if [[ "$attempt" == "60" ]]; then
      echo "Borrado bloqueado: el vault $BACKUP_VAULT todavía conserva recovery points." >&2
      exit 2
    fi
    sleep 10
  done
  echo "PROJECT_BACKUP_RECOVERY_POINTS_PURGED:$BACKUP_VAULT"
fi

empty_versioned_bucket() {
  local bucket="$1"
  local expected_project="${2:-$PROJECT_NAME}"
  local project_tag

  project_tag="$(aws s3api get-bucket-tagging --region "$REGION" --bucket "$bucket" \
    --query "TagSet[?Key=='Project'].Value | [0]" --output text 2>/dev/null || true)"
  if [[ "$project_tag" != "$expected_project" ]]; then
    echo "Borrado bloqueado: el bucket $bucket no confirma la etiqueta Project=$expected_project." >&2
    exit 2
  fi

  aws s3 rm "s3://$bucket" --recursive --region "$REGION"
  # Repeat the first service page until empty. This safely handles buckets with
  # more than one 1,000-object S3 delete batch, including noncurrent versions.
  for object_set in Versions DeleteMarkers; do
    while true; do
      objects="$(aws s3api list-object-versions --region "$REGION" \
        --bucket "$bucket" --max-items 1000 \
        --query "${object_set}[].{Key:Key,VersionId:VersionId}" --output json)"
      if [[ "$objects" == "null" || "$objects" == "[]" || -z "$objects" ]]; then
        break
      fi
      delete_errors="$(aws s3api delete-objects --region "$REGION" --bucket "$bucket" \
        --delete "{\"Objects\":$objects,\"Quiet\":true}" \
        --query 'Errors' --output json)"
      if [[ "$delete_errors" != "null" && "$delete_errors" != "[]" ]]; then
        echo "Borrado bloqueado: S3 devolvió errores al vaciar $bucket." >&2
        exit 2
      fi
    done
  done

  remaining_versions="$(aws s3api list-object-versions --region "$REGION" --bucket "$bucket" \
    --query 'length(Versions || `[]`)' --output text)"
  remaining_markers="$(aws s3api list-object-versions --region "$REGION" --bucket "$bucket" \
    --query 'length(DeleteMarkers || `[]`)' --output text)"
  if [[ "$remaining_versions" != "0" || "$remaining_markers" != "0" ]]; then
    echo "Borrado bloqueado: $bucket todavía tiene $remaining_versions versiones y $remaining_markers marcadores." >&2
    exit 2
  fi
}

# The recordings stack retains its bucket by design. Remove the stack first,
# then explicitly delete the now-empty bucket so no storage keeps billing.
if cloudformation_stack_exists "$VOICE_STACK"; then
  VOICE_STATUS="$(aws cloudformation describe-stacks --region "$REGION" \
    --stack-name "$VOICE_STACK" --query 'Stacks[0].StackStatus' --output text)"
  if [[ "$VOICE_STATUS" != "CREATE_COMPLETE" && "$VOICE_STATUS" != "UPDATE_COMPLETE" ]]; then
    echo "Borrado bloqueado: el stack de grabaciones no está estable ($VOICE_STATUS)." >&2
    exit 2
  fi
  ensure_stack_in_sync "$VOICE_STACK"

  VOICE_BUCKET="$(aws cloudformation describe-stacks --region "$REGION" \
    --stack-name "$VOICE_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='VoiceRecordingsBucketName'].OutputValue" --output text)"
  if [[ -z "$VOICE_BUCKET" || "$VOICE_BUCKET" == "None" || "$VOICE_BUCKET" != "$PROJECT_NAME-voice-"* ]]; then
    echo "Borrado bloqueado: el stack no devolvió el bucket de grabaciones esperado." >&2
    exit 2
  fi

  empty_versioned_bucket "$VOICE_BUCKET"
  aws cloudformation delete-stack --region "$REGION" --stack-name "$VOICE_STACK"
  aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$VOICE_STACK"
  aws s3api delete-bucket --region "$REGION" --bucket "$VOICE_BUCKET"
  echo "VOICE_STACK_AND_BUCKET_DELETED:$VOICE_STACK"
else
  stack_probe_status=$?
  [[ "$stack_probe_status" == "1" ]] || exit "$stack_probe_status"
fi

BUCKET_NAME="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`AssetBucketName`].OutputValue' \
  --output text 2>/dev/null || true)"

if [[ -n "$BUCKET_NAME" && "$BUCKET_NAME" != "None" ]]; then
  empty_versioned_bucket "$BUCKET_NAME"
fi

FILES_BUCKET="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='FilesBucketName'].OutputValue" \
  --output text 2>/dev/null || true)"
if [[ -n "$FILES_BUCKET" && "$FILES_BUCKET" != "None" ]]; then
  empty_versioned_bucket "$FILES_BUCKET"
fi

aws cloudformation delete-stack --region "$REGION" --stack-name "$STACK_NAME"
aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$STACK_NAME"

if [[ -n "$DB_IDENTIFIER" && "$DB_IDENTIFIER" != "None" ]]; then
  snapshots="$(aws rds describe-db-snapshots --region "$REGION" \
    --db-instance-identifier "$DB_IDENTIFIER" --snapshot-type manual \
    --query 'DBSnapshots[].DBSnapshotIdentifier' --output text)"
  for snapshot_id in $snapshots; do
    [[ -n "$snapshot_id" && "$snapshot_id" != "None" ]] || continue
    aws rds delete-db-snapshot --region "$REGION" \
      --db-snapshot-identifier "$snapshot_id" >/dev/null
    aws rds wait db-snapshot-deleted --region "$REGION" \
      --db-snapshot-identifier "$snapshot_id"
    echo "PROJECT_RDS_SNAPSHOT_DELETED:$snapshot_id"
  done
  remaining_snapshots="$(aws rds describe-db-snapshots --region "$REGION" \
    --db-instance-identifier "$DB_IDENTIFIER" --snapshot-type manual \
    --query 'length(DBSnapshots)' --output text)"
  if [[ "$remaining_snapshots" != "0" ]]; then
    echo "Borrado incompleto: quedan $remaining_snapshots snapshots manuales de $DB_IDENTIFIER." >&2
    exit 2
  fi
fi

if [[ "$PURGE_PROJECT_SECRETS" == "true" ]]; then
  delete_project_secret "$DATABASE_SECRET_ARN" "$PROJECT_NAME/rds/master-$STACK_NAME"
  delete_project_secret "$PORTAL_ADMIN_SECRET_ARN" "$PROJECT_NAME/portal/admin"
  delete_project_secret "$AZURE_FUNCTION_KEY_SECRET" "$PROJECT_NAME/azure/function-key"

  if ssm_parameter="$(aws ssm get-parameter --region "$REGION" \
    --name /tangamandapio/azure/function-key 2>&1)"; then
    aws ssm delete-parameter --region "$REGION" \
      --name /tangamandapio/azure/function-key
    echo "AZURE_FUNCTION_PARAMETER_DELETED:/tangamandapio/azure/function-key"
  elif [[ "$ssm_parameter" != *"ParameterNotFound"* ]]; then
    echo "No se pudo verificar el parámetro SSM del proyecto: $ssm_parameter" >&2
    exit 2
  fi
else
  echo "PROJECT_SECRETS_PRESERVED: Secrets Manager y SSM quedan intactos; usa PURGE_PROJECT_SECRETS=true y CONFIRM_PURGE_PROJECT_SECRETS=$STACK_NAME solo para eliminarlos."
fi

for deleted_stack in "$STACK_NAME" "$VOICE_STACK" "${VPN_STACK_NAME:-tangamandapio-aws-azure-vpn}" "${ROUTER_STACK_NAME:-tangamandapio-aws-azure-p2s-router}"; do
  if cloudformation_stack_exists "$deleted_stack"; then
    echo "Borrado incompleto: el stack $deleted_stack todavía existe." >&2
    exit 2
  else
    stack_probe_status=$?
    [[ "$stack_probe_status" == "1" ]] || exit "$stack_probe_status"
  fi
done

echo "PROJECT_STACKS_AND_RETAINED_DATA_PURGED:$STACK_NAME"

