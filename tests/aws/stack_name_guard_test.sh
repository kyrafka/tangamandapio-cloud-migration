#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tangama-stack-guard.XXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

AWS_MOCK="$SCRIPT_DIR/fixtures/mock_aws_destroy_unsafe_template.sh"
export AWS_CALL_LOG="$TEMP_DIR/aws-calls.log"

assert_blocked_without_stack() {
  local script_path="$1"
  local script_name="$(basename "$script_path")"
  local supplied_stack="$2"
  local output_path="$TEMP_DIR/output.log"
  local exit_code=0

  : > "$AWS_CALL_LOG"
  set +e
  if [[ "$supplied_stack" == "__UNSET__" ]]; then
    env -u STACK_NAME AWS_CLI="$AWS_MOCK" bash "$script_path" >"$output_path" 2>&1
    exit_code=$?
  else
    env STACK_NAME="$supplied_stack" AWS_CLI="$AWS_MOCK" bash "$script_path" >"$output_path" 2>&1
    exit_code=$?
  fi
  set -e

  if [[ "$exit_code" -ne 2 ]] || ! grep -q 'STACK_NAME.*explícitamente' "$output_path"; then
    echo "STACK_NAME_GUARD_FAILED: $script_name no rechazó el stack ausente/incorrecto." >&2
    cat "$output_path" >&2
    return 1
  fi
  if [[ -s "$AWS_CALL_LOG" ]]; then
    echo "STACK_NAME_GUARD_FAILED: $script_name llamó AWS antes de validar STACK_NAME." >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/deploy.sh" "__UNSET__"
assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/rebuild.sh" "__UNSET__"
assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/destroy.sh" "__UNSET__"

assert_blocked_positional_script() {
  local script_name="$1"
  local supplied_stack="$2"
  local script_path="$REPOSITORY_ROOT/tests/aws/$script_name"
  local output_path="$TEMP_DIR/output.log"
  local exit_code=0

  : > "$AWS_CALL_LOG"
  set +e
  if [[ "$supplied_stack" == "__UNSET__" ]]; then
    env -u STACK_NAME AWS_CLI="$AWS_MOCK" AWS_CALL_LOG="$AWS_CALL_LOG" DEMO_ALARM_STATE=YES \
      bash "$script_path" >"$output_path" 2>&1
    exit_code=$?
  else
    env -u STACK_NAME AWS_CLI="$AWS_MOCK" AWS_CALL_LOG="$AWS_CALL_LOG" DEMO_ALARM_STATE=YES \
      bash "$script_path" "$supplied_stack" >"$output_path" 2>&1
    exit_code=$?
  fi
  set -e

  if [[ "$exit_code" -ne 2 ]] || ! grep -q 'STACK_NAME.*verificado' "$output_path"; then
    echo "STACK_NAME_GUARD_FAILED: $script_name no rechazó el stack ausente/incorrecto." >&2
    cat "$output_path" >&2
    return 1
  fi
  if [[ -s "$AWS_CALL_LOG" ]]; then
    echo "STACK_NAME_GUARD_FAILED: $script_name llamó AWS antes de validar el stack." >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/deploy.sh" "tangamandapio-safety-test"
assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/rebuild.sh" "tangamandapio-safety-test"
assert_blocked_without_stack "${REPOSITORY_ROOT}/iac/cloudformation/destroy.sh" "tangamandapio-safety-test"
for script in pt-sto-01-s3.sh pt-mon-01-alarm.sh; do
  assert_blocked_positional_script "$script" "__UNSET__"
  assert_blocked_positional_script "$script" "tangamandapio-safety-test"
done

assert_rebuild_stack_lookup() {
  local lookup_mode="$1"
  local expected_result="$2"
  local output_path="$TEMP_DIR/rebuild-${lookup_mode}.log"
  local exit_code=0

  : > "$AWS_CALL_LOG"
  set +e
  printf '\n' | env \
    STACK_NAME=tangamandapio-live-20261014 \
    AZURE_FULFILLMENT_URL=https://example.invalid/api/fulfillment \
    AZURE_FUNCTION_KEY_SECRET=demo/function-key \
    AWS_CLI="$AWS_MOCK" \
    AWS_CALL_LOG="$AWS_CALL_LOG" \
    MOCK_STACK_LOOKUP="$lookup_mode" \
    bash "${REPOSITORY_ROOT}/iac/cloudformation/rebuild.sh" >"$output_path" 2>&1
  exit_code=$?
  set -e

  case "$expected_result" in
    absent)
      if [[ "$exit_code" -ne 0 ]] || ! grep -q 'Cancelado; no se crearon recursos' "$output_path"; then
        echo "STACK_LOOKUP_GUARD_FAILED: un stack explícitamente inexistente no llegó a la confirmación manual segura." >&2
        cat "$output_path" >&2
        return 1
      fi
      if ! grep -q 'cloudformation validate-template' "$AWS_CALL_LOG"; then
        echo "STACK_LOOKUP_GUARD_FAILED: no se alcanzó la validación local posterior a confirmar la ausencia." >&2
        cat "$AWS_CALL_LOG" >&2
        return 1
      fi
      ;;
    blocked)
      if [[ "$exit_code" -ne 2 ]] || ! grep -q 'No se pudo confirmar que el stack' "$output_path"; then
        echo "STACK_LOOKUP_GUARD_FAILED: $lookup_mode no detuvo la reconstrucción." >&2
        cat "$output_path" >&2
        return 1
      fi
      if grep -q 'cloudformation validate-template\|cloudformation create-stack' "$AWS_CALL_LOG"; then
        echo "STACK_LOOKUP_GUARD_FAILED: $lookup_mode permitió avanzar luego de fallar la consulta." >&2
        cat "$AWS_CALL_LOG" >&2
        return 1
      fi
      ;;
    exists)
      if [[ "$exit_code" -ne 2 ]] || ! grep -q 'El stack .* ya existe' "$output_path"; then
        echo "STACK_LOOKUP_GUARD_FAILED: un stack existente no detuvo la reconstrucción." >&2
        cat "$output_path" >&2
        return 1
      fi
      if grep -q 'cloudformation validate-template\|cloudformation create-stack' "$AWS_CALL_LOG"; then
        echo "STACK_LOOKUP_GUARD_FAILED: un stack existente permitió avanzar." >&2
        cat "$AWS_CALL_LOG" >&2
        return 1
      fi
      ;;
  esac

  if grep -q 'cloudformation create-stack' "$AWS_CALL_LOG"; then
    echo "STACK_LOOKUP_GUARD_FAILED: la prueba no debe crear recursos." >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

assert_rebuild_stack_lookup missing absent
assert_rebuild_stack_lookup existing exists
for lookup_mode in access-denied expired-token network; do
  assert_rebuild_stack_lookup "$lookup_mode" blocked
done

echo "STACK_NAME_GUARD=PASSED (stack explícito; errores de consulta fail-closed; sin creación AWS)"
