#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf -- "$temp"' EXIT
cat > "$temp/aws" <<'MOCK'
#!/usr/bin/env bash
case "$*" in
  *"sts get-caller-identity"*) printf '654654388734\n' ;;
  *"describe-stacks"*"tangamandapio-tailscale-pilot"*) printf 'Stack does not exist\n' >&2; exit 1 ;;
  *"describe-stack-resource"*) printf 'vpc-1234\n' ;;
  *"list-hosted-zones-by-vpc"*) printf 'None\n' ;;
  *StackStatus*) printf 'UPDATE_COMPLETE\n' ;;
  *StackDriftStatus*) printf 'IN_SYNC\n' ;;
  *get-template*) printf 'Resources:\n  Database:\n    DeletionPolicy: Delete\n' ;;
  *) printf 'unexpected AWS call\n' >&2; exit 9 ;;
esac
MOCK
chmod +x "$temp/aws"
set +e
AWS_CLI="$temp/aws" EXPECTED_AWS_ACCOUNT_ID=654654388734 STACK_NAME=tangamandapio-live-20261103 \
  CONFIRM_DELETE_DATA=true PURGE_PROJECT_RESOURCES=true \
  CONFIRM_STACK_NAME=tangamandapio-live-20261103 TANGAMA_PYTHON="${TEST_PYTHON:?}" \
  bash "$root/iac/cloudformation/destroy.sh" >"$temp/out" 2>&1
status=$?
set -e
if [[ $status -ne 2 ]] || ! grep -q 'template desplegado no demuestra' "$temp/out"; then
  cat "$temp/out" >&2
  exit 1
fi
echo 'Python override respected; unsafe template refused.'
