#!/usr/bin/env bash
# Install the AWS-side monitor on an already enrolled, healthy backup router.
# This does not enroll Tailscale, create network routes, or store credentials.
set -euo pipefail

if [[ "${1:-}" != "--apply" ]]; then
  echo 'Uso: definir la configuración indicada en la guía y ejecutar --apply en el router AWS de respaldo.' >&2
  exit 2
fi
for name in EXPECTED_AWS_ACCOUNT_ID AWS_REGION ROUTE_TABLE_ID WMS_PRIVATE_IP PRIMARY_INSTANCE_ID PRIMARY_ENI BACKUP_ENI WMS_HOSTNAME; do
  if [[ -z "${!name:-}" ]]; then
    echo "Falta la variable obligatoria $name." >&2
    exit 2
  fi
done
if [[ ! "$EXPECTED_AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
  echo 'EXPECTED_AWS_ACCOUNT_ID debe tener 12 dígitos.' >&2
  exit 2
fi
if [[ "${PREFER_SELF:-false}" != true && "${PREFER_SELF:-false}" != false ]]; then
  echo 'PREFER_SELF solo admite true o false.' >&2
  exit 2
fi
if [[ "${INSTALL_SCOPED_NAT:-false}" != true && "${INSTALL_SCOPED_NAT:-false}" != false ]]; then
  echo 'INSTALL_SCOPED_NAT solo admite true o false.' >&2
  exit 2
fi
if [[ "${INSTALL_SCOPED_NAT:-false}" == true && -z "${WMS_SOURCE_CIDR:-}" ]]; then
  echo 'Para instalar NAT, define WMS_SOURCE_CIDR con la subred de aplicación autorizada.' >&2
  exit 2
fi
if [[ "$(id -u)" != 0 ]]; then
  echo 'Ejecuta el instalador con permisos de administrador en el router de respaldo.' >&2
  exit 2
fi
for command in aws python3 curl systemctl flock; do
  command -v "$command" >/dev/null 2>&1 || { echo "Falta $command." >&2; exit 2; }
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTROLLER="$SCRIPT_DIR/tailscale_failover.py"
[[ -f "$CONTROLLER" ]] || { echo 'Falta tailscale_failover.py.' >&2; exit 2; }
ARGS=(--region "$AWS_REGION" --table "$ROUTE_TABLE_ID" --destination "$WMS_PRIVATE_IP/32"
      --primary-instance "$PRIMARY_INSTANCE_ID" --primary-eni "$PRIMARY_ENI"
      --backup-eni "$BACKUP_ENI" --hostname "$WMS_HOSTNAME")
if [[ "${PREFER_SELF:-false}" == true ]]; then ARGS+=(--prefer-self); fi

ACCOUNT="$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)"
[[ "$ACCOUNT" == "$EXPECTED_AWS_ACCOUNT_ID" ]] || { echo 'La cuenta AWS no coincide.' >&2; exit 2; }
TOKEN="$(curl -fsS --max-time 3 -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)"
INSTANCE_ID="$(curl -fsS --max-time 3 -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)"
unset TOKEN
BACKUP_OWNER="$(aws ec2 describe-network-interfaces --region "$AWS_REGION" --network-interface-ids "$BACKUP_ENI" --query 'NetworkInterfaces[0].Attachment.InstanceId' --output text)"
[[ "$INSTANCE_ID" == "$BACKUP_OWNER" && "$INSTANCE_ID" != "$PRIMARY_INSTANCE_ID" ]] || {
  echo 'Este equipo no es el dueño de la interfaz de respaldo.' >&2; exit 2;
}

if [[ "${INSTALL_SCOPED_NAT:-false}" == true ]]; then
  NAT_SCRIPT="$SCRIPT_DIR/tailscale_nat.py"
  [[ -f "$NAT_SCRIPT" ]] || { echo 'Falta tailscale_nat.py; no se instaló NAT.' >&2; exit 2; }
  stack="$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].Tags[?Key=='aws:cloudformation:stack-name'].Value | [0]" --output text)"
  project="$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" --query "Reservations[0].Instances[0].Tags[?Key=='Project'].Value | [0]" --output text)"
  [[ "$project" == Tangamandapio && ( "$stack" == tangamandapio-tailscale-pilot || "$stack" == tangamandapio-tailscale-pilot-b ) ]] || {
    echo 'La instancia no es un router del proyecto verificado; no se instaló NAT.' >&2; exit 2;
  }
  python3 - "$NAT_SCRIPT" "$WMS_SOURCE_CIDR" "$WMS_PRIVATE_IP" <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('tangama_nat', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.install(sys.argv[2], sys.argv[3], Path('/etc/systemd/system/tangamandapio-wms-nat.service'),
               Path('/etc/sysctl.d/99-tangamandapio-wms-forward.conf'))
PY
fi

# This verifies the active route, both WMS health checks, forwarding and the
# scoped NAT rule. It neither changes the route nor installs VPN credentials.
python3 "$CONTROLLER" "${ARGS[@]}" --preflight

install -d -m 0755 /opt/tangamandapio
install -m 0755 "$CONTROLLER" /opt/tangamandapio/tailscale_failover.py.new
mv -f /opt/tangamandapio/tailscale_failover.py.new /opt/tangamandapio/tailscale_failover.py
python3 "$CONTROLLER" "${ARGS[@]}" --render-service > /etc/systemd/system/tangamandapio-route-failover.service.new
mv -f /etc/systemd/system/tangamandapio-route-failover.service.new /etc/systemd/system/tangamandapio-route-failover.service
cat > /etc/systemd/system/tangamandapio-route-failover.timer <<'TIMER'
[Unit]
Description=Check Tangamandapio private WMS route
[Timer]
OnBootSec=45s
OnUnitActiveSec=30s
AccuracySec=1s
Persistent=true
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now tangamandapio-route-failover.timer
systemctl is-active --quiet tangamandapio-route-failover.timer
if [[ "${PREFER_SELF:-false}" == true ]]; then
  echo 'Monitor instalado; retorno preferente tras verificaciones estables.'
else
  echo 'Monitor instalado para tomar la ruta si falla el otro router.'
fi
