import base64
import hmac
import hashlib
import json
import logging
import math
import os
import secrets
import socket
import sqlite3
import tempfile
import threading
import time
import uuid
from io import BytesIO
from contextlib import closing
from functools import wraps
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from flask import (
    Flask,
    current_app,
    g,
    has_request_context,
    jsonify,
    redirect,
    request,
    send_file,
    send_from_directory,
    session,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from cloud_observability import collect_cloudwatch_metrics


LOGGER = logging.getLogger("tangamandapio.api")
WMS_DEMO_CATALOG = {
    "SKU-ARROZ-001": {"name": "Arroz premium · saco 50 kg", "unit_price": 42.50},
    "SKU-AZUCAR-001": {"name": "Azúcar rubia · saco 50 kg", "unit_price": 37.50},
    "SKU-ACEITE-001": {"name": "Aceite vegetal · caja x 12", "unit_price": 86.00},
}


def env_int(name, default):
    """Entero de entorno sin tumbar el arranque si el valor viene mal escrito."""
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        LOGGER.warning(json.dumps({"event": "invalid_env_integer", "name": name}))
        return default


def default_voice_recordings_bucket(database_secret_arn):
    """Derive the dedicated bucket name used by this CloudFormation project.

    An explicit VOICE_RECORDINGS_BUCKET always wins. The AWS deployment already
    injects DB_SECRET_ARN into the service environment, which gives us the
    account and region without another startup network call.
    """
    arn_parts = str(database_secret_arn or "").split(":")
    if len(arn_parts) < 6 or arn_parts[0] != "arn" or arn_parts[2] != "secretsmanager":
        return ""
    account_id, region = arn_parts[4], arn_parts[3]
    if not account_id.isdigit() or not region:
        return ""
    return "tangamandapio-voice-{}-{}".format(account_id, region)


def configure_logging():
    """El logger de la app no hereda nada: sin handler los INFO se pierden."""
    logger = logging.getLogger("tangamandapio.api")
    logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False


class MemoryRateLimitStore:
    """Mapa de intentos en memoria: sirve a una sola instancia y a los tests."""

    def __init__(self, limit=4096):
        self.entries = {}
        self.limit = int(limit)

    @property
    def size(self):
        return len(self.entries)

    def get(self, key):
        return self.entries.get(key)

    def put(self, key, entry, now):
        if self.size > self.limit:
            self.prune(now, max_attempts=entry.get("failures", 0))
        self.entries[key] = entry

    def delete(self, key):
        self.entries.pop(key, None)

    def prune(self, now, max_attempts):
        expired = [
            key
            for key, entry in self.entries.items()
            if now >= entry["locked_until"] and entry["failures"] < max_attempts
        ]
        for key in expired:
            self.entries.pop(key, None)


class DatabaseRateLimitStore:
    """Contador de intentos guardado en la misma base de datos que los pedidos.

    El mapa en memoria era propio de cada proceso: con dos instancias y dos
    workers de gunicorn el umbral efectivo llegaba a multiplicarse por cuatro.
    La tabla `login_attempts` vive en la base de datos, así que el límite es
    del servicio y no del nodo, y sobrevive a un reinicio.

    El reloj es de pared (`time.time`) y no `time.monotonic`, porque dos
    procesos solo pueden comparar marcas compartidas.
    """

    clock = time.time

    def __init__(self, database_target):
        self.database_target = database_target

    @property
    def size(self):
        with connect(self.database_target) as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM login_attempts").fetchone()
        return int(row["total"])

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

    def delete(self, key):
        with connect(self.database_target) as connection:
            connection.execute("DELETE FROM login_attempts WHERE attempt_key = ?", (key,))
            connection.commit()

    def prune(self, now, max_attempts):
        with connect(self.database_target) as connection:
            connection.execute(
                "DELETE FROM login_attempts WHERE locked_until <= ? AND failures < ?",
                (now, max_attempts),
            )
            connection.commit()


class LoginRateLimiter:
    """Bloquea intentos de login repetidos por IP y usuario.

    El estado lo aporta el almacén: `MemoryRateLimitStore` por defecto y
    `DatabaseRateLimitStore` cuando el servicio corre sobre PostgreSQL con
    varias instancias. Con `max_attempts <= 0` queda desactivado.
    """

    def __init__(self, max_attempts=5, lockout_seconds=300, store=None, clock=None):
        self.max_attempts = int(max_attempts)
        self.lockout_seconds = int(lockout_seconds)
        self.store = store if store is not None else MemoryRateLimitStore()
        shared_clock = getattr(self.store, "clock", None)
        self._clock = clock or shared_clock or time.monotonic

    @property
    def enabled(self):
        return self.max_attempts > 0 and self.lockout_seconds > 0

    def retry_after(self, key, now=None):
        """Segundos restantes de bloqueo; 0 significa que puede intentar."""
        if not self.enabled:
            return 0.0
        now = self._clock() if now is None else now
        entry = self.store.get(key)
        if entry is None or now >= entry["locked_until"]:
            return 0.0
        return entry["locked_until"] - now

    def record_failure(self, key, now=None):
        if not self.enabled:
            return
        now = self._clock() if now is None else now
        entry = self.store.get(key)
        if entry is None:
            entry = {"failures": 0, "locked_until": 0.0}
        if entry["failures"] >= self.max_attempts and now >= entry["locked_until"]:
            entry["failures"] = 0
        entry["failures"] += 1
        if entry["failures"] >= self.max_attempts:
            entry["locked_until"] = now + self.lockout_seconds
        self.store.put(key, entry, now)

    def reset(self, key):
        self.store.delete(key)



def create_app(test_config=None):
    configure_logging()
    static_folder = Path(__file__).parent / "static"
    local_data_root = (
        Path(os.getenv("LOCALAPPDATA"))
        if os.getenv("LOCALAPPDATA")
        else Path.home() / ".local" / "share"
    ) / "Tangamandapio"
    app = Flask(__name__, static_folder=str(static_folder), static_url_path="")
    app.config.from_mapping(
        DATABASE_URL=os.getenv("DATABASE_URL", "").strip(),
        DATABASE_PATH=os.getenv(
            "DATABASE_PATH", str(local_data_root / "tangamandapio.db")
        ),
        AZURE_FULFILLMENT_URL=os.getenv("AZURE_FULFILLMENT_URL", ""),
        AZURE_FUNCTION_KEY=os.getenv("AZURE_FUNCTION_KEY", ""),
        AUTO_DISPATCH_EVENTS=os.getenv("AUTO_DISPATCH_EVENTS", "true").lower()
        in {"1", "true", "yes"},
        # 0 (por defecto) mantiene el reintento apagado: solo se enciende cuando
        # el entorno lo declara, para no dejar hilos en imports y en tests.
        OUTBOX_RETRY_INTERVAL=env_int("OUTBOX_RETRY_INTERVAL", 0),
        OUTBOX_RETRY_MAX_ATTEMPTS=env_int("OUTBOX_RETRY_MAX_ATTEMPTS", 10),
        LOGIN_RATE_LIMIT_MAX=env_int("LOGIN_RATE_LIMIT_MAX", 5),
        LOGIN_RATE_LIMIT_SECONDS=env_int("LOGIN_RATE_LIMIT_SECONDS", 300),
        SECRET_KEY=os.getenv("APP_SESSION_SECRET", "development-only-change-me"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"},
        BOOTSTRAP_ADMIN_USERNAME=os.getenv(
            "BOOTSTRAP_ADMIN_USERNAME", "admin@tangamandapio.local"
        ),
        BOOTSTRAP_ADMIN_PASSWORD=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""),
        # Solo para una demostración académica controlada. Si no se declara,
        # no se crean cuentas de telefonía con credenciales conocidas.
        DEMO_VOICE_PASSWORD=os.getenv("DEMO_VOICE_PASSWORD", ""),
        # Producción solo graba cuando puede usar el bucket privado dedicado.
        # SQLite conserva el almacén local para pruebas aisladas.
        DB_SECRET_ARN=os.getenv("DB_SECRET_ARN", "").strip(),
        AWS_REGION_NAME=os.getenv("AWS_REGION_NAME", "").strip(),
        CLOUDWATCH_REGION_NAME=os.getenv("CLOUDWATCH_REGION_NAME", os.getenv("AWS_REGION_NAME", "")).strip(),
        CLOUDWATCH_LOAD_BALANCER_FULL_NAME=os.getenv("CLOUDWATCH_LOAD_BALANCER_FULL_NAME", "").strip(),
        CLOUDWATCH_TARGET_GROUP_FULL_NAME=os.getenv("CLOUDWATCH_TARGET_GROUP_FULL_NAME", "").strip(),
        CLOUDWATCH_RDS_INSTANCE_ID=os.getenv("CLOUDWATCH_RDS_INSTANCE_ID", "").strip(),
        CLOUDWATCH_AUTO_SCALING_GROUP=os.getenv("CLOUDWATCH_AUTO_SCALING_GROUP", "").strip(),
        CLOUDWATCH_WAF_WEB_ACL_NAME=os.getenv("CLOUDWATCH_WAF_WEB_ACL_NAME", "").strip(),
        CLOUDWATCH_WAF_REGION=os.getenv("CLOUDWATCH_WAF_REGION", "").strip(),
        VOICE_RECORDINGS_BUCKET=(
            os.getenv("VOICE_RECORDINGS_BUCKET", "").strip()
            or default_voice_recordings_bucket(os.getenv("DB_SECRET_ARN", ""))
        ),
        VOICE_RECORDINGS_PREFIX=os.getenv("VOICE_RECORDINGS_PREFIX", "voice-recordings").strip("/"),
        VOICE_RECORDINGS_ENABLED=os.getenv(
            "VOICE_RECORDINGS_ENABLED",
            "true"
            if (
                not os.getenv("DATABASE_URL", "").strip()
                or os.getenv("VOICE_RECORDINGS_BUCKET", "").strip()
                or default_voice_recordings_bucket(os.getenv("DB_SECRET_ARN", ""))
            )
            else "false",
        ).lower()
        in {"1", "true", "yes"},
        VOICE_RECORDINGS_DIR=os.getenv("VOICE_RECORDINGS_DIR", "").strip(),
        VOICE_RECORDING_RETENTION_DAYS=env_int("VOICE_RECORDING_RETENTION_DAYS", 30),
        VOICE_RECORDING_MAX_BYTES=env_int("VOICE_RECORDING_MAX_BYTES", 15 * 1024 * 1024),
        WEBRTC_TURN_URLS=tuple(
            url.strip()
            for url in os.getenv("WEBRTC_TURN_URLS", "").split(",")
            if url.strip()
        ),
        WEBRTC_TURN_SHARED_SECRET=os.getenv("WEBRTC_TURN_SHARED_SECRET", ""),
        WEBRTC_TURN_CREDENTIAL_TTL_SECONDS=env_int(
            "WEBRTC_TURN_CREDENTIAL_TTL_SECONDS", 600
        ),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    # El ALB termina TLS y reenvía X-Forwarded-Proto. Sin esto Flask siempre ve
    # request.is_secure=False, no emite HSTS y genera URLs internas en http.
    # Solo es seguro porque el puerto 8080 es alcanzable únicamente desde el SG del ALB.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1, x_port=1)

    if test_config:
        app.config.update(test_config)

    if is_postgresql(configured_database_target(app.config)) and not app.config["VOICE_RECORDINGS_BUCKET"]:
        if app.config["VOICE_RECORDINGS_ENABLED"]:
            LOGGER.error("Voice recordings disabled: a private S3 bucket is required for PostgreSQL deployments")
        app.config["VOICE_RECORDINGS_ENABLED"] = False
    app.extensions["voice_recording_s3_client"] = app.config.get("VOICE_RECORDING_S3_CLIENT")

    database_path = configured_database_target(app.config)
    if not app.config["VOICE_RECORDINGS_DIR"]:
        recordings_root = (
            Path(app.instance_path) / "voice_recordings"
            if is_postgresql(database_path)
            else local_data_root / "voice_recordings"
        )
        app.config["VOICE_RECORDINGS_DIR"] = str(recordings_root)
    if not is_postgresql(database_path):
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    initialize_database(database_path)

    app.extensions["voice_recording_purge_last"] = 0.0

    def maybe_purge_expired_recordings():
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return
        now_monotonic = time.monotonic()
        if now_monotonic - app.extensions["voice_recording_purge_last"] < 3600:
            return
        purge_expired_voice_recordings(
            database_path,
            app.config["VOICE_RECORDINGS_DIR"],
            datetime.now(timezone.utc).isoformat(),
            s3_client=voice_recording_s3_client(app) if app.config["VOICE_RECORDINGS_BUCKET"] else None,
            s3_bucket=app.config["VOICE_RECORDINGS_BUCKET"],
            s3_prefix=app.config["VOICE_RECORDINGS_PREFIX"],
        )
        app.extensions["voice_recording_purge_last"] = now_monotonic

    maybe_purge_expired_recordings()
    ensure_portal_bootstrap(app, database_path)
    app.extensions["metrics"] = {
        "requests_total": 0,
        "orders_created_total": 0,
        "outbox_delivered_total": 0,
        "outbox_failed_total": 0,
    }
    # El contador vive en la base de datos: con dos instancias detrás del ALB
    # cada proceso ve los mismos intentos y el umbral deja de ser por nodo.
    app.extensions["login_rate_limiter"] = LoginRateLimiter(
        max_attempts=app.config["LOGIN_RATE_LIMIT_MAX"],
        lockout_seconds=app.config["LOGIN_RATE_LIMIT_SECONDS"],
        store=DatabaseRateLimitStore(database_path),
    )

    # Reintento programado del outbox: el despacho no depende de que un cliente
    # vuelva a llamar al endpoint manual. Desactivado con OUTBOX_RETRY_INTERVAL=0
    # y siempre apagado en tests para no dejar hilos sueltos.
    start_outbox_retry_worker(app, database_path)

    @app.before_request
    def start_request_observation():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.before_request
    def reject_cross_origin_writes():
        """Refuerza SameSite: un sitio ajeno no puede escribir con nuestra cookie.

        Solo se exige coherencia cuando el navegador informa Origin o Referer;
        clientes sin navegador (curl, integraciones) siguen autorizados.
        """
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        header = request.headers.get("Origin") or request.headers.get("Referer")
        if not header:
            return None
        if urlparse(header).netloc == request.host:
            return None
        LOGGER.warning(
            json.dumps(
                {
                    "event": "cross_origin_denied",
                    "request_id": g.get("request_id"),
                    "method": request.method,
                    "path": request.path,
                    "origin": urlparse(header).netloc,
                }
            )
        )
        return jsonify(error="cross_origin_denied"), 403

    @app.before_request
    def require_csrf_token():
        """Exige un token de sincronía para toda escritura con sesión abierta.

        El token vive dentro de la cookie de sesión, que es HttpOnly: un sitio
        ajeno puede hacer que el navegador envíe la cookie, pero no puede leerla
        para rellenar la cabecera. Solo se aplica cuando la sesión ya tiene
        token, es decir, desde que el cliente consultó `/api/auth/session`;
        antes de eso la sesión no está vinculada a nada que valga la pena
        proteger y los clientes sin navegador siguen funcionando.
        """
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        expected = session.get("csrf_token")
        if not expected:
            return None
        provided = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(expected, provided):
            LOGGER.warning(
                json.dumps(
                    {
                        "event": "csrf_token_denied",
                        "request_id": g.get("request_id"),
                        "method": request.method,
                        "path": request.path,
                    }
                )
            )
            return jsonify(error="csrf_token_required"), 403
        return None

    @app.before_request
    def require_temporary_password_rotation():
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
            "style-src 'self'; media-src 'self' blob:"
        )
        # La llamada interna usa únicamente audio WebRTC iniciado por una
        # acción explícita del usuario. No pedimos cámara ni concedemos otros
        # dispositivos al portal.
        response.headers["Permissions-Policy"] = "microphone=(self), camera=(self)"
        if "no-store" not in response.headers.get("Cache-Control", "").lower():
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
                    "user_id": session.get("portal_user_id"),
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
        limiter_key = "{}|{}".format(request.remote_addr or "unknown", username)
        retry_after = limiter.retry_after(limiter_key)
        if retry_after > 0:
            LOGGER.warning(
                json.dumps(
                    {
                        "event": "login_rate_limited",
                        "request_id": g.request_id,
                        "username": username,
                        "retry_after": int(retry_after) + 1,
                    }
                )
            )
            return (
                jsonify(error="too_many_attempts", retry_after=int(retry_after) + 1),
                429,
                {"Retry-After": str(int(retry_after) + 1)},
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
            LOGGER.warning(json.dumps({"event": "login_denied", "username": username, "request_id": g.request_id}))
            return jsonify(error="invalid_credentials"), 401
        limiter.reset(limiter_key)
        # Rotación: el cookie de sesión anterior se descarta por completo; el
        # token que lo acompañaba deja de valer y la siguiente consulta a
        # /api/auth/session emite otro distinto.
        session.clear()
        session["portal_user_id"] = row["id"]
        session["portal_user_version"] = row["auth_version"]
        write_audit(database_path, row["id"], "auth.login", "portal_user", row["id"])
        return jsonify(user=portal_user(database_path, row["id"]))

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
        # El token se emite también sin sesión abierta: el portal lo pide antes
        # de login y a partir de ahí toda escritura debe llevarlo.
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
            connection.execute(
                """
                UPDATE portal_users
                SET password_hash = ?, must_change_password = FALSE,
                    auth_version = auth_version + 1
                WHERE id = ?
                """,
                (generate_password_hash(new_password), user["id"]),
            )
            connection.commit()
        write_audit(database_path, user["id"], "auth.password_change", "portal_user", user["id"])
        session.clear()
        return jsonify(password_changed=True, reauthenticate=True)

    @app.get("/api")
    def index():
        return jsonify(
            service="Tangamandapio Cloud Demo",
            instance=socket.gethostname(),
            endpoints=[
                "/health",
                "/ready",
                "/api/orders",
                "/api/multicloud",
                "/api/voice/directory",
            ],
        )

    @app.get("/")
    def web_index():
        if (static_folder / "index.html").is_file():
            return send_from_directory(static_folder, "index.html")
        return index()

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
                database=database_status,
                instance=socket.gethostname(),
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            status_code,
        )

    @app.get("/ready")
    def ready():
        try:
            with connect(database_path) as connection:
                connection.execute("SELECT 1").fetchone()
            return jsonify(status="ready", dependencies={"database": "ok"})
        except Exception:
            return jsonify(status="not_ready", dependencies={"database": "error"}), 503

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

    @app.get("/api/orders/<int:order_id>")
    @require_roles("customer", "sales", "warehouse", "operations", "admin", "auditor")
    def order_detail(order_id):
        """Detalle de un pedido con su línea de tiempo WMS.

        La lista responde con las filas de la tabla; aquí se añaden los
        eventos del outbox y las entradas de auditoría del mismo pedido, que
        es lo que hace falta para entender por qué está en ese estado. Un
        cliente solo ve los pedidos de su empresa, igual que en la lista.
        """
        user = g.portal_user
        company_filter = " AND o.company_id = ?" if user["role"] == "customer" else ""
        params = [order_id]
        if company_filter:
            params.append(user["company_id"])
        with connect(database_path) as connection:
            order = connection.execute(
                """
                SELECT o.id, o.customer, o.total, o.reference, o.status, o.created_at,
                       c.name AS company, creator.username AS created_by
                FROM orders AS o
                LEFT JOIN companies AS c ON c.id = o.company_id
                LEFT JOIN portal_users AS creator ON creator.id = o.created_by
                WHERE o.id = ?
                """
                + company_filter,
                tuple(params),
            ).fetchone()
            if order is None:
                return jsonify(error="order_not_found"), 404
            events = connection.execute(
                """
                SELECT event_id, status, attempts, last_error, created_at, delivered_at
                FROM outbox_events WHERE order_id = ? ORDER BY created_at
                """,
                (order_id,),
            ).fetchall()
            audits = connection.execute(
                """
                SELECT action, created_at FROM audit_log
                WHERE subject_type = 'order' AND subject_id = ?
                ORDER BY created_at
                """,
                (str(order_id),),
            ).fetchall()

        timeline = [
            {
                "kind": "order",
                "at": order["created_at"],
                "title": "Pedido creado",
                "detail": order["reference"] or "sin referencia",
            }
        ]
        for audit in audits:
            timeline.append(
                {
                    "kind": "audit",
                    "at": audit["created_at"],
                    "title": "Registro de auditoria",
                    "detail": audit["action"],
                }
            )
        for event in events:
            timeline.append(
                {
                    "kind": "outbox",
                    "at": event["created_at"],
                    "title": "Evento encolado en el outbox",
                    "detail": "{} - {}".format(event["event_id"], event["status"]),
                }
            )
            if event["last_error"]:
                timeline.append(
                    {
                        "kind": "error",
                        "at": event["created_at"],
                        "title": "Ultimo error de entrega",
                        "detail": event["last_error"],
                    }
                )
            if event["delivered_at"]:
                timeline.append(
                    {
                        "kind": "wms",
                        "at": event["delivered_at"],
                        "title": "Entregado al WMS",
                        "detail": "{} intento(s) de reenvio".format(event["attempts"]),
                    }
                )
        timeline.sort(key=lambda entry: entry["at"] or "")

        return jsonify(
            order=dict(order),
            timeline=timeline,
            events=[dict(event) for event in events],
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

    @app.get("/api/wms/inventory")
    @require_roles("operations", "admin")
    def wms_demo_inventory():
        """Read the protected Azure sample-inventory endpoint server-side."""
        service_url = str(app.config.get("AZURE_FULFILLMENT_URL", "")).strip()
        function_key = str(app.config.get("AZURE_FUNCTION_KEY", "")).strip()
        if not service_url or not function_key:
            return jsonify(error="not_configured", provider="Azure"), 503
        upstream_request = Request(
            azure_inventory_url(service_url),
            headers={"Accept": "application/json", "x-functions-key": function_key},
        )
        try:
            with urlopen(upstream_request, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if (
                not isinstance(payload, dict)
                or payload.get("mode") != "demo-inventory-ledger"
                or not isinstance(payload.get("items"), list)
            ):
                return jsonify(error="invalid_azure_response"), 502
            return jsonify(payload)
        except HTTPError:
            return jsonify(error="unavailable", provider="Azure"), 502
        except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return jsonify(error="unavailable", provider="Azure"), 502

    @app.post("/api/wms/demo-orders")
    @require_roles("operations", "admin")
    def create_wms_demo_order():
        """Create an audited, SKU-bearing lab order and durable AWS outbox event."""
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify(error="invalid_request_body"), 400
        sku = str(payload.get("sku", ""))
        quantity = payload.get("quantity")
        if sku not in WMS_DEMO_CATALOG:
            return jsonify(error="invalid_demo_sku"), 400
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 10:
            return jsonify(error="invalid_demo_quantity"), 400

        service_url = str(app.config.get("AZURE_FULFILLMENT_URL", "")).strip()
        function_key = str(app.config.get("AZURE_FUNCTION_KEY", "")).strip()
        if not service_url or not function_key:
            return jsonify(error="not_configured", provider="Azure"), 503
        inventory_request = Request(
            azure_inventory_url(service_url),
            headers={"Accept": "application/json", "x-functions-key": function_key},
        )
        try:
            with urlopen(inventory_request, timeout=4) as response:
                inventory = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return jsonify(error="azure_inventory_unavailable"), 503
        remote_items = inventory.get("items", []) if isinstance(inventory, dict) else []
        remote_item = next(
            (
                item
                for item in remote_items
                if isinstance(item, dict) and item.get("sku") == sku
            ),
            None,
        ) if isinstance(remote_items, list) else None
        if not remote_item or inventory.get("mode") != "demo-inventory-ledger":
            return jsonify(error="azure_inventory_unavailable"), 503
        available = remote_item.get("on_hand")
        if isinstance(available, bool) or not isinstance(available, int):
            return jsonify(error="invalid_azure_response"), 502
        if quantity > available:
            return jsonify(error="insufficient_demo_stock", available=available, sku=sku), 409

        product = WMS_DEMO_CATALOG[sku]
        unit_price = float(product["unit_price"])
        total = round(unit_price * quantity, 2)
        user = g.portal_user
        created_at = datetime.now(timezone.utc).isoformat()
        reference = f"WMS-DEMO-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"
        order_items = [{"sku": sku, "name": product["name"], "quantity": quantity, "unit_price": unit_price}]
        with connect(database_path) as connection:
            order_id = insert_and_return_id(
                connection,
                """
                INSERT INTO orders (customer, total, created_at, company_id, created_by, reference, status, items_json)
                VALUES (?, ?, ?, ?, ?, ?, 'created', ?)
                """,
                (
                    "Pedido de laboratorio · WMS",
                    total,
                    created_at,
                    user["company_id"],
                    user["id"],
                    reference,
                    json.dumps(order_items, separators=(",", ":")),
                ),
            )
            event_id = f"evt-{uuid.uuid4().hex}"
            event_payload = {
                "event_id": event_id,
                "event_type": "order.created",
                "schema_version": "1.0",
                "source": "aws-wms-demo-console",
                "occurred_at": created_at,
                "order": {
                    "id": order_id,
                    "customer": "Pedido de laboratorio · WMS",
                    "total": total,
                    "created_at": created_at,
                    "items": [{"sku": sku, "quantity": quantity}],
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

        write_audit(
            database_path,
            user["id"],
            "wms.demo_order.create",
            "order",
            order_id,
            {"sku": sku, "quantity": quantity, "event_id": event_id},
        )
        delivery = {"status": "pending", "event_id": event_id}
        if app.config["AUTO_DISPATCH_EVENTS"]:
            delivery = dispatch_outbox_event(app, database_path, event_id)
        return jsonify(
            id=order_id,
            reference=reference,
            sku=sku,
            quantity=quantity,
            total=total,
            status="created",
            event_id=event_id,
            fulfillment=delivery,
            note="Pedido ficticio de laboratorio; el resultado actualiza solo el inventario demo de Azure.",
        ), 201

    @app.get("/api/outbox/<event_id>/fulfillment-status")
    @require_roles("operations", "admin", "auditor", "warehouse")
    def outbox_fulfillment_status(event_id):
        """Read the final processing status of an AWS outbox event from Azure."""
        if (
            not 8 <= len(event_id) <= 80
            or not event_id.isascii()
            or not all(character.isalnum() or character in "-_" for character in event_id)
        ):
            return jsonify(error="invalid_event_id"), 400

        with connect(database_path) as connection:
            event = connection.execute(
                "SELECT event_id FROM outbox_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        if event is None:
            return jsonify(error="event_not_found"), 404

        service_url = str(app.config.get("AZURE_FULFILLMENT_URL", "")).strip()
        function_key = str(app.config.get("AZURE_FUNCTION_KEY", "")).strip()
        if not service_url or not function_key:
            return jsonify(status="not_configured", provider="Azure"), 503

        upstream_request = Request(
            azure_event_status_url(service_url, event_id),
            headers={"Accept": "application/json", "x-functions-key": function_key},
        )
        try:
            with urlopen(upstream_request, timeout=3) as response:
                upstream_body = json.loads(response.read().decode("utf-8"))
            if (
                not isinstance(upstream_body, dict)
                or upstream_body.get("event_id") != event_id
                or not isinstance(upstream_body.get("status"), str)
            ):
                return jsonify(error="invalid_azure_response"), 502

            fulfillment_status = upstream_body["status"]
            return jsonify(
                provider="Azure",
                event_id=event_id,
                fulfillment_status=fulfillment_status,
                simulated=(
                    upstream_body.get("mode") == "demo-only"
                    or str(upstream_body.get("mode", "")).startswith("demo-")
                    or fulfillment_status.startswith("simulated_")
                ),
                note=upstream_body.get("note"),
            )
        except HTTPError as error:
            if error.code == 404:
                return jsonify(error="azure_event_not_found", event_id=event_id), 404
            return jsonify(status="unavailable", provider="Azure", error="upstream_http_error"), 502
        except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return jsonify(status="unavailable", provider="Azure", error="upstream_error"), 502

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

    @app.get("/platform")
    def platform_console():
        user = current_portal_user(database_path)
        if user is None:
            return redirect("/", code=303)
        if user["role"] not in {"admin", "operations"}:
            return "Acceso restringido a Administración y Operaciones TI.", 403
        return send_from_directory(static_folder / "platform", "index.html")

    @app.get("/api/platform/overview")
    @require_roles("admin", "operations")
    def platform_overview():
        try:
            window_minutes = int(request.args.get("window", "60"))
            cloudwatch = collect_cloudwatch_metrics(app.config, window_minutes)
        except (TypeError, ValueError):
            return jsonify(error="invalid_metrics_window"), 400
        return jsonify(
            cloudwatch=cloudwatch,
            application={
                "instance": socket.gethostname(),
                "requests_since_worker_start": app.extensions["metrics"]["requests_total"],
                "orders_created_since_worker_start": app.extensions["metrics"]["orders_created_total"],
                "counter_scope": "este proceso web; CloudWatch ALB agrega el tráfico de la capa",
            },
            security={
                "role_enforcement": "backend",
                "csrf": "enabled",
                "session_cookie_secure": bool(app.config["SESSION_COOKIE_SECURE"]),
                "session_cookie_httponly": bool(app.config["SESSION_COOKIE_HTTPONLY"]),
                "recordings_enabled": bool(app.config["VOICE_RECORDINGS_ENABLED"]),
                "database": "postgresql" if is_postgresql(configured_database_target(app.config)) else "sqlite_demo",
            },
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
        return jsonify([dict(row) for row in rows])

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
                connection.commit()
            except Exception as error:
                if is_integrity_error(error):
                    return jsonify(error="company_slug_already_exists"), 409
                raise
        write_audit(
            database_path,
            g.portal_user["id"],
            "company.create",
            "company",
            company_id,
            {"slug": slug},
        )
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
                    INSERT INTO portal_users(username, password_hash, role, company_id, active, created_at)
                    VALUES (?, ?, ?, ?, TRUE, ?)
                    """,
                    (
                        username,
                        generate_password_hash(password),
                        role,
                        company_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                connection.commit()
            except Exception as error:
                if is_integrity_error(error):
                    return jsonify(error="username_already_exists"), 409
                raise
        write_audit(
            database_path,
            g.portal_user["id"],
            "user.create",
            "portal_user",
            user_id,
            {"role": role, "company_id": company_id},
        )
        return jsonify(user=portal_user(database_path, user_id)), 201

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
            connection.commit()

        write_audit(
            database_path,
            g.portal_user["id"],
            "user.update",
            "portal_user",
            user_id,
            {"role": role, "company_id": company_id, "active": active, "sessions_revoked": True},
        )
        return jsonify(user=portal_user(database_path, user_id))

    @app.post("/api/admin/users/<int:user_id>/reset-password")
    @require_roles("admin")
    def reset_user_password(user_id):
        if user_id == g.portal_user["id"]:
            return jsonify(error="use_self_service_password_change"), 409
        temporary_password = secrets.token_urlsafe(18)
        with connect(database_path) as connection:
            target = connection.execute(
                "SELECT id FROM portal_users WHERE id = ?", (user_id,)
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
            connection.commit()
        write_audit(
            database_path,
            g.portal_user["id"],
            "user.password_reset",
            "portal_user",
            user_id,
            {"temporary_password_issued": True, "sessions_revoked": True},
        )
        return jsonify(
            user=portal_user(database_path, user_id),
            temporary_password=temporary_password,
            reveal_once=True,
        )

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

    # --- Telefonía interna WebRTC ---------------------------------------
    # Esta capa es deliberadamente distinta de SIP/PBX: persiste solo la
    # señalización mínima (offer/answer/ICE) y el estado de la llamada. El
    # audio no atraviesa Flask, no se graba y no se almacena en la base.
    @app.get("/api/voice/directory")
    @require_roles(*VOICE_ROLES)
    def voice_directory():
        user = g.portal_user
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, username, role, company_id
                FROM portal_users
                WHERE active = TRUE AND role IN ('sales', 'operations', 'admin') AND id != ?
                ORDER BY username
                """,
                (user["id"],),
            ).fetchall()
        return jsonify(
            [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "role": row["role"],
                    "extension": voice_extension(row["id"]),
                }
                for row in rows
            ]
        )

    @app.get("/api/voice/ice-config")
    @require_roles(*VOICE_ROLES)
    def voice_ice_config():
        now = int(time.time())
        ttl = max(60, min(int(app.config["WEBRTC_TURN_CREDENTIAL_TTL_SECONDS"]), 3600))
        ice_servers = [{"urls": "stun:stun.l.google.com:19302"}]
        secret = str(app.config["WEBRTC_TURN_SHARED_SECRET"] or "")
        turn_urls = app.config["WEBRTC_TURN_URLS"]
        result = {"ice_servers": ice_servers, "turn_configured": bool(secret and turn_urls)}
        if secret and turn_urls:
            expires_at = now + ttl
            username = "{}:{}".format(expires_at, g.portal_user["id"])
            credential = base64.b64encode(
                hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
            ).decode("ascii")
            ice_servers.extend(
                {
                    "urls": url,
                    "username": username,
                    "credential": credential,
                    "credentialType": "password",
                }
                for url in turn_urls
            )
            result["expires_at"] = datetime.fromtimestamp(expires_at, timezone.utc).isoformat()
        return jsonify(result)

    @app.get("/api/voice/calls")
    @require_roles(*VOICE_ROLES)
    def list_voice_calls():
        user = g.portal_user
        expire_voice_calls(database_path)
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT vc.id, vc.caller_user_id, vc.callee_user_id, vc.status,
                       vc.created_at, vc.updated_at, vc.ended_at,
                       caller.username AS caller_username, callee.username AS callee_username
                FROM voice_calls AS vc
                JOIN portal_users AS caller ON caller.id = vc.caller_user_id
                JOIN portal_users AS callee ON callee.id = vc.callee_user_id
                WHERE vc.caller_user_id = ? OR vc.callee_user_id = ?
                ORDER BY vc.updated_at DESC
                LIMIT 30
                """,
                (user["id"], user["id"]),
            ).fetchall()
        return jsonify([voice_call_for_view(row, user["id"]) for row in rows])

    @app.post("/api/voice/calls")
    @require_roles(*VOICE_ROLES)
    def create_voice_call():
        payload = request.get_json(silent=True) or {}
        try:
            callee_id = int(payload.get("callee_id"))
        except (TypeError, ValueError):
            return jsonify(error="voice_callee_required"), 400

        caller = g.portal_user
        if callee_id == caller["id"]:
            return jsonify(error="voice_cannot_call_self"), 400
        with connect(database_path) as connection:
            callee = connection.execute(
                """
                SELECT id, username, role, active FROM portal_users
                WHERE id = ?
                """,
                (callee_id,),
            ).fetchone()
            if (
                callee is None
                or not callee["active"]
                or callee["role"] not in VOICE_ROLES
            ):
                return jsonify(error="voice_recipient_not_available"), 404
            call_id = "call-{}".format(uuid.uuid4().hex)
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO voice_calls(
                    id, caller_user_id, callee_user_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, 'ringing', ?, ?)
                """,
                (call_id, caller["id"], callee_id, now, now),
            )
            connection.commit()

        write_audit(
            database_path,
            caller["id"],
            "voice.call.create",
            "voice_call",
            call_id,
            {"callee_user_id": callee_id},
        )
        return (
            jsonify(
                id=call_id,
                status="ringing",
                direction="outgoing",
                peer={
                    "id": callee["id"],
                    "username": callee["username"],
                    "extension": voice_extension(callee["id"]),
                },
                created_at=now,
            ),
            201,
        )

    @app.get("/api/voice/calls/<call_id>/signals")
    @require_roles(*VOICE_ROLES)
    def get_voice_signals(call_id):
        user = g.portal_user
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            rows = connection.execute(
                """
                SELECT id, kind, payload, created_at, sender_user_id
                FROM voice_signals
                WHERE call_id = ? AND recipient_user_id = ? AND delivered_at IS NULL
                ORDER BY id ASC LIMIT 100
                """,
                (call_id, user["id"]),
            ).fetchall()
            delivered_at = datetime.now(timezone.utc).isoformat()
            signals = []
            for row in rows:
                connection.execute(
                    "UPDATE voice_signals SET delivered_at = ? WHERE id = ? AND delivered_at IS NULL",
                    (delivered_at, row["id"]),
                )
                signals.append(
                    {
                        "id": row["id"],
                        "kind": row["kind"],
                        "payload": json.loads(row["payload"]),
                        "created_at": row["created_at"],
                        "sender_user_id": row["sender_user_id"],
                    }
                )
            connection.commit()
        return jsonify(signals)

    @app.post("/api/voice/calls/<call_id>/signals")
    @require_roles(*VOICE_ROLES)
    def send_voice_signal(call_id):
        user = g.portal_user
        payload = request.get_json(silent=True) or {}
        kind = str(payload.get("kind", "")).strip().lower()
        if kind not in VOICE_SIGNAL_KINDS:
            return jsonify(error="voice_signal_kind_invalid"), 400
        signal_payload = payload.get("payload", {})
        if not isinstance(signal_payload, dict):
            return jsonify(error="voice_signal_payload_invalid"), 400
        try:
            serialized_payload = json.dumps(signal_payload, separators=(",", ":"))
        except (TypeError, ValueError):
            return jsonify(error="voice_signal_payload_invalid"), 400
        if len(serialized_payload.encode("utf-8")) > MAX_VOICE_SIGNAL_BYTES:
            return jsonify(error="voice_signal_payload_too_large"), 413

        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            validation_error = validate_voice_signal(call, user["id"], kind)
            if validation_error:
                return jsonify(error=validation_error), 409

            recipient_id = (
                call["callee_user_id"]
                if call["caller_user_id"] == user["id"]
                else call["caller_user_id"]
            )
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO voice_signals(
                    call_id, sender_user_id, recipient_user_id, kind, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (call_id, user["id"], recipient_id, kind, serialized_payload, now),
            )
            if kind == "answer":
                connection.execute(
                    "UPDATE voice_calls SET status = 'accepted', updated_at = ? WHERE id = ?",
                    (now, call_id),
                )
            elif kind in {"reject", "hangup"}:
                terminal_status = "rejected" if kind == "reject" else "ended"
                connection.execute(
                    """
                    UPDATE voice_calls
                    SET status = ?, updated_at = ?, ended_at = ?
                    WHERE id = ?
                    """,
                    (terminal_status, now, now, call_id),
                )
                connection.execute(
                    "UPDATE voice_recordings SET status = 'declined', updated_at = ? WHERE call_id = ? AND status = 'requested'",
                    (now, call_id),
                )
            else:
                connection.execute(
                    "UPDATE voice_calls SET updated_at = ? WHERE id = ?",
                    (now, call_id),
                )
            connection.commit()

        if kind in {"offer", "answer", "reject", "hangup"}:
            write_audit(
                database_path,
                user["id"],
                "voice.call.{}".format(kind),
                "voice_call",
                call_id,
            )
        return jsonify(status="accepted", kind=kind, call_id=call_id)

    @app.post("/api/voice/calls/<call_id>/recording/request")
    @require_roles(*VOICE_ROLES)
    def request_voice_recording(call_id):
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return jsonify(error="voice_recordings_disabled"), 503
        user = g.portal_user
        now = datetime.now(timezone.utc)
        now_text = now.isoformat()
        expires_at = (now + timedelta(days=max(1, app.config["VOICE_RECORDING_RETENTION_DAYS"]))).isoformat()
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            if call["status"] != "accepted":
                return jsonify(error="voice_call_not_active"), 409
            try:
                connection.execute(
                    """
                    INSERT INTO voice_recordings(
                        call_id, caller_user_id, callee_user_id, requester_user_id,
                        status, caller_consented, callee_consented,
                        created_at, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, 'requested', ?, ?, ?, ?, ?)
                    """,
                    (
                        call_id,
                        call["caller_user_id"],
                        call["callee_user_id"],
                        user["id"],
                        user["id"] == call["caller_user_id"],
                        user["id"] == call["callee_user_id"],
                        now_text,
                        now_text,
                        expires_at,
                    ),
                )
            except Exception as error:
                if is_integrity_error(error):
                    return jsonify(error="voice_recording_already_requested"), 409
                raise
            peer_id = call["callee_user_id"] if user["id"] == call["caller_user_id"] else call["caller_user_id"]
            connection.execute(
                """
                INSERT INTO voice_signals(
                    call_id, sender_user_id, recipient_user_id, kind, payload, created_at
                ) VALUES (?, ?, ?, 'recording_request', '{}', ?)
                """,
                (call_id, user["id"], peer_id, now_text),
            )
            connection.commit()
        write_audit(database_path, user["id"], "voice.recording.request", "voice_call", call_id)
        return jsonify(status="requested", call_id=call_id), 201

    @app.post("/api/voice/calls/<call_id>/recording/consent")
    @require_roles(*VOICE_ROLES)
    def consent_voice_recording(call_id):
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return jsonify(error="voice_recordings_disabled"), 503
        payload = request.get_json(silent=True) or {}
        consent = payload.get("consent")
        if not isinstance(consent, bool):
            return jsonify(error="voice_recording_consent_required"), 400
        user = g.portal_user
        now = datetime.now(timezone.utc).isoformat()
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            recording = connection.execute(
                "SELECT * FROM voice_recordings WHERE call_id = ?", (call_id,)
            ).fetchone()
            if recording is None or recording["status"] != "requested":
                return jsonify(error="voice_recording_request_not_pending"), 409
            if user["id"] == recording["requester_user_id"]:
                return jsonify(error="voice_recording_requester_already_consented"), 409
            if call["status"] != "accepted":
                return jsonify(error="voice_call_not_active"), 409
            status = "approved" if consent else "declined"
            consent_column = "caller_consented" if user["id"] == call["caller_user_id"] else "callee_consented"
            connection.execute(
                f"UPDATE voice_recordings SET status = ?, {consent_column} = ?, updated_at = ? WHERE call_id = ?",
                (status, consent, now, call_id),
            )
            peer_id = call["callee_user_id"] if user["id"] == call["caller_user_id"] else call["caller_user_id"]
            signal_kind = "recording_approved" if consent else "recording_declined"
            connection.execute(
                """
                INSERT INTO voice_signals(
                    call_id, sender_user_id, recipient_user_id, kind, payload, created_at
                ) VALUES (?, ?, ?, ?, '{}', ?)
                """,
                (call_id, user["id"], peer_id, signal_kind, now),
            )
            connection.commit()
        write_audit(
            database_path,
            user["id"],
            "voice.recording.{}".format("consent" if consent else "decline"),
            "voice_call",
            call_id,
        )
        return jsonify(status=status, call_id=call_id)

    @app.post("/api/voice/calls/<call_id>/recording/start")
    @require_roles(*VOICE_ROLES)
    def start_voice_recording(call_id):
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return jsonify(error="voice_recordings_disabled"), 503
        user = g.portal_user
        now = datetime.now(timezone.utc).isoformat()
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            recording = connection.execute(
                "SELECT * FROM voice_recordings WHERE call_id = ?", (call_id,)
            ).fetchone()
            if recording is None:
                return jsonify(error="voice_recording_not_approved"), 409
            if recording["requester_user_id"] != user["id"]:
                return jsonify(error="voice_recording_start_not_allowed"), 403
            if recording["status"] != "approved":
                return jsonify(error="voice_recording_not_approved"), 409
            if (
                call["status"] != "accepted"
                or not recording["caller_consented"]
                or not recording["callee_consented"]
            ):
                return jsonify(error="voice_recording_not_consented"), 409
            updated = connection.execute(
                "UPDATE voice_recordings SET status = 'recording', updated_at = ? WHERE call_id = ? AND status = 'approved'",
                (now, call_id),
            )
            if updated.rowcount != 1:
                connection.commit()
                return jsonify(error="voice_recording_not_approved"), 409
            peer_id = call["callee_user_id"] if user["id"] == call["caller_user_id"] else call["caller_user_id"]
            connection.execute(
                """
                INSERT INTO voice_signals(
                    call_id, sender_user_id, recipient_user_id, kind, payload, created_at
                ) VALUES (?, ?, ?, 'recording_started', '{}', ?)
                """,
                (call_id, user["id"], peer_id, now),
            )
            connection.commit()
        write_audit(database_path, user["id"], "voice.recording.started", "voice_call", call_id)
        return jsonify(status="recording", call_id=call_id)

    @app.post("/api/voice/calls/<call_id>/recording/stop")
    @require_roles(*VOICE_ROLES)
    def stop_voice_recording(call_id):
        user = g.portal_user
        now = datetime.now(timezone.utc).isoformat()
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            recording = connection.execute(
                "SELECT * FROM voice_recordings WHERE call_id = ?", (call_id,)
            ).fetchone()
            if recording is None or recording["status"] not in {"approved", "recording"}:
                return jsonify(error="voice_recording_not_active"), 409
            connection.execute(
                "UPDATE voice_recordings SET status = 'stopped', updated_at = ? WHERE call_id = ?",
                (now, call_id),
            )
            peer_id = call["callee_user_id"] if user["id"] == call["caller_user_id"] else call["caller_user_id"]
            connection.execute(
                """
                INSERT INTO voice_signals(
                    call_id, sender_user_id, recipient_user_id, kind, payload, created_at
                ) VALUES (?, ?, ?, 'recording_stopped', '{}', ?)
                """,
                (call_id, user["id"], peer_id, now),
            )
            connection.commit()
        write_audit(database_path, user["id"], "voice.recording.stop", "voice_call", call_id)
        return jsonify(status="stopped", call_id=call_id)

    @app.post("/api/voice/calls/<call_id>/recording/upload")
    @require_roles(*VOICE_ROLES)
    def upload_voice_recording(call_id):
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return jsonify(error="voice_recordings_disabled"), 503
        max_bytes = max(1024, int(app.config["VOICE_RECORDING_MAX_BYTES"]))
        # Override el límite global únicamente para esta ruta, y seguir aplicando
        # un máximo estricto al archivo individual.
        request.max_content_length = max_bytes + 256 * 1024
        uploaded = request.files.get("recording")
        if uploaded is None:
            return jsonify(error="voice_recording_file_required"), 400
        mime_type = (uploaded.mimetype or "").lower()
        extension_by_type = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a"}
        extension = extension_by_type.get(mime_type)
        if extension is None:
            return jsonify(error="voice_recording_type_invalid"), 415
        content = uploaded.stream.read(max_bytes + 1)
        if not content:
            return jsonify(error="voice_recording_empty"), 400
        if len(content) > max_bytes:
            return jsonify(error="voice_recording_too_large"), 413

        user = g.portal_user
        with connect(database_path) as connection:
            call = voice_call_for_user(connection, call_id, user["id"])
            if call is None:
                return jsonify(error="voice_call_not_found"), 404
            recording = connection.execute(
                "SELECT * FROM voice_recordings WHERE call_id = ?", (call_id,)
            ).fetchone()
            if recording is None or recording["status"] != "stopped":
                return jsonify(error="voice_recording_not_consented"), 409
            if not recording["caller_consented"] or not recording["callee_consented"]:
                return jsonify(error="voice_recording_not_consented"), 409
            if recording["requester_user_id"] != user["id"]:
                return jsonify(error="voice_recording_uploader_not_allowed"), 403
            if recording["storage_name"]:
                return jsonify(error="voice_recording_already_uploaded"), 409

        recordings_dir = Path(app.config["VOICE_RECORDINGS_DIR"]).resolve()
        static_root = Path(app.static_folder).resolve()
        bucket = app.config["VOICE_RECORDINGS_BUCKET"]
        prefix = app.config["VOICE_RECORDINGS_PREFIX"].strip("/")
        if not prefix or any(part in {"", ".", ".."} for part in prefix.split("/")):
            return jsonify(error="voice_recording_storage_misconfigured"), 500
        if not bucket and (recordings_dir == static_root or static_root in recordings_dir.parents):
            LOGGER.error("Voice recording storage must be outside the public static directory")
            return jsonify(error="voice_recording_storage_misconfigured"), 500
        if is_postgresql(database_path) and not bucket:
            return jsonify(error="voice_recording_storage_misconfigured"), 503
        if not bucket:
            recordings_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(recordings_dir, 0o700)
            except OSError:
                pass
        recording_id = "rec-{}".format(uuid.uuid4().hex)
        storage_name = "{}.{}".format(recording_id, extension)
        final_path = recordings_dir / storage_name
        partial_path = recordings_dir / (storage_name + ".part")
        storage_key = "{}/{}".format(prefix, storage_name)
        digest = hashlib.sha256(content).hexdigest()
        s3_object_created = False
        try:
            if bucket:
                s3_client = voice_recording_s3_client(app)
                if s3_client is None:
                    return jsonify(error="voice_recording_storage_unavailable"), 503
                s3_client.put_object(
                    Bucket=bucket,
                    Key=storage_key,
                    Body=content,
                    ContentType=mime_type,
                    ServerSideEncryption="AES256",
                    Metadata={"sha256": digest},
                )
                s3_object_created = True
            else:
                with partial_path.open("xb") as destination:
                    destination.write(content)
                    destination.flush()
                    os.fsync(destination.fileno())
                try:
                    os.chmod(partial_path, 0o600)
                except OSError:
                    pass
                os.replace(partial_path, final_path)
            uploaded_at_dt = datetime.now(timezone.utc)
            uploaded_at = uploaded_at_dt.isoformat()
            expires_at = (
                uploaded_at_dt
                + timedelta(days=max(1, int(app.config["VOICE_RECORDING_RETENTION_DAYS"])))
            ).isoformat()
            with connect(database_path) as connection:
                updated = connection.execute(
                    """
                    UPDATE voice_recordings
                    SET status = 'saved', storage_name = ?, mime_type = ?, size_bytes = ?,
                        sha256 = ?, uploaded_at = ?, updated_at = ?, expires_at = ?
                    WHERE call_id = ? AND requester_user_id = ?
                      AND status IN ('approved','stopped') AND storage_name IS NULL
                    """,
                    (
                        storage_name,
                        mime_type,
                        len(content),
                        digest,
                        uploaded_at,
                        uploaded_at,
                        expires_at,
                        call_id,
                        user["id"],
                    ),
                )
                if updated.rowcount != 1:
                    connection.commit()
                    if s3_object_created:
                        s3_client.delete_object(Bucket=bucket, Key=storage_key)
                    else:
                        final_path.unlink(missing_ok=True)
                    return jsonify(error="voice_recording_already_uploaded"), 409
                connection.commit()
            write_audit(
                database_path,
                user["id"],
                "voice.recording.saved",
                "voice_call",
                call_id,
                {"size_bytes": len(content)},
            )
        except Exception:
            partial_path.unlink(missing_ok=True)
            if s3_object_created:
                try:
                    s3_client.delete_object(Bucket=bucket, Key=storage_key)
                except Exception:
                    LOGGER.exception("Could not clean up an uncommitted voice recording object")
            elif not bucket:
                final_path.unlink(missing_ok=True)
            LOGGER.exception("voice recording upload failed")
            return jsonify(error="voice_recording_save_failed"), 500
        return jsonify(status="saved", id=recording_id, size_bytes=len(content), expires_at=expires_at), 201

    @app.get("/api/voice/recordings")
    @require_roles(*VOICE_ROLES)
    def list_voice_recordings():
        user = g.portal_user
        if app.config["VOICE_RECORDINGS_ENABLED"]:
            maybe_purge_expired_recordings()
        with connect(database_path) as connection:
            rows = connection.execute(
                """
                SELECT vr.call_id, vr.storage_name, vr.mime_type, vr.size_bytes,
                       vr.created_at, vr.uploaded_at, vr.expires_at,
                       caller.id AS caller_id, caller.username AS caller_username,
                       callee.id AS callee_id, callee.username AS callee_username
                FROM voice_recordings AS vr
                JOIN portal_users AS caller ON caller.id = vr.caller_user_id
                JOIN portal_users AS callee ON callee.id = vr.callee_user_id
                WHERE vr.status = 'saved' AND vr.expires_at > ?
                  AND (vr.caller_user_id = ? OR vr.callee_user_id = ? OR ? = 'admin')
                ORDER BY vr.created_at DESC LIMIT 100
                """,
                (datetime.now(timezone.utc).isoformat(), user["id"], user["id"], user["role"]),
            ).fetchall()
        recordings = []
        for row in rows:
            peer_id = row["callee_id"] if row["caller_id"] == user["id"] else row["caller_id"]
            peer_username = row["callee_username"] if row["caller_id"] == user["id"] else row["caller_username"]
            recordings.append(
                {
                    "id": row["storage_name"].rsplit(".", 1)[0],
                    "call_id": row["call_id"],
                    "peer": {"id": peer_id, "username": peer_username},
                    "created_at": row["created_at"],
                    "uploaded_at": row["uploaded_at"],
                    "expires_at": row["expires_at"],
                    "size_bytes": row["size_bytes"],
                    "mime_type": row["mime_type"],
                    "file_url": "/api/voice/recordings/{}/file".format(row["storage_name"].rsplit(".", 1)[0]),
                }
            )
        return jsonify(enabled=app.config["VOICE_RECORDINGS_ENABLED"], recordings=recordings)

    @app.get("/api/voice/recordings/<recording_id>/file")
    @require_roles(*VOICE_ROLES)
    def get_voice_recording_file(recording_id):
        if not app.config["VOICE_RECORDINGS_ENABLED"]:
            return jsonify(error="voice_recordings_disabled"), 503
        if len(recording_id) != 36 or not recording_id.startswith("rec-") or any(
            character not in "0123456789abcdef" for character in recording_id[4:]
        ):
            return jsonify(error="voice_recording_not_found"), 404
        maybe_purge_expired_recordings()
        user = g.portal_user
        with connect(database_path) as connection:
            row = connection.execute(
                """
                SELECT storage_name, mime_type, expires_at
                FROM voice_recordings
                WHERE status = 'saved'
                  AND (caller_user_id = ? OR callee_user_id = ? OR ? = 'admin')
                  AND storage_name LIKE ?
                """,
                (user["id"], user["id"], user["role"], recording_id + ".%"),
            ).fetchone()
        if row is None:
            return jsonify(error="voice_recording_not_found"), 404
        if row["expires_at"] <= datetime.now(timezone.utc).isoformat():
            return jsonify(error="voice_recording_expired"), 410
        bucket = app.config["VOICE_RECORDINGS_BUCKET"]
        if bucket:
            prefix = app.config["VOICE_RECORDINGS_PREFIX"].strip("/")
            storage_key = "{}/{}".format(prefix, row["storage_name"])
            try:
                s3_object = voice_recording_s3_client(app).get_object(
                    Bucket=bucket, Key=storage_key
                )
                content = s3_object["Body"].read()
            except Exception as error:
                error_code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if error_code in {"NoSuchKey", "NoSuchBucket", "404", "NotFound"}:
                    return jsonify(error="voice_recording_not_found"), 404
                LOGGER.exception("Could not read a private voice recording from S3")
                return jsonify(error="voice_recording_storage_unavailable"), 503
            extension = Path(row["storage_name"]).suffix.lower().lstrip(".")
            response = send_file(
                BytesIO(content),
                mimetype=row["mime_type"],
                as_attachment=False,
                download_name="grabacion-{}.{}".format(recording_id, extension),
                conditional=False,
            )
        else:
            recordings_dir = Path(app.config["VOICE_RECORDINGS_DIR"]).resolve()
            file_path = (recordings_dir / row["storage_name"]).resolve()
            if file_path.parent != recordings_dir or not file_path.is_file():
                return jsonify(error="voice_recording_not_found"), 404
            extension = file_path.suffix.lower().lstrip(".")
            response = send_file(
                file_path,
                mimetype=row["mime_type"],
                as_attachment=False,
                download_name="grabacion-{}.{}".format(recording_id, extension),
                conditional=False,
            )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    @app.get("/<path:asset_path>")
    def web_assets(asset_path):
        if (static_folder / asset_path).is_file():
            return send_from_directory(static_folder, asset_path)
        if (static_folder / "index.html").is_file() and not asset_path.startswith("api/"):
            return send_from_directory(static_folder, "index.html")
        return jsonify(error="not_found"), 404

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
VOICE_ROLES = ("sales", "operations", "admin")
VOICE_SIGNAL_KINDS = {"offer", "answer", "ice", "hangup", "reject"}
MAX_VOICE_SIGNAL_BYTES = 32 * 1024
VOICE_RING_TIMEOUT = timedelta(minutes=2)
VOICE_DELIVERED_SIGNAL_RETENTION = timedelta(minutes=10)


def voice_extension(user_id):
    """Extensión de laboratorio determinista; una PBX real la administrará.

    No se guarda ninguna contraseña SIP en el portal. Esta numeración permite
    que dos cuentas del laboratorio se identifiquen sin crear otro secreto.
    """
    return str(2000 + int(user_id))


def voice_call_for_user(connection, call_id, user_id):
    return connection.execute(
        """
        SELECT id, caller_user_id, callee_user_id, status, created_at, updated_at, ended_at
        FROM voice_calls
        WHERE id = ? AND (caller_user_id = ? OR callee_user_id = ?)
        """,
        (call_id, user_id, user_id),
    ).fetchone()


def voice_call_for_view(row, user_id):
    """Serializa el otro extremo sin filtrar IDs de terceros innecesarios."""
    call = dict(row)
    outgoing = call["caller_user_id"] == user_id
    peer_id = call["callee_user_id"] if outgoing else call["caller_user_id"]
    peer_username = call["callee_username"] if outgoing else call["caller_username"]
    return {
        "id": call["id"],
        "status": call["status"],
        "direction": "outgoing" if outgoing else "incoming",
        "peer": {
            "id": peer_id,
            "username": peer_username,
            "extension": voice_extension(peer_id),
        },
        "created_at": call["created_at"],
        "updated_at": call["updated_at"],
        "ended_at": call["ended_at"],
    }


def validate_voice_signal(call, sender_user_id, kind):
    """Impide que un participante cambie estados que pertenecen al otro."""
    is_caller = call["caller_user_id"] == sender_user_id
    status = call["status"]
    if kind == "offer":
        return None if is_caller and status == "ringing" else "voice_offer_not_allowed"
    if kind == "answer":
        return None if not is_caller and status == "ringing" else "voice_answer_not_allowed"
    if kind == "reject":
        return None if not is_caller and status == "ringing" else "voice_reject_not_allowed"
    if kind == "ice":
        return None if status in {"ringing", "accepted"} else "voice_call_not_active"
    if kind == "hangup":
        return None if status in {"ringing", "accepted"} else "voice_call_not_active"
    return "voice_signal_kind_invalid"


def expire_voice_calls(database_path):
    """Expira timbrados abandonados y limpia señalización ya entregada.

    La auditoría conserva el hecho de la llamada, pero no hay razón para
    retener indefinidamente SDP o candidatos ICE de sesiones ya concluidas.
    """
    cutoff = (datetime.now(timezone.utc) - VOICE_RING_TIMEOUT).isoformat()
    signal_cutoff = (
        datetime.now(timezone.utc) - VOICE_DELIVERED_SIGNAL_RETENTION
    ).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE voice_calls
            SET status = 'expired', updated_at = ?, ended_at = ?
            WHERE status = 'ringing' AND created_at < ?
            """,
            (now, now, cutoff),
        )
        connection.execute(
            "DELETE FROM voice_signals WHERE delivered_at IS NOT NULL AND created_at < ?",
            (signal_cutoff,),
        )
        connection.commit()


def voice_recording_s3_client(app):
    """Create one lazy S3 client per process, using the instance role."""
    client = app.extensions.get("voice_recording_s3_client")
    if client is not None:
        return client
    if not app.config.get("VOICE_RECORDINGS_BUCKET"):
        return None
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("boto3 is required for S3-backed voice recordings") from error
    client = boto3.client("s3", region_name=app.config.get("AWS_REGION_NAME") or None)
    app.extensions["voice_recording_s3_client"] = client
    return client


def purge_expired_voice_recordings(
    database_path,
    recordings_directory,
    now_text=None,
    s3_client=None,
    s3_bucket="",
    s3_prefix="voice-recordings",
):
    """Delete expired audio and metadata; S3 lifecycle is the durable backstop."""
    now_text = now_text or datetime.now(timezone.utc).isoformat()
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT call_id, storage_name FROM voice_recordings WHERE expires_at <= ?",
            (now_text,),
        ).fetchall()
    root = Path(recordings_directory).resolve()
    deleted_call_ids = []
    for row in rows:
        storage_name = row["storage_name"]
        try:
            if storage_name and s3_bucket:
                if s3_client is None:
                    continue
                if Path(storage_name).name != storage_name:
                    LOGGER.error("Invalid voice recording storage key in database")
                    continue
                s3_client.delete_object(
                    Bucket=s3_bucket,
                    Key="{}/{}".format(s3_prefix.strip("/"), storage_name),
                )
            elif storage_name:
                if Path(storage_name).name != storage_name:
                    LOGGER.error("Invalid local voice recording storage key in database")
                    continue
                expired_path = (root / storage_name).resolve()
                if expired_path.parent != root:
                    LOGGER.error("Voice recording path escaped the configured storage directory")
                    continue
                expired_path.unlink(missing_ok=True)
            deleted_call_ids.append(row["call_id"])
        except Exception:
            LOGGER.exception("Could not delete an expired voice recording")
    if deleted_call_ids:
        with connect(database_path) as connection:
            for call_id in deleted_call_ids:
                connection.execute(
                    "DELETE FROM voice_recordings WHERE call_id = ? AND expires_at <= ?",
                    (call_id, now_text),
                )
            connection.commit()


def portal_user_row(database_path, user_id):
    if not user_id:
        return None
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT u.id, u.username, u.role, u.company_id, u.active,
                   u.auth_version, u.must_change_password, c.name AS company
            FROM portal_users AS u
            LEFT JOIN companies AS c ON c.id = u.company_id
            WHERE u.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None or not row["active"]:
        return None
    result = dict(row)
    result["active"] = bool(result["active"])
    result["must_change_password"] = bool(result["must_change_password"])
    return result


def portal_user(database_path, user_id):
    result = portal_user_row(database_path, user_id)
    if result is None:
        return None
    result.pop("auth_version", None)
    return result


def current_portal_user(database_path):
    result = portal_user_row(database_path, session.get("portal_user_id"))
    if result is None:
        return None
    session_version = session.get("portal_user_version")
    try:
        session_version = int(session_version)
    except (TypeError, ValueError):
        session.clear()
        return None
    if session_version != int(result["auth_version"]):
        session.clear()
        return None
    result.pop("auth_version", None)
    return result


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


def write_audit(database_path, user_id, action, subject_type, subject_id=None, detail=None):
    with connect(database_path) as connection:
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
                INSERT INTO portal_users(username, password_hash, role, company_id, active, created_at)
                VALUES (?, ?, 'admin', ?, TRUE, ?)
                ON CONFLICT(username) DO NOTHING
                """,
                (
                    app.config["BOOTSTRAP_ADMIN_USERNAME"].strip().lower(),
                    generate_password_hash(password),
                    company_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        demo_password = app.config.get("DEMO_VOICE_PASSWORD", "")
        if demo_password:
            for username, role in (
                ("comercial.demo@tangamandapio.local", "sales"),
                ("operaciones.demo@tangamandapio.local", "operations"),
            ):
                connection.execute(
                    """
                    INSERT INTO portal_users(username, password_hash, role, company_id, active, created_at)
                    VALUES (?, ?, ?, ?, TRUE, ?)
                    ON CONFLICT(username) DO NOTHING
                    """,
                    (
                        username,
                        generate_password_hash(demo_password),
                        role,
                        company_id,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        connection.commit()


def migrations_directory():
    """Raíz de las migraciones; cambia entre repo (`app/src`) y artefacto."""
    here = Path(__file__).resolve().parent
    for candidate in (here / "migrations", here.parent / "migrations"):
        if candidate.is_dir():
            return candidate
    return here / "migrations"


def split_sql(script):
    """Divide un archivo de migración en sentencias ejecutables una a una.

    Ni SQLite ni psycopg2 aceptan varios `CREATE` en una sola llamada. Las
    migraciones del proyecto no usan punto y coma dentro de literales, así que
    partir por `;` es seguro y evita tener dialectos de parsing distintos.
    """
    lines = [line for line in script.splitlines() if not line.strip().startswith("--")]
    return [chunk.strip() for chunk in "\n".join(lines).split(";") if chunk.strip()]


def apply_migrations(database_path):
    """Aplica en orden las migraciones pendientes y devuelve sus versiones.

    Cada versión se graba en `schema_migrations` dentro de su propia
    transacción: si una migración falla, la anterior ya quedó registrada y el
    siguiente arranque retoma justo donde se cortó.
    """
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        dialect = "postgres" if isinstance(connection, PostgreSQLConnection) else "sqlite"
        directory = migrations_directory() / dialect
        applied = {
            row["version"]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        available = sorted(directory.glob("*.sql")) if directory.is_dir() else []

        executed = []
        for path in available:
            if path.stem in applied:
                continue
            statements = split_sql(path.read_text(encoding="utf-8"))
            if not statements:
                raise RuntimeError("migracion_vacia: {}".format(path.name))
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (path.stem, datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()
            executed.append(path.stem)
            LOGGER.info(
                json.dumps(
                    {"event": "db_migration_applied", "version": path.stem, "dialect": dialect}
                )
            )
        return executed


def initialize_database(database_path):
    apply_migrations(database_path)
    with connect(database_path) as connection:
        if isinstance(connection, PostgreSQLConnection):
            ensure_column(connection, "orders", "company_id", "BIGINT")
            ensure_column(connection, "orders", "created_by", "BIGINT")
            ensure_column(connection, "orders", "reference", "TEXT")
            ensure_column(connection, "orders", "status", "TEXT NOT NULL DEFAULT 'created'")
            connection.commit()
            return

        ensure_column(connection, "orders", "company_id", "INTEGER")
        ensure_column(connection, "orders", "created_by", "INTEGER")
        ensure_column(connection, "orders", "reference", "TEXT")
        ensure_column(connection, "orders", "status", "TEXT NOT NULL DEFAULT 'created'")
        connection.commit()


def azure_event_url(service_url):
    base = service_url.rstrip("/")
    return base if base.endswith("/api/fulfillment/events") else f"{base}/api/fulfillment/events"


def azure_event_status_url(service_url, event_id):
    return f"{azure_event_url(service_url)}/{quote(event_id, safe='')}"


def azure_inventory_url(service_url):
    base = str(service_url).rstrip("/")
    suffix = "/api/fulfillment/events"
    if base.endswith(suffix):
        base = base[: -len(suffix)]
    return f"{base}/api/wms/inventory"


def azure_health_url(service_url):
    base = service_url.rstrip("/")
    if base.endswith("/api/fulfillment/events"):
        base = base[: -len("/api/fulfillment/events")]
    return f"{base}/api/health" if ".azurewebsites.net" in base else f"{base}/health"


def outbox_backoff_seconds(interval, attempts):
    """Espera exponencial antes del siguiente intento, tope de una hora."""
    if interval <= 0:
        return 0
    return min(interval * (2 ** min(max(int(attempts), 0), 10)), 3600)


def retry_pending_outbox(app, database_path, deadlines, now=None):
    """Despacha en segundo plano los eventos no entregados cuyo plazo ya venció.

    `deadlines` guarda el instante (monotónico) en que cada evento vuelve a ser
    elegible; se mantiene en memoria a propósito para no tocar el esquema.
    Devuelve una lista con el resultado de cada intento realmente ejecutado.
    """
    interval = int(app.config.get("OUTBOX_RETRY_INTERVAL", 0))
    max_attempts = int(app.config.get("OUTBOX_RETRY_MAX_ATTEMPTS", 10))
    if interval <= 0 or max_attempts <= 0:
        return []
    if not str(app.config.get("AZURE_FULFILLMENT_URL", "")).strip():
        return []
    if now is None:
        now = time.monotonic()

    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT event_id, attempts FROM outbox_events
            WHERE status != 'delivered' AND attempts < ?
            ORDER BY created_at
            """,
            (max_attempts,),
        ).fetchall()

    results = []
    for row in rows:
        event_id = row["event_id"]
        if now < deadlines.get(event_id, 0.0):
            continue
        delivery = dispatch_outbox_event(app, database_path, event_id)
        results.append(delivery)
        if delivery.get("status") == "delivered":
            deadlines.pop(event_id, None)
        else:
            deadlines[event_id] = now + outbox_backoff_seconds(interval, row["attempts"] + 1)
    return results


def start_outbox_retry_worker(app, database_path):
    """Arranca el hilo de reintento; devuelve None cuando está desactivado."""
    interval = int(app.config.get("OUTBOX_RETRY_INTERVAL", 0))
    if interval <= 0 or app.config.get("TESTING"):
        return None
    deadlines = {}

    def sweep_forever():
        while True:
            time.sleep(interval)
            try:
                with app.app_context():
                    outcomes = retry_pending_outbox(app, database_path, deadlines)
            except Exception:
                LOGGER.exception("outbox_retry_sweep_failed")
                continue
            for outcome in outcomes:
                LOGGER.info(json.dumps({"event": "outbox_retry", **outcome}))

    worker = threading.Thread(target=sweep_forever, name="outbox-retry", daemon=True)
    worker.start()
    app.extensions["outbox_retry_worker"] = worker
    LOGGER.info(json.dumps({"event": "outbox_retry_worker_started", "interval": interval}))
    return worker


def log_outbox_dispatch(result):
    """Una línea por intento, con las ids que cruzan AWS y Azure."""
    entry = {"event": "outbox_dispatch", "instance": socket.gethostname(), **result}
    if has_request_context() and g.get("request_id"):
        entry["request_id"] = g.get("request_id")
    LOGGER.info(json.dumps(entry))


def dispatch_outbox_event(app, database_path, event_id):
    """Deliver an already committed event. A failure never rolls back the order."""
    with connect(database_path) as connection:
        row = connection.execute(
            "SELECT payload, attempts, order_id FROM outbox_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    def finish(result):
        log_outbox_dispatch(result)
        return result

    if row is None:
        return finish({"status": "not_found", "event_id": event_id})

    attempt = int(row["attempts"]) + 1
    order_id = row["order_id"]
    service_url = app.config["AZURE_FULFILLMENT_URL"].rstrip("/")
    if not service_url:
        return finish(
            {
                "status": "pending",
                "event_id": event_id,
                "order_id": order_id,
                "attempt": attempt,
                "reason": "azure_not_configured",
            }
        )

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
        return finish(
            {
                "status": "delivered",
                "event_id": event_id,
                "order_id": order_id,
                "attempt": attempt,
                "upstream": status,
            }
        )
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        with connect(database_path) as connection:
            connection.execute(
                """
                UPDATE outbox_events
                SET status = 'failed', attempts = attempts + 1, last_error = ?
                WHERE event_id = ? AND status != 'delivered'
                """,
                (type(error).__name__, event_id),
            )
            connection.commit()
        app.extensions["metrics"]["outbox_failed_total"] += 1
        return finish(
            {
                "status": "pending",
                "event_id": event_id,
                "order_id": order_id,
                "attempt": attempt,
                "reason": type(error).__name__,
            }
        )


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
