#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf -- "$temp"' EXIT
cat > "$temp/aws" <<'MOCK'
#!/usr/bin/env bash
if [[ "$1 $2" == 'sts get-caller-identity' ]]; then
  printf '654654388734\n'
  exit 0
fi
printf 'mock reached next check\n' >&2
exit 99
MOCK
chmod +x "$temp/aws"
set +e
printf 'DELETE ALL tangamandapio-live-20261103\r\n' | \
  AWS_CLI="$temp/aws" EXPECTED_AWS_ACCOUNT_ID=654654388734 \
  STACK_NAME=tangamandapio-live-20261103 CONFIRM_STACK_NAME=tangamandapio-live-20261103 \
  CONFIRM_DELETE_DATA=true PURGE_PROJECT_RESOURCES=true \
  bash "$root/iac/cloudformation/lifecycle.sh" down >"$temp/out" 2>&1
status=$?
set -e
if [[ $status -ne 99 ]] || ! grep -q 'mock reached next check' "$temp/out"; then
  cat "$temp/out" >&2
  exit 1
fi
echo 'Windows CRLF confirmation accepted; next safety check reached.'
