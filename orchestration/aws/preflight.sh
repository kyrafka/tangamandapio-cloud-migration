#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="${1:-${ROOT_DIR}/iac/cloudformation/aws-lab.yaml}"
STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"

test -f "$TEMPLATE"

echo '== TEMPLATE =='
aws cloudformation validate-template \
  --region "$REGION" \
  --no-cli-pager \
  --template-body "file://${TEMPLATE}" \
  --query 'Description' \
  --output text

echo '== STACK =='
aws cloudformation list-stacks \
  --region "$REGION" \
  --no-cli-pager \
  --query "StackSummaries[?StackName=='${STACK_NAME}'].[StackName,StackStatus]" \
  --output table

echo '== RECURSOS ETIQUETADOS =='
aws resourcegroupstaggingapi get-resources \
  --region "$REGION" \
  --no-cli-pager \
  --tag-filters Key=Project,Values=tangamandapio \
  --query 'length(ResourceTagMappingList)' \
  --output text

echo "PREFLIGHT_OK stack=${STACK_NAME} region=${REGION}"

