#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >> "$AWS_CALL_LOG"
case "$*" in
  *"cloudformation describe-stack-resource"*) printf 'tangamandapio-high-cpu\n' ;;
  *"cloudwatch describe-alarms"*)
    if [[ "${MOCK_FAIL_AFTER_ALARM:-false}" == "true" ]] && grep -q -- '--state-value ALARM' "$AWS_CALL_LOG"; then
      exit 9
    fi
    cat "$MOCK_ALARM_STATE_FILE"
    printf '\n'
    ;;
  *"cloudwatch set-alarm-state"*)
    state=''
    previous=''
    for argument in "$@"; do
      if [[ "$previous" == '--state-value' ]]; then
        state="$argument"
        break
      fi
      previous="$argument"
    done
    if [[ "$state" != 'ALARM' && "$state" != 'OK' && "$state" != 'INSUFFICIENT_DATA' ]]; then
      exit 8
    fi
    printf '%s\n' "$state" > "$MOCK_ALARM_STATE_FILE"
    ;;
  *) printf 'None\n' ;;
esac
