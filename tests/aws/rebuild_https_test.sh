#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
temp="$(mktemp -d)"
trap 'rm -rf -- "$temp"' EXIT
cat > "$temp/aws" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$AWS_CALL_LOG"
case "$*" in
  *"secretsmanager describe-secret"*"demo/function-key"*) exit 0 ;;
  *"secretsmanager describe-secret"*) exit 255 ;;
  *"acm describe-certificate"*"Certificate.Status"*) printf 'ISSUED\n' ;;
  *"acm describe-certificate"*"Certificate.SubjectAlternativeNames"*) printf '%s\n' "${MOCK_CERT_DOMAIN:-portal.example.com}" ;;
  *"cloudformation describe-stacks"*) printf 'An error occurred (ValidationError) when calling the DescribeStacks operation: Stack with id tangamandapio-live-20261104 does not exist\n' >&2; exit 255 ;;
  *"cloudformation validate-template"*) printf '{}\n' ;;
  *"cloudformation create-stack"*) exit 73 ;;
  *) printf 'Unexpected mocked AWS call\n' >&2; exit 99 ;;
esac
MOCK
chmod +x "$temp/aws"
cert='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789abc'
common=(STACK_NAME=tangamandapio-live-20261104 AZURE_FULFILLMENT_URL=https://example.invalid AZURE_FUNCTION_KEY_SECRET=demo/function-key AWS_CLI="$temp/aws" AWS_CALL_LOG="$temp/aws.log" CERTIFICATE_ARN="$cert")

set +e
env "${common[@]}" PORTAL_DOMAIN_NAME='' bash "$root/iac/cloudformation/rebuild.sh" >"$temp/missing.log" 2>&1
status=$?
set -e
if [[ $status -ne 2 ]] || ! grep -q 'HTTPS requiere definir juntos' "$temp/missing.log"; then
  cat "$temp/missing.log" >&2; exit 1
fi

set +e
env "${common[@]}" PORTAL_DOMAIN_NAME=portal.example.com MOCK_CERT_DOMAIN=other.example.com bash "$root/iac/cloudformation/rebuild.sh" >"$temp/mismatch.log" 2>&1
status=$?
set -e
if [[ $status -ne 2 ]] || ! grep -q 'certificado ACM no cubre' "$temp/mismatch.log"; then
  cat "$temp/mismatch.log" >&2; exit 1
fi

: > "$temp/aws.log"
set +e
printf 'REBUILD\n' | env "${common[@]}" PORTAL_DOMAIN_NAME=portal.example.com ALARM_NOTIFICATION_EMAIL_PRIMARY=first@example.com ALARM_NOTIFICATION_EMAIL_ALTERNATE=second@example.com bash "$root/iac/cloudformation/rebuild.sh" >"$temp/valid.log" 2>&1
status=$?
set -e
if [[ $status -ne 73 ]] || ! grep -q "ParameterKey=CertificateArn,ParameterValue=$cert" "$temp/aws.log" || ! grep -q 'ParameterKey=PortalDomainName,ParameterValue=portal.example.com' "$temp/aws.log" || ! grep -q 'ParameterKey=AlarmNotificationEmailPrimary,ParameterValue=first@example.com' "$temp/aws.log" || ! grep -q 'ParameterKey=AlarmNotificationEmailAlternate,ParameterValue=second@example.com' "$temp/aws.log"; then
  cat "$temp/valid.log" >&2; cat "$temp/aws.log" >&2; exit 1
fi
echo 'HTTPS rebuild validates the certificate and passes certificate, domain and optional alert emails.'
