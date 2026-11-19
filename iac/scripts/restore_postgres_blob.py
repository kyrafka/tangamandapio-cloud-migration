"""Verify and restore an encrypted PostgreSQL backup into an isolated cluster."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from botocore.exceptions import ClientError
from run_postgres_blob_export import CONTAINER, KEY_ID, REGION, SCRIPTS, STORAGE, aws, azure, wait_export

class RefuseRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def unwrap(key_id, wrapped):
    token = azure("account", "get-access-token", "--resource", "https://vault.azure.net", "--query", "accessToken", "-o", "tsv")
    value = base64.urlsafe_b64encode(wrapped).decode().rstrip("=")
    body = json.dumps({"alg": "RSA-OAEP-256", "value": value}).encode()
    request = Request(f"{key_id}/unwrapkey?api-version=7.4", data=body, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
    })
    with build_opener(RefuseRedirect()).open(request, timeout=25) as response:
        encoded = json.load(response)["value"]
        return base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))


def verify_hash(data, expected):
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), expected):
        raise RuntimeError("SHA-256 verification failed")


def restore_on_host(args):
    if (args.storage, args.container, args.key_id) != (STORAGE, CONTAINER, KEY_ID):
        raise RuntimeError("Restore target does not match the project's known storage and key")
    started = monotonic()
    start_timestamp = datetime.now(timezone.utc)
    with TemporaryDirectory(prefix="tangama-restore-") as directory:
        download = Path(directory) / "ciphertext.json"
        azure("storage", "blob", "download", "--account-name", STORAGE, "--container-name", CONTAINER,
              "--name", args.object, "--file", str(download), "--auth-mode", "login", "-o", "none")
        ciphertext = download.read_bytes()
    verify_hash(ciphertext, args.cipher_sha256)
    envelope = json.loads(ciphertext)
    if envelope["key_id"] != KEY_ID:
        raise RuntimeError("Unexpected Key Vault key version")
    data_key = unwrap(KEY_ID, base64.b64decode(envelope["wrapped_key"], validate=True))
    expiry = (datetime.now(timezone.utc) + timedelta(minutes=12)).strftime("%Y-%m-%dT%H:%MZ")
    url = azure("storage", "blob", "generate-sas", "--account-name", STORAGE, "--container-name", CONTAINER,
                "--name", args.object, "--permissions", "r", "--expiry", expiry, "--as-user", "--auth-mode", "login",
                "--https-only", "--full-uri", "-o", "tsv")
    expected_host = f"{STORAGE}.blob.core.windows.net"
    if urlsplit(url).netloc != expected_host or len(data_key) != 32:
        raise RuntimeError("Restore authorization failed validation")

    parameter = f"/tangamandapio/dr/restore/{uuid4().hex[:12]}"
    client = aws(args.profile)
    files = ("postgres_blob_restore_host.py", "postgres_blob_export.py", "postgres_backup_crypto.py")
    cleanup = " ".join(f'"$w/{name}"' for name in files)
    commands = ["set -eu", "umask 077", "w=$(mktemp -d /dev/shm/tangama-restore-script.XXXXXXXX)",
                f'''trap 'rm -f -- {cleanup}; rmdir -- "$w"' EXIT''', "export PYTHONDONTWRITEBYTECODE=1"]
    for name in files:
        data = base64.b64encode((SCRIPTS / name).read_bytes()).decode()
        commands.append(f'printf %s {shlex.quote(data)} | base64 -d > "$w/{name}"')
    commands.append("command -v initdb >/dev/null || dnf -q install -y postgresql18-server >/dev/null")
    options = ["--region", REGION, "--parameter", parameter, "--blob-host", expected_host, "--container", CONTAINER,
               "--object", args.object, "--key-id", KEY_ID, "--archive-sha256", args.archive_sha256,
               "--cipher-sha256", args.cipher_sha256]
    commands.append('python3 "$w/postgres_blob_restore_host.py" ' + shlex.join(options))
    value = json.dumps({"read_url": url, "data_key": base64.b64encode(data_key).decode()})
    client.put_parameter(Name=parameter, Value=value, Type="SecureString", Description="One-time isolated PostgreSQL restore")
    try:
        response = client.send_command(InstanceIds=[args.restore_host], DocumentName="AWS-RunShellScript",
                                       Comment="Isolated Tangamandapio PostgreSQL restore from Azure Blob",
                                       Parameters={"commands": commands, "executionTimeout": ["270"]})
        command_id = response["Command"]["CommandId"]
        print(json.dumps({"restore_command": command_id}), flush=True)
        result = wait_export(client, command_id, args.restore_host)
        return {**result, "restore_started_utc": start_timestamp.isoformat(),
                "restore_seconds": round(monotonic() - started, 3), "ssm_command_id": command_id}
    finally:
        client.delete_parameter(Name=parameter)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("storage", "container", "object", "key-id", "cipher-sha256", "archive-sha256"):
        parser.add_argument(f"--{flag}", required=True)
    parser.add_argument("--restore-host", required=True, help="SSM instance for the temporary socket-only PostgreSQL cluster")
    parser.add_argument("--profile", default="main")
    args = parser.parse_args()
    try:
        print(json.dumps(restore_on_host(args)))
    except ClientError as exc:
        print(f"{exc.operation_name}: {exc.response['Error']['Code']}", file=sys.stderr)
        sys.exit(1)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
