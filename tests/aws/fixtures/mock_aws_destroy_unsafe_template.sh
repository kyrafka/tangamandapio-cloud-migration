#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >> "$AWS_CALL_LOG"

case "$*" in
  *"cloudformation describe-stacks"*)
    case "${MOCK_STACK_LOOKUP:-default}" in
      missing)
        printf 'An error occurred (ValidationError) when calling the DescribeStacks operation: Stack with id tangamandapio-live-20261014 does not exist\n' >&2
        exit 255
        ;;
      access-denied)
        printf 'An error occurred (AccessDenied) when calling the DescribeStacks operation: not authorized\n' >&2
        exit 255
        ;;
      expired-token)
        printf 'An error occurred (ExpiredToken) when calling the DescribeStacks operation: token expired\n' >&2
        exit 255
        ;;
      network)
        printf 'Could not connect to the endpoint URL\n' >&2
        exit 255
        ;;
      existing)
        printf '{"Stacks":[{"StackName":"tangamandapio-live-20261014","StackStatus":"CREATE_COMPLETE"}]}\n'
        exit 0
        ;;
    esac
    ;;
esac

case "$*" in
  *"StackStatus"*) printf 'UPDATE_COMPLETE\n' ;;
  *"StackDriftStatus"*) printf 'IN_SYNC\n' ;;
  *"TemplateBody.Resources.Database.DeletionPolicy"*) printf 'Delete\n' ;;
  *"TemplateBody.Resources.Database.UpdateReplacePolicy"*) printf 'Delete\n' ;;
  *"TemplateBody.Resources.DBSecret.DeletionPolicy"*) printf 'Delete\n' ;;
  *"TemplateBody.Resources.DBSecret.UpdateReplacePolicy"*) printf 'Delete\n' ;;
  *"TemplateBody.Resources.PortalAdminSecret.DeletionPolicy"*) printf 'Delete\n' ;;
  *"TemplateBody.Resources.PortalAdminSecret.UpdateReplacePolicy"*) printf 'Delete\n' ;;
  *) printf 'None\n' ;;
esac
