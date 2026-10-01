import json
import logging
import math
import os
import socket
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, g, jsonify, request, send_from_directory


LOGGER = logging.getLogger("tangamandapio.api")


def create_app(test_config=None):
    static_folder = Path(__file__).parent / "static"
    app = Flask(__name__, static_folder=str(static_folder), static_url_path="")
    app.config.from_mapping(
        DATABASE_PATH=os.getenv(
            "DATABASE_PATH", str(Path(tempfile.gettempdir()) / "tangamandapio.db")
        ),
        AZURE_FULFILLMENT_URL=os.getenv("AZURE_FULFILLMENT_URL", ""),
        AZURE_FUNCTION_KEY=os.getenv("AZURE_FUNCTION_KEY", ""),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(database_path)

    @app.before_request
    def start_request_observation():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def secure_and_observe(response):
        response.headers["X-Request-ID"] = g.get("request_id", str(uuid.uuid4()))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
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

    @app.get("/api")
    def index():
        return jsonify(
            service="Tangamandapio Cloud Demo",
            instance=socket.gethostname(),
            endpoints=["/health", "/ready", "/api/orders", "/api/multicloud"],
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
        except sqlite3.Error:
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
        except sqlite3.Error:
            return jsonify(status="not_ready", dependencies={"database": "error"}), 503

    @app.get("/api/orders")
    def list_orders():
        with connect(database_path) as connection:
            rows = connection.execute(
                "SELECT id, customer, total, created_at FROM orders ORDER BY id DESC"
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/orders")
    def create_order():
        payload = request.get_json(silent=True) or {}
        customer = str(payload.get("customer", "")).strip()

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
        ):
            return (
                jsonify(
                    error="customer (1-120 caracteres) y total (0-1000000) son obligatorios"
                ),
                400,
            )

        created_at = datetime.now(timezone.utc).isoformat()
        with connect(database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO orders (customer, total, created_at) VALUES (?, ?, ?)",
                (customer, total, created_at),
            )
            connection.commit()
            order_id = cursor.lastrowid

        return (
            jsonify(
                id=order_id,
                customer=customer,
                total=total,
                created_at=created_at,
                instance=socket.gethostname(),
            ),
            201,
        )

    @app.get("/api/multicloud")
    def multicloud_status():
        service_url = app.config["AZURE_FULFILLMENT_URL"].rstrip("/")
        if not service_url:
            return jsonify(status="not_configured"), 503

        headers = {"Accept": "application/json"}
        token = app.config["AZURE_FUNCTION_KEY"]
        if token:
            headers["x-functions-key"] = token

        upstream_request = Request(f"{service_url}/health", headers=headers)
        try:
            with urlopen(upstream_request, timeout=3) as response:
                upstream_body = json.loads(response.read().decode("utf-8"))
            return jsonify(status="connected", provider="Azure", upstream=upstream_body)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            return jsonify(status="unavailable", error=type(error).__name__), 502

    @app.post("/api/multicloud/sync")
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

        upstream_request = Request(
            f"{service_url}/api/fulfillment/events", data=body, headers=headers, method="POST"
        )
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

    return app


def connect(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def initialize_database(database_path):
    with connect(database_path) as connection:
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
        connection.commit()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
