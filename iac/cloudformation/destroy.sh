#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() { "$AWS_CLI" "$@" | tr -d '\r'; }
fi

STACK_NAME="${STACK_NAME:-}"
REGION="${AWS_REGION:-us-east-1}"
VOICE_STACK="${VOICE_STACK_NAME:-tangamandapio-voice-recordings}"
PROJECT_NAME="${PROJECT_NAME:-tangamandapio}"

if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "Borrado bloqueado: define STACK_NAME explícitamente con el nombre del stack verificado (tangamandapio-live-YYYYMMDD)." >&2
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

STACK_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' --output text)"
if [[ "$STACK_STATUS" != "UPDATE_COMPLETE" && "$STACK_STATUS" != "CREATE_COMPLETE" ]]; then
  echo "Borrado bloqueado: el stack no está estable (estado: $STACK_STATUS)." >&2
  exit 2
fi

DRIFT_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query 'Stacks[0].DriftInformation.StackDriftStatus' --output text)"
if [[ "$DRIFT_STATUS" != "IN_SYNC" ]]; then
  echo "Borrado bloqueado: revisa primero el drift (estado: $DRIFT_STATUS)." >&2
  exit 2
fi

# Drift detection does not validate CloudFormation lifecycle attributes. Read
# the deployed template itself and refuse deletion unless the database and its
# credential secret have recoverable policies. This is intentionally before
# touching the recordings stack or any bucket.
DB_DELETION_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.Database.DeletionPolicy' --output text)"
DB_REPLACE_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.Database.UpdateReplacePolicy' --output text)"
DB_SECRET_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.DBSecret.DeletionPolicy' --output text)"
DB_SECRET_REPLACE_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.DBSecret.UpdateReplacePolicy' --output text)"
ADMIN_SECRET_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.PortalAdminSecret.DeletionPolicy' --output text)"
ADMIN_SECRET_REPLACE_POLICY="$(aws cloudformation get-template \
  --region "$REGION" --stack-name "$STACK_NAME" --template-stage Original \
  --query 'TemplateBody.Resources.PortalAdminSecret.UpdateReplacePolicy' --output text)"
if [[ "$DB_DELETION_POLICY" != "Snapshot" || "$DB_REPLACE_POLICY" != "Snapshot" || \
  "$DB_SECRET_POLICY" != "Retain" || "$DB_SECRET_REPLACE_POLICY" != "Retain" || \
  "$ADMIN_SECRET_POLICY" != "Retain" || "$ADMIN_SECRET_REPLACE_POLICY" != "Retain" ]]; then
  echo "Borrado bloqueado: el template desplegado no demuestra Snapshot/Snapshot/Retain para la base y retención del secreto DB/admin (obtenido: $DB_DELETION_POLICY/$DB_REPLACE_POLICY/$DB_SECRET_POLICY/$DB_SECRET_REPLACE_POLICY/$ADMIN_SECRET_POLICY/$ADMIN_SECRET_REPLACE_POLICY)." >&2
  exit 2
fi
echo "Protección validada en el template desplegado: RDS Snapshot/Snapshot; secretos DB/admin Retain. Los snapshots manuales no se borran con este script."

DB_IDENTIFIER="$(aws cloudformation describe-stack-resources \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "StackResources[?LogicalResourceId=='Database'].PhysicalResourceId" \
  --output text)"
AZURE_FUNCTION_KEY_SECRET="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Parameters[?ParameterKey=='AzureFunctionKeySecret'].ParameterValue" \
  --output text)"

if [[ "${PRESERVE_RDS_SNAPSHOT:-false}" == "true" ]]; then
  SNAPSHOT_ID="${STACK_NAME}-final-$(date -u +%Y%m%d%H%M%S)"
  aws rds create-db-snapshot --region "$REGION" \
    --db-instance-identifier "$DB_IDENTIFIER" \
    --db-snapshot-identifier "$SNAPSHOT_ID" >/dev/null
  aws rds wait db-snapshot-available --region "$REGION" \
    --db-snapshot-identifier "$SNAPSHOT_ID"
  echo "Snapshot conservado: $SNAPSHOT_ID (su almacenamiento seguirá generando cargos)."
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
if aws cloudformation describe-stacks --region "$REGION" --stack-name "$VOICE_STACK" >/dev/null 2>&1; then
  VOICE_STATUS="$(aws cloudformation describe-stacks --region "$REGION" \
    --stack-name "$VOICE_STACK" --query 'Stacks[0].StackStatus' --output text)"
  VOICE_DRIFT="$(aws cloudformation describe-stacks --region "$REGION" \
    --stack-name "$VOICE_STACK" --query 'Stacks[0].DriftInformation.StackDriftStatus' --output text)"
  if [[ "$VOICE_STATUS" != "CREATE_COMPLETE" && "$VOICE_STATUS" != "UPDATE_COMPLETE" ]]; then
    echo "Borrado bloqueado: el stack de grabaciones no está estable ($VOICE_STATUS)." >&2
    exit 2
  fi
  if [[ "$VOICE_DRIFT" != "IN_SYNC" ]]; then
    echo "Borrado bloqueado: revisa el drift del stack de grabaciones ($VOICE_DRIFT)." >&2
    exit 2
  fi

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

echo "RDS_SNAPSHOTS_PRESERVED: CloudFormation lifecycle policy conserva el snapshot final; los snapshots manuales existentes permanecen intactos."

if [[ -n "$AZURE_FUNCTION_KEY_SECRET" && "$AZURE_FUNCTION_KEY_SECRET" != "None" ]] && \
  aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$AZURE_FUNCTION_KEY_SECRET" >/dev/null 2>&1; then
  aws secretsmanager delete-secret --region "$REGION" \
    --secret-id "$AZURE_FUNCTION_KEY_SECRET" --force-delete-without-recovery >/dev/null
  echo "AZURE_FUNCTION_SECRET_DELETED:$AZURE_FUNCTION_KEY_SECRET"
fi

if aws ssm get-parameter --region "$REGION" \
  --name /tangamandapio/azure/function-key >/dev/null 2>&1; then
  aws ssm delete-parameter --region "$REGION" \
    --name /tangamandapio/azure/function-key
  echo "AZURE_FUNCTION_PARAMETER_DELETED:/tangamandapio/azure/function-key"
fi

echo "STACK_DELETED:$STACK_NAME"

