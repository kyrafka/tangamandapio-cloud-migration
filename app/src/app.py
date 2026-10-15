import json
import hashlib
import hmac
import logging
import math
import os
import re
import secrets
import socket
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, current_app, g, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from .erp_service import grant_default_erp_roles, initialize_erp_database, register_erp_routes


LOGGER = logging.getLogger("tangamandapio.api")


def _alarm_sns_client(config, unsigned=False):
    """Create an SNS client scoped by the app's AWS region configuration."""
    factory = config.get("ALARM_SNS_CLIENT_FACTORY")
    if factory:
        return factory(unsigned=unsigned)
    configured_client = config.get("ALARM_SNS_CLIENT")
    if configured_client is not None:
        return configured_client
    import boto3

    client_options = {"region_name": config.get("AWS_REGION_NAME") or None}
    if unsigned:
        from botocore import UNSIGNED
        from botocore.config import Config

        client_options["config"] = Config(signature_version=UNSIGNED)
    return boto3.client("sns", **client_options)


class DatabaseRateLimitStore:
    """Persist login counters in the shared application database."""

    clock = time.time

    def __init__(self, database_target):
        self.database_target = database_target

    def get(self, key):
        with connect(self.database_target) as connection:
            row = connection.execute(
                "SELECT failures, locked_until FROM login_attempts WHERE attempt_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {"failures": row["failures"], "locked_until": row["locked_until"]}

    def put(self, key, entry, now):
        with connect(self.database_target) as connection:
            connection.execute(
                """
                INSERT INTO login_attempts (attempt_key, failures, locked_until)
                VALUES (?, ?, ?)
                ON CONFLICT (attempt_key) DO UPDATE SET
                    failures = excluded.failures,
                    locked_until = excluded.locked_until
                """,
                (key, entry["failures"], entry["locked_until"]),
            )
            connection.commit()

    def record_failure(self, key, now, max_attempts, lockout_seconds):
        """Increment atomically so concurrent workers cannot lose failures."""
        with connect(self.database_target) as connection:
            connection.execute(
                """
                INSERT INTO login_attempts (attempt_key, failures, locked_until)
                VALUES (?, 1, CASE WHEN ? <= 1 THEN ? + ? ELSE 0 END)
                ON CONFLICT (attempt_key) DO UPDATE SET
                    failures = CASE
                        WHEN login_attempts.locked_until > ? THEN login_attempts.failures
                        WHEN login_attempts.failures >= ? THEN 1
                        ELSE login_attempts.failures + 1
                    END,
                    locked_until = CASE
                        WHEN login_attempts.locked_until > ? THEN login_attempts.locked_until
                        WHEN (
                            CASE WHEN login_attempts.failures >= ? THEN 1
                            ELSE login_attempts.failures + 1 END
                        ) >= ? THEN ? + ?
                        ELSE 0
                    END
                """,
                (
                    key,
                    max_attempts,
                    now,
                    lockout_seconds,
                    now,
                    max_attempts,
                    now,
                    max_attempts,
                    max_attempts,
                    now,
                    lockout_seconds,
                ),
            )
            connection.commit()

    def delete(self, key):
        with connect(self.database_target) as connection:
            connection.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (key,))
            connection.commit()


class LoginRateLimiter:
    """Limit repeated authentication failures across app processes."""

    def __init__(self, store, max_attempts=5, lockout_seconds=300, clock=None):
        self.store = store
        self.max_attempts = int(max_attempts)
        self.lockout_seconds = int(lockout_seconds)
        self._clock = clock or store.clock

    @property
    def enabled(self):
        return self.max_attempts > 0 and self.lockout_seconds > 0

    def retry_after(self, key):
        if not self.enabled:
            return 0.0
        now = self._clock()
        entry = self.store.get(key)
        if entry is None or now >= entry["locked_until"]:
            return 0.0
        return entry["locked_until"] - now

    def record_failure(self, key):
        if not self.enabled:
            return
        now = self._clock()
        if hasattr(self.store, "record_failure"):
            self.store.record_failure(
                key, now, self.max_attempts, self.lockout_seconds
            )
            return
        entry = self.store.get(key) or {"failures": 0, "locked_until": 0.0}
        if entry["failures"] >= self.max_attempts and now >= entry["locked_until"]:
            entry["failures"] = 0
        entry["failures"] += 1
        if entry["failures"] >= self.max_attempts:
            entry["locked_until"] = now + self.lockout_seconds
        self.store.put(key, entry, now)

    def reset(self, key):
        self.store.delete(key)


def create_app(test_config=None):
    static_folder = Path(__file__).parent / "static"
    app = Flask(__name__, static_folder=str(static_folder), static_url_path="")
    app.config.from_mapping(
        DATABASE_URL=os.getenv("DATABASE_URL", "").strip(),
        DATABASE_PATH=os.getenv(
            "DATABASE_PATH", str(Path(tempfile.gettempdir()) / "tangamandapio.db")
        ),
        AZURE_FULFILLMENT_URL=os.getenv("AZURE_FULFILLMENT_URL", ""),
        AZURE_FUNCTION_KEY=os.getenv("AZURE_FUNCTION_KEY", ""),
        AWS_REGION_NAME=os.getenv("AWS_REGION_NAME", "").strip(),
        ALARM_NOTIFICATION_TOPIC_ARN=os.getenv("ALARM_NOTIFICATION_TOPIC_ARN", "").strip(),
        METRICS_ENABLED=os.getenv("METRICS_ENABLED", "false").lower()
        in {"1", "true", "yes"},
        ERP_SMTP_HOST=os.getenv("ERP_SMTP_HOST", "").strip(),
        ERP_SMTP_PORT=os.getenv("ERP_SMTP_PORT", "587"),
        ERP_SMTP_SECURITY=os.getenv("ERP_SMTP_SECURITY", "starttls").strip().lower(),
        ERP_SMTP_USERNAME=os.getenv("ERP_SMTP_USERNAME", ""),
        ERP_SMTP_PASSWORD=os.getenv("ERP_SMTP_PASSWORD", ""),
        ERP_SMTP_FROM=os.getenv("ERP_SMTP_FROM", "no-reply@tangamandapio.local").strip(),
        ERP_SMTP_RECIPIENT_DOMAIN=os.getenv("ERP_SMTP_RECIPIENT_DOMAIN", "").strip().lower(),
        AUTO_DISPATCH_EVENTS=os.getenv("AUTO_DISPATCH_EVENTS", "true").lower()
        in {"1", "true", "yes"},
        SECRET_KEY=os.getenv("APP_SESSION_SECRET", "development-only-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"},
        CSRF_ENABLED=os.getenv("CSRF_ENABLED", "true").lower() in {"1", "true", "yes"},
        BOOTSTRAP_ADMIN_USERNAME=os.getenv(
            "BOOTSTRAP_ADMIN_USERNAME", "admin@tangamandapio.local"
        ),
        BOOTSTRAP_ADMIN_PASSWORD=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""),
        FORCE_BOOTSTRAP_PASSWORD_CHANGE=os.getenv(
            "FORCE_BOOTSTRAP_PASSWORD_CHANGE", "true"
        ).lower() in {"1", "true", "yes"},
        FORCE_INITIAL_PASSWORD_CHANGE=os.getenv(
            "FORCE_INITIAL_PASSWORD_CHANGE", "true"
        ).lower() in {"1", "true", "yes"},
        LOGIN_RATE_LIMIT_MAX=int(os.getenv("LOGIN_RATE_LIMIT_MAX", "5")),
        LOGIN_RATE_LIMIT_SECONDS=int(os.getenv("LOGIN_RATE_LIMIT_SECONDS", "300")),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    database_path = configured_database_target(app.config)
    if not is_postgresql(database_path):
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    initialize_database(database_path)
    ensure_portal_bootstrap(app, database_path)
    app.extensions["login_rate_limiter"] = LoginRateLimiter(
        store=DatabaseRateLimitStore(database_path),
        max_attempts=app.config["LOGIN_RATE_LIMIT_MAX"],
        lockout_seconds=app.config["LOGIN_RATE_LIMIT_SECONDS"],
    )
    app.extensions["metrics"] = {
        "requests_total": 0,
        "orders_created_total": 0,
        "outbox_delivered_total": 0,
        "outbox_failed_total": 0,
    }

    @app.before_request
    def start_request_observation():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.before_request
    def reject_cross_origin_writes():
        if not app.config["CSRF_ENABLED"] or request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        source = request.headers.get("Origin") or request.headers.get("Referer")
        if not source:
            return None
        try:
            parsed = urlsplit(source)
        except ValueError:
            parsed = None
        if (
            parsed is None
            or parsed.scheme not in {"http", "https"}
            or parsed.netloc.casefold() != request.host.casefold()
        ):
            LOGGER.warning(json.dumps({
                "event": "cross_origin_denied",
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
            }))
            return jsonify(error="cross_origin_denied"), 403
        return None

    @app.before_request
    def require_csrf_token():
        if not app.config["CSRF_ENABLED"] or request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        expected = session.get("csrf_token")
        provided = request.headers.get("X-CSRF-Token", "")
        if not expected or not provided or not hmac.compare_digest(expected, provided):
            LOGGER.warning(json.dumps({
                "event": "csrf_token_denied",
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
            }))
            return jsonify(error="csrf_token_required"), 403
        return None

    @app.before_request
    def require_temporary_password_change():
        if not request.path.startswith("/api/") or request.path in {
            "/api/auth/login",
            "/api/auth/logout",
            "/api/auth/session",
            "/api/auth/password",
        }:
            return None
        user = current_portal_user(database_path)
        if user and user["must_change_password"]:
            return jsonify(error="password_change_required"), 428
        return None

    @app.after_request
    def secure_and_observe(response):
        app.extensions["metrics"]["requests_total"] += 1
        response.headers["X-Request-ID"] = g.get("request_id", str(uuid.uuid4()))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'; script-src 'self'; "
            "style-src 'self'"
        )
        existing_cache_control = response.headers.get("Cache-Control", "").lower()
        if "no-store" not in existing_cache_control:
            asset_name = Path(request.path).name
            is_static_asset = request.path.startswith(("/assets/", "/images/"))
            is_content_versioned = bool(
                re.fullmatch(r"index-[A-Za-z0-9_-]{8,}\.(?:js|css)", asset_name)
                or re.fullmatch(r".+-[0-9a-f]{12}\.[A-Za-z0-9]+", asset_name)
                or re.fullmatch(
                    r".+-v[0-9]+\.(?:png|jpe?g|webp|avif|svg)", asset_name
                )
            )
            if is_static_asset and is_content_versioned:
                response.headers["Cache-Control"] = (
                    "public, max-age=31536000, immutable"
                )
            elif response.mimetype == "text/html":
                response.headers["Cache-Control"] = (
                    "no-cache, max-age=0, must-revalidate"
                )
            else:
                response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        LOGGER.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": response.headers["X-Request-ID"],
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(
                        (time.perf_counter() - g.get("request_started_at", time.perf_counter()))
                        * 1000,
                        2,
                    ),
                    "instance": socket.gethostname(),
                }
            )
        )
        return response

    @app.get("/metrics")
    def metrics():
        if not app.config["METRICS_ENABLED"]:
            return "", 404
        user = current_portal_user(configured_database_target(app.config))
        if user is None:
            return jsonify(error="authentication_required"), 401
        if user["role"] != "admin":
            return jsonify(error="insufficient_role"), 403
        values = app.extensions["metrics"]
        lines = [
            "# HELP tangamandapio_http_requests_total Total HTTP responses generated by the API.",
            "# TYPE tangamandapio_http_requests_total counter",
            f"tangamandapio_http_requests_total {values['requests_total']}",
            "# HELP tangamandapio_orders_created_total Orders durably created in the local outbox demo.",
            "# TYPE tangamandapio_orders_created_total counter",
            f"tangamandapio_orders_created_total {values['orders_created_total']}",
            "# HELP tangamandapio_outbox_events_total Outbox delivery attempts grouped by result.",
            "# TYPE tangamandapio_outbox_events_total counter",
            f"tangamandapio_outbox_events_total{{result=\"delivered\"}} {values['outbox_delivered_total']}",
            f"tangamandapio_outbox_events_total{{result=\"failed\"}} {values['outbox_failed_total']}",
        ]
        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not username or not password:
            return jsonify(error="credentials_required"), 400
        limiter = app.extensions["login_rate_limiter"]
        limiter_key = hmac.new(
            str(app.config["SECRET_KEY"]).encode("utf-8"),
            f"{request.remote_addr or 'unknown'}\0{username}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        retry_after = limiter.retry_after(limiter_key)
        if retry_after > 0:
            wait_seconds = int(retry_after) + 1
            LOGGER.warning(json.dumps({"event": "login_rate_limited", "request_id": g.request_id}))
            return (
                jsonify(error="too_many_attempts", retry_after=wait_seconds),
                429,
                {"Retry-After": str(wait_seconds)},
            )
        with connect(database_path) as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash, role, company_id, active,
                       auth_version, must_change_password
                FROM portal_users WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if row is None or not row["active"] or not check_password_hash(row["password_hash"], password):
            limiter.record_failure(limiter_key)
            LOGGER.warning(json.dumps({"event": "login_denied", "request_id": g.request_id}))
            return jsonify(error="invalid_credentials"), 401
        limiter.reset(limiter_key)
        session.clear()
        session["portal_user_id"] = row["id"]
        session["portal_user_version"] = row["auth_version"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        write_audit(database_path, row["id"], "auth.login", "portal_user", row["id"])
        return jsonify(user=portal_user(database_path, row["id"]), csrf_token=session["csrf_token"])

    @app.post("/api/auth/logout")
    def logout():
        user = current_portal_user(database_path)
        if user:
            write_audit(database_path, user["id"], "auth.logout", "portal_user", user["id"])
        session.clear()
        return "", 204

    @app.get("/api/auth/session")
    def session_status():
        user = current_portal_user(database_path)
        if not session.get("csrf_token"):
            session["csrf_token"] = secrets.token_urlsafe(32)
        if user is None:
            return jsonify(authenticated=False, csrf_token=session["csrf_token"]), 200
        return jsonify(authenticated=True, user=user, csrf_token=session["csrf_token"])

    @app.post("/api/auth/password")
    def change_own_password():
        user = current_portal_user(database_path)
        if user is None:
            return jsonify(error="authentication_required"), 401
        payload = request.get_json(silent=True) or {}
        current_password = str(payload.get("current_password", ""))
        new_password = str(payload.get("new_password", ""))
        if len(new_password) < 12 or len(new_password) > 256:
            return jsonify(error="invalid_new_password"), 400

        with connect(database_path) as connection:
            row = connection.execute(
                "SELECT password_hash FROM portal_users WHERE id = ? AND active = TRUE",
                (user["id"],),
            ).fetchone()
            if row is None or not check_password_hash(row["password_hash"], current_password):
                return jsonify(error="current_password_invalid"), 403
            if check_password_hash(row["password_hash"], new_password):
                return jsonify(error="password_reuse_not_allowed"), 400
            connection.execute(
                """
                UPDATE portal_users
                SET password_hash = ?, must_change_password = FALSE,
                    auth_version = auth_version + 1
                WHERE id = ?
                """,
                (generate_password_hash(new_password), user["id"]),
            )
            insert_audit(
                connection,
                user["id"],
                "auth.password_change",
                "portal_user",
                user["id"],
                {"sessions_revoked": True},
            )
            connection.commit()
        session.clear()
        return jsonify(password_changed=True, reauthenticate=True)

    @app.get("/api")
    def index():
        return jsonify(
            service="Tangamandapio Cloud Demo",
            endpoints=["/health", "/ready", "/api/orders", "/api/multicloud"],
        )

    @app.get("/")
    def web_index():
        if (static_folder / "index.html").is_file():
            return send_from_directory(static_folder, "index.html")
        return index()

    @app.get("/administracion")
    def administration_console():
        user = current_portal_user(database_path)
        if user is None:
            return redirect("/", code=303)
        if user["role"] != "admin":
            return "Acceso restringido a Administración.", 403
        return send_from_directory(static_folder / "admin", "index.html")

    @app.get("/health")
    def health():
        database_status = "ok"
        try:
            with connect(database_path) as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception:
            database_status = "error"

        status_code = 200 if database_status == "ok" else 503
        return (
            jsonify(
                status="ok" if status_code == 200 else "degraded",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            status_code,
        )

    @app.get("/ready")
    def ready():
        try:
            with connect(database_path) as connection:
                connection.execute("SELECT 1").fetchone()
            return jsonify(status="ready")
        except Exception:
            return jsonify(status="not_ready"), 503

    @app.get("/api/orders")
    @require_roles("customer", "sales", "warehouse", "operations", "admin", "auditor")
    def list_orders():
        user = g.portal_user
        query = """
            SELECT o.id, o.customer, o.total, o.reference, o.status, o.created_at,
                   c.name AS company, creator.username AS created_by
            FROM orders AS o
            LEFT JOIN companies AS c ON c.id = o.company_id
            LEFT JOIN portal_users AS creator ON creator.id = o.created_by
        """
        params = ()
        if user["role"] == "customer":
            query += " WHERE o.company_id = ?"
            params = (user["company_id"],)
        query += " ORDER BY o.id DESC LIMIT 50"
        with connect(database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/orders")
    @require_roles("customer", "sales", "admin")
    def create_order():
        payload = request.get_json(silent=True) or {}
        customer = str(payload.get("customer", "")).strip()
        reference = str(payload.get("reference", "")).strip()
        user = g.portal_user

        try:
            total = float(payload.get("total"))
        except (TypeError, ValueError):
            total = -1

        if (
            not customer
            or len(customer) > 120
            or not math.isfinite(total)
            or total < 0
            or total > 1_000_000
            or len(reference) > 80
        ):
            return (
                jsonify(
                    error="customer (1-120 caracteres) y total (0-1000000) son obligatorios"
                ),
                400,
            )

        created_at = datetime.now(timezone.utc).isoformat()
        with connect(database_path) as connection:
            order_id = insert_and_return_id(
                connection,
                """
                INSERT INTO orders (customer, total, created_at, company_id, created_by, reference, status)
                VALUES (?, ?, ?, ?, ?, ?, 'created')
                """,
                (customer, total, created_at, user["company_id"], user["id"], reference or None),
            )
            event_id = f"evt-{uuid.uuid4().hex}"
            event_payload = {
                "event_id": event_id,
                "event_type": "order.created",
                "schema_version": "1.0",
                "source": "aws-order-core",
                "occurred_at": created_at,
                "order": {
                    "id": order_id,
                    "customer": customer,
                    "total": total,
                    "created_at": created_at,
                },
            }
            connection.execute(
                """
                INSERT INTO outbox_events(event_id, order_id, payload, status, attempts, created_at)
                VALUES (?, ?, ?, 'pending', 0, ?)
                """,
                (event_id, order_id, json.dumps(event_payload, separators=(",", ":")), created_at),
            )
            connection.commit()

        app.extensions["metrics"]["orders_created_total"] += 1
        write_audit(
            database_path,
            user["id"],
            "order.create",
            "order",
            order_id,
            {"company_id": user["company_id"], "reference": reference},
        )
        delivery = {"status": "pending", "event_id": event_id}
        if app.config["AUTO_DISPATCH_EVENTS"]:
            delivery = dispatch_outbox_event(app, database_path, event_id)

        return (
            jsonify(
                id=order_id,
                customer=customer,
                total=total,
                reference=reference or None,
                status="created",
                created_at=created_at,
                instance=socket.gethostname(),
                fulfillment=delivery,
            ),
            201,
        )

    @app.get("/api/outbox")
    @require_roles("operations", "admin", "auditor", "warehouse")
    def list_outbox():
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT event_id, order_id, status, attempts, last_error, created_at, delivered_at
                FROM outbox_events ORDER BY created_at DESC LIMIT 30
                """
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/outbox/<event_id>/retry")
    @require_roles("operations", "admin")
    def retry_outbox(event_id):
        delivery = dispatch_outbox_event(app, database_path, event_id)
        if delivery.get("status") == "not_found":
            return jsonify(error="event_not_found"), 404
        write_audit(
            database_path,
            g.portal_user["id"],
            "outbox.retry",
            "outbox_event",
            event_id,
            {"result": delivery.get("status")},
        )
        return jsonify(delivery)

    @app.get("/api/dashboard")
    @require_roles("customer", "sales", "warehouse", "operations", "admin", "auditor")
    def dashboard():
        user = g.portal_user
        with connect(database_path) as connection:
            order_query = "SELECT COUNT(*) AS count FROM orders"
            params = ()
            if user["role"] == "customer":
                order_query += " WHERE company_id = ?"
                params = (user["company_id"],)
            order_count = connection.execute(order_query, params).fetchone()["count"]
            pending = connection.execute(
                "SELECT COUNT(*) AS count FROM outbox_events WHERE status != 'delivered'"
            ).fetchone()["count"]
            delivered = connection.execute(
                "SELECT COUNT(*) AS count FROM outbox_events WHERE status = 'delivered'"
            ).fetchone()["count"]
        return jsonify(
            orders=order_count,
            outbox={"pending": pending, "delivered": delivered},
            role=user["role"],
            company=user["company"],
        )

    @app.get("/api/admin/users")
    @require_roles("admin")
    def list_users():
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT u.id, u.username, u.role, u.active, u.must_change_password,
                       u.company_id, u.created_at, c.name AS company
                FROM portal_users AS u JOIN companies AS c ON c.id = u.company_id
                ORDER BY u.id DESC
                """
            ).fetchall()
        return jsonify([
            {**dict(row), "must_change_password": bool(row["must_change_password"])}
            for row in rows
        ])

    @app.post("/api/admin/companies")
    @require_roles("admin")
    def create_company():
        """Provision an isolated B2B tenant before assigning its users.

        This deliberately remains an administrator-only operation: a user must
        never select an arbitrary tenant while registering an account.
        """
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name", "")).strip()
        slug = str(payload.get("slug", "")).strip().lower()
        if (
            not name
            or len(name) > 160
            or not slug
            or len(slug) > 80
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in slug)
        ):
            return jsonify(error="invalid_company_payload"), 400
        with connect(database_path) as connection:
            try:
                company_id = insert_and_return_id(
                    connection,
                    "INSERT INTO companies(name, slug, created_at) VALUES (?, ?, ?)",
                    (name, slug, datetime.now(timezone.utc).isoformat()),
                )
                insert_audit(
                    connection,
                    g.portal_user["id"],
                    "company.create",
                    "company",
                    company_id,
                    {"slug": slug},
                )
                connection.commit()
            except Exception as error:
                if is_integrity_error(error):
                    return jsonify(error="company_slug_already_exists"), 409
                raise
        return jsonify(id=company_id, name=name, slug=slug), 201

    @app.get("/api/admin/companies")
    @require_roles("admin")
    def list_companies():
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.name, c.slug, c.created_at, COUNT(u.id) AS users
                FROM companies AS c
                LEFT JOIN portal_users AS u ON u.company_id = c.id
                GROUP BY c.id, c.name, c.slug, c.created_at
                ORDER BY LOWER(c.name)
                """
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/admin/users")
    @require_roles("admin")
    def create_user():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip().lower()
        password = str(payload.get("password", ""))
        role = str(payload.get("role", "")).strip().lower()
        company_id = payload.get("company_id") or g.portal_user["company_id"]
        if not username or len(username) > 160 or len(password) < 12 or role not in PORTAL_ROLES:
            return jsonify(error="invalid_user_payload"), 400
        with connect(database_path) as connection:
            company = connection.execute("SELECT id FROM companies WHERE id = ?", (company_id,)).fetchone()
            if company is None:
                return jsonify(error="company_not_found"), 400
            try:
                user_id = insert_and_return_id(
                    connection,
                    """
                    INSERT INTO portal_users(
                        username, password_hash, role, company_id, active,
                        created_at, must_change_password
                    )
                    VALUES (?, ?, ?, ?, TRUE, ?, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        role,
                        company_id,
                        datetime.now(timezone.utc).isoformat(),
                        bool(app.config["FORCE_INITIAL_PASSWORD_CHANGE"]),
                    ),
                )
                grant_default_erp_roles(connection, user_id, role, g.portal_user["id"])
                insert_audit(
                    connection,
                    g.portal_user["id"],
                    "user.create",
                    "portal_user",
                    user_id,
                    {"role": role, "company_id": company_id},
                )
                connection.commit()
            except Exception as error:
                if is_integrity_error(error):
                    return jsonify(error="username_already_exists"), 409
                raise
        return jsonify(user=portal_user(database_path, user_id)), 201

    @app.post("/api/admin/users/<int:user_id>/reset-password")
    @require_roles("admin")
    def reset_user_password(user_id):
        if user_id == g.portal_user["id"]:
            return jsonify(error="use_self_service_password_change"), 409
        temporary_password = secrets.token_urlsafe(18)
        with connect(database_path) as connection:
            target = connection.execute(
                "SELECT id, username FROM portal_users WHERE id = ? AND active = TRUE",
                (user_id,),
            ).fetchone()
            if target is None:
                return jsonify(error="user_not_found"), 404
            connection.execute(
                """
                UPDATE portal_users
                SET password_hash = ?, must_change_password = TRUE,
                    auth_version = auth_version + 1
                WHERE id = ?
                """,
                (generate_password_hash(temporary_password), user_id),
            )
            insert_audit(
                connection,
                g.portal_user["id"],
                "user.password_reset",
                "portal_user",
                user_id,
                {"temporary_password_issued": True, "sessions_revoked": True},
            )
            connection.commit()
        return jsonify(
            user_id=user_id,
            username=target["username"],
            temporary_password=temporary_password,
            must_change_password=True,
        )

    @app.patch("/api/admin/users/<int:user_id>")
    @require_roles("admin")
    def update_user(user_id):
        payload = request.get_json(silent=True) or {}
        allowed_fields = {"role", "company_id", "active"}
        if not payload or set(payload) - allowed_fields:
            return jsonify(error="invalid_user_update"), 400

        with connect(database_path) as connection:
            current = connection.execute(
                "SELECT id, role, company_id, active FROM portal_users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if current is None:
                return jsonify(error="user_not_found"), 404

            role = str(payload.get("role", current["role"])).strip().lower()
            company_id = payload.get("company_id", current["company_id"])
            active = payload.get("active", bool(current["active"]))
            if role not in PORTAL_ROLES or type(active) is not bool:
                return jsonify(error="invalid_user_update"), 400
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return jsonify(error="invalid_user_update"), 400
            company = connection.execute(
                "SELECT id FROM companies WHERE id = ?", (company_id,)
            ).fetchone()
            if company is None:
                return jsonify(error="company_not_found"), 400

            if user_id == g.portal_user["id"] and (not active or role != "admin"):
                return jsonify(error="cannot_remove_own_admin_access"), 409
            removing_admin = bool(current["active"]) and current["role"] == "admin" and (
                not active or role != "admin"
            )
            if removing_admin:
                other_admin = connection.execute(
                    """
                    SELECT id FROM portal_users
                    WHERE role = 'admin' AND active = TRUE AND id != ?
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
                if other_admin is None:
                    return jsonify(error="cannot_remove_last_admin"), 409

            connection.execute(
                """
                UPDATE portal_users
                SET role = ?, company_id = ?, active = ?, auth_version = auth_version + 1
                WHERE id = ?
                """,
                (role, company_id, active, user_id),
            )
            insert_audit(
                connection,
                g.portal_user["id"],
                "user.update",
                "portal_user",
                user_id,
                {"role": role, "company_id": company_id, "active": active, "sessions_revoked": True},
            )
            connection.commit()
        return jsonify(user=portal_user(database_path, user_id))

    def alarm_notification_topic_arn():
        return app.config.get("ALARM_NOTIFICATION_TOPIC_ARN", "").strip()

    def list_alarm_email_subscriptions(client, topic_arn):
        subscriptions = []
        next_token = None
        while True:
            parameters = {"TopicArn": topic_arn}
            if next_token:
                parameters["NextToken"] = next_token
            page = client.list_subscriptions_by_topic(**parameters)
            for item in page.get("Subscriptions", []):
                if item.get("Protocol") != "email":
                    continue
                subscription_arn = item.get("SubscriptionArn", "")
                subscriptions.append({
                    "protocol": "email",
                    "endpoint": item.get("Endpoint", ""),
                    "subscription_arn": subscription_arn,
                    "status": "confirmed" if subscription_arn.startswith(topic_arn + ":") else "pending_confirmation",
                })
            next_token = page.get("NextToken")
            if not next_token:
                break
        return sorted(subscriptions, key=lambda item: item["endpoint"].casefold())

    def alarm_sns_error(error, operation):
        error_code = "unknown"
        if isinstance(getattr(error, "response", None), dict):
            error_code = error.response.get("Error", {}).get("Code", error_code)
        LOGGER.warning(json.dumps({
            "event": "alarm_subscription_operation_failed",
            "operation": operation,
            "error_code": error_code,
            "actor_id": g.portal_user["id"],
        }))
        if error_code in {"AccessDenied", "AuthorizationError", "NotAuthorized"}:
            return jsonify(error="alarm_service_access_denied"), 503
        if error_code in {"InvalidParameter", "InvalidParameterValue"}:
            return jsonify(error="alarm_subscription_invalid"), 400
        return jsonify(error="alarm_service_unavailable"), 503

    @app.get("/api/admin/alarm-subscriptions")
    @require_roles("admin")
    def get_alarm_subscriptions():
        topic_arn = alarm_notification_topic_arn()
        if not topic_arn:
            return jsonify(error="alarm_notifications_not_configured"), 503
        try:
            subscriptions = list_alarm_email_subscriptions(_alarm_sns_client(app.config), topic_arn)
        except Exception as error:
            return alarm_sns_error(error, "list")
        return jsonify(topic_configured=True, subscriptions=subscriptions, confirmation_required=True)

    @app.post("/api/admin/alarm-subscriptions")
    @require_roles("admin")
    def add_alarm_subscription():
        topic_arn = alarm_notification_topic_arn()
        if not topic_arn:
            return jsonify(error="alarm_notifications_not_configured"), 503
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return jsonify(error="invalid_alarm_email"), 400
        try:
            client = _alarm_sns_client(app.config)
            existing = next((item for item in list_alarm_email_subscriptions(client, topic_arn)
                             if item["endpoint"].casefold() == email.casefold()), None)
            if existing:
                return jsonify(subscription=existing, already_exists=True), 200
            result = client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email, ReturnSubscriptionArn=True)
            subscription_arn = result.get("SubscriptionArn", "PendingConfirmation")
            status = "confirmed" if subscription_arn.startswith(topic_arn + ":") else "pending_confirmation"
            subject_id = hashlib.sha256(email.casefold().encode("utf-8")).hexdigest()[:20]
            write_audit(database_path, g.portal_user["id"], "alarm_subscription.create", "sns_email_subscription",
                        subject_id, {"protocol": "email", "status": status})
        except Exception as error:
            return alarm_sns_error(error, "subscribe")
        return jsonify(subscription={"protocol": "email", "endpoint": email,
                                     "subscription_arn": subscription_arn, "status": status},
                       already_exists=False), 201

    @app.delete("/api/admin/alarm-subscriptions")
    @require_roles("admin")
    def remove_alarm_subscription():
        topic_arn = alarm_notification_topic_arn()
        if not topic_arn:
            return jsonify(error="alarm_notifications_not_configured"), 503
        payload = request.get_json(silent=True) or {}
        subscription_arn = str(payload.get("subscription_arn", "")).strip()
        if not subscription_arn or not subscription_arn.startswith(topic_arn + ":"):
            return jsonify(error="alarm_subscription_not_found"), 404
        try:
            signed_client = _alarm_sns_client(app.config)
            current = next((item for item in list_alarm_email_subscriptions(signed_client, topic_arn)
                            if item["subscription_arn"] == subscription_arn), None)
            if current is None:
                return jsonify(error="alarm_subscription_not_found"), 404
            if current["status"] != "confirmed":
                return jsonify(error="alarm_subscription_pending_confirmation"), 409
            # SNS permits this operation without signing by default; the route first verifies
            # the exact confirmed email ARN against this one configured topic and admin session.
            _alarm_sns_client(app.config, unsigned=True).unsubscribe(SubscriptionArn=subscription_arn)
            write_audit(database_path, g.portal_user["id"], "alarm_subscription.remove", "sns_email_subscription",
                        hashlib.sha256(subscription_arn.encode("utf-8")).hexdigest()[:20],
                        {"protocol": "email", "status": "removed"})
        except Exception as error:
            return alarm_sns_error(error, "unsubscribe")
        return jsonify(status="removed"), 200

    @app.get("/api/audit")
    @require_roles("admin", "operations", "auditor")
    def audit_log():
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT a.id, a.action, a.subject_type, a.subject_id, a.detail, a.created_at,
                       COALESCE(u.username, 'system') AS actor
                FROM audit_log AS a LEFT JOIN portal_users AS u ON u.id = a.user_id
                ORDER BY a.id DESC LIMIT 100
                """
            ).fetchall()
        results = []
        for row in rows:
            entry = dict(row)
            if entry["detail"]:
                entry["detail"] = json.loads(entry["detail"])
            results.append(entry)
        return jsonify(results)

    @app.get("/api/multicloud")
    @require_roles("operations", "admin", "auditor", "warehouse")
    def multicloud_status():
        service_url = app.config["AZURE_FULFILLMENT_URL"].rstrip("/")
        if not service_url:
            return jsonify(status="not_configured"), 503

        headers = {"Accept": "application/json"}
        token = app.config["AZURE_FUNCTION_KEY"]
        if token:
            headers["x-functions-key"] = token

        upstream_request = Request(f"{azure_health_url(service_url)}", headers=headers)
        try:
            with urlopen(upstream_request, timeout=3) as response:
                upstream_body = json.loads(response.read().decode("utf-8"))
            return jsonify(status="connected", provider="Azure", upstream=upstream_body)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            return jsonify(status="unavailable", error=type(error).__name__), 502

    @app.post("/api/multicloud/sync")
    @require_roles("operations", "admin")
    def multicloud_sync():
        service_url = app.config["AZURE_FULFILLMENT_URL"].rstrip("/")
        if not service_url:
            return jsonify(status="not_configured"), 503

        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify(error="se requiere un objeto JSON"), 400

        body = json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        token = app.config["AZURE_FUNCTION_KEY"]
        if token:
            headers["x-functions-key"] = token

        upstream_request = Request(azure_event_url(service_url), data=body, headers=headers, method="POST")
        try:
            with urlopen(upstream_request, timeout=3) as response:
                upstream_body = json.loads(response.read().decode("utf-8"))
            return jsonify(status="synchronized", provider="Azure", upstream=upstream_body)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            return jsonify(status="unavailable", error=type(error).__name__), 502

    @app.get("/<path:asset_path>")
    def web_assets(asset_path):
        if (static_folder / asset_path).is_file():
            return send_from_directory(static_folder, asset_path)
        if (static_folder / "index.html").is_file() and not asset_path.startswith("api/"):
            return send_from_directory(static_folder, "index.html")
        return jsonify(error="not_found"), 404

    register_erp_routes(
        app,
        database_path,
        connect=connect,
        insert_and_return_id=insert_and_return_id,
        write_audit=write_audit,
        require_roles=require_roles,
        dispatch_outbox_event=dispatch_outbox_event,
    )

    return app


def configured_database_target(config):
    """Prefer a managed PostgreSQL URL when the environment supplies one."""
    return config.get("DATABASE_URL") or config["DATABASE_PATH"]


def is_postgresql(database_target):
    return str(database_target).startswith(("postgresql://", "postgres://"))


class PostgreSQLConnection:
    """Small DB-API adapter so the application keeps one query surface.

    SQLite uses ``?`` placeholders while psycopg2 uses ``%s``. Keeping the
    conversion here makes local tests and managed RDS follow the same business
    logic without copying route implementations.
    """

    def __init__(self, raw_connection):
        self.raw_connection = raw_connection

    def execute(self, statement, params=()):
        from psycopg2.extras import RealDictCursor

        cursor = self.raw_connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(statement.replace("?", "%s"), params)
        return cursor

    def commit(self):
        self.raw_connection.commit()

    def close(self):
        self.raw_connection.close()


def connect(database_target):
    if is_postgresql(database_target):
        try:
            import psycopg2
        except ImportError as error:
            raise RuntimeError("PostgreSQL requires psycopg2-binary in the application image") from error
        return closing(PostgreSQLConnection(psycopg2.connect(database_target, connect_timeout=5)))
    connection = sqlite3.connect(database_target)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def insert_and_return_id(connection, statement, params):
    if isinstance(connection, PostgreSQLConnection):
        row = connection.execute(f"{statement.strip().rstrip(';')} RETURNING id", params).fetchone()
        return row["id"]
    return connection.execute(statement, params).lastrowid


def is_integrity_error(error):
    if isinstance(error, sqlite3.IntegrityError):
        return True
    try:
        import psycopg2

        return isinstance(error, psycopg2.IntegrityError)
    except ImportError:
        return False


PORTAL_ROLES = {"customer", "sales", "warehouse", "operations", "admin", "auditor"}


def portal_user(database_path, user_id, include_auth_version=False):
    if not user_id:
        return None
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT u.id, u.username, u.role, u.company_id, u.active,
                   u.must_change_password, u.auth_version, c.name AS company
            FROM portal_users AS u
            LEFT JOIN companies AS c ON c.id = u.company_id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None or not row["active"]:
        return None
    user = dict(row)
    user["must_change_password"] = bool(user["must_change_password"])
    if not include_auth_version:
        user.pop("auth_version", None)
    return user


def current_portal_user(database_path):
    user = portal_user(
        database_path, session.get("portal_user_id"), include_auth_version=True
    )
    if user is None:
        return None
    session_version = session.get("portal_user_version")
    if session_version is None or int(session_version) != int(user["auth_version"]):
        return None
    user.pop("auth_version", None)
    return user


def require_roles(*roles):
    allowed = set(roles)

    def decorator(endpoint):
        @wraps(endpoint)
        def wrapped(*args, **kwargs):
            user = current_portal_user(configured_database_target(current_app.config))
            if user is None:
                return jsonify(error="authentication_required"), 401
            if allowed and user["role"] not in allowed:
                return jsonify(error="insufficient_role"), 403
            g.portal_user = user
            return endpoint(*args, **kwargs)

        return wrapped

    return decorator


def insert_audit(connection, user_id, action, subject_type, subject_id=None, detail=None):
    """Append an audit row to the caller's transaction."""
    connection.execute(
        """
        INSERT INTO audit_log(user_id, action, subject_type, subject_id, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            subject_type,
            str(subject_id) if subject_id is not None else None,
            json.dumps(detail, separators=(",", ":")) if detail else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def write_audit(database_path, user_id, action, subject_type, subject_id=None, detail=None):
    with connect(database_path) as connection:
        insert_audit(connection, user_id, action, subject_type, subject_id, detail)
        connection.commit()


def ensure_column(connection, table, column, definition):
    if isinstance(connection, PostgreSQLConnection):
        row = connection.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            ) AS exists
            """,
            (table, column),
        ).fetchone()
        if not row["exists"]:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_portal_bootstrap(app, database_path):
    """Create the first tenant and administrator only when a password is supplied.

    Production receives the password from a Secrets Manager-backed environment
    variable. Local tests provide it through their isolated configuration.
    """
    with connect(database_path) as connection:
        company = connection.execute(
            "SELECT id FROM companies WHERE slug = ?", ("tangamandapio",)
        ).fetchone()
        if company is None:
            try:
                company_id = insert_and_return_id(
                    connection,
                    "INSERT INTO companies(name, slug, created_at) VALUES (?, ?, ?)",
                    ("Tangamandapio S.A.C.", "tangamandapio", datetime.now(timezone.utc).isoformat()),
                )
            except Exception as error:
                if not is_integrity_error(error):
                    raise
                company = connection.execute(
                    "SELECT id FROM companies WHERE slug = ?", ("tangamandapio",)
                ).fetchone()
                company_id = company["id"]
        else:
            company_id = company["id"]

        password = app.config.get("BOOTSTRAP_ADMIN_PASSWORD", "")
        if password:
            connection.execute(
                """
                INSERT INTO portal_users(
                    username, password_hash, role, company_id, active,
                    created_at, must_change_password
                )
                VALUES (?, ?, 'admin', ?, TRUE, ?, ?)
                ON CONFLICT(username) DO NOTHING
                """,
                (
                    app.config["BOOTSTRAP_ADMIN_USERNAME"].strip().lower(),
                    generate_password_hash(password),
                    company_id,
                    datetime.now(timezone.utc).isoformat(),
                    bool(app.config["FORCE_BOOTSTRAP_PASSWORD_CHANGE"]),
                ),
            )
        for user in connection.execute("SELECT id, role FROM portal_users WHERE active = TRUE").fetchall():
            grant_default_erp_roles(connection, user["id"], user["role"])
        connection.commit()


def initialize_database(database_path):
    with connect(database_path) as connection:
        if isinstance(connection, PostgreSQLConnection):
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portal_users (
                    id BIGSERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('customer','sales','warehouse','operations','admin','auditor')),
                    company_id BIGINT NOT NULL REFERENCES companies(id),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES portal_users(id),
                    action TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT,
                    detail TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGSERIAL PRIMARY KEY,
                    customer TEXT NOT NULL,
                    total NUMERIC(12,2) NOT NULL CHECK (total >= 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS outbox_events (
                    event_id TEXT PRIMARY KEY,
                    order_id BIGINT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    delivered_at TIMESTAMPTZ
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    attempt_key TEXT PRIMARY KEY,
                    failures INTEGER NOT NULL DEFAULT 0,
                    locked_until DOUBLE PRECISION NOT NULL DEFAULT 0
                )
                """
            )
            ensure_column(connection, "portal_users", "auth_version", "BIGINT NOT NULL DEFAULT 1")
            ensure_column(connection, "portal_users", "must_change_password", "BOOLEAN NOT NULL DEFAULT FALSE")
            ensure_column(connection, "orders", "company_id", "BIGINT")
            ensure_column(connection, "orders", "created_by", "BIGINT")
            ensure_column(connection, "orders", "reference", "TEXT")
            ensure_column(connection, "orders", "status", "TEXT NOT NULL DEFAULT 'created'")
            initialize_erp_database(connection, postgres=True)
            connection.commit()
            return

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS portal_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('customer','sales','warehouse','operations','admin','auditor')),
                company_id INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT,
                detail TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES portal_users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                total REAL NOT NULL CHECK (total >= 0),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox_events (
                event_id TEXT PRIMARY KEY,
                order_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'failed')),
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at TEXT NOT NULL,
                delivered_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_attempts (
                attempt_key TEXT PRIMARY KEY,
                failures INTEGER NOT NULL DEFAULT 0,
                locked_until REAL NOT NULL DEFAULT 0
            )
            """
        )
        ensure_column(connection, "portal_users", "auth_version", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "portal_users", "must_change_password", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "orders", "company_id", "INTEGER")
        ensure_column(connection, "orders", "created_by", "INTEGER")
        ensure_column(connection, "orders", "reference", "TEXT")
        ensure_column(connection, "orders", "status", "TEXT NOT NULL DEFAULT 'created'")
        initialize_erp_database(connection, postgres=False)
        connection.commit()


def azure_event_url(service_url):
    base = service_url.rstrip("/")
    return base if base.endswith("/api/fulfillment/events") else f"{base}/api/fulfillment/events"


def azure_health_url(service_url):
    base = service_url.rstrip("/")
    if base.endswith("/api/fulfillment/events"):
        base = base[: -len("/api/fulfillment/events")]
    return f"{base}/api/health" if ".azurewebsites.net" in base else f"{base}/health"


def dispatch_outbox_event(app, database_path, event_id):
    """Deliver an already committed event. A failure never rolls back the order."""
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT payload, attempts FROM outbox_events WHERE event_id = ?", (event_id,)
        ).fetchone()
    if row is None:
        return {"status": "not_found", "event_id": event_id}

    service_url = app.config["AZURE_FULFILLMENT_URL"].rstrip("/")
    if not service_url:
        return {"status": "pending", "event_id": event_id, "reason": "azure_not_configured"}

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    token = app.config["AZURE_FUNCTION_KEY"]
    if token:
        headers["x-functions-key"] = token

    try:
        upstream_request = Request(
            azure_event_url(service_url),
            data=row["payload"].encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(upstream_request, timeout=5) as response:
            upstream_body = json.loads(response.read().decode("utf-8"))
        status = upstream_body.get("status", "accepted")
        if status not in {"queued", "queued_duplicate", "duplicate", "accepted"}:
            raise ValueError("unexpected_upstream_status")
        with connect(database_path) as connection:
            connection.execute(
                """
                UPDATE outbox_events
                SET status = 'delivered', attempts = attempts + 1, last_error = NULL, delivered_at = ?
                WHERE event_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), event_id),
            )
            connection.commit()
        app.extensions["metrics"]["outbox_delivered_total"] += 1
        return {"status": "delivered", "event_id": event_id, "upstream": status}
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        with connect(database_path) as connection:
            connection.execute(
                """
                UPDATE outbox_events
                SET status = 'failed', attempts = attempts + 1, last_error = ?
                WHERE event_id = ?
                """,
                (type(error).__name__, event_id),
            )
            connection.commit()
        app.extensions["metrics"]["outbox_failed_total"] += 1
        return {"status": "pending", "event_id": event_id, "reason": type(error).__name__}


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
