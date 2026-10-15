#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tangama-certificate-preflight.XXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

AWS_MOCK="$SCRIPT_DIR/fixtures/mock_aws_certificate_preflight.sh"
DEPLOY_SCRIPT="$REPOSITORY_ROOT/iac/cloudformation/deploy.sh"
export AWS_CALL_LOG="$TEMP_DIR/aws-calls.log"
STACK_NAME='tangamandapio-live-20261013'
VALID_CERTIFICATE_ARN='arn:aws:acm:us-east-1:123456789012:certificate/01234567-89ab-cdef-0123-456789abcdef'

run_deploy() {
  local output_path="$TEMP_DIR/output.log"
  local exit_code=0
  : >"$AWS_CALL_LOG"
  set +e
  env \
    AWS_CLI="$AWS_MOCK" \
    AWS_REGION="${TEST_AWS_REGION:-us-east-1}" \
    STACK_NAME="$STACK_NAME" \
    CERTIFICATE_ARN="${TEST_CERTIFICATE_ARN-$VALID_CERTIFICATE_ARN}" \
    PORTAL_DOMAIN_NAME="${TEST_PORTAL_DOMAIN_NAME-portal.example.com}" \
    MOCK_CERT_STATUS="${MOCK_CERT_STATUS:-ISSUED}" \
    MOCK_CERT_NAMES="${MOCK_CERT_NAMES:-portal.example.com}" \
    MOCK_VALIDATE_EXIT=42 \
    bash "$DEPLOY_SCRIPT" >"$output_path" 2>&1
  exit_code=$?
  set -e
  printf '%s\n' "$exit_code"
}

assert_rejected_before_template_validation() {
  local expected_exit="$1"
  local expected_message="$2"
  local exit_code
  exit_code="$(run_deploy)"
  if [[ "$exit_code" -ne "$expected_exit" ]] || ! grep -qi "$expected_message" "$TEMP_DIR/output.log"; then
    echo "CERTIFICATE_PREFLIGHT_FAILED: expected exit $expected_exit and message '$expected_message'." >&2
    cat "$TEMP_DIR/output.log" >&2
    return 1
  fi
  if grep -q 'cloudformation validate-template\|cloudformation create-change-set' "$AWS_CALL_LOG"; then
    echo 'CERTIFICATE_PREFLIGHT_FAILED: rejected input reached template validation or change-set creation.' >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

assert_valid_certificate_reaches_template_validation() {
  local stack_status="${1:-UPDATE_COMPLETE}"
  local exit_code
  export MOCK_STACK_STATUS="$stack_status"
  exit_code="$(run_deploy)"
  if [[ "$exit_code" -ne 42 ]] || ! grep -q 'cloudformation validate-template' "$AWS_CALL_LOG"; then
    echo 'CERTIFICATE_PREFLIGHT_FAILED: valid certificate inputs did not pass the HTTPS guards.' >&2
    cat "$TEMP_DIR/output.log" >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
  if grep -q 'cloudformation create-change-set' "$AWS_CALL_LOG"; then
    echo 'CERTIFICATE_PREFLIGHT_FAILED: the mock run attempted to create a change set.' >&2
    cat "$AWS_CALL_LOG" >&2
    return 1
  fi
}

# The pair is mandatory; no ACM lookup or mutation may follow a partial input.
export TEST_CERTIFICATE_ARN="$VALID_CERTIFICATE_ARN"
export TEST_PORTAL_DOMAIN_NAME=''
unset MOCK_CERT_STATUS MOCK_CERT_NAMES
assert_rejected_before_template_validation 2 'HTTPS requiere definir juntos'

# Reject malformed public DNS names and certificates from another ALB region.
unset TEST_CERTIFICATE_ARN
export TEST_PORTAL_DOMAIN_NAME='portal_bad.example.com'
assert_rejected_before_template_validation 2 'no parece un nombre DNS público válido'
export TEST_PORTAL_DOMAIN_NAME='-portal.example.com'
assert_rejected_before_template_validation 2 'no parece un nombre DNS público válido'
export TEST_PORTAL_DOMAIN_NAME='portal-.example.com'
assert_rejected_before_template_validation 2 'no parece un nombre DNS público válido'
printf -v TEST_PORTAL_DOMAIN_NAME '%064d.example.com' 0
assert_rejected_before_template_validation 2 'no parece un nombre DNS público válido'
unset TEST_PORTAL_DOMAIN_NAME
export TEST_AWS_REGION='us-west-2'
assert_rejected_before_template_validation 2 'debe estar en la región del balanceador'
unset TEST_AWS_REGION

# A pending certificate and an uncovered SAN must fail closed before template validation.
export MOCK_CERT_STATUS='PENDING_VALIDATION'
assert_rejected_before_template_validation 2 'debe estar ISSUED'
unset MOCK_CERT_STATUS
export MOCK_CERT_NAMES='other.example.com'
assert_rejected_before_template_validation 2 'no cubre PORTAL_DOMAIN_NAME'

# A wildcard covers exactly one left-most label, not multiple nested labels.
export MOCK_CERT_NAMES='*.example.com'
export TEST_PORTAL_DOMAIN_NAME='a.b.example.com'
assert_rejected_before_template_validation 2 'no cubre PORTAL_DOMAIN_NAME'

# Exact SAN and a one-level wildcard both pass. Mixed-case hostnames are normalized.
unset MOCK_CERT_NAMES
export TEST_PORTAL_DOMAIN_NAME='Portal.Example.com'
export MOCK_CERT_NAMES='portal.example.com'
assert_valid_certificate_reaches_template_validation

export TEST_PORTAL_DOMAIN_NAME='portal.example.com'
export MOCK_CERT_NAMES='*.example.com'
assert_valid_certificate_reaches_template_validation

# A completed rollback is stable and may accept a guarded update.
assert_valid_certificate_reaches_template_validation 'UPDATE_ROLLBACK_COMPLETE'

echo 'CERTIFICATE_PREFLIGHT=PASSED (mock AWS; no change set or cloud mutation)'
