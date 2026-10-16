#!/usr/bin/env bash
set -euo pipefail

: "${AWS_CALL_LOG:?AWS_CALL_LOG must point to a temporary call log}"
printf '%s\n' "$*" >>"$AWS_CALL_LOG"

case "$*" in
  *"cloudformation describe-stacks"*"Stacks[0].StackStatus"*) printf 'UPDATE_COMPLETE\n' ;;
  *"cloudformation describe-stacks"*"StackDriftStatus"*) printf 'IN_SYNC\n' ;;
  *"cloudformation describe-stacks"*"ParameterKey"*)
    printf 'DatabaseMultiAZ DatabaseBackupRetentionDays EnableWaf ManageWafAssociation WafRateLimitPerIp EnableAwsBackup ResetAdministratorPassword ApplicationArtifactKey ApplicationArtifactRevision ApplicationArtifactSha256\n'
    ;;
  *"cloudformation validate-template"*) printf '{}\n' ;;
  *"cloudformation create-change-set"*) printf 'arn:aws:cloudformation:us-east-1:123456789012:changeSet:test/abc123\n' ;;
  *"cloudformation wait change-set-create-complete"*) ;;
  *"cloudformation describe-change-set"*) printf '[]\n' ;;
  *)
    echo "UNEXPECTED AWS CLI call: $*" >&2
    exit 92
    ;;
esac
