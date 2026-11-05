#!/usr/bin/env bash
set -euo pipefail

# Guarded lifecycle entry point for the Tangamandapio AWS CloudFormation stack.
# It delegates deployment/deletion to the existing reviewed scripts; it never
# deletes and recreates resources in one unattended operation.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ACTION="${1:-}"
REGION="${AWS_REGION:-us-east-1}"
EXPECTED_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-}"
STACK_NAME="${STACK_NAME:-}"

usage() {
  cat <<'EOF'
Uso:
  EXPECTED_AWS_ACCOUNT_ID=<12 dígitos> STACK_NAME=tangamandapio-live-YYYYMMDD \
    bash iac/cloudformation/lifecycle.sh up|down|dns|vpn-route

up crea un stack ausente usando rebuild.sh; requiere AZURE_FULFILLMENT_URL y
AZURE_FUNCTION_KEY_SECRET (nombre de Secrets Manager, nunca el valor de la clave).
Para HTTPS requiere también CERTIFICATE_ARN y PORTAL_DOMAIN_NAME juntos;
sin ellos el balanceador se crea solo con HTTP.
Los correos SNS son opcionales mediante ALARM_NOTIFICATION_EMAIL_PRIMARY y
ALARM_NOTIFICATION_EMAIL_ALTERNATE y requieren confirmar cada suscripción.
También requiere RDS_SNAPSHOT_IDENTIFIER, salvo aceptación explícita de una base vacía.
ENABLE_PRIVATE_WMS_DNS=true integra la verificación/creación del DNS privado
después de crear la VPC; exige WMS_HOSTNAME y WMS_PRIVATE_IP. Esta opción no
crea ni enrola los routers, las rutas ni el Private Endpoint de Azure.
dns reanuda solo esa etapa si la VPC ya existe, sin reconstruir el portal.
vpn-route verifica la tabla y router del proyecto y crea solo la ruta privada
ausente; requiere ROUTE_TABLE_ID, ROUTER_ENI y WMS_PRIVATE_IP. Nunca reemplaza
una ruta existente que apunte a otro router.
down elimina el stack principal y los stacks conocidos de grabaciones y VPN
mediante destroy.sh. Exige CONFIRM_DELETE_DATA=true, PURGE_PROJECT_RESOURCES=true
y CONFIRM_STACK_NAME idéntico. Purga snapshots y copias AWS Backup, y conserva
Secrets Manager/SSM por defecto. Para purgar credenciales se requieren además
PURGE_PROJECT_SECRETS=true y CONFIRM_PURGE_PROJECT_SECRETS=<el mismo STACK_NAME>.

La cuenta y la región se verifican antes de operar. Los datos se pierden; el ERP
recrea sus maestros sintéticos al arrancar el portal.
EOF
}

fail() {
  printf 'Operación detenida: %s\n' "$1" >&2
  exit 2
}

[[ "$ACTION" == "up" || "$ACTION" == "down" || "$ACTION" == "dns" || "$ACTION" == "vpn-route" ]] || { usage >&2; exit 2; }
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || fail "define EXPECTED_AWS_ACCOUNT_ID con el ID de la cuenta esperada."
[[ "$STACK_NAME" =~ ^tangamandapio-live-[0-9]{8}$ ]] || fail "define STACK_NAME con el nombre exacto del stack Tangamandapio."

if [[ -n "${AWS_CLI:-}" ]]; then
  # The native Windows AWS CLI writes CRLF even when called from Git Bash/WSL.
  # Strip carriage returns so account IDs and status values compare reliably.
  aws_cli() { "$AWS_CLI" "$@" | tr -d '\r'; }
else
  command -v aws >/dev/null 2>&1 || fail "no se encontró AWS CLI."
  aws_cli() { command aws "$@" | tr -d '\r'; }
fi

ACTUAL_ACCOUNT_ID="$(aws_cli sts get-caller-identity --query Account --output text --region "$REGION")" || \
  fail "AWS STS no pudo verificar la sesión; no se tocaron recursos."
[[ "$ACTUAL_ACCOUNT_ID" == "$EXPECTED_ACCOUNT_ID" ]] || \
  fail "la sesión apunta a otra cuenta ($ACTUAL_ACCOUNT_ID); se esperaba $EXPECTED_ACCOUNT_ID."

printf 'Alcance: solo AWS %s; no despliega VPN privada operativa ni región secundaria, no reconstruye Azure y no finaliza AWS Academy. Azure se opera con su lifecycle Terraform independiente.\n' "$REGION"

export AWS_REGION="$REGION"
export STACK_NAME

ensure_private_dns() {
  [[ -n "${WMS_HOSTNAME:-}" && -n "${WMS_PRIVATE_IP:-}" ]] || fail "define WMS_HOSTNAME y WMS_PRIVATE_IP para el DNS privado."
  VPC_ID="$(aws_cli cloudformation describe-stack-resource --region "$REGION" --stack-name "$STACK_NAME" --logical-resource-id VPC --query 'StackResourceDetail.PhysicalResourceId' --output text)" || fail "no se pudo obtener la VPC del stack."
  [[ "$VPC_ID" =~ ^vpc-[0-9a-f]+$ ]] || fail "la VPC devuelta no es válida; no se configuró DNS."
  export VPC_ID WMS_HOSTNAME WMS_PRIVATE_IP EXPECTED_AWS_ACCOUNT_ID
  bash "$SCRIPT_DIR/rebuild-private-wms-dns.sh" --ensure || fail "DNS privado no quedó verificado; no repitas el despliegue a ciegas."
}

case "$ACTION" in
  vpn-route)
    [[ -n "${ROUTE_TABLE_ID:-}" && -n "${ROUTER_ENI:-}" && -n "${WMS_PRIVATE_IP:-}" ]] || fail "define ROUTE_TABLE_ID, ROUTER_ENI y WMS_PRIVATE_IP."
    VPC_ID="$(aws_cli cloudformation describe-stack-resource --region "$REGION" --stack-name "$STACK_NAME" --logical-resource-id VPC --query 'StackResourceDetail.PhysicalResourceId' --output text)" || fail "no se pudo obtener la VPC del stack."
    [[ "$VPC_ID" =~ ^vpc-[0-9a-f]+$ ]] || fail "la VPC devuelta no es válida."
    helper="$SCRIPT_DIR/../scripts/ensure_private_wms_route.py"
    if command -v cygpath >/dev/null 2>&1; then helper="$(cygpath -m "$helper")"; fi
    "${TANGAMA_PYTHON:-python3}" "$helper" --account "$EXPECTED_ACCOUNT_ID" --region "$REGION" --stack "$STACK_NAME" --vpc "$VPC_ID" --table "$ROUTE_TABLE_ID" --eni "$ROUTER_ENI" --destination "$WMS_PRIVATE_IP" --apply
    ;;
  dns)
    ensure_private_dns
    ;;
  up)
    [[ -n "${AZURE_FULFILLMENT_URL:-}" ]] || fail "define AZURE_FULFILLMENT_URL."
    [[ -n "${AZURE_FUNCTION_KEY_SECRET:-}" ]] || fail "define AZURE_FUNCTION_KEY_SECRET con el nombre del secreto, no su valor."
    [[ "${ENABLE_PRIVATE_WMS_DNS:-false}" == true || "${ENABLE_PRIVATE_WMS_DNS:-false}" == false ]] || fail "ENABLE_PRIVATE_WMS_DNS solo acepta true o false."
    if [[ "${ENABLE_PRIVATE_WMS_DNS:-false}" == true ]]; then
      [[ "${WMS_HOSTNAME:-}" =~ ^[a-z0-9][a-z0-9-]*\.azurewebsites\.net$ ]] || fail "define WMS_HOSTNAME con el nombre exacto de la Function."
      [[ "${AZURE_FULFILLMENT_URL%/}" == "https://$WMS_HOSTNAME" ]] || fail "AZURE_FULFILLMENT_URL debe coincidir con WMS_HOSTNAME."
      [[ "${WMS_PRIVATE_IP:-}" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fail "define WMS_PRIVATE_IP como dirección IPv4 privada."
      IFS=. read -r a b c d <<< "$WMS_PRIVATE_IP"
      for octet in "$a" "$b" "$c" "$d"; do
        [[ "$octet" =~ ^(0|[1-9][0-9]{0,2})$ ]] && (( octet <= 255 )) || fail "WMS_PRIVATE_IP no es IPv4 válida."
      done
      (( a == 10 || (a == 172 && b >= 16 && b <= 31) || (a == 192 && b == 168) )) || fail "WMS_PRIVATE_IP debe ser privada."
    fi
    if [[ -z "${RDS_SNAPSHOT_IDENTIFIER:-}" && "${ALLOW_EMPTY_DATABASE:-false}" != "true" ]]; then
      fail "define RDS_SNAPSHOT_IDENTIFIER para restaurar datos o ALLOW_EMPTY_DATABASE=true si aceptas crear una base vacía."
    fi
    printf 'Cuenta AWS verificada: %s (%s). Se crearán recursos facturables en %s.\n' \
      "$ACTUAL_ACCOUNT_ID" "$REGION" "$STACK_NAME"
    if [[ -z "${RDS_SNAPSHOT_IDENTIFIER:-}" ]]; then
      printf 'AVISO: la base nueva quedará vacía.\n'
    fi
    printf 'Escribe CREATE %s para continuar: ' "$STACK_NAME"
    read -r confirmation
    confirmation="${confirmation%$'\r'}"
    [[ "$confirmation" == "CREATE $STACK_NAME" ]] || fail "confirmación incorrecta; no se creó infraestructura."
    bash "$SCRIPT_DIR/rebuild.sh"
    if [[ "${ENABLE_PRIVATE_WMS_DNS:-false}" == true ]]; then
      ensure_private_dns
    fi
    ;;
  down)
    [[ "${CONFIRM_DELETE_DATA:-}" == "true" ]] || fail "define CONFIRM_DELETE_DATA=true solo tras respaldar/revisar los datos."
    [[ "${PURGE_PROJECT_RESOURCES:-}" == "true" ]] || fail "define PURGE_PROJECT_RESOURCES=true porque se borrarán snapshots y backups retenidos."
    [[ "${CONFIRM_STACK_NAME:-}" == "$STACK_NAME" ]] || fail "CONFIRM_STACK_NAME debe coincidir exactamente con STACK_NAME."
    PURGE_PROJECT_SECRETS="${PURGE_PROJECT_SECRETS:-false}"
    [[ "$PURGE_PROJECT_SECRETS" == "true" || "$PURGE_PROJECT_SECRETS" == "false" ]] || fail "PURGE_PROJECT_SECRETS solo acepta true o false."
    if [[ "$PURGE_PROJECT_SECRETS" == "true" && "${CONFIRM_PURGE_PROJECT_SECRETS:-}" != "$STACK_NAME" ]]; then
      fail "para purgar Secrets Manager/SSM, CONFIRM_PURGE_PROJECT_SECRETS debe coincidir exactamente con STACK_NAME."
    fi
    printf 'Cuenta AWS verificada: %s (%s). Se eliminará %s y los stacks conocidos de grabaciones/VPN; sus objetos S3 se borrarán.\n' \
      "$ACTUAL_ACCOUNT_ID" "$REGION" "$STACK_NAME"
    if [[ "$PURGE_PROJECT_SECRETS" == "true" ]]; then
      printf 'Se perderán la base, snapshots, backups y credenciales. Escribe DELETE ALL INCLUDING SECRETS %s: ' "$STACK_NAME"
      read -r confirmation
      confirmation="${confirmation%$'\r'}"
      [[ "$confirmation" == "DELETE ALL INCLUDING SECRETS $STACK_NAME" ]] || fail "confirmación incorrecta; no se eliminó infraestructura."
    else
      printf 'Se borrarán la base, snapshots y backups; Secrets Manager/SSM se conservan. Escribe DELETE ALL %s para continuar: ' "$STACK_NAME"
      read -r confirmation
      confirmation="${confirmation%$'\r'}"
      [[ "$confirmation" == "DELETE ALL $STACK_NAME" ]] || fail "confirmación incorrecta; no se eliminó infraestructura."
    fi
    export PURGE_PROJECT_RESOURCES=true
    export PURGE_PROJECT_SECRETS
    exec bash "$SCRIPT_DIR/destroy.sh"
    ;;
esac
