#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() { "$AWS_CLI" "$@"; }
fi

STACK_NAME="${1:-${STACK_NAME:-}}"
if [[ ! "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]]; then
  echo "PT-MON-01 bloqueado: STACK_NAME debe indicar explícitamente el stack verificado (tangamandapio-live-YYYYMMDD)." >&2
  exit 2
fi
if [[ "${DEMO_ALARM_STATE:-}" != "YES" ]]; then
  echo "Cancelado: use DEMO_ALARM_STATE=YES para autorizar el cambio temporal de estado." >&2
  exit 2
fi

REGION="${AWS_REGION:-us-east-1}"
ALARM_NAME="$(aws cloudformation describe-stack-resource --stack-name "$STACK_NAME" \
  --logical-resource-id HighCPUAlarm --region "$REGION" \
  --query 'StackResourceDetail.PhysicalResourceId' --output text)"
if [[ -z "$ALARM_NAME" || "$ALARM_NAME" == "None" ]]; then
  echo "PT-MON-01 bloqueado: el stack no expone HighCPUAlarm." >&2
  exit 2
fi

ORIGINAL_STATE="$(aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME" \
  --region "$REGION" --query 'MetricAlarms[0].StateValue' --output text)"
case "$ORIGINAL_STATE" in
  OK|ALARM|INSUFFICIENT_DATA) ;;
  *) echo "PT-MON-01 bloqueado: estado original no válido ($ORIGINAL_STATE)." >&2; exit 2 ;;
esac

restore_alarm_state() {
  local command_status=$?
  trap - EXIT
  if ! aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" \
    --state-value "$ORIGINAL_STATE" --state-reason "PT-MON-01: restaurar estado previo" \
    --region "$REGION" >/dev/null; then
    echo "PT-MON-01: no se pudo restaurar el estado original $ORIGINAL_STATE de $ALARM_NAME." >&2
    [[ "$command_status" -ne 0 ]] || command_status=1
  fi
  exit "$command_status"
}
trap restore_alarm_state EXIT

aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value ALARM --state-reason "PT-MON-01 demostracion controlada" --region "$REGION"
STATE="$(aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME" --region "$REGION" --query 'MetricAlarms[0].StateValue' --output text)"
printf '{"test_id":"PT-MON-01","stack":"%s","alarm":"%s","observed_state":"%s","method":"manual-demo-state"}\n' "$STACK_NAME" "$ALARM_NAME" "$STATE"
test "$STATE" = "ALARM"
