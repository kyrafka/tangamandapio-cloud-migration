#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="${1:-aws-lab.yaml}"

aws cloudformation validate-template \
  --region "$REGION" \
  --template-body "file://$TEMPLATE" >/dev/null

aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE" \
  --parameter-overrides ProjectName=tangamandapio InstanceType=t3.micro DBInstanceClass=db.t3.micro \
  --tags Project=tangamandapio Environment=demo ManagedBy=cloudformation \
  --no-fail-on-empty-changeset

aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs' \
  --output table

