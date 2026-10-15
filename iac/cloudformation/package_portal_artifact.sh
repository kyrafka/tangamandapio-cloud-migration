#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AWS_CLI:-}" ]]; then
  aws() { "$AWS_CLI" "$@" | tr -d '\r'; }
fi

# Package the release directory that corresponds to the running portal.  With
# no bucket argument this creates a local artifact for inspection/rebuilds;
# with a bucket it uploads that exact artifact to S3.
#
# Usage:
#   ./iac/cloudformation/package_portal_artifact.sh
#   ./iac/cloudformation/package_portal_artifact.sh BUCKET [OBJECT_KEY]

bucket="${1:-}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
application_root="$repository_root/app/aws_release/current"
staging_directory="$(mktemp -d)"
revision="$(tr -cd 'A-Za-z0-9._-' < "$application_root/BUILD_REVISION" | head -c 80)"
artifact_name="portal-b2b-${revision:-local}.tar.gz"
artifact_path="$staging_directory/$artifact_name"
local_output="${LOCAL_ARTIFACT_PATH:-$repository_root/artifacts/$artifact_name}"
object_key="${2:-releases/tangamandapio/$artifact_name}"

cleanup() {
  rm -rf "$staging_directory"
}
trap cleanup EXIT

test -f "$application_root/app.py"
test -f "$application_root/erp_service.py"
test -f "$application_root/requirements.txt"
test -f "$application_root/requirements.lock"
test -f "$application_root/BUILD_REVISION"
test -f "$application_root/static/index.html"
test -d "$application_root/migrations"

cp "$application_root/app.py" "$staging_directory/app.py"
cp "$application_root/erp_service.py" "$staging_directory/erp_service.py"
cp "$application_root/requirements.txt" "$staging_directory/requirements.txt"
cp "$application_root/requirements.lock" "$staging_directory/requirements.lock"
cp "$application_root/BUILD_REVISION" "$staging_directory/BUILD_REVISION"
cp -R "$application_root/static" "$staging_directory/static"
cp -R "$application_root/migrations" "$staging_directory/migrations"
artifact_files=(app.py erp_service.py requirements.txt requirements.lock static migrations BUILD_REVISION)
if [[ -f "$application_root/cloud_observability.py" ]]; then
  cp "$application_root/cloud_observability.py" "$staging_directory/cloud_observability.py"
  artifact_files+=(cloud_observability.py)
fi

source_date_epoch="${SOURCE_DATE_EPOCH:-0}"
if [[ ! "$source_date_epoch" =~ ^[0-9]+$ ]]; then
  echo 'SOURCE_DATE_EPOCH debe ser un entero no negativo.' >&2
  exit 2
fi

# WSL and Git Bash can report different source permission bits for the same
# Windows files. Normalize the staged tree so archive hashes are portable.
find "$staging_directory" -type d -exec chmod 0755 {} +
find "$staging_directory" -type f -exec chmod 0644 {} +

# Normalize member order, timestamps, ownership, and the gzip header so the
# same release tree always produces the same bytes and can be hash-attested.
tar --sort=name --mtime="@${source_date_epoch}" --owner=0 --group=0 \
  --numeric-owner -C "$staging_directory" -cf - "${artifact_files[@]}" \
  | gzip -n -9 > "$artifact_path"

if [[ -n "$bucket" ]]; then
  aws s3 cp "$artifact_path" "s3://$bucket/$object_key" --sse AES256
  aws s3api head-object --bucket "$bucket" --key "$object_key" \
    --query '{Bytes:ContentLength,Version:VersionId,Updated:LastModified}' --output table
else
  mkdir -p "$(dirname "$local_output")"
  cp "$artifact_path" "$local_output"
  printf 'Artefacto local listo: %s\n' "$local_output"
  sha256sum "$local_output"
fi
