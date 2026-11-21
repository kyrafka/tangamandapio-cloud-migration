"""Start and verify the ERP on a loopback PostgreSQL clone from Azure Blob."""

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
from contextlib import closing
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

from werkzeug.serving import make_server

from postgres_backup_crypto import open_envelope
from restore_postgres_blob import CONTAINER, KEY_ID, STORAGE, RefuseRedirect, azure, unwrap, verify_hash

RELEASE = Path(__file__).resolve().parents[2] / "app" / "aws_release" / "current"
DB_NAME = "tangama_recovery"


def pg_run(bin_dir, name, *args, data=None, env=None):
    program = bin_dir / (name + (".exe" if os.name == "nt" else ""))
    result = subprocess.run(
        [str(program), *map(str, args)],
        input=data,
        env=env,
        capture_output=name != "pg_ctl",
        stdout=subprocess.DEVNULL if name == "pg_ctl" else None,
        stderr=subprocess.DEVNULL if name == "pg_ctl" else None,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"{name} failed (exit {result.returncode})")
    return result.stdout.decode("utf-8", "replace").strip() if result.stdout else ""


def verify_portal(application, exercise_writes=False):
    server = make_server("127.0.0.1", 0, application, threaded=True)
    port = server.server_port
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{port}"
    checks = {}

    def call(client, stage, route, expected=200, data=None, csrf=None):
        headers = {"Content-Type": "application/json", "Origin": origin}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        req = Request(origin + route, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            response = client.open(req, timeout=8)
        except HTTPError as error:
            response = error
        with response:
            status = response.code
            if status != expected:
                raise RuntimeError(f"{stage} returned HTTP {status}, expected {expected}")
            checks[stage] = status
            return json.load(response) if response.headers.get_content_type() == "application/json" else None

    def login(client, label, username, password, role):
        session = call(client, f"{label}_csrf", "/api/auth/session")
        auth = call(client, f"{label}_login", "/api/auth/login",
                    data={"username": username, "password": password}, csrf=session["csrf_token"])
        if auth["user"]["role"] != role:
            raise RuntimeError(f"{label} recovered the wrong role")
        return call(client, f"{label}_session", "/api/auth/session")["csrf_token"]

    admin = build_opener(ProxyHandler({}), RefuseRedirect(), HTTPCookieProcessor(CookieJar()))
    staff = build_opener(ProxyHandler({}), RefuseRedirect(), HTTPCookieProcessor(CookieJar()))
    recovered_orders = None
    try:
        call(admin, "http_health", "/health")
        call(admin, "http_ready", "/ready")
        call(admin, "erp_without_session", "/api/erp/access", expected=401)
        admin_token = login(
            admin, "admin", application.config["BOOTSTRAP_ADMIN_USERNAME"],
            application.config["BOOTSTRAP_ADMIN_PASSWORD"], "admin",
        )
        recovered_orders = len(call(admin, "restored_orders", "/api/orders"))
        call(admin, "erp_html", "/erp")
        call(admin, "erp_overview", "/api/erp/overview")
        call(admin, "erp_sales", "/api/erp/sales/orders")
        call(admin, "erp_finance", "/api/erp/finance/documents")
        if exercise_writes:
            partner = call(admin, "create_erp_partner", "/api/erp/partners", 201, {
                "kind": "both", "name": "Socio de ensayo aislado", "tax_id": "RECOVERY-TEST-01",
            }, admin_token)
            order = {"partner_id": partner["id"], "items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]}
            inventory = {"mode": "demo-inventory-ledger", "items": [{"sku": "SKU-ARROZ-001", "on_hand": 25}]}
            with patch("erp_service.fetch_wms_inventory", return_value=(inventory, None)):
                call(admin, "create_erp_sale", "/api/erp/sales/orders", 201, order, admin_token)
                purchase = call(admin, "create_erp_purchase", "/api/erp/purchases/orders", 201, order, admin_token)
            receipt = call(admin, "queue_purchase_receipt", f"/api/erp/purchases/orders/{purchase['id']}/receive",
                           202, {}, admin_token)
            if receipt["status"] != "receipt_pending":
                raise RuntimeError("Isolated purchase receipt must remain in the outbox")
            expense = call(admin, "create_erp_expense", "/api/erp/finance/expenses", 201,
                           {"description": "Gasto de ensayo aislado", "amount": 18.25}, admin_token)
            settlement = call(admin, "settle_erp_expense", f"/api/erp/finance/documents/{expense['id']}/settle",
                              200, {}, admin_token)
            if settlement["status"] != "paid":
                raise RuntimeError("Isolated expense did not settle")
        recipient = f"restore-{secrets.token_hex(6)}@example.invalid"
        password = secrets.token_urlsafe(26)
        user = call(admin, "create_isolated_user", "/api/admin/users", expected=201,
                    data={"username": recipient, "password": password, "role": "warehouse"}, csrf=admin_token)["user"]
        subject = "Comprobación aislada de recuperación"
        message = call(admin, "send_internal_mail", "/api/erp/mail", expected=201,
                       data={"recipient_id": user["id"], "subject": subject, "body": "Mensaje sintético."},
                       csrf=admin_token)
        if message.get("smtp_status") != "portal_only":
            raise RuntimeError("The recovery exercise must use only the internal mailbox")
        staff_token = login(staff, "warehouse", recipient, password, "warehouse")
        call(staff, "warehouse_finance_forbidden", "/api/erp/finance/documents", expected=403)
        messages = call(staff, "receive_internal_mail", "/api/erp/mail?folder=inbox")
        if not any(item["id"] == message["id"] and item["subject"] == subject and item["unread"] for item in messages):
            raise RuntimeError("The internal message did not reach the isolated mailbox")
        read = call(staff, "read_internal_mail", f"/api/erp/mail/{message['id']}/read", data={}, csrf=staff_token)
        if not read["read"] or read["unread_messages"] != 0:
            raise RuntimeError("The isolated mailbox did not confirm reading")
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
    return checks, recovered_orders


def prepare_restricted_roles(bin_dir, db, env, work, owner_url, port):
    import psycopg2

    from app import connect, initialize_database
    from erp_service import initialize_erp_database

    initialize_database(owner_url)
    with connect(owner_url) as connection:
        initialize_erp_database(connection, postgres=True)
        connection.commit()
    policy = Path(__file__).with_name("postgres_runtime_privileges.sql")
    pg_run(bin_dir, "psql", *db, "-Xq", "-v", "ON_ERROR_STOP=1", "--single-transaction",
           "-d", DB_NAME, "-f", policy, env=env)
    runtime_password = secrets.token_urlsafe(26)
    backup_password = secrets.token_urlsafe(26)
    passwords = (f"ALTER ROLE tangama_app_runtime PASSWORD '{runtime_password}';"
                 f"ALTER ROLE tangama_backup_reader PASSWORD '{backup_password}';")
    pg_run(bin_dir, "psql", *db, "-Xq", "-v", "ON_ERROR_STOP=1", "-d", DB_NAME, data=passwords.encode(), env=env)
    runtime_url = f"postgresql://tangama_app_runtime:{runtime_password}@127.0.0.1:{port}/{DB_NAME}"
    backup_url = f"postgresql://tangama_backup_reader:{backup_password}@127.0.0.1:{port}/{DB_NAME}"
    checks = {}
    for label, url, statement in (
        ("runtimeCannotCreateTables", runtime_url, "CREATE TABLE public.disallowed (id int)"),
        ("runtimeCannotChangeMigrations", runtime_url, "DELETE FROM public.schema_migrations WHERE FALSE"),
        ("backupCannotChangeOrders", backup_url, "UPDATE public.orders SET id = id WHERE FALSE"),
    ):
        with closing(psycopg2.connect(url)) as connection, connection.cursor() as cursor:
            try:
                cursor.execute(statement)
            except psycopg2.errors.InsufficientPrivilege:
                checks[label] = True
            else:
                raise RuntimeError(f"PostgreSQL did not enforce {label}")
    reader_dump = work / "reader.dump"
    pg_run(bin_dir, "pg_dump", "-h", "127.0.0.1", "-p", port, "-U", "tangama_backup_reader",
           "--format=custom", "--no-owner", "--no-privileges", "--file", reader_dump, DB_NAME,
           env=dict(env, PGPASSWORD=backup_password))
    dump_index = pg_run(bin_dir, "pg_restore", "--list", reader_dump, env=env)
    checks["backupIncludesOrdersAndSequences"] = all(name in dump_index for name in (
        "TABLE DATA public orders", "TABLE DATA public internal_messages", "SEQUENCE SET public orders_id_seq",
    ))
    if not checks["backupIncludesOrdersAndSequences"]:
        raise RuntimeError("The backup role dump does not include the required data and sequences")
    return runtime_url, checks


def rehearse(args):
    document = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    manifest = document.get("verifiedManifest", document)
    if not re.fullmatch(r"postgres/\d{8}-daily\.json", manifest["object"]):
        raise RuntimeError("Expected a scheduled Tangamandapio backup object")
    start = monotonic()
    with TemporaryDirectory(prefix="tangama-erp-recovery-") as directory:
        work = Path(directory)
        encrypted = work / "archive.json"
        azure("storage", "blob", "download", "--account-name", STORAGE, "--container-name", CONTAINER,
              "--name", manifest["object"], "--file", str(encrypted), "--auth-mode", "login", "-o", "none")
        ciphertext = encrypted.read_bytes()
        encrypted.unlink()
        verify_hash(ciphertext, manifest["cipher_sha256"])
        if json.loads(ciphertext)["key_id"] != KEY_ID:
            raise RuntimeError("Unexpected Key Vault key version")
        archive = open_envelope(ciphertext, lambda wrapped: unwrap(KEY_ID, wrapped))
        verify_hash(archive, manifest["archive_sha256"])
        if len(archive) != manifest["archive_bytes"]:
            raise RuntimeError("Archive size differs from the verified manifest")
        materialized = monotonic()

        cluster = work / "db"
        password = secrets.token_urlsafe(26)
        password_file = work / "pg-password"
        password_file.write_text(password + "\n", encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if not key.startswith(("PG", "AWS_"))}
        env["PGPASSWORD"] = password
        try:
            pg_run(args.postgres_bin, "initdb", "-D", cluster, "--username=restore", "--auth=scram-sha-256",
                   "--locale=C", "--encoding=UTF8", "--no-sync", f"--pwfile={password_file}", env=env)
        finally:
            password_file.unlink(missing_ok=True)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        db = ("-h", "127.0.0.1", "-p", str(port), "-U", "restore")
        try:
            pg_run(args.postgres_bin, "pg_ctl", "-w", "-t", "25", "-D", cluster, "-l", work / "postgres.log",
                   "-o", f"-p {port} -c listen_addresses=127.0.0.1 -c shared_buffers=16MB", "start", env=env)
            pg_run(args.postgres_bin, "createdb", *db, DB_NAME, env=env)
            pg_run(args.postgres_bin, "pg_restore", *db, "--exit-on-error", "--no-owner", "--no-privileges",
                   "--single-transaction", "-d", DB_NAME, data=archive, env=env)
            restored = monotonic()
            sql = """SELECT json_build_object('tables',count(*),
                     'orders',(SELECT count(*) FROM public.orders),
                     'outbox',(SELECT count(*) FROM public.outbox_events),
                     'listen',current_setting('listen_addresses'),
                     'engine',current_setting('server_version'))
                     FROM pg_tables WHERE schemaname='public';"""
            records = json.loads(pg_run(
                args.postgres_bin, "psql", *db, "-XAt", "-v", "ON_ERROR_STOP=1", "-d", DB_NAME, "-c", sql, env=env))
            if records["listen"] != "127.0.0.1" or records["tables"] < 20:
                raise RuntimeError("The restored schema or isolation check failed")

            # Importing app initializes its module-level Flask app. Isolate
            # that initialization as well as the PostgreSQL application below.
            for key in tuple(os.environ):
                if key.startswith(("AWS_", "ERP_SMTP_", "AZURE_", "VOICE_RECORDINGS_")):
                    os.environ.pop(key)
            os.environ.update(DATABASE_PATH=str(work / "import.sqlite"), DATABASE_URL="", DB_SECRET_ARN="",
                              BOOTSTRAP_ADMIN_PASSWORD="", OUTBOX_RETRY_INTERVAL="0", AUTO_DISPATCH_EVENTS="false")
            sys.path.insert(0, str(RELEASE))
            from app import create_app

            owner_url = f"postgresql://restore:{password}@127.0.0.1:{port}/{DB_NAME}"
            database_url, permissions = owner_url, {}
            if args.restricted_runtime:
                database_url, permissions = prepare_restricted_roles(args.postgres_bin, db, env, work, owner_url, port)
            application = create_app({
                "DATABASE_URL": database_url,
                "DATABASE_SCHEMA_MODE": "verify" if args.restricted_runtime else "migrate",
                "SECRET_KEY": secrets.token_urlsafe(32),
                "BOOTSTRAP_ADMIN_USERNAME": f"restore-admin-{secrets.token_hex(5)}@example.invalid",
                "BOOTSTRAP_ADMIN_PASSWORD": secrets.token_urlsafe(26),
                "RESET_BOOTSTRAP_ADMIN_PASSWORD": False,
                "FORCE_INITIAL_PASSWORD_CHANGE": False,
                "SESSION_COOKIE_SECURE": False,
                "AUTO_DISPATCH_EVENTS": False,
                "OUTBOX_RETRY_INTERVAL": 0,
                "VOICE_RECORDINGS_ENABLED": False,
                "INTERNAL_ERP_ENABLED": True,
            })
            checks, orders = verify_portal(application, exercise_writes=args.restricted_runtime)
            if orders != min(records["orders"], 50):
                raise RuntimeError("ERP order count differs from the restored database")
            done = monotonic()
        finally:
            if (cluster / "postmaster.pid").exists():
                pg_run(args.postgres_bin, "pg_ctl", "-w", "-t", "25", "-D", cluster, "-m", "fast", "stop", env=env)

    return {
        "capturedUTC": datetime.now(timezone.utc).isoformat(),
        "backup": manifest["object"],
        "backupCreatedUTC": manifest["source_started_utc"],
        "verifiedManifest": {
            key: manifest[key] for key in
            ("object", "source_started_utc", "archive_sha256", "cipher_sha256", "archive_bytes")
        },
        "release": (RELEASE / "BUILD_REVISION").read_text().strip(),
        "destination": "workstation loopback, isolated from production",
        "azureBlobAndKeyVault": True,
        "archiveAndCiphertextSHA256Verified": True,
        "awsApisDuringExercise": False,
        "externalIntegrationsEnabled": False,
        "postgreSQL": records,
        "restrictedRoleChecks": permissions,
        "ordersSeenByERP": orders,
        "http": checks,
        "seconds": {
            "downloadAndDecrypt": round(materialized - start, 3),
            "isolatedPostgresRestored": round(restored - start, 3),
            "erpAndChecksCompleted": round(done - start, 3),
        },
        "ephemeralClusterRemoved": not cluster.exists(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="Trusted SHA-256 manifest for a scheduled backup")
    parser.add_argument("--postgres-bin", type=Path, required=True, help="Directory with initdb, pg_ctl and pg_restore")
    parser.add_argument("--restricted-runtime", action="store_true", help="Verify with separate ERP and backup SQL roles")
    try:
        print(json.dumps(rehearse(parser.parse_args()), indent=2))
    except (OSError, RuntimeError, KeyError, ValueError, subprocess.TimeoutExpired) as error:
        print(str(error) if isinstance(error, RuntimeError) else type(error).__name__, file=sys.stderr)
        sys.exit(1)
