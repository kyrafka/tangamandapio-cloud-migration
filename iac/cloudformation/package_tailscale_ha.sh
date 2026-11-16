#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-main}"
EXPECTED_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-481056890449}"
APP_STACK_NAME="${APP_STACK_NAME:-tangamandapio-live-20261116}"
BUNDLE="$(mktemp "${TMPDIR:-/tmp}/tangamandapio-router.XXXXXX.tar.gz")"
trap 'rm -f -- "$BUNDLE"' EXIT

export AWS_PROFILE="$PROFILE" AWS_REGION="$REGION"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
[[ "$ACCOUNT_ID" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Cuenta AWS distinta a la esperada; no se sube ningún artefacto." >&2
  exit 2
}

STACK_STATUS="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$APP_STACK_NAME" \
  --query 'Stacks[0].StackStatus' --output text)"
[[ "$STACK_STATUS" == "UPDATE_COMPLETE" || "$STACK_STATUS" == "CREATE_COMPLETE" ]] || {
  echo "La pila de aplicación no está estable: $STACK_STATUS" >&2
  exit 2
}
ASSET_BUCKET="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$APP_STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='AssetBucketName'].OutputValue | [0]" --output text)"
[[ "$ASSET_BUCKET" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || {
  echo 'No se pudo validar el bucket privado de artefactos.' >&2
  exit 2
}

tar -czf "$BUNDLE" -C "$REPOSITORY_ROOT/iac/scripts" \
  bootstrap_tailscale_router.sh tailscale_ha_controller.py tailscale_router_health.py tailscale_nat.py
ARTIFACT_SHA256="$(sha256sum "$BUNDLE" | awk '{print $1}')"
ARTIFACT_KEY="releases/tangamandapio/tailscale-ha-${ARTIFACT_SHA256}.tar.gz"

EXISTING_SHA="$(aws s3api head-object --bucket "$ASSET_BUCKET" --key "$ARTIFACT_KEY" --region "$REGION" \
  --query 'Metadata.sha256' --output text 2>/dev/null || true)"
if [[ "$EXISTING_SHA" == "None" || -z "$EXISTING_SHA" ]]; then
  aws s3 cp "$BUNDLE" "s3://$ASSET_BUCKET/$ARTIFACT_KEY" --region "$REGION" \
    --sse AES256 --metadata "sha256=$ARTIFACT_SHA256" >/dev/null
elif [[ "$EXISTING_SHA" != "$ARTIFACT_SHA256" ]]; then
  echo 'El objeto content-addressed existe pero su metadato SHA no coincide; no se sobrescribe.' >&2
  exit 2
fi

aws s3api head-object --bucket "$ASSET_BUCKET" --key "$ARTIFACT_KEY" --region "$REGION" \
  --query '{ContentLength:ContentLength,Metadata:Metadata,ServerSideEncryption:ServerSideEncryption}' --output json
printf 'RouterArtifactKey=%s\nRouterArtifactSha256=%s\n' "$ARTIFACT_KEY" "$ARTIFACT_SHA256"
