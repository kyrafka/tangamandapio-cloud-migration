#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_EXECUTE_AWS:-}" != "YES" ]]; then
  echo 'Cancelado: este paso crea NAT Gateway, ALB, EC2, RDS y otros recursos facturables. Use CONFIRM_EXECUTE_AWS=YES.' >&2
  exit 2
fi

STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
CHANGE_SET_NAME="${CHANGE_SET_NAME:?Defina CHANGE_SET_NAME con el change set aprobado}"
REGION="${AWS_REGION:-us-east-1}"

aws cloudformation execute-change-set \
  --region "$REGION" \
  --no-cli-pager \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME"

echo "DEPLOYMENT_STARTED stack=${STACK_NAME} region=${REGION}"
echo 'Use verify_platform.sh después de que CloudFormation alcance CREATE_COMPLETE.'

