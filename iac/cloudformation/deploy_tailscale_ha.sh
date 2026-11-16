#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-main}"
EXPECTED_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-481056890449}"
APP_STACK_NAME="${APP_STACK_NAME:-tangamandapio-live-20261116}"
ROUTER_STACK_NAME="${ROUTER_STACK_NAME:-tangamandapio-aws-azure-tailscale-ha}"
BUNDLE="$(mktemp "${TMPDIR:-/tmp}/tangamandapio-router.XXXXXX.tar.gz")"
trap 'rm -f -- "$BUNDLE"' EXIT

export AWS_PROFILE="$PROFILE"
export AWS_REGION="$REGION"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
if [[ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]]; then
  echo "Cuenta AWS distinta a la esperada ($EXPECTED_ACCOUNT_ID): $ACCOUNT_ID" >&2
  exit 2
fi

APP_STATUS="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$APP_STACK_NAME" --query 'Stacks[0].StackStatus' --output text)"
if [[ "$APP_STATUS" != "UPDATE_COMPLETE" && "$APP_STATUS" != "CREATE_COMPLETE" ]]; then
  echo "La pila de aplicación no está estable: $APP_STATUS" >&2
  exit 2
fi
if aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" >/dev/null 2>&1; then
  echo "La pila $ROUTER_STACK_NAME ya existe; no se actualizará a ciegas." >&2
  exit 2
fi

for secret_name in tangamandapio/tailscale/aws-pilot tangamandapio/tailscale/aws-backup; do
  aws secretsmanager describe-secret --region "$REGION" --secret-id "$secret_name" >/dev/null || {
    echo "Falta $secret_name. Créalo en Secrets Manager con la clave de alta Tailscale y vuelve a ejecutar." >&2
    exit 2
  }
  auth_value="$(aws secretsmanager get-secret-value --region "$REGION" --secret-id "$secret_name" \
    --query SecretString --output text)"
  if [[ ! "$auth_value" =~ ^tskey-auth-[A-Za-z0-9_-]{20,}$ ]]; then
    unset auth_value
    echo "El secreto $secret_name no contiene una clave de alta Tailscale válida; no se crearán routers." >&2
    exit 2
  fi
  unset auth_value
done

stack_outputs="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$APP_STACK_NAME" --query 'Stacks[0].Outputs' --output json)"
VPC_ID="$(python3 -c 'import json,sys; x=json.load(sys.stdin); print(next(i["OutputValue"] for i in x if i["OutputKey"]=="VpcId"))' <<<"$stack_outputs")"
APP_ROUTE_TABLE_ID="$(python3 -c 'import json,sys; x=json.load(sys.stdin); print(next(i["OutputValue"] for i in x if i["OutputKey"]=="AppRouteTableId"))' <<<"$stack_outputs")"
ASSET_BUCKET="$(python3 -c 'import json,sys; x=json.load(sys.stdin); print(next(i["OutputValue"] for i in x if i["OutputKey"]=="AssetBucketName"))' <<<"$stack_outputs")"
APP_SUBNET_A="$(aws cloudformation describe-stack-resource --region "$REGION" --stack-name "$APP_STACK_NAME" --logical-resource-id AppSubnetA --query 'StackResourceDetail.PhysicalResourceId' --output text)"
APP_SUBNET_B="$(aws cloudformation describe-stack-resource --region "$REGION" --stack-name "$APP_STACK_NAME" --logical-resource-id AppSubnetB --query 'StackResourceDetail.PhysicalResourceId' --output text)"

if [[ ! "$VPC_ID" =~ ^vpc-[0-9a-f]{8,17}$ || ! "$APP_ROUTE_TABLE_ID" =~ ^rtb-[0-9a-f]{8,17}$ ||
      ! "$APP_SUBNET_A" =~ ^subnet-[0-9a-f]{8,17}$ || ! "$APP_SUBNET_B" =~ ^subnet-[0-9a-f]{8,17}$ ]]; then
  echo "La pila de aplicación no devolvió VPC, subredes o tabla app válidas." >&2
  exit 2
fi

EXISTING_ROUTE="$(aws ec2 describe-route-tables --region "$REGION" --route-table-ids "$APP_ROUTE_TABLE_ID" \
  --query "RouteTables[0].Routes[?DestinationCidrBlock=='10.20.1.4/32'].NetworkInterfaceId | [0]" --output text)"
if [[ "$EXISTING_ROUTE" != "None" && -n "$EXISTING_ROUTE" ]]; then
  echo "Ya existe una ruta 10.20.1.4/32 hacia $EXISTING_ROUTE; revisa el destino antes de crear otra." >&2
  exit 2
fi

tar -czf "$BUNDLE" -C "$REPOSITORY_ROOT/iac/scripts" \
  bootstrap_tailscale_router.sh tailscale_ha_controller.py tailscale_router_health.py tailscale_nat.py
ARTIFACT_SHA256="$(sha256sum "$BUNDLE" | awk '{print $1}')"
ARTIFACT_KEY="releases/tangamandapio/tailscale-ha-${ARTIFACT_SHA256}.tar.gz"
aws s3 cp "$BUNDLE" "s3://$ASSET_BUCKET/$ARTIFACT_KEY" --region "$REGION" --sse AES256 >/dev/null
aws s3api head-object --bucket "$ASSET_BUCKET" --key "$ARTIFACT_KEY" --region "$REGION" >/dev/null

TEMPLATE="$SCRIPT_DIR/aws-azure-tailscale-ha.yaml"
aws cloudformation validate-template --region "$REGION" --template-body "file://$TEMPLATE" >/dev/null
aws cloudformation create-stack \
  --region "$REGION" \
  --stack-name "$ROUTER_STACK_NAME" \
  --template-body "file://$TEMPLATE" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    "ParameterKey=VpcId,ParameterValue=$VPC_ID" \
    "ParameterKey=AppSubnetA,ParameterValue=$APP_SUBNET_A" \
    "ParameterKey=AppSubnetB,ParameterValue=$APP_SUBNET_B" \
    "ParameterKey=AppRouteTableId,ParameterValue=$APP_ROUTE_TABLE_ID" \
    "ParameterKey=AssetBucketName,ParameterValue=$ASSET_BUCKET" \
    "ParameterKey=RouterArtifactKey,ParameterValue=$ARTIFACT_KEY" \
    "ParameterKey=RouterArtifactSha256,ParameterValue=$ARTIFACT_SHA256" \
    "ParameterKey=EnablePrivateWmsRoute,ParameterValue=false" >/dev/null

echo "Creando $ROUTER_STACK_NAME en $REGION; la ruta privada permanece DESACTIVADA."
aws cloudformation wait stack-create-complete --region "$REGION" --stack-name "$ROUTER_STACK_NAME"
aws ec2 wait instance-status-ok --region "$REGION" \
  --instance-ids \
  "$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='PrimaryRouterInstanceId'].OutputValue | [0]" --output text)" \
  "$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" --query "Stacks[0].Outputs[?OutputKey=='BackupRouterInstanceId'].OutputValue | [0]" --output text)"

echo "Routers creados. Verifica que Tailscale los muestre como conectados y que ambas sondas /health den ready=true."
echo "Luego ejecuta enable_tailscale_ha_route.sh para activar la ruta y validar la Function desde las EC2 de aplicación."
