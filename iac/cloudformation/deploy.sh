#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() {
    local -a args=()
    local arg
    for arg in "$@"; do
      # Git Bash exposes local files as /c/... and WSL as /mnt/c/...; the native
      # Windows AWS CLI expects drive-letter paths for CloudFormation files.
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

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_NAME="${STACK_NAME:-}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="${1:-$SCRIPT_DIR/aws-lab.yaml}"
CHANGE_SET_NAME="${CHANGE_SET_NAME:-tangamandapio-$(date -u +%Y%m%dT%H%M%SZ)}"
APPLY_CHANGE_SET="${APPLY_CHANGE_SET:-false}"
CERTIFICATE_ARN="${CERTIFICATE_ARN:-}"
PORTAL_DOMAIN_NAME="${PORTAL_DOMAIN_NAME:-}"

if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "Despliegue bloqueado: define STACK_NAME explícitamente con el stack del proyecto verificado (tangamandapio-live-YYYYMMDD)." >&2
  exit 2
fi

if [[ ! -f "$TEMPLATE" ]]; then
  echo "No existe la plantilla: $TEMPLATE" >&2
  exit 2
fi

if [[ -n "${APPLICATION_ARTIFACT_KEY:-}" || -n "${APPLICATION_ARTIFACT_REVISION:-}" || -n "${APPLICATION_ARTIFACT_SHA256:-}" ]]; then
  if [[ -z "${APPLICATION_ARTIFACT_KEY:-}" || -z "${APPLICATION_ARTIFACT_REVISION:-}" || -z "${APPLICATION_ARTIFACT_SHA256:-}" ]]; then
    echo "Para publicar un artefacto, define APPLICATION_ARTIFACT_KEY, APPLICATION_ARTIFACT_REVISION y APPLICATION_ARTIFACT_SHA256 juntos." >&2
    exit 2
  fi
  if [[ ! "${APPLICATION_ARTIFACT_SHA256}" =~ ^[a-f0-9]{64}$ ]]; then
    echo "APPLICATION_ARTIFACT_SHA256 debe contener exactamente 64 caracteres hexadecimales en minúscula." >&2
    exit 2
  fi
  if [[ "${APPLICATION_ARTIFACT_KEY}" != *"${APPLICATION_ARTIFACT_SHA256}"* ]]; then
    echo "APPLICATION_ARTIFACT_KEY debe incluir el SHA-256 completo para preservar el release previo y permitir rollback." >&2
    exit 2
  fi
fi

for override_name in DATABASE_MULTI_AZ ENABLE_WAF MANAGE_WAF_ASSOCIATION ENABLE_AWS_BACKUP; do
  override_value="${!override_name:-}"
  if [[ -n "$override_value" && "$override_value" != "true" && "$override_value" != "false" ]]; then
    echo "$override_name solo acepta true o false." >&2
    exit 2
  fi
done

if [[ -n "${WAF_RATE_LIMIT_PER_IP:-}" ]]; then
  if [[ ! "$WAF_RATE_LIMIT_PER_IP" =~ ^[0-9]+$ ]] ||
     (( WAF_RATE_LIMIT_PER_IP < 1000 || WAF_RATE_LIMIT_PER_IP > 2000000000 )); then
    echo "WAF_RATE_LIMIT_PER_IP debe ser un entero entre 1000 y 2000000000." >&2
    exit 2
  fi
fi

if [[ -n "${DATABASE_BACKUP_RETENTION_DAYS:-}" ]]; then
  if [[ ! "$DATABASE_BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] ||
     (( DATABASE_BACKUP_RETENTION_DAYS < 1 || DATABASE_BACKUP_RETENTION_DAYS > 35 )); then
    echo "DATABASE_BACKUP_RETENTION_DAYS debe ser un entero entre 1 y 35." >&2
    exit 2
  fi
fi

STACK_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' \
  --output text)"
if [[ "$STACK_STATUS" != "UPDATE_COMPLETE" &&
      "$STACK_STATUS" != "CREATE_COMPLETE" &&
      "$STACK_STATUS" != "UPDATE_ROLLBACK_COMPLETE" ]]; then
  echo "El stack debe estar estable antes de preparar cambios; estado actual: $STACK_STATUS" >&2
  exit 2
fi

DRIFT_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].DriftInformation.StackDriftStatus' \
  --output text)"
if [[ "$DRIFT_STATUS" != "IN_SYNC" ]]; then
  echo "Despliegue cancelado: primero revisa el drift del stack (estado: $DRIFT_STATUS)." >&2
  exit 2
fi

if [[ -n "$CERTIFICATE_ARN" || -n "$PORTAL_DOMAIN_NAME" ]]; then
  if [[ -z "$CERTIFICATE_ARN" || -z "$PORTAL_DOMAIN_NAME" ]]; then
    echo "HTTPS requiere definir juntos CERTIFICATE_ARN y PORTAL_DOMAIN_NAME." >&2
    exit 2
  fi
  PORTAL_DOMAIN_NAME="${PORTAL_DOMAIN_NAME,,}"
  if [[ ${#PORTAL_DOMAIN_NAME} -gt 253 || ! "$PORTAL_DOMAIN_NAME" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]]; then
    echo "PORTAL_DOMAIN_NAME no parece un nombre DNS público válido." >&2
    exit 2
  fi
  if [[ ! "$CERTIFICATE_ARN" =~ ^arn:aws:acm:[a-z0-9-]+:[0-9]{12}:certificate/[a-f0-9-]{36}$ ]]; then
    echo "CERTIFICATE_ARN no tiene formato ACM válido." >&2
    exit 2
  fi
  CERTIFICATE_REGION="${CERTIFICATE_ARN#arn:aws:acm:}"
  CERTIFICATE_REGION="${CERTIFICATE_REGION%%:*}"
  if [[ "$CERTIFICATE_REGION" != "$REGION" ]]; then
    echo "El certificado ACM debe estar en la región del balanceador ($REGION)." >&2
    exit 2
  fi
  CERTIFICATE_STATUS="$(aws acm describe-certificate \
    --region "$REGION" \
    --certificate-arn "$CERTIFICATE_ARN" \
    --query 'Certificate.Status' \
    --output text)"
  if [[ "$CERTIFICATE_STATUS" != "ISSUED" ]]; then
    echo "El certificado ACM debe estar ISSUED antes de habilitar el listener HTTPS (estado: $CERTIFICATE_STATUS)." >&2
    exit 2
  fi
  CERTIFICATE_NAMES="$(aws acm describe-certificate \
    --region "$REGION" \
    --certificate-arn "$CERTIFICATE_ARN" \
    --query 'Certificate.SubjectAlternativeNames' \
    --output text)"
  CERTIFICATE_COVERS_DOMAIN=false
  for certificate_name in $CERTIFICATE_NAMES; do
    certificate_name="${certificate_name,,}"
    if [[ "$certificate_name" == "$PORTAL_DOMAIN_NAME" ]]; then
      CERTIFICATE_COVERS_DOMAIN=true
      break
    fi
    if [[ "$certificate_name" == \*.* ]]; then
      certificate_suffix="${certificate_name#*.}"
      if [[ "$PORTAL_DOMAIN_NAME" == *".$certificate_suffix" ]]; then
        certificate_prefix="${PORTAL_DOMAIN_NAME%.$certificate_suffix}"
        if [[ -n "$certificate_prefix" && "$certificate_prefix" != *.* ]]; then
          CERTIFICATE_COVERS_DOMAIN=true
          break
        fi
      fi
    fi
  done
  if [[ "$CERTIFICATE_COVERS_DOMAIN" != "true" ]]; then
    echo "El certificado ACM no cubre PORTAL_DOMAIN_NAME; no se preparará HTTPS." >&2
    exit 2
  fi
fi

aws cloudformation validate-template \
  --region "$REGION" \
  --template-body "file://$TEMPLATE" >/dev/null

# Preserve every current parameter, including NoEcho values that AWS will not
# return in clear text. Only explicitly supplied deployment controls are changed.
PARAMETER_KEYS="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Parameters[].ParameterKey' \
  --output text)"
if [[ -z "$PARAMETER_KEYS" || "$PARAMETER_KEYS" == "None" ]]; then
  echo "No se pudieron leer los parámetros actuales del stack." >&2
  exit 2
fi

PARAMETERS=()
for key in $PARAMETER_KEYS; do
  case "$key" in
    ApplicationArtifactKey)
      if [[ -n "${APPLICATION_ARTIFACT_KEY:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$APPLICATION_ARTIFACT_KEY")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    ApplicationArtifactRevision)
      if [[ -n "${APPLICATION_ARTIFACT_REVISION:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$APPLICATION_ARTIFACT_REVISION")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    ApplicationArtifactSha256)
      if [[ -n "${APPLICATION_ARTIFACT_SHA256:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$APPLICATION_ARTIFACT_SHA256")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    CertificateArn)
      if [[ -n "$CERTIFICATE_ARN" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$CERTIFICATE_ARN")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    PortalDomainName)
      if [[ -n "$PORTAL_DOMAIN_NAME" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$PORTAL_DOMAIN_NAME")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    BootstrapMode)
      if [[ -n "${BOOTSTRAP_MODE:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$BOOTSTRAP_MODE")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    ExistingDatabaseSecretArn)
      if [[ -n "${DATABASE_SECRET_ARN:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$DATABASE_SECRET_ARN")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    ManageDatabaseMasterPassword)
      if [[ -n "${MANAGE_DATABASE_MASTER_PASSWORD:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$MANAGE_DATABASE_MASTER_PASSWORD")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    AlarmNotificationEmailPrimary)
      if [[ -n "${ALARM_NOTIFICATION_EMAIL_PRIMARY:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$ALARM_NOTIFICATION_EMAIL_PRIMARY")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    AlarmNotificationEmailAlternate)
      if [[ -n "${ALARM_NOTIFICATION_EMAIL_ALTERNATE:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$ALARM_NOTIFICATION_EMAIL_ALTERNATE")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    DatabaseMultiAZ)
      if [[ -n "${DATABASE_MULTI_AZ:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$DATABASE_MULTI_AZ")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    DatabaseBackupRetentionDays)
      if [[ -n "${DATABASE_BACKUP_RETENTION_DAYS:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$DATABASE_BACKUP_RETENTION_DAYS")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    EnableWaf)
      if [[ -n "${ENABLE_WAF:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$ENABLE_WAF")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    ManageWafAssociation)
      if [[ -n "${MANAGE_WAF_ASSOCIATION:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$MANAGE_WAF_ASSOCIATION")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    WafRateLimitPerIp)
      if [[ -n "${WAF_RATE_LIMIT_PER_IP:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$WAF_RATE_LIMIT_PER_IP")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    EnableAwsBackup)
      if [[ -n "${ENABLE_AWS_BACKUP:-}" ]]; then
        PARAMETERS+=("ParameterKey=$key,ParameterValue=$ENABLE_AWS_BACKUP")
      else
        PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true")
      fi
      ;;
    *) PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true") ;;
  esac
done

# When this parameter is introduced by the template update, it is absent from
# DescribeStacks until that update completes. Include it explicitly for a
# first artifact publication instead of silently taking the compatibility default.
if [[ -n "${APPLICATION_ARTIFACT_SHA256:-}" && "$PARAMETER_KEYS" != *ApplicationArtifactSha256* ]]; then
  PARAMETERS+=("ParameterKey=ApplicationArtifactSha256,ParameterValue=$APPLICATION_ARTIFACT_SHA256")
fi
if [[ -n "$PORTAL_DOMAIN_NAME" && "$PARAMETER_KEYS" != *PortalDomainName* ]]; then
  PARAMETERS+=("ParameterKey=PortalDomainName,ParameterValue=$PORTAL_DOMAIN_NAME")
fi
if [[ "$PARAMETER_KEYS" != *WafRateLimitPerIp* ]]; then
  PARAMETERS+=("ParameterKey=WafRateLimitPerIp,ParameterValue=${WAF_RATE_LIMIT_PER_IP:-30000}")
fi

CHANGE_SET_ID="$(aws cloudformation create-change-set \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --change-set-type UPDATE \
  --template-body "file://$TEMPLATE" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameters "${PARAMETERS[@]}" \
  --query Id \
  --output text)"

if ! aws cloudformation wait change-set-create-complete \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_ID"; then
  CHANGE_SET_STATUS="$(aws cloudformation describe-change-set \
    --region "$REGION" \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_ID" \
    --query Status --output text)"
  CHANGE_SET_REASON="$(aws cloudformation describe-change-set \
    --region "$REGION" \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_ID" \
    --query StatusReason --output text)"
  if [[ "$CHANGE_SET_STATUS" == "FAILED" && "$CHANGE_SET_REASON" == *"didn't contain changes"* ]]; then
    echo "Sin cambios: la plantilla ya coincide con el stack y los parámetros se conservaron."
    exit 0
  fi
  echo "No se pudo preparar el change set: $CHANGE_SET_STATUS — $CHANGE_SET_REASON" >&2
  exit 2
fi

echo "Change set preparado (no ejecutado): $CHANGE_SET_NAME"
aws cloudformation describe-change-set \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_ID" \
  --query 'Changes[].ResourceChange.[Action,LogicalResourceId,ResourceType,Replacement]' \
  --output table

if [[ "$APPLY_CHANGE_SET" != "true" ]]; then
  echo "El change set no se ejecutó. Revisa la tabla; para aplicar, repite con APPLY_CHANGE_SET=true y confirma el nombre exacto del stack."
  exit 0
fi

if [[ "${CONFIRM_STACK_NAME:-}" != "$STACK_NAME" ]]; then
  echo "Ejecución bloqueada. Define CONFIRM_STACK_NAME exactamente como STACK_NAME después de revisar el change set." >&2
  exit 2
fi

read -r -p "Escribe APPLY para ejecutar el change set de $STACK_NAME: " confirmation
if [[ "$confirmation" != "APPLY" ]]; then
  echo "Cancelado; el change set permanece sin ejecutar."
  exit 0
fi

aws cloudformation execute-change-set \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_ID"
aws cloudformation wait stack-update-complete --region "$REGION" --stack-name "$STACK_NAME"
aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].{Status:StackStatus,Outputs:Outputs}' \
  --output table
