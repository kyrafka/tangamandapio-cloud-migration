#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
package_script="$repository_root/iac/cloudformation/package_portal_artifact.sh"
test_directory="$(mktemp -d "${TMPDIR:-/tmp}/tangama-artifact-test.XXXXXX")"
artifact_path="$test_directory/portal-test.tar.gz"
second_artifact_path="$test_directory/portal-test-second.tar.gz"

cleanup() {
  rm -rf -- "$test_directory"
}
trap cleanup EXIT

LOCAL_ARTIFACT_PATH="$artifact_path" bash "$package_script" >/dev/null
test -s "$artifact_path"
LOCAL_ARTIFACT_PATH="$second_artifact_path" bash "$package_script" >/dev/null
test -s "$second_artifact_path"

artifact_sha256="$(sha256sum "$artifact_path" | awk '{print $1}')"
second_artifact_sha256="$(sha256sum "$second_artifact_path" | awk '{print $1}')"
[[ "$artifact_sha256" =~ ^[a-f0-9]{64}$ ]]
if [[ "$artifact_sha256" != "$second_artifact_sha256" ]]; then
  echo 'El mismo árbol de release produjo paquetes binariamente distintos.' >&2
  exit 1
fi
printf '%s  %s\n' "$artifact_sha256" "$artifact_path" | sha256sum --check --status

if ! tar -tvzf "$artifact_path" | awk '
  {
    kind = substr($1, 1, 1)
    mode = substr($1, 1, 10)
    if ((kind == "-" && mode != "-rw-r--r--") ||
        (kind == "d" && mode != "drwxr-xr-x")) exit 1
  }
'; then
  echo 'El paquete debe usar permisos normalizados: archivos 0644 y directorios 0755.' >&2
  exit 1
fi

text_paths="$(tar -tzf "$artifact_path" | grep -E '(\.(py|txt|lock|html|css|js|sql|csv|json|svg|xml|map)|/BUILD_REVISION)$')"
while IFS= read -r text_path; do
  if tar -xOzf "$artifact_path" "$text_path" | LC_ALL=C grep -F $'\r' >/dev/null; then
    echo "El archivo de texto del paquete conserva CRLF: $text_path" >&2
    exit 1
  fi
done <<< "$text_paths"

archive_contents="$(tar -tzf "$artifact_path")"
for required_path in \
  app.py \
  erp_service.py \
  requirements.txt \
  requirements.lock \
  BUILD_REVISION \
  static/index.html \
  static/assets/catalogCsv.js \
  static/images/tangamandapio-operations.svg \
  static/templates/inventario_sintetico.csv \
  static/templates/plantilla_catalogo_sintetico.xlsx; do
  if ! grep -Fxq "$required_path" <<<"$archive_contents"; then
    echo "El paquete del portal no contiene: $required_path" >&2
    exit 1
  fi
done

if grep -Eq '^static/audio/sweet-dove-ambient\.mp3$|^static/images/walpurgis-.*\.png$' <<<"$archive_contents"; then
  echo "El paquete del portal contiene material local no autorizado para redistribución." >&2
  exit 1
fi

while IFS= read -r text_path; do
  case "$text_path" in
    *.py|*.html|*.css|*.js|*.svg)
      if tar -xOzf "$artifact_path" "$text_path" | grep -Eq 'walpurgis-|sweet-dove-ambient'; then
        echo "El paquete conserva referencias a material local excluido: $text_path" >&2
        exit 1
      fi
      ;;
  esac
done <<< "$(grep -E '\.(py|html|css|js|svg)$' <<<"$archive_contents")"

if ! grep -Eq '^migrations/.+\.sql$' <<<"$archive_contents"; then
  echo "El paquete del portal no contiene las migraciones." >&2
  exit 1
fi

release_lock="$(tar -xOzf "$artifact_path" requirements.lock)"
if ! grep -Eq '^[A-Za-z0-9_.-]+==[^[:space:]\\]+ \\' <<<"$release_lock" || \
  ! grep -Eq -- '--hash=sha256:[a-f0-9]{64}' <<<"$release_lock"; then
  echo "El lock del release AWS no contiene pins y hashes SHA-256." >&2
  exit 1
fi

if grep -Eiq '(^|/)(\.env([^/]*)?|credentials|\.aws)(/|$)|\.(pem|key)$' <<<"$archive_contents"; then
  echo "El paquete del portal contiene un nombre asociado a secretos o claves." >&2
  exit 1
fi

printf 'PORTAL_ARTIFACT=APROBADO sha256=%s\n' "$artifact_sha256"
