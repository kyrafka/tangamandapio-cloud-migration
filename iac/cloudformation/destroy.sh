#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"

BUCKET_NAME="$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs[?OutputKey==`AssetBucketName`].OutputValue' \
  --output text 2>/dev/null || true)"

if [[ -n "$BUCKET_NAME" && "$BUCKET_NAME" != "None" ]]; then
  aws s3 rm "s3://$BUCKET_NAME" --recursive || true
  aws s3api delete-objects \
    --bucket "$BUCKET_NAME" \
    --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: Versions[].{Key:Key,VersionId:VersionId},Quiet:true}' --output json)" 2>/dev/null || true
  aws s3api delete-objects \
    --bucket "$BUCKET_NAME" \
    --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId},Quiet:true}' --output json)" 2>/dev/null || true
fi

aws cloudformation delete-stack --region "$REGION" --stack-name "$STACK_NAME"
aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$STACK_NAME"
echo "STACK_DELETED:$STACK_NAME"

