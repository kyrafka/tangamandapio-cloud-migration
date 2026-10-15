#!/usr/bin/env bash
set -euo pipefail

: "${AWS_CALL_LOG:?AWS_CALL_LOG must point to a temporary call log}"
printf '%s\n' "$*" >>"$AWS_CALL_LOG"

case "$*" in
  *"cloudformation describe-stacks"*"Stacks[0].StackStatus"*)
    printf '%s\n' "${MOCK_STACK_STATUS:-UPDATE_COMPLETE}"
    ;;
  *"cloudformation describe-stacks"*"StackDriftStatus"*)
    printf 'IN_SYNC\n'
    ;;
  *"acm describe-certificate"*"Certificate.Status"*)
    printf '%s\n' "${MOCK_CERT_STATUS:-ISSUED}"
    ;;
  *"acm describe-certificate"*"Certificate.SubjectAlternativeNames"*)
    printf '%s\n' "${MOCK_CERT_NAMES:-portal.example.com}"
    ;;
  *"cloudformation validate-template"*)
    # A sentinel exit proves that valid certificate inputs passed every local
    # HTTPS guard. The test intentionally stops before creating a change set.
    exit "${MOCK_VALIDATE_EXIT:-42}"
    ;;
  *"cloudformation create-change-set"*)
    echo 'UNEXPECTED: preflight test attempted to create a change set' >&2
    exit 91
    ;;
  *)
    echo "UNEXPECTED AWS CLI call: $*" >&2
    exit 92
    ;;
esac
