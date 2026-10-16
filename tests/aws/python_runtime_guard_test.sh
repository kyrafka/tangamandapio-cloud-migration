#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
template_path="$repository_root/iac/cloudformation/aws-lab.yaml"

for expected in \
  'dnf install -y python3.12 python3.12-pip' \
  'python3.12 -m venv /opt/tangamandapio/venv' \
  '/opt/tangamandapio/venv/bin/python -m pip install --no-cache-dir --require-hashes -r /opt/tangamandapio/requirements.lock' \
  'ExecStart=/opt/tangamandapio/venv/bin/gunicorn'; do
  if ! grep -Fq "$expected" "$template_path"; then
    echo "La plantilla no configura el runtime Python aislado esperado: $expected" >&2
    exit 1
  fi
done

if ! grep -Fq 'Encrypted: true' "$template_path"; then
  echo 'El volumen raíz EC2 debe permanecer cifrado.' >&2
  exit 1
fi

for expected in \
  'HealthCheckType: ELB' \
  'DefaultInstanceWarmup: 420' \
  'AutoScalingRollingUpdate:' \
  'MinInstancesInService: 2' \
  'MaxBatchSize: 1' \
  'PauseTime: PT7M' \
  "MaxSize: '5'" \
  'LaunchTemplateId: !Ref LaunchTemplate'; do
  if ! grep -Fq "$expected" "$template_path"; then
    echo "La plantilla no protege el reemplazo gradual con capacidad saludable: $expected" >&2
    exit 1
  fi
done

if grep -Fq 'AutoScalingInstanceRefresh:' "$template_path"; then
  echo 'La SCP de AWS Academy deniega StartInstanceRefresh; usar AutoScalingRollingUpdate de CloudFormation.' >&2
  exit 1
fi

if grep -Eq 'dnf install -y python3-pip|pip3 install' "$template_path"; then
  echo 'La plantilla todavía instala el portal sobre el Python del sistema o sin el venv fijado.' >&2
  exit 1
fi

printf 'AWS_RUNTIME=PYTHON_3_12_VENV_HASH_LOCK_APPROVED\n'
