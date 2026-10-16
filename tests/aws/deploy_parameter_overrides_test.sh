#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tangama-deploy-params.XXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

AWS_MOCK="$SCRIPT_DIR/fixtures/mock_aws_deploy_parameters.sh"
DEPLOY_SCRIPT="$REPOSITORY_ROOT/iac/cloudformation/deploy.sh"
export AWS_CALL_LOG="$TEMP_DIR/aws-calls.log"
STACK_NAME='tangamandapio-live-20261013'

assert_invalid_override_rejected() {
  local name="$1" value="$2" expected="$3"
  local output="$TEMP_DIR/${name}.log" exit_code=0
  : >"$AWS_CALL_LOG"
  set +e
  env AWS_CLI="$AWS_MOCK" STACK_NAME="$STACK_NAME" "$name=$value" \
    bash "$DEPLOY_SCRIPT" >"$output" 2>&1
  exit_code=$?
  set -e
  if [[ "$exit_code" -ne 2 ]] || ! grep -q "$expected" "$output" || [[ -s "$AWS_CALL_LOG" ]]; then
    echo "DEPLOY_PARAMETER_GUARD_FAILED: $name=$value no fue rechazado antes de AWS." >&2
    cat "$output" >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

assert_invalid_override_rejected DATABASE_MULTI_AZ maybe 'solo acepta true o false'
assert_invalid_override_rejected ENABLE_WAF yes 'solo acepta true o false'
assert_invalid_override_rejected DATABASE_BACKUP_RETENTION_DAYS 0 'entero entre 1 y 35'
assert_invalid_override_rejected DATABASE_BACKUP_RETENTION_DAYS 36 'entero entre 1 y 35'
assert_invalid_override_rejected WAF_RATE_LIMIT_PER_IP 999 'entero entre 1000 y 2000000000'
assert_invalid_override_rejected WAF_RATE_LIMIT_PER_IP 2000000001 'entero entre 1000 y 2000000000'

: >"$AWS_CALL_LOG"
env \
  AWS_CLI="$AWS_MOCK" \
  STACK_NAME="$STACK_NAME" \
  DATABASE_MULTI_AZ=true \
  DATABASE_BACKUP_RETENTION_DAYS=7 \
  ENABLE_WAF=true \
  MANAGE_WAF_ASSOCIATION=true \
  WAF_RATE_LIMIT_PER_IP=30000 \
  ENABLE_AWS_BACKUP=false \
  bash "$DEPLOY_SCRIPT" >"$TEMP_DIR/valid.log" 2>&1

for expected in \
  'ParameterKey=DatabaseMultiAZ,ParameterValue=true' \
  'ParameterKey=DatabaseBackupRetentionDays,ParameterValue=7' \
  'ParameterKey=EnableWaf,ParameterValue=true' \
  'ParameterKey=ManageWafAssociation,ParameterValue=true' \
  'ParameterKey=WafRateLimitPerIp,ParameterValue=30000' \
  'ParameterKey=EnableAwsBackup,ParameterValue=false' \
  'ParameterKey=ResetAdministratorPassword,UsePreviousValue=true'; do
  if ! grep -Fq -- "$expected" "$AWS_CALL_LOG"; then
    echo "DEPLOY_PARAMETER_FORWARDING_FAILED: falta $expected en el change set." >&2
    cat "$AWS_CALL_LOG" >&2
    cat "$TEMP_DIR/valid.log" >&2
    exit 1
  fi
done

echo 'DEPLOY_PARAMETER_OVERRIDES=PASSED (mock AWS; no cloud mutation)'
