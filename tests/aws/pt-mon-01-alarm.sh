#!/usr/bin/env bash
set -euo pipefail

if [[ "${DEMO_ALARM_STATE:-}" != "YES" ]]; then
  echo "Cancelado: use DEMO_ALARM_STATE=YES para autorizar el cambio temporal de estado." >&2
  exit 2
fi

STACK_NAME="${1:-tangamandapio-live-20260930}"
REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-tangamandapio}"
ALARM_NAME="${PROJECT_NAME}-high-cpu"

aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value ALARM --state-reason "PT-MON-01 demostracion controlada" --region "$REGION"
STATE="$(aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME" --region "$REGION" --query 'MetricAlarms[0].StateValue' --output text)"
printf '{"test_id":"PT-MON-01","stack":"%s","alarm":"%s","observed_state":"%s","method":"manual-demo-state"}\n' "$STACK_NAME" "$ALARM_NAME" "$STATE"
aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value INSUFFICIENT_DATA --state-reason "Fin de PT-MON-01; retorno al control de metricas" --region "$REGION"
test "$STATE" = "ALARM"
