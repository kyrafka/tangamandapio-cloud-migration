#!/usr/bin/env bash
set -euo pipefail

# Usage from a clean checkout (for example AWS CloudShell):
#   ./iac/cloudformation/package_portal_artifact.sh BUCKET [OBJECT_KEY]
# The compiled static portal is intentionally bundled with the Python source.

bucket="${1:?indica el bucket privado del proyecto}"
object_key="${2:-releases/portal-b2b-v1.tar.gz}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
application_root="$repository_root/app"
staging_directory="$(mktemp -d)"
artifact_path="$staging_directory/portal-b2b.tar.gz"

cleanup() {
  rm -rf "$staging_directory"
}
trap cleanup EXIT

test -f "$application_root/src/app.py"
test -f "$application_root/requirements.txt"
test -f "$application_root/src/static/index.html"

mkdir -p "$staging_directory/static"
cp "$application_root/src/app.py" "$staging_directory/app.py"
cp "$application_root/requirements.txt" "$staging_directory/requirements.txt"
cp -R "$application_root/src/static/." "$staging_directory/static/"

git -C "$repository_root" rev-parse --short HEAD > "$staging_directory/BUILD_REVISION"
tar -C "$staging_directory" -czf "$artifact_path" app.py requirements.txt static BUILD_REVISION

aws s3 cp "$artifact_path" "s3://$bucket/$object_key" --sse AES256
aws s3api head-object --bucket "$bucket" --key "$object_key" \
  --query '{Bytes:ContentLength,Version:VersionId,Updated:LastModified}' --output table
