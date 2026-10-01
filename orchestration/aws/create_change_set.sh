#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="${1:-${ROOT_DIR}/iac/cloudformation/aws-lab.yaml}"
STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
CHANGE_SET_NAME="${CHANGE_SET_NAME:-tangamandapio-preflight-$(date +%Y%m%d-%H%M%S)}"
REGION="${AWS_REGION:-us-east-1}"

test -f "$TEMPLATE"

aws cloudformation create-change-set \
  --region "$REGION" \
  --no-cli-pager \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --change-set-type CREATE \
  --template-body "file://${TEMPLATE}" \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=tangamandapio \
    ParameterKey=InstanceType,ParameterValue=t3.micro \
    ParameterKey=DBInstanceClass,ParameterValue=db.t3.micro \
  --tags \
    Key=Project,Value=tangamandapio \
    Key=Environment,Value=demo \
    Key=ManagedBy,Value=cloudformation \
  --query Id \
  --output text

aws cloudformation wait change-set-create-complete \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME"

aws cloudformation describe-change-set \
  --region "$REGION" \
  --no-cli-pager \
  --stack-name "$STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --query 'Changes[].ResourceChange.[Action,ResourceType,LogicalResourceId]' \
  --output table

printf 'CHANGE_SET_READY stack=%s change_set=%s region=%s\n' "$STACK_NAME" "$CHANGE_SET_NAME" "$REGION"

