#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() {
    local -a args=()
    local arg
    for arg in "$@"; do
      # Git Bash exposes local files as /c/... and WSL as /mnt/c/...; the native
      # Windows AWS CLI expects drive-letter paths for files and S3 uploads.
      if [[ "$arg" =~ ^file:///mnt/([a-zA-Z])/(.*)$ ]]; then
        arg="file://${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}"
      elif [[ "$arg" =~ ^file:///([a-zA-Z])/(.*)$ ]]; then
        arg="file://${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}"
      elif [[ "$arg" =~ ^/mnt/([a-zA-Z])/(.*)$ ]]; then
        arg="${BASH_REMATCH[1]^^}:/${BASH_REMATCH[2]}"
      fi
      args+=("$arg")
    done
    "$AWS_CLI" "${args[@]}" | tr -d '\r'
  }
fi

# Rebuild a deleted demo stack in two phases: create with zero EC2 instances,
# publish the exact checked-in release artifact, then enable the Auto Scaling
# Group. This script never deletes resources.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
STACK_NAME="${STACK_NAME:-}"
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-tangamandapio}"
TEMPLATE="${TEMPLATE:-$SCRIPT_DIR/aws-lab.yaml}"
FUNCTION_URL="${AZURE_FULFILLMENT_URL:-}"
FUNCTION_KEY_SECRET="${AZURE_FUNCTION_KEY_SECRET:-}"
SNAPSHOT_IDENTIFIER="${RDS_SNAPSHOT_IDENTIFIER:-}"
RESET_ADMINISTRATOR_PASSWORD="${RESET_ADMINISTRATOR_ON_RESTORE:-false}"

if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "Reconstrucción bloqueada: define STACK_NAME explícitamente con un nombre de proyecto verificado (tangamandapio-live-YYYYMMDD)." >&2
  exit 2
fi

REVISION="$(tr -cd 'A-Za-z0-9._-' < "$REPOSITORY_ROOT/app/aws_release/current/BUILD_REVISION" | head -c 80)"
ARTIFACT_KEY="${APPLICATION_ARTIFACT_KEY:-}"
ARTIFACT_PATH="$(mktemp "${TMPDIR:-/tmp}/tangamandapio-portal.XXXXXX.tar.gz")"

cleanup() {
  rm -f -- "$ARTIFACT_PATH"
}
trap cleanup EXIT

if [[ ! -f "$TEMPLATE" ]]; then
  echo "No existe la plantilla: $TEMPLATE" >&2
  exit 2
fi
if [[ -z "$FUNCTION_URL" || -z "$FUNCTION_KEY_SECRET" ]]; then
  echo "Define AZURE_FULFILLMENT_URL y AZURE_FUNCTION_KEY_SECRET con la Function ya publicada y su clave sincronizada en Secrets Manager." >&2
  exit 2
fi
if ! aws secretsmanager describe-secret --region "$REGION" --secret-id "$FUNCTION_KEY_SECRET" \
  --cli-connect-timeout 5 --cli-read-timeout 20 >/dev/null; then
  echo "No existe el secreto Azure indicado en Secrets Manager; no se crearán recursos." >&2
  exit 2
fi
if [[ "$RESET_ADMINISTRATOR_PASSWORD" != "true" && "$RESET_ADMINISTRATOR_PASSWORD" != "false" ]]; then
  echo "RESET_ADMINISTRATOR_ON_RESTORE solo acepta true o false." >&2
  exit 2
fi

DATABASE_SECRET_ARN=""
RESTORE_MASTER_SECRET_AFTER_BOOTSTRAP=false
if [[ -n "${DATABASE_SECRET_NAME:-}" ]]; then
  DATABASE_SECRET_CANDIDATES=("$DATABASE_SECRET_NAME")
else
  DATABASE_SECRET_CANDIDATES=(
    "$PROJECT_NAME/rds/master-$STACK_NAME"
    "$PROJECT_NAME/rds/master"
  )
fi
for database_secret_name in "${DATABASE_SECRET_CANDIDATES[@]}"; do
  if aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$database_secret_name" \
    --cli-connect-timeout 5 --cli-read-timeout 20 >/dev/null 2>&1; then
    DATABASE_SECRET_ARN="$(aws secretsmanager describe-secret --region "$REGION" \
      --secret-id "$database_secret_name" --query ARN --output text \
      --cli-connect-timeout 5 --cli-read-timeout 20)"
    break
  fi
done

PORTAL_ADMIN_SECRET_ARN=""
if [[ -n "${PORTAL_ADMIN_SECRET_NAME:-}" ]]; then
  PORTAL_ADMIN_SECRET_CANDIDATES=("$PORTAL_ADMIN_SECRET_NAME")
else
  PORTAL_ADMIN_SECRET_CANDIDATES=("$PROJECT_NAME/portal/admin")
fi
for portal_admin_secret_name in "${PORTAL_ADMIN_SECRET_CANDIDATES[@]}"; do
  if aws secretsmanager describe-secret --region "$REGION" \
    --secret-id "$portal_admin_secret_name" \
    --cli-connect-timeout 5 --cli-read-timeout 20 >/dev/null 2>&1; then
    PORTAL_ADMIN_SECRET_ARN="$(aws secretsmanager describe-secret --region "$REGION" \
      --secret-id "$portal_admin_secret_name" --query ARN --output text \
      --cli-connect-timeout 5 --cli-read-timeout 20)"
    break
  fi
done

if [[ -n "$SNAPSHOT_IDENTIFIER" ]]; then
  if [[ -z "$DATABASE_SECRET_ARN" ]]; then
    RESTORE_MASTER_SECRET_AFTER_BOOTSTRAP=true
  fi
  if [[ -z "$PORTAL_ADMIN_SECRET_ARN" && "$RESET_ADMINISTRATOR_PASSWORD" != "true" ]]; then
    echo "No se restaurará RDS: falta el secreto del admin original; define RESET_ADMINISTRATOR_ON_RESTORE=true para un reset de acceso único y auditado." >&2
    exit 2
  fi
  if ! aws rds describe-db-snapshots --region "$REGION" \
    --db-snapshot-identifier "$SNAPSHOT_IDENTIFIER" >/dev/null; then
    echo "No se restaurará RDS: no se pudo consultar el snapshot solicitado." >&2
    exit 2
  fi
  SNAPSHOT_STATUS="$(aws rds describe-db-snapshots --region "$REGION" \
    --db-snapshot-identifier "$SNAPSHOT_IDENTIFIER" \
    --query 'DBSnapshots[0].Status' --output text)"
  SNAPSHOT_ENGINE="$(aws rds describe-db-snapshots --region "$REGION" \
    --db-snapshot-identifier "$SNAPSHOT_IDENTIFIER" \
    --query 'DBSnapshots[0].Engine' --output text)"
  SNAPSHOT_ENCRYPTED="$(aws rds describe-db-snapshots --region "$REGION" \
    --db-snapshot-identifier "$SNAPSHOT_IDENTIFIER" \
    --query 'DBSnapshots[0].Encrypted' --output text)"
  if [[ "$SNAPSHOT_STATUS" != "available" || "$SNAPSHOT_ENGINE" != "postgres" || \
    ( "$SNAPSHOT_ENCRYPTED" != "True" && "$SNAPSHOT_ENCRYPTED" != "true" ) ]]; then
    echo "No se restaurará RDS: se requiere un snapshot PostgreSQL cifrado en estado available." >&2
    exit 2
  fi
elif [[ "$RESET_ADMINISTRATOR_PASSWORD" == "true" ]]; then
  echo "RESET_ADMINISTRATOR_ON_RESTORE=true requiere RDS_SNAPSHOT_IDENTIFIER; no se tocará una base vacía o existente." >&2
  exit 2
fi

STACK_LOOKUP_OUTPUT=""
if STACK_LOOKUP_OUTPUT="$(aws cloudformation describe-stacks --region "$REGION" \
  --stack-name "$STACK_NAME" 2>&1)"; then
  echo "El stack $STACK_NAME ya existe. Este flujo solo crea un stack ausente; no modifica ni borra el existente." >&2
  exit 2
elif [[ "$STACK_LOOKUP_OUTPUT" != *"(ValidationError)"* || \
  "$STACK_LOOKUP_OUTPUT" != *"Stack with id $STACK_NAME does not exist"* ]]; then
  echo "No se pudo confirmar que el stack $STACK_NAME esté ausente. Revisa credenciales, permisos y conectividad; la reconstrucción se detiene sin crear recursos." >&2
  exit 2
fi

aws cloudformation validate-template --region "$REGION" --template-body "file://$TEMPLATE" >/dev/null
aws cloudformation validate-template --region "$REGION" \
  --template-body "file://$SCRIPT_DIR/voice-recordings.yaml" >/dev/null

echo "Se creará $STACK_NAME en $REGION con capacidad EC2 temporalmente en cero."
if [[ -n "$SNAPSHOT_IDENTIFIER" ]]; then
  if [[ "$RESTORE_MASTER_SECRET_AFTER_BOOTSTRAP" == "true" ]]; then
    echo "La base se restaurará cifrada y privada en bootstrap; luego CloudFormation activará el secreto maestro administrado por RDS antes de habilitar EC2."
  else
    echo "La base se restaurará desde el snapshot cifrado indicado y usará el secreto maestro existente."
  fi
  if [[ "$RESET_ADMINISTRATOR_PASSWORD" == "true" ]]; then
    echo "El acceso admin se restablecerá una sola vez desde la versión actual del secreto y exigirá cambio al iniciar sesión."
  else
    echo "Se reutilizará el secreto admin retenido; el usuario y la contraseña del snapshot no se modificarán."
  fi
else
  echo "La base se creará vacía; si existe un secreto maestro retenido, se reutilizará."
fi
echo "Para desplegar en el perfil de máxima disponibilidad del laboratorio, define DATABASE_MULTI_AZ=true ENABLE_WAF=true ENABLE_AWS_BACKUP=true."
read -r -p "Escribe REBUILD para continuar: " confirmation
if [[ "$confirmation" != "REBUILD" ]]; then
  echo "Cancelado; no se crearon recursos."
  exit 0
fi

# Create and hash the exact artifact before stack creation so the launch
# template can verify the downloaded bytes before extracting or running code.
LOCAL_ARTIFACT_PATH="$ARTIFACT_PATH" "$SCRIPT_DIR/package_portal_artifact.sh"
ARTIFACT_SHA256="$(sha256sum "$ARTIFACT_PATH" | awk '{print $1}')"
if [[ ! "$ARTIFACT_SHA256" =~ ^[a-f0-9]{64}$ ]]; then
  echo "No se pudo calcular un SHA-256 válido para el artefacto; no se creará el stack." >&2
  exit 2
fi
if [[ -z "$ARTIFACT_KEY" ]]; then
  ARTIFACT_KEY="releases/tangamandapio/portal-b2b-${REVISION}-${ARTIFACT_SHA256}.tar.gz"
elif [[ "$ARTIFACT_KEY" != *"$ARTIFACT_SHA256"* ]]; then
  echo "APPLICATION_ARTIFACT_KEY debe incluir el SHA-256 completo para conservar releases inmutables y permitir rollback." >&2
  exit 2
fi

PARAMETERS=(
  "ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
  "ParameterKey=InstanceType,ParameterValue=${INSTANCE_TYPE:-t3.micro}"
  "ParameterKey=DBInstanceClass,ParameterValue=${DB_INSTANCE_CLASS:-db.t3.micro}"
  "ParameterKey=ApplicationArtifactKey,ParameterValue=$ARTIFACT_KEY"
  "ParameterKey=ApplicationArtifactRevision,ParameterValue=$REVISION"
  "ParameterKey=ApplicationArtifactSha256,ParameterValue=$ARTIFACT_SHA256"
  "ParameterKey=InternalErpEnabled,ParameterValue=true"
  "ParameterKey=AzureFulfillmentUrl,ParameterValue=$FUNCTION_URL"
  "ParameterKey=AzureFunctionKeySecret,ParameterValue=$FUNCTION_KEY_SECRET"
  "ParameterKey=DatabaseMultiAZ,ParameterValue=${DATABASE_MULTI_AZ:-false}"
  "ParameterKey=DatabaseBackupRetentionDays,ParameterValue=${DATABASE_BACKUP_RETENTION_DAYS:-1}"
  "ParameterKey=ManageDatabaseMasterPassword,ParameterValue=false"
  "ParameterKey=ResetAdministratorPassword,ParameterValue=$RESET_ADMINISTRATOR_PASSWORD"
  "ParameterKey=EnableWaf,ParameterValue=${ENABLE_WAF:-false}"
  "ParameterKey=ManageWafAssociation,ParameterValue=true"
  "ParameterKey=EnableAwsBackup,ParameterValue=${ENABLE_AWS_BACKUP:-false}"
  "ParameterKey=BootstrapMode,ParameterValue=true"
)
if [[ -n "$DATABASE_SECRET_ARN" ]]; then
  PARAMETERS+=("ParameterKey=ExistingDatabaseSecretArn,ParameterValue=$DATABASE_SECRET_ARN")
fi
if [[ -n "$PORTAL_ADMIN_SECRET_ARN" ]]; then
  PARAMETERS+=("ParameterKey=ExistingPortalAdminSecretArn,ParameterValue=$PORTAL_ADMIN_SECRET_ARN")
fi
if [[ -n "$SNAPSHOT_IDENTIFIER" ]]; then
  PARAMETERS+=("ParameterKey=DatabaseSnapshotIdentifier,ParameterValue=$SNAPSHOT_IDENTIFIER")
fi

aws cloudformation create-stack \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --template-body "file://$TEMPLATE" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameters "${PARAMETERS[@]}" >/dev/null
aws cloudformation wait stack-create-complete --region "$REGION" --stack-name "$STACK_NAME"

# The recordings bucket is a separate stack. Create it only after the portal
# stack has restored its IAM role, which the bucket policy references.
VOICE_STACK="${VOICE_STACK_NAME:-tangamandapio-voice-recordings}"
if aws cloudformation describe-stacks --region "$REGION" --stack-name "$VOICE_STACK" >/dev/null 2>&1; then
  VOICE_STATUS="$(aws cloudformation describe-stacks \
    --region "$REGION" --stack-name "$VOICE_STACK" \
    --query 'Stacks[0].StackStatus' --output text)"
  if [[ "$VOICE_STATUS" != "CREATE_COMPLETE" && "$VOICE_STATUS" != "UPDATE_COMPLETE" ]]; then
    echo "El stack de grabaciones existe pero no está estable ($VOICE_STATUS); el portal queda en bootstrap (cero EC2)." >&2
    exit 2
  fi
else
  aws cloudformation create-stack \
    --region "$REGION" \
    --stack-name "$VOICE_STACK" \
    --template-body "file://$SCRIPT_DIR/voice-recordings.yaml" \
    --parameters \
      ParameterKey=ProjectName,ParameterValue=tangamandapio \
      ParameterKey=ApplicationRoleName,ParameterValue=LabRole >/dev/null
  aws cloudformation wait stack-create-complete --region "$REGION" --stack-name "$VOICE_STACK"
fi

ASSET_BUCKET="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='AssetBucketName'].OutputValue" \
  --output text)"
if [[ -z "$ASSET_BUCKET" || "$ASSET_BUCKET" == "None" ]]; then
  echo "El stack no devolvió el bucket de artefactos; se conserva el stack en modo seguro (cero EC2) para diagnóstico." >&2
  exit 2
fi

aws s3 cp "$ARTIFACT_PATH" "s3://$ASSET_BUCKET/$ARTIFACT_KEY" --region "$REGION" --sse AES256
aws s3api head-object --bucket "$ASSET_BUCKET" --key "$ARTIFACT_KEY" --region "$REGION" >/dev/null

# Newly created stacks start with drift status NOT_CHECKED. Record a baseline
# before deploy.sh enforces its IN_SYNC guard for the capacity update.
DRIFT_DETECTION_ID="$(aws cloudformation detect-stack-drift \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query StackDriftDetectionId \
  --output text)"
DRIFT_DETECTION_STATUS="DETECTION_IN_PROGRESS"
for ((attempt = 0; attempt < 36; attempt++)); do
  DRIFT_DETECTION_STATUS="$(aws cloudformation describe-stack-drift-detection-status \
    --region "$REGION" \
    --stack-drift-detection-id "$DRIFT_DETECTION_ID" \
    --query DetectionStatus \
    --output text)"
  [[ "$DRIFT_DETECTION_STATUS" == "DETECTION_COMPLETE" ]] && break
  if [[ "$DRIFT_DETECTION_STATUS" == "DETECTION_FAILED" ]]; then
    echo "La detección de drift falló; el stack se conserva en bootstrap (cero EC2)." >&2
    exit 2
  fi
  sleep 5
done
if [[ "$DRIFT_DETECTION_STATUS" != "DETECTION_COMPLETE" ]]; then
  echo "La detección de drift excedió el tiempo límite; el stack se conserva en bootstrap (cero EC2)." >&2
  exit 2
fi
DRIFT_STATUS="$(aws cloudformation describe-stack-drift-detection-status \
  --region "$REGION" \
  --stack-drift-detection-id "$DRIFT_DETECTION_ID" \
  --query StackDriftStatus \
  --output text)"
if [[ "$DRIFT_STATUS" != "IN_SYNC" ]]; then
  echo "El stack recién creado no está en sync ($DRIFT_STATUS); se conserva en bootstrap (cero EC2)." >&2
  exit 2
fi

if [[ "$RESTORE_MASTER_SECRET_AFTER_BOOTSTRAP" == "true" ]]; then
  echo "Activando el secreto maestro administrado por RDS con una actualización de CloudFormation; el Auto Scaling Group permanece en cero."
  printf 'APPLY\n' | env \
    STACK_NAME="$STACK_NAME" \
    AWS_REGION="$REGION" \
    APPLY_CHANGE_SET=true \
    CONFIRM_STACK_NAME="$STACK_NAME" \
    BOOTSTRAP_MODE=true \
    MANAGE_DATABASE_MASTER_PASSWORD=true \
    "$SCRIPT_DIR/deploy.sh" "$TEMPLATE"

  POST_UPDATE_DRIFT_ID="$(aws cloudformation detect-stack-drift \
    --region "$REGION" --stack-name "$STACK_NAME" \
    --query StackDriftDetectionId --output text)"
  POST_UPDATE_DRIFT_STATUS="DETECTION_IN_PROGRESS"
  for ((attempt = 0; attempt < 36; attempt++)); do
    POST_UPDATE_DRIFT_STATUS="$(aws cloudformation describe-stack-drift-detection-status \
      --region "$REGION" --stack-drift-detection-id "$POST_UPDATE_DRIFT_ID" \
      --query DetectionStatus --output text)"
    [[ "$POST_UPDATE_DRIFT_STATUS" == "DETECTION_COMPLETE" ]] && break
    if [[ "$POST_UPDATE_DRIFT_STATUS" == "DETECTION_FAILED" ]]; then
      echo "La verificación posterior a habilitar el secreto falló; el portal sigue aislado en bootstrap." >&2
      exit 2
    fi
    sleep 5
  done
  if [[ "$POST_UPDATE_DRIFT_STATUS" != "DETECTION_COMPLETE" ]]; then
    echo "La verificación posterior excedió el tiempo límite; el portal sigue aislado en bootstrap." >&2
    exit 2
  fi
  POST_UPDATE_DRIFT="$(aws cloudformation describe-stack-drift-detection-status \
    --region "$REGION" --stack-drift-detection-id "$POST_UPDATE_DRIFT_ID" \
    --query StackDriftStatus --output text)"
  if [[ "$POST_UPDATE_DRIFT" != "IN_SYNC" ]]; then
    echo "La plantilla no refleja todavía el secreto administrado por RDS ($POST_UPDATE_DRIFT); no se habilitarán instancias." >&2
    exit 2
  fi
  DATABASE_SECRET_ARN="$(aws cloudformation describe-stacks \
    --region "$REGION" --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" \
    --output text)"
  if [[ -z "$DATABASE_SECRET_ARN" || "$DATABASE_SECRET_ARN" == "None" ]]; then
    echo "RDS no devolvió el ARN del secreto administrado; el portal permanece en bootstrap." >&2
    exit 2
  fi
fi

printf 'APPLY\n' | env \
  STACK_NAME="$STACK_NAME" \
  AWS_REGION="$REGION" \
  APPLY_CHANGE_SET=true \
  CONFIRM_STACK_NAME="$STACK_NAME" \
  BOOTSTRAP_MODE=false \
  DATABASE_SECRET_ARN="${DATABASE_SECRET_ARN:-}" \
  MANAGE_DATABASE_MASTER_PASSWORD="$([[ "$RESTORE_MASTER_SECRET_AFTER_BOOTSTRAP" == "true" ]] && echo true || echo false)" \
  APPLICATION_ARTIFACT_KEY="$ARTIFACT_KEY" \
  APPLICATION_ARTIFACT_REVISION="$REVISION" \
  "$SCRIPT_DIR/deploy.sh" "$TEMPLATE"

DNS_NAME="$(aws cloudformation describe-stacks \
  --region "$REGION" --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
  --output text)"
echo "Stack actualizado. Verificación final pendiente: http://$DNS_NAME/health"
