#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${1:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"
BUCKET="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='AssetBucketName'].OutputValue" --output text)"
KEY="qa/pt-sto-01-${RANDOM}-$(date +%s).txt"
SOURCE_FILE="$(mktemp)"
TARGET_FILE="$(mktemp)"
trap 'rm -f "$SOURCE_FILE" "$TARGET_FILE"; aws s3api delete-object --bucket "$BUCKET" --key "$KEY" --region "$REGION" >/dev/null 2>&1 || true' EXIT

printf 'Tangamandapio PT-STO-01 %s\n' "$(date -u +%FT%TZ)" > "$SOURCE_FILE"
SOURCE_HASH="$(sha256sum "$SOURCE_FILE" | awk '{print $1}')"
aws s3api put-object --bucket "$BUCKET" --key "$KEY" --body "$SOURCE_FILE" --region "$REGION" >/dev/null
aws s3api get-object --bucket "$BUCKET" --key "$KEY" --region "$REGION" "$TARGET_FILE" >/dev/null
TARGET_HASH="$(sha256sum "$TARGET_FILE" | awk '{print $1}')"

test "$SOURCE_HASH" = "$TARGET_HASH"
printf '{"test_id":"PT-STO-01","status":"APROBADA","bucket":"%s","sha256":"%s"}\n' "$BUCKET" "$SOURCE_HASH"
