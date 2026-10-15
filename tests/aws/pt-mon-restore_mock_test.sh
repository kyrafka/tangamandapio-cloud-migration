#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tangama-alarm-restore.XXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

run_alarm_test() {
  local label="$1"
  local mock_failure="$2"
  local expected_exit="$3"
  local log_path="$TEMP_DIR/$label.calls"
  local state_path="$TEMP_DIR/$label.state"
  local output_path="$TEMP_DIR/$label.output"
  local exit_code=0

  printf 'OK\n' > "$state_path"
  set +e
  AWS_CLI="$SCRIPT_DIR/fixtures/mock_aws_alarm_state.sh" \
    AWS_CALL_LOG="$log_path" MOCK_ALARM_STATE_FILE="$state_path" \
    MOCK_FAIL_AFTER_ALARM="$mock_failure" DEMO_ALARM_STATE=YES \
    bash "$REPOSITORY_ROOT/tests/aws/pt-mon-01-alarm.sh" tangamandapio-live-20261013 \
    >"$output_path" 2>&1
  exit_code=$?
  set -e

  if [[ "$exit_code" -ne "$expected_exit" ]]; then
    echo "PT_MON_RESTORE_FAILED: $label salió con $exit_code (se esperaba $expected_exit)." >&2
    cat "$output_path" >&2
    return 1
  fi
  if [[ "$(tr -d '\r\n' < "$state_path")" != 'OK' ]]; then
    echo "PT_MON_RESTORE_FAILED: $label dejó la alarma en un estado distinto al original." >&2
    cat "$log_path" >&2
    return 1
  fi
  if ! grep -q -- '--state-value ALARM' "$log_path" || ! grep -q -- '--state-value OK' "$log_path"; then
    echo "PT_MON_RESTORE_FAILED: $label no registró tanto el cambio temporal como la restauración." >&2
    cat "$log_path" >&2
    return 1
  fi
}

run_alarm_test success false 0
run_alarm_test failure-after-mutation true 9
echo 'PT_MON_RESTORE=PASSED (restaura el estado original tras éxito y error simulado)'
