#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"

STATUS="$(aws cloudformation describe-stacks --region "$REGION" --no-cli-pager --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)"
test "$STATUS" = 'CREATE_COMPLETE'

ALB_DNS="$(aws cloudformation describe-stacks --region "$REGION" --no-cli-pager --stack-name "$STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" --output text)"
TARGET_ARN="$(aws cloudformation describe-stack-resources --region "$REGION" --no-cli-pager --stack-name "$STACK_NAME" --logical-resource-id TargetGroup --query 'StackResources[0].PhysicalResourceId' --output text)"

echo '== TARGET HEALTH =='
aws elbv2 describe-target-health \
  --region "$REGION" \
  --no-cli-pager \
  --target-group-arn "$TARGET_ARN" \
  --query 'TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table

echo '== APPLICATION HEALTH =='
curl --fail --silent --show-error "http://${ALB_DNS}/health"
printf '\nVERIFY_OK stack=%s application=http://%s\n' "$STACK_NAME" "$ALB_DNS"

