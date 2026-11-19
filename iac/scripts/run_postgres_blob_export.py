"""Start and verify one RDS-to-Blob export using the operator's cloud sessions."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from uuid import uuid4

import botocore.session
from botocore.exceptions import ClientError


ACCOUNT_ID = "481056890449"
SUBSCRIPTION_ID = "1480b165-7420-4bed-a201-5ecadd7104d0"
REGION = "us-east-2"
STORAGE = "sttangama261030r"
CONTAINER = "tangama-postgres-backups"
KEY_ID = "https://kv-tangama-261030r.vault.azure.net/keys/postgres-backup-wrap/29aa95ea1d7e47f6955ce7c3fe14f0b5"
SCRIPTS = Path(__file__).resolve().parent


def az_cli():
    if os.name == "nt":
        interpreter = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        interpreter /= "Microsoft SDKs/Azure/CLI2/python.exe"
        if interpreter.is_file():
            return [str(interpreter), "-IBm", "azure.cli"]
    return ["az"]


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=70)
    if result.returncode:
        raise RuntimeError(f"{Path(arguments[0]).name} {arguments[-1] if arguments[-1] in {'tsv', 'json', 'none'} else 'command'} failed")
    return result.stdout.strip()


def azure(*args):
    return command([*az_cli(), *args, "--only-show-errors"])


def aws(profile):
    data = json.loads(command(["aws", "configure", "export-credentials", "--profile", profile, "--format", "process"]))
    session = botocore.session.get_session()
    session.set_credentials(data["AccessKeyId"], data["SecretAccessKey"], data.get("SessionToken"))
    if session.create_client("sts", region_name=REGION).get_caller_identity()["Account"] != ACCOUNT_ID:
        raise RuntimeError("AWS account mismatch")
    return session.create_client("ssm", region_name=REGION)


def remote_commands(pem, blob, parameter):
    commands = ["set -eu", "umask 077", "w=$(mktemp -d /dev/shm/tangama-export-script.XXXXXXXX)",
                '''trap 'rm -f -- "$w/postgres_blob_export.py" "$w/postgres_backup_crypto.py" "$w/public.pem"; rmdir -- "$w"' EXIT''',
                "export PYTHONDONTWRITEBYTECODE=1"]
    files = {name: (SCRIPTS / name).read_bytes() for name in ("postgres_blob_export.py", "postgres_backup_crypto.py")}
    files["public.pem"] = pem
    for name, data in files.items():
        encoded = base64.b64encode(data).decode("ascii")
        commands.append(f'printf %s {shlex.quote(encoded)} | base64 -d > "$w/{name}"')
    commands.extend(["command -v pg_dump >/dev/null || dnf -q install -y postgresql18 >/dev/null", "pg_dump --version"])
    arguments = ["--region", REGION, "--parameter", parameter, "--blob-host", f"{STORAGE}.blob.core.windows.net",
                 "--container", CONTAINER, "--object", blob, "--key-id", KEY_ID]
    commands.append('python3 "$w/postgres_blob_export.py" --public-key "$w/public.pem" ' + shlex.join(arguments))
    return commands


def wait_export(client, command_id, instance):
    end = monotonic() + 300
    while monotonic() < end:
        try:
            execution = client.get_command_invocation(CommandId=command_id, InstanceId=instance)
        except client.exceptions.InvocationDoesNotExist:
            sleep(4)
            continue
        status = execution["Status"]
        if status == "Success":
            return json.loads(execution["StandardOutputContent"].strip().splitlines()[-1])
        if status in {"Failed", "Cancelled", "TimedOut"}:
            raise RuntimeError(f"SSM {status}: {execution['StandardErrorContent'].strip()[:350]}")
        sleep(4)
    raise RuntimeError("SSM timed out while waiting for export")


def run(profile, instance):
    client = aws(profile)
    if azure("account", "show", "--query", "id", "-o", "tsv") != SUBSCRIPTION_ID:
        raise RuntimeError("Azure subscription mismatch")
    now = datetime.now(timezone.utc)
    identifier = uuid4().hex[:12]
    blob = f"postgres/{now:%Y%m%dT%H%M%SZ}-{identifier}.json"
    parameter = f"/tangamandapio/dr/blob-write/{identifier}"
    expiry = (now + timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%MZ")
    with TemporaryDirectory(prefix="tangama-key-") as directory:
        pem = Path(directory) / "public.pem"
        azure("keyvault", "key", "download", "--id", KEY_ID, "--file", str(pem), "--encoding", "PEM", "-o", "none")
        commands = remote_commands(pem.read_bytes(), blob, parameter)
    url = azure("storage", "blob", "generate-sas", "--account-name", STORAGE, "--container-name", CONTAINER,
                "--name", blob, "--permissions", "c", "--expiry", expiry, "--as-user", "--auth-mode", "login",
                "--https-only", "--full-uri", "-o", "tsv")
    if not url.startswith(f"https://{STORAGE}.blob.core.windows.net/{CONTAINER}/{blob}?"):
        raise RuntimeError("Blob write authorization missing")
    client.put_parameter(Name=parameter, Value=url, Type="SecureString", Description="Temporary create-only Tangamandapio Blob upload")
    try:
        launch = client.send_command(InstanceIds=[instance], DocumentName="AWS-RunShellScript",
                                     Comment="Encrypted Tangamandapio RDS export to Azure Blob",
                                     Parameters={"commands": commands, "executionTimeout": ["270"]})
        command_id = launch["Command"]["CommandId"]
        print(json.dumps({"command_id": command_id, "object": blob}), flush=True)
        result = wait_export(client, command_id, instance)
        info = json.loads(azure("storage", "blob", "show", "--account-name", STORAGE, "--container-name", CONTAINER,
                               "--name", blob, "--auth-mode", "login", "--query",
                               "{bytes:properties.contentLength,metadata:metadata}", "-o", "json"))
        metadata = {key.lower(): value for key, value in (info["metadata"] or {}).items()}
        if not info["bytes"] or metadata.get("archive_sha256") != result["archive_sha256"]:
            raise RuntimeError("Azure Blob metadata verification failed")
        return {**result, "blob_bytes": info["bytes"], "ssm_command_id": command_id, "key_id": KEY_ID}
    finally:
        client.delete_parameter(Name=parameter)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="main")
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.profile, args.instance)))
    except ClientError as exc:
        print(f"{exc.operation_name}: {exc.response['Error']['Code']}", file=sys.stderr)
        sys.exit(1)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
