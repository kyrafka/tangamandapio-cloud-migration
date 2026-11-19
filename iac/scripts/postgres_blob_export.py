"""Export the application PostgreSQL database to a new encrypted Azure blob.

Run as root via SSM on an application host with PostgreSQL 18 client tools.
An operator supplies a short-lived, create-only blob URL in Parameter Store.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from postgres_backup_crypto import MAX_ARCHIVE_BYTES, seal


class RefuseRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def quiet_command(command, **kwargs):
    result = subprocess.run(command, capture_output=True, timeout=180, **kwargs)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} exited {result.returncode}")
    return result.stdout


def aws_text(region, arguments):
    return quiet_command(["aws", *arguments, "--region", region, "--output", "text", "--no-cli-pager"]).decode().strip()


def source_environment(region, root_certificate):
    pid = quiet_command(["systemctl", "show", "-p", "MainPID", "--value", "tangamandapio"]).decode().strip()
    if not re.fullmatch(r"[1-9][0-9]*", pid):
        raise RuntimeError("Application is not running")
    values = dict(item.split(b"=", 1) for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in item)
    host = values[b"DB_HOST"].decode()
    secret_id = values[b"DB_SECRET_ARN"].decode()
    database = values[b"DATABASE_NAME"].decode()
    if not host.endswith(f".{region}.rds.amazonaws.com") or not database:
        raise RuntimeError("Unexpected PostgreSQL source")
    credentials = json.loads(aws_text(region, ["secretsmanager", "get-secret-value", "--secret-id", secret_id, "--query", "SecretString"]))
    return {
        "PATH": os.environ["PATH"], "PGHOST": host, "PGDATABASE": database,
        "PGUSER": credentials["username"], "PGPASSWORD": credentials["password"],
        "PGSSLMODE": "verify-full", "PGSSLROOTCERT": str(root_certificate), "PGCONNECT_TIMEOUT": "8",
    }


def export(args):
    started = datetime.now(timezone.utc)
    with TemporaryDirectory(prefix="tangama-export-", dir="/dev/shm") as directory:
        work = Path(directory)
        root_certificate = work / "rds-ca.pem"
        with urlopen("https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem", timeout=15) as response:
            root_certificate.write_bytes(response.read(1_000_000))
        env = source_environment(args.region, root_certificate)
        archive = work / "source.dump"
        quiet_command(["pg_dump", "--format=custom", "--no-owner", "--no-privileges", "--file", str(archive)], env=env)
        if not 0 < archive.stat().st_size <= MAX_ARCHIVE_BYTES:
            raise RuntimeError("Archive outside allowed size")
        data = archive.read_bytes()
        dump_sha = hashlib.sha256(data).hexdigest()
        envelope = seal(data, args.public_key.read_bytes(), args.key_id)
    sas = aws_text(args.region, ["ssm", "get-parameter", "--name", args.parameter, "--with-decryption", "--query", "Parameter.Value"])
    dest = urlsplit(sas)
    permissions = parse_qs(dest.query).get("sp", [])
    if (dest.scheme, dest.netloc, dest.path, permissions) != (
        "https", args.blob_host, f"/{args.container}/{args.object}", ["c"]
    ) or dest.fragment:
        raise RuntimeError("Storage URL does not match the designated create-only object")
    request = Request(sas, data=envelope, method="PUT", headers={
        "x-ms-blob-type": "BlockBlob", "If-None-Match": "*", "Content-Type": "application/json",
        "x-ms-meta-archive_sha256": dump_sha, "x-ms-meta-created_utc": started.isoformat(),
    })
    with build_opener(RefuseRedirect()).open(request, timeout=60) as response:
        if response.status != 201:
            raise RuntimeError("Unexpected upload response")
        return {"object": args.object, "source_started_utc": started.isoformat(),
                "archive_sha256": dump_sha, "cipher_sha256": hashlib.sha256(envelope).hexdigest(),
                "archive_bytes": len(data), "upload_http": response.status}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "parameter", "blob-host", "container", "object", "key-id"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(export(args)))
    except Exception as exc:
        print(f"Export failed: {type(exc).__name__} {getattr(exc, 'code', '')}", file=sys.stderr)
        if isinstance(exc, RuntimeError):
            print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
