#!/usr/bin/env bash
# Create the private WMS DNS stack only when no identical zone already serves
# the target VPC. Existing manually-created zones require a reviewed migration.
set -euo pipefail
MODE="${1:-}"
[[ "$MODE" == "--apply" || "$MODE" == "--ensure" ]] || { echo 'Uso: configurar variables y ejecutar --apply o --ensure.' >&2; exit 2; }
for name in EXPECTED_AWS_ACCOUNT_ID AWS_REGION VPC_ID WMS_HOSTNAME WMS_PRIVATE_IP; do
  [[ -n "${!name:-}" ]] || { echo "Falta $name." >&2; exit 2; }
done
[[ "$EXPECTED_AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || { echo 'Cuenta AWS inválida.' >&2; exit 2; }
[[ "$VPC_ID" =~ ^vpc-[0-9a-f]+$ ]] || { echo 'VPC inválida.' >&2; exit 2; }
[[ "$AWS_REGION" =~ ^[a-z0-9-]+$ ]] || { echo 'Región inválida.' >&2; exit 2; }
[[ "$WMS_HOSTNAME" =~ ^[a-z0-9][a-z0-9-]*\.azurewebsites\.net$ ]] || { echo 'Nombre WMS inválido.' >&2; exit 2; }
PYTHON_BIN="${TANGAMA_PYTHON:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo 'No se encuentra TANGAMA_PYTHON/python3.' >&2; exit 2; }
"$PYTHON_BIN" -c 'import ipaddress,sys; x=ipaddress.ip_address(sys.argv[1]); sys.exit(0 if x.version == 4 and x.is_private else 2)' "$WMS_PRIVATE_IP" || {
  echo 'La dirección WMS debe ser IPv4 privada.' >&2; exit 2;
}
if [[ -n "${AWS_CLI:-}" ]]; then
  aws_cli() { "$AWS_CLI" "$@" | tr -d '\r'; }
else
  aws_cli() { command aws "$@" | tr -d '\r'; }
fi
ACCOUNT="$(aws_cli sts get-caller-identity --region "$AWS_REGION" --query Account --output text)"
[[ "$ACCOUNT" == "$EXPECTED_AWS_ACCOUNT_ID" ]] || { echo 'La cuenta AWS no coincide.' >&2; exit 2; }
STACK_NAME="${PRIVATE_DNS_STACK_NAME:-tangamandapio-private-wms-dns}"
[[ "$STACK_NAME" =~ ^tangamandapio-[a-z0-9-]+$ ]] || { echo 'Nombre de stack inválido.' >&2; exit 2; }
# Never create a duplicate private zone for a VPC or silently adopt the live one.
ZONE_IDS="$(aws_cli route53 list-hosted-zones-by-name --dns-name "$WMS_HOSTNAME" \
  --query "HostedZones[?Name=='$WMS_HOSTNAME.' && Config.PrivateZone==\`true\`].Id" --output text)"
matched_zone=''
for zone_id in $ZONE_IDS; do
  [[ "$zone_id" != 'None' ]] || continue
  associated="$(aws_cli route53 get-hosted-zone --id "$zone_id" \
    --query "length(VPCs[?VPCId=='$VPC_ID' && VPCRegion=='$AWS_REGION'])" --output text)"
  if [[ "$associated" != 0 ]]; then
    [[ -z "$matched_zone" ]] || { echo 'Más de una zona privada coincide; revisión manual requerida.' >&2; exit 2; }
    matched_zone="$zone_id"
  fi
done
if [[ -n "$matched_zone" ]]; then
  [[ "$MODE" == '--ensure' ]] || { echo 'Ya existe una zona privada para este nombre y VPC; revisa su migración antes de desplegar.' >&2; exit 2; }
  records="$(aws_cli route53 list-resource-record-sets --hosted-zone-id "$matched_zone" \
    --query "ResourceRecordSets[?Name=='$WMS_HOSTNAME.' && Type=='A']" --output json)" || {
      echo 'No se pudo verificar el registro privado.' >&2; exit 2;
    }
  printf '%s' "$records" | "$PYTHON_BIN" -c 'import json,sys; r=json.load(sys.stdin); name,ip=sys.argv[1:]; ok=len(r)==1 and r[0].get("Name")==name+"." and r[0].get("Type")=="A" and r[0].get("TTL")==60 and r[0].get("ResourceRecords")==[{"Value":ip}] and not any(k in r[0] for k in ("SetIdentifier","Weight","Region","Failover","GeoLocation","MultiValueAnswer","HealthCheckId")); sys.exit(0 if ok else 2)' "$WMS_HOSTNAME" "$WMS_PRIVATE_IP" || {
      echo 'El registro privado existente no coincide; no se modificó.' >&2; exit 2;
    }
  echo 'Zona y registro DNS privados existentes verificados; no se modificaron.'
  exit 0
fi
if stack_response="$(aws_cli cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK_NAME" 2>&1)"; then
  echo 'El stack DNS ya existe; revisa sus recursos antes de actualizarlo.' >&2
  exit 2
elif [[ "$stack_response" != *'does not exist'* ]]; then
  echo 'No se pudo verificar si el stack DNS existe; no se aplicarán cambios.' >&2
  exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aws_cli cloudformation deploy --region "$AWS_REGION" --stack-name "$STACK_NAME" \
  --template-file "$SCRIPT_DIR/aws-private-wms-dns.yaml" --no-fail-on-empty-changeset \
  --parameter-overrides "VpcId=$VPC_ID" "WmsHostname=$WMS_HOSTNAME" "WmsPrivateIp=$WMS_PRIVATE_IP"
echo 'Zona DNS privada creada para el WMS; no se modificó DNS público.'
