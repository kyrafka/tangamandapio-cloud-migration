"""Prepare PostgreSQL runtime and backup users from exact Secrets Manager references."""

import argparse
import json
import re
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

import boto3
import psycopg2
from botocore.exceptions import ClientError
from psycopg2 import sql
from psycopg2.extensions import encrypt_password


def read_credential(client, arn, username=None):
    try:
        value = json.loads(client.get_secret_value(SecretId=arn)["SecretString"])
    except ClientError as error:
        code = error.response["Error"]["Code"]
        raise RuntimeError(f"Secrets Manager rejected the {username or 'owner'} credential ({code})") from None
    if not value.get("username") or not value.get("password") or (username and value["username"] != username):
        raise ValueError("Unexpected SQL credential fields or user")
    return value


def prepare(args):
    if not args.host.endswith(f".{args.region}.rds.amazonaws.com"):
        raise ValueError("Expected the PostgreSQL endpoint of the selected AWS region")
    session = boto3.Session(region_name=args.region, profile_name=args.profile)
    account = session.client("sts").get_caller_identity()["Account"]
    arns = (args.owner, args.runtime, args.backup)
    if account != args.account or len(set(arns)) != 3 or not all(
        re.fullmatch(rf"arn:aws:secretsmanager:{args.region}:{account}:secret:[A-Za-z0-9/_+=.@-]+", arn)
        for arn in arns
    ):
        raise ValueError("Expected three distinct credential ARNs in the selected account and region")
    client = session.client("secretsmanager")
    owner = read_credential(client, args.owner)
    runtime = read_credential(client, args.runtime, "tangama_app_runtime")
    backup = read_credential(client, args.backup, "tangama_backup_reader")
    if owner["username"] in (runtime["username"], backup["username"]):
        raise ValueError("The database owner must be distinct from both runtime roles")

    with TemporaryDirectory(prefix="tangama-rds-role-setup-") as work:
        certificate = Path(work) / "rds-ca.pem"
        with urlopen("https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem", timeout=15) as response:
            certificate.write_bytes(response.read(1_000_000))
        connection_args = {"host": args.host, "port": args.port, "dbname": args.database,
                           "sslmode": "verify-full", "sslrootcert": str(certificate), "connect_timeout": 8}
        with closing(psycopg2.connect(**connection_args, user=owner["username"], password=owner["password"])) as connection:
            with connection, connection.cursor() as cursor:
                cursor.execute("SELECT version FROM public.schema_migrations ORDER BY version")
                applied = {row[0] for row in cursor.fetchall()}
                present = {path.stem for path in args.migrations.glob("*.sql")}
                recovery = "0010_admin_recovery_events"
                if recovery not in present or not present - {recovery} or present - applied - {recovery}:
                    raise RuntimeError("Apply the project's earlier migrations as the owner before provisioning")
                if not args.apply:
                    return {"account": account, "verifiedTLS": True, "appliedMigrationCount": len(applied), "changed": False}
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("tangamandapio:schema-migrations",))
                cursor.execute((args.migrations / f"{recovery}.sql").read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO public.schema_migrations (version, applied_at) VALUES (%s, CURRENT_TIMESTAMP::text) "
                    "ON CONFLICT (version) DO NOTHING", (recovery,),
                )
                cursor.execute(args.privileges.read_text(encoding="utf-8"))
                for login in (runtime, backup):
                    verifier = encrypt_password(login["password"], login["username"], cursor, "scram-sha-256")
                    cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD %s").format(sql.Identifier(login["username"])), (verifier,))

        for login in (runtime, backup):
            with closing(psycopg2.connect(**connection_args, user=login["username"], password=login["password"])) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_user, has_schema_privilege(current_user, 'public', 'CREATE')")
                    if cursor.fetchone() != (login["username"], False):
                        raise RuntimeError("Dedicated SQL role or schema access did not match the policy")
                    cursor.execute("SELECT 1 FROM public.orders LIMIT 1")
        return {"account": account, "verifiedTLS": True, "changed": True, "runtimeLogin": True, "backupLogin": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("account", "region", "host", "database", "owner", "runtime", "backup"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--migrations", type=Path, required=True)
    parser.add_argument("--privileges", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    print(json.dumps(prepare(parser.parse_args())))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error))
        raise SystemExit(1) from None
    except Exception as error:
        # Do not print AWS responses, connection arguments, SQL text or verifiers.
        print(f"PostgreSQL role setup failed: {type(error).__name__} {getattr(error, 'pgcode', '') or ''}")
        raise SystemExit(1) from None
