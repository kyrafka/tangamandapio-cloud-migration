#!/usr/bin/env bash
set -euo pipefail

# This script runs only on the two private router instances. It reads the
# single-use key from Secrets Manager, never from user data or command output.
if [[ $# -lt 4 ]]; then
  echo "Uso: $0 <role> <region> <auth-secret-name> <router-hostname> [route-table-id primary-eni primary-private-ip backup-eni sns-topic-arn]" >&2
  exit 2
fi

ROUTER_ROLE="$1"
AWS_REGION="$2"
AUTH_SECRET_NAME="$3"
ROUTER_HOSTNAME="$4"
WMS_PRIVATE_IP="10.20.1.4"
WMS_HOSTNAME="tangama-flex-261104.azurewebsites.net"

[[ "$ROUTER_ROLE" == primary || "$ROUTER_ROLE" == backup ]] || { echo 'Rol de router inválido.' >&2; exit 2; }
[[ "$AWS_REGION" =~ ^us-[a-z]+-[0-9]+$ ]] || { echo 'Región inválida.' >&2; exit 2; }
[[ "$AUTH_SECRET_NAME" =~ ^tangamandapio/tailscale/aws-(pilot|backup)$ ]] || { echo 'Nombre de secreto no autorizado.' >&2; exit 2; }
[[ "$ROUTER_HOSTNAME" =~ ^tangamandapio-aws-(pilot|backup)$ ]] || { echo 'Nombre de host inválido.' >&2; exit 2; }
if [[ "$ROUTER_ROLE" == primary ]]; then
  [[ $# -eq 4 ]] || { echo 'El router principal acepta solo cuatro parámetros.' >&2; exit 2; }
  ROUTE_TABLE_ID=""
  PRIMARY_ENI=""
  PRIMARY_PRIVATE_IP=""
  BACKUP_ENI=""
  SNS_TOPIC_ARN=""
else
  [[ $# -eq 8 ]] || { echo 'El router de respaldo requiere cuatro parámetros adicionales.' >&2; exit 2; }
  ROUTE_TABLE_ID="$5"
  PRIMARY_ENI="$6"
  PRIMARY_PRIVATE_IP="$7"
  SNS_TOPIC_ARN="$8"
  BACKUP_ENI=""
  [[ "$ROUTE_TABLE_ID" =~ ^rtb-[0-9a-f]{8,17}$ ]] || { echo 'Tabla de rutas inválida.' >&2; exit 2; }
  [[ "$PRIMARY_ENI" =~ ^eni-[0-9a-f]{8,17}$ ]] || { echo 'Interfaz de router principal inválida.' >&2; exit 2; }
  [[ "$PRIMARY_PRIVATE_IP" =~ ^10\.10\.(10|11)\.[0-9]{1,3}$ ]] || { echo 'IP privada del router principal inválida.' >&2; exit 2; }
  [[ "$SNS_TOPIC_ARN" =~ ^arn:aws:sns:us-east-2:[0-9]{12}:tangamandapio-alarms$ ]] || { echo 'Tema SNS inválido.' >&2; exit 2; }
fi

dnf install -y python3 tar iptables
if ! command -v curl >/dev/null 2>&1; then
  dnf install -y curl
fi
if ! command -v aws >/dev/null 2>&1; then
  dnf install -y awscli-2
fi

install -d -m 0755 /opt/tangamandapio-router
install -d -m 0700 /run/tangamandapio
install -d -m 0700 /var/lib/tangamandapio/route-ha

INSTALLER="$(mktemp /run/tangamandapio/tailscale-install.XXXXXX)"
curl -fsSL --retry 3 --connect-timeout 5 https://tailscale.com/install.sh -o "$INSTALLER"
chmod 0700 "$INSTALLER"
bash "$INSTALLER"
rm -f "$INSTALLER"
systemctl enable --now tailscaled

umask 077
trap 'rm -f /run/tangamandapio/auth-key' EXIT
aws secretsmanager get-secret-value \
  --region "$AWS_REGION" \
  --secret-id "$AUTH_SECRET_NAME" \
  --query SecretString \
  --output text > /run/tangamandapio/auth-key
chmod 0600 /run/tangamandapio/auth-key
grep -Eq '^tskey-auth-[A-Za-z0-9_-]{20,}$' /run/tangamandapio/auth-key || {
  rm -f /run/tangamandapio/auth-key
  echo 'El valor almacenado no tiene formato de clave de alta Tailscale.' >&2
  exit 2
}

tailscale up \
  --auth-key=file:/run/tangamandapio/auth-key \
  --hostname="$ROUTER_HOSTNAME" \
  --advertise-tags=tag:tangama-aws-router \
  --accept-routes=true
rm -f /run/tangamandapio/auth-key
trap - EXIT
umask 022

install -m 0755 /opt/tangamandapio-router/tailscale_router_health.py /usr/local/sbin/tangamandapio-router-health.py
install -m 0755 /opt/tangamandapio-router/tailscale_nat.py /usr/local/sbin/tangamandapio-router-nat.py
install -m 0755 /opt/tangamandapio-router/tailscale_ha_controller.py /usr/local/sbin/tangamandapio-route-ha.py

printf 'net.ipv4.ip_forward=1\n' > /etc/sysctl.d/99-tangamandapio-router.conf
sysctl --system >/dev/null

python3 /usr/local/sbin/tangamandapio-router-nat.py \
  --source 10.10.10.0/23 \
  --destination "$WMS_PRIVATE_IP" > /etc/systemd/system/tangamandapio-wms-nat.service

cat > /etc/systemd/system/tangamandapio-router-health.service <<EOF
[Unit]
Description=Salud privada del router Tangamandapio
After=network-online.target tailscaled.service tangamandapio-wms-nat.service
Wants=network-online.target
[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /usr/local/sbin/tangamandapio-router-health.py --bind 0.0.0.0 --port 9797 --wms-private-ip $WMS_PRIVATE_IP --wms-hostname $WMS_HOSTNAME
Restart=always
RestartSec=1
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/run
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now tangamandapio-wms-nat.service
systemctl enable --now tangamandapio-router-health.service

if [[ "$ROUTER_ROLE" == backup ]]; then
  dnf install -y python3.11 python3.11-pip
  /usr/bin/python3.11 -m venv /opt/tangamandapio-router/ha-venv
  /opt/tangamandapio-router/ha-venv/bin/python -m pip install --disable-pip-version-check 'botocore==1.44.0'
  IMDS_TOKEN="$(curl -fsS --max-time 2 -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)"
  IMDS_MAC="$(curl -fsS --max-time 2 -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/network/interfaces/macs/ | head -n1 | tr -d '/')"
  BACKUP_ENI="$(curl -fsS --max-time 2 -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" "http://169.254.169.254/latest/meta-data/network/interfaces/macs/$IMDS_MAC/interface-id")"
  unset IMDS_TOKEN
  [[ "$BACKUP_ENI" =~ ^eni-[0-9a-f]{8,17}$ && "$BACKUP_ENI" != "$PRIMARY_ENI" ]] || { echo 'No se pudo validar la interfaz de respaldo.' >&2; exit 2; }
  cat > /etc/systemd/system/tangamandapio-route-ha.service <<EOF
[Unit]
Description=Conmutación comprobada de la ruta privada WMS
After=network-online.target tailscaled.service tangamandapio-router-health.service
Wants=network-online.target
[Service]
Type=simple
User=root
ExecStart=/opt/tangamandapio-router/ha-venv/bin/python /usr/local/sbin/tangamandapio-route-ha.py --region $AWS_REGION --route-table-id $ROUTE_TABLE_ID --destination $WMS_PRIVATE_IP/32 --primary-eni $PRIMARY_ENI --backup-eni $BACKUP_ENI --primary-private-ip $PRIMARY_PRIVATE_IP --hostname $WMS_HOSTNAME --sns-topic-arn $SNS_TOPIC_ARN --state-file /var/lib/tangamandapio/route-ha/state.json --interval 0.3
Environment=AWS_METADATA_SERVICE_TIMEOUT=2 AWS_METADATA_SERVICE_NUM_ATTEMPTS=2
Restart=always
RestartSec=1
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/tangamandapio/route-ha
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now tangamandapio-route-ha.service
fi

systemctl is-active --quiet tailscaled
systemctl is-active --quiet tangamandapio-router-health.service
if [[ "$ROUTER_ROLE" == backup ]]; then
  systemctl is-active --quiet tangamandapio-route-ha.service
fi
echo "Router $ROUTER_ROLE instalado; la clave se retiró del directorio temporal."
