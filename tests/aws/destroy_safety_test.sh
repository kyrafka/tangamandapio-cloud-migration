#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tangama-destroy-test.XXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

export AWS_CALL_LOG="$TEMP_DIR/aws-calls.log"
set +e
AWS_CLI="$SCRIPT_DIR/fixtures/mock_aws_destroy_unsafe_template.sh" \
  STACK_NAME="tangamandapio-live-20261013" \
  AWS_REGION="us-east-1" \
  CONFIRM_DELETE_DATA="true" \
  CONFIRM_STACK_NAME="tangamandapio-live-20261013" \
  bash "$REPOSITORY_ROOT/iac/cloudformation/destroy.sh" \
  >"$TEMP_DIR/stdout.log" 2>"$TEMP_DIR/stderr.log"
EXIT_CODE=$?
set -e

if [[ "$EXIT_CODE" -ne 2 ]]; then
  echo "DESTROY_SAFETY_FAILED: unsafe deployed template returned exit $EXIT_CODE (expected 2)." >&2
  cat "$TEMP_DIR/stdout.log" "$TEMP_DIR/stderr.log" >&2
  exit 1
fi
if ! grep -q 'template desplegado no demuestra Snapshot/Snapshot/Retain' "$TEMP_DIR/stderr.log"; then
  echo "DESTROY_SAFETY_FAILED: missing fail-closed lifecycle-policy diagnostic." >&2
  cat "$TEMP_DIR/stdout.log" "$TEMP_DIR/stderr.log" >&2
  exit 1
fi
if grep -Eiq 'delete-stack|delete-bucket|delete-secret|delete-parameter|delete-db-snapshot|delete-objects|(^| )rm( |$)|create-db-snapshot' "$AWS_CALL_LOG"; then
  echo "DESTROY_SAFETY_FAILED: the script attempted a destructive call before its recovery-policy guard." >&2
  cat "$AWS_CALL_LOG" >&2
  exit 1
fi

echo "DESTROY_SAFETY=PASSED (unsafe deployed lifecycle policy refused before any mutation)"
