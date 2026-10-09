#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACK_NAME="${STACK_NAME:-tangamandapio-live-20261005}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="${1:-$SCRIPT_DIR/aws-lab.yaml}"
CHANGE_SET_NAME="${CHANGE_SET_NAME:-tangamandapio-$(date -u +%Y%m%dT%H%M%SZ)}"
APPLY_CHANGE_SET="${APPLY_CHANGE_SET:-false}"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "No existe la plantilla: $TEMPLATE" >&2
  exit 2
fi

STACK_STATUS="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' \
  --output text)"
if [[ "$STACK_STATUS" != "UPDATE_COMPLETE" && "$STACK_STATUS" != "CREATE_COMPLETE" ]]; then
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

aws cloudformation validate-template \
  --region "$REGION" \
  --template-body "file://$TEMPLATE" >/dev/null

if [[ -n "${APPLICATION_ARTIFACT_KEY:-}" || -n "${APPLICATION_ARTIFACT_REVISION:-}" ]]; then
  if [[ -z "${APPLICATION_ARTIFACT_KEY:-}" || -z "${APPLICATION_ARTIFACT_REVISION:-}" ]]; then
    echo "Para publicar un artefacto, define APPLICATION_ARTIFACT_KEY y APPLICATION_ARTIFACT_REVISION juntos." >&2
    exit 2
  fi
fi

# Preserve every current parameter, including NoEcho values that AWS will not
# return in clear text. Only the optional artifact pair can be changed here.
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
    *) PARAMETERS+=("ParameterKey=$key,UsePreviousValue=true") ;;
  esac
done

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
