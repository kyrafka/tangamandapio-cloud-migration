"""Restore one authenticated archive into a short-lived Unix-socket PostgreSQL cluster."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from postgres_backup_crypto import open_envelope
from postgres_blob_export import RefuseRedirect, aws_text, quiet_command


def verify(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("SHA-256 mismatch")


def restore(args):
    started = monotonic()
    input_data = json.loads(aws_text(args.region, ["ssm", "get-parameter", "--name", args.parameter, "--with-decryption", "--query", "Parameter.Value"]))
    url = urlsplit(input_data["read_url"])
    if (url.scheme, url.netloc, url.path) != ("https", args.blob_host, f"/{args.container}/{args.object}"):
        raise RuntimeError("Unexpected Blob URL")
    with build_opener(RefuseRedirect()).open(Request(input_data["read_url"]), timeout=35) as response:
        ciphertext = response.read(140 * 1024 * 1024)
    verify(ciphertext, args.cipher_sha256)
    if json.loads(ciphertext)["key_id"] != args.key_id:
        raise RuntimeError("Unexpected wrapping key version")
    archive = open_envelope(ciphertext, lambda _: base64.b64decode(input_data["data_key"]))
    verify(archive, args.archive_sha256)
    with TemporaryDirectory(prefix="tangama-restore-", dir="/dev/shm") as directory:
        work = Path(directory)
        pg = ["runuser", "-u", "postgres", "--"]
        user = quiet_command(["id", "-u", "postgres"])
        group = quiet_command(["id", "-g", "postgres"])
        os.chown(work, int(user), int(group))
        data_dir = str(work / "data")
        port = "54773"
        socket = ["-h", directory, "-p", port, "-U", "postgres"]
        quiet_command([*pg, "initdb", "-D", data_dir, "-A", "trust", "--no-sync", "--locale=C"])
        try:
            settings = f"-k {directory} -p {port} -c listen_addresses='' -c shared_buffers=16MB -c max_connections=5"
            quiet_command([*pg, "pg_ctl", "-w", "-D", data_dir, "-l", str(work / "postgres.log"), "-o", settings, "start"])
            quiet_command([*pg, "createdb", *socket, "tangama_restore"])
            quiet_command([*pg, "pg_restore", *socket, "--exit-on-error", "--no-owner", "--no-privileges", "-d", "tangama_restore"], input=archive)
            check = """SELECT json_build_object('tables',count(*),
              'portal_users',(SELECT count(*) FROM public.portal_users),
              'orders',(SELECT count(*) FROM public.orders),
              'outbox_events',(SELECT count(*) FROM public.outbox_events),
              'tcp_enabled',current_setting('listen_addresses') <> '',
              'engine',current_setting('server_version')) FROM pg_tables WHERE schemaname='public';"""
            counts = json.loads(quiet_command([*pg, "psql", *socket, "-XAt", "-v", "ON_ERROR_STOP=1", "-d", "tangama_restore", "-c", check]))
            if counts["tables"] < 3 or counts["tcp_enabled"]:
                raise RuntimeError("Isolated restore verification failed")
            return {"object": args.object, "restore_host_seconds": round(monotonic() - started, 3), **counts}
        finally:
            if (Path(data_dir) / "postmaster.pid").exists():
                subprocess.run([*pg, "pg_ctl", "-w", "-D", data_dir, "-m", "immediate", "stop"], check=True, capture_output=True, timeout=25)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "parameter", "blob-host", "container", "object", "key-id", "archive-sha256", "cipher-sha256"):
        parser.add_argument(f"--{name}", required=True)
    try:
        print(json.dumps(restore(parser.parse_args())))
    except Exception as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
