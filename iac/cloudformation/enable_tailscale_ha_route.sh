#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-2}"
PROFILE="${AWS_PROFILE:-main}"
EXPECTED_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-481056890449}"
APP_STACK_NAME="${APP_STACK_NAME:-tangamandapio-live-20261116}"
ROUTER_STACK_NAME="${ROUTER_STACK_NAME:-tangamandapio-aws-azure-tailscale-ha}"
HOSTNAME="tangama-flex-261104.azurewebsites.net"

export AWS_PROFILE="$PROFILE" AWS_REGION="$REGION"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
[[ "$ACCOUNT_ID" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Cuenta AWS distinta a la esperada; no se modifica ninguna ruta." >&2
  exit 2
}

stack_status="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" \
  --query 'Stacks[0].StackStatus' --output text)"
[[ "$stack_status" == "CREATE_COMPLETE" || "$stack_status" == "UPDATE_COMPLETE" ]] || {
  echo "La pila de routers no está estable: $stack_status" >&2
  exit 2
}

output() {
  aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text
}

PRIMARY="$(output PrimaryRouterInstanceId)"
BACKUP="$(output BackupRouterInstanceId)"
ROUTE_TABLE="$(output ApplicationRouteTableId)"
PRIMARY_ENI="$(aws ec2 describe-instances --region "$REGION" --instance-ids "$PRIMARY" \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' --output text)"
BACKUP_ENI="$(aws ec2 describe-instances --region "$REGION" --instance-ids "$BACKUP" \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' --output text)"

for id in "$PRIMARY" "$BACKUP"; do
  [[ "$id" =~ ^i-[0-9a-f]{8,17}$ ]] || { echo 'ID de router no válido.' >&2; exit 2; }
done
[[ "$ROUTE_TABLE" =~ ^rtb-[0-9a-f]{8,17}$ && "$PRIMARY_ENI" =~ ^eni-[0-9a-f]{8,17}$ && \
   "$BACKUP_ENI" =~ ^eni-[0-9a-f]{8,17}$ && "$PRIMARY_ENI" != "$BACKUP_ENI" ]] || {
  echo 'Tabla o interfaces de router no válidas.' >&2
  exit 2
}

existing_target="$(aws ec2 describe-route-tables --region "$REGION" --route-table-ids "$ROUTE_TABLE" \
  --query "RouteTables[0].Routes[?DestinationCidrBlock=='10.20.1.4/32'].NetworkInterfaceId | [0]" --output text)"
if [[ "$existing_target" != "None" && -n "$existing_target" ]]; then
  echo "Ya hay una ruta a 10.20.1.4/32 ($existing_target); primero concilia su dueño en CloudFormation." >&2
  exit 2
fi

check_router() {
  local instance_id="$1"
  local command_id
  local output_text
  command_id="$(aws ssm send-command --region "$REGION" --instance-ids "$instance_id" \
    --document-name AWS-RunShellScript \
    --parameters 'commands=curl -fsS --connect-timeout 1 --max-time 3 http://127.0.0.1:9797/health' \
    --query 'Command.CommandId' --output text)"
  aws ssm wait command-executed --region "$REGION" --command-id "$command_id" --instance-id "$instance_id"
  output_text="$(aws ssm get-command-invocation --region "$REGION" --command-id "$command_id" \
    --instance-id "$instance_id" --query StandardOutputContent --output text)"
  [[ "$output_text" == *'"ready":true'* ]] || {
    echo "Router $instance_id no confirma Tailscale y acceso privado sano; la ruta no se activa." >&2
    exit 2
  }
}

echo 'Comprobando salud por SSM de los dos routers antes de crear la ruta.'
check_router "$PRIMARY"
check_router "$BACKUP"

parameter_keys="$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$ROUTER_STACK_NAME" \
  --query 'Stacks[0].Parameters[].ParameterKey' --output text | tr -d '\r')"
read -r -a keys <<< "$parameter_keys"
previous_parameters=()
for key in "${keys[@]}"; do
  if [[ "$key" != EnablePrivateWmsRoute ]]; then
    previous_parameters+=("ParameterKey=$key,UsePreviousValue=true")
  fi
done

aws cloudformation update-stack --region "$REGION" --stack-name "$ROUTER_STACK_NAME" \
  --use-previous-template --capabilities CAPABILITY_NAMED_IAM \
  --parameters "${previous_parameters[@]}" ParameterKey=EnablePrivateWmsRoute,ParameterValue=true >/dev/null
aws cloudformation wait stack-update-complete --region "$REGION" --stack-name "$ROUTER_STACK_NAME"

rollback_route() {
  echo 'La comprobación privada desde las EC2 no pasó; desactivando la ruta recién creada.' >&2
  aws cloudformation update-stack --region "$REGION" --stack-name "$ROUTER_STACK_NAME" \
    --use-previous-template --capabilities CAPABILITY_NAMED_IAM \
    --parameters "${previous_parameters[@]}" ParameterKey=EnablePrivateWmsRoute,ParameterValue=false >/dev/null
  aws cloudformation wait stack-update-complete --region "$REGION" --stack-name "$ROUTER_STACK_NAME"
}

APP_INSTANCES_TEXT="$(aws autoscaling describe-auto-scaling-groups --region "$REGION" \
  --auto-scaling-group-names tangamandapio-asg \
  --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId' --output text | tr -d '\r')"
read -r -a APP_INSTANCES <<< "$APP_INSTANCES_TEXT"
if (( ${#APP_INSTANCES[@]} < 2 )); then
  rollback_route
  echo 'El ASG no tiene sus dos EC2 InService; se revirtió la ruta.' >&2
  exit 2
fi

for instance_id in "${APP_INSTANCES[@]}"; do
  if ! command_id="$(aws ssm send-command --region "$REGION" --instance-ids "$instance_id" \
    --document-name AWS-RunShellScript \
    --parameters "commands=curl -fsS --connect-timeout 2 --max-time 8 --retry 5 --retry-all-errors --retry-delay 5 --output /dev/null --write-out private_function_http=%{http_code}_private_ip=%{remote_ip} https://${HOSTNAME}/api/health" \
    --query 'Command.CommandId' --output text)"; then
    rollback_route
    exit 2
  fi
  if ! aws ssm wait command-executed --region "$REGION" --command-id "$command_id" --instance-id "$instance_id"; then
    rollback_route
    echo "La prueba desde $instance_id falló; se revirtió la ruta." >&2
    exit 2
  fi
  if ! result="$(aws ssm get-command-invocation --region "$REGION" --command-id "$command_id" \
    --instance-id "$instance_id" --query StandardOutputContent --output text)" || \
    [[ "$result" != *'private_function_http=200_private_ip=10.20.1.4'* ]]; then
    rollback_route
    echo "La Function privada no devolvió 200 desde $instance_id; se revirtió la ruta." >&2
    exit 2
  fi
  printf '%s: private Function HTTP 200\n' "$instance_id"
done

echo 'Ruta privada activa por CloudFormation; las dos EC2 de aplicación llegaron al Private Endpoint por HTTPS.'
