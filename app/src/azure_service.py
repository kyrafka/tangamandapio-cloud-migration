"""Persistent local contract simulator for the Azure WMS Function.

The simulator is for local development only. In a cloud deployment the Azure
Function + Blob/Queue implementation remains the inventory authority.
"""

import hashlib
import hmac
import json
import logging
import math
import os
import re
import socket
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, g, jsonify, request


LOGGER = logging.getLogger("tangamandapio.azure_simulator")
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
DEMO_PRODUCTS = {
    "SKU-ARROZ-001": {"name": "Arroz premium · saco 50 kg", "unit": "saco", "unit_price": 42.50, "initial_stock": 25},
    "SKU-AZUCAR-001": {"name": "Azúcar rubia · saco 50 kg", "unit": "saco", "unit_price": 37.50, "initial_stock": 40},
    "SKU-ACEITE-001": {"name": "Aceite vegetal · caja x 12", "unit": "caja", "unit_price": 86.00, "initial_stock": 18},
    "SKU-CAFE-001": {"name": "Café tostado · saco 10 kg", "unit": "saco", "unit_price": 128.00, "initial_stock": 12},
    "SKU-FREJOL-001": {"name": "Fréjol canario · saco 25 kg", "unit": "saco", "unit_price": 119.90, "initial_stock": 20},
    "SKU-QUINUA-001": {"name": "Quinua blanca · saco 25 kg", "unit": "saco", "unit_price": 172.00, "initial_stock": 14},
    "SKU-AVENA-001": {"name": "Avena tradicional · saco 25 kg", "unit": "saco", "unit_price": 91.50, "initial_stock": 32},
    "SKU-FIDEOS-001": {"name": "Fideos tallarín · caja x 20", "unit": "caja", "unit_price": 64.00, "initial_stock": 28},
    "SKU-LECHE-001": {"name": "Leche evaporada · caja x 48", "unit": "caja", "unit_price": 154.80, "initial_stock": 38},
    "SKU-ATUN-001": {"name": "Atún en conserva · caja x 48", "unit": "caja", "unit_price": 218.00, "initial_stock": 16},
    "SKU-GALLETAS-001": {"name": "Galletas surtidas · caja x 24", "unit": "caja", "unit_price": 55.00, "initial_stock": 42},
    "SKU-MAIZ-001": {"name": "Maíz amarillo · saco 50 kg", "unit": "saco", "unit_price": 89.90, "initial_stock": 26},
}


def _connect(path):
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return closing(connection)


def _initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("""CREATE TABLE IF NOT EXISTS wms_inventory (
            sku TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT NOT NULL,
            unit_price REAL NOT NULL, on_hand INTEGER NOT NULL CHECK(on_hand >= 0),
            updated_at TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS wms_events (
            event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL, status TEXT NOT NULL, result_json TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        now = datetime.now(timezone.utc).isoformat()
        for sku, product in DEMO_PRODUCTS.items():
            connection.execute(
                """INSERT INTO wms_inventory(sku,name,unit,unit_price,on_hand,updated_at)
                   VALUES(?,?,?,?,?,?) ON CONFLICT(sku) DO NOTHING""",
                (sku, product["name"], product["unit"], product["unit_price"], product["initial_stock"], now),
            )
        connection.commit()


def _validated_items(payload, event_type, known_skus=None):
    parent_key = "purchase_order" if event_type == "purchase.received" else "order"
    parent = payload.get(parent_key) if isinstance(payload.get(parent_key), dict) else {}
    items = parent.get("items", payload.get("items"))
    if items is None:
        return (None, None) if event_type == "order.created" else (None, "purchase receipt requires SKU lines")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        return None, "items must contain 1 to 20 lines"
    normalized, seen = [], set()
    known_skus = set(DEMO_PRODUCTS) if known_skus is None else known_skus
    for item in items:
        if not isinstance(item, dict):
            return None, "each line must contain SKU and quantity"
        sku, quantity = str(item.get("sku", "")), item.get("quantity")
        if sku not in known_skus or isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000 or sku in seen:
            return None, "invalid SKU, quantity, or duplicate line"
        normalized.append({"sku": sku, "quantity": quantity})
        seen.add(sku)
    return normalized, None


def _apply_event(connection, event_id, event_type, payload, digest):
    now = datetime.now(timezone.utc).isoformat()
    known_skus = {
        row[0]
        for row in connection.execute("SELECT sku FROM wms_inventory").fetchall()
    }
    items, error = _validated_items(payload, event_type, known_skus)
    if error:
        return {"event_id": event_id, "event_type": event_type, "status": "rejected_invalid_items", "mode": "demo-inventory-ledger", "note": error, "items": [], "processed_at": now}
    if not items:
        return {"event_id": event_id, "event_type": event_type, "status": "awaiting_items", "mode": "demo-inventory-ledger", "note": "No se modificó el inventario porque el evento no incluye líneas.", "items": [], "processed_at": now}

    stocks = {}
    for item in items:
        row = connection.execute("SELECT on_hand FROM wms_inventory WHERE sku=?", (item["sku"],)).fetchone()
        stocks[item["sku"]] = int(row["on_hand"]) if row else 0
    if event_type == "order.created":
        unavailable = [{**item, "available": stocks[item["sku"]]} for item in items if item["quantity"] > stocks[item["sku"]]]
        if unavailable:
            return {"event_id": event_id, "event_type": event_type, "status": "rejected_insufficient_stock", "mode": "demo-inventory-ledger", "note": "Stock de laboratorio insuficiente; no se modificó ninguna línea.", "items": unavailable, "processed_at": now}
        delta = -1
        result_status = "demo_fulfillment_completed"
        note = "Venta aplicada una sola vez al inventario ficticio local. No representa existencias comerciales."
    elif event_type == "purchase.received":
        delta = 1
        result_status = "demo_restock_completed"
        note = "Recepción aplicada una sola vez al inventario ficticio local. No representa existencias comerciales."
    else:
        return {"event_id": event_id, "event_type": event_type, "status": "rejected_event_type", "mode": "demo-inventory-ledger", "note": "Tipo de evento no soportado.", "items": [], "processed_at": now}

    changed = []
    for item in items:
        on_hand = stocks[item["sku"]] + delta * item["quantity"]
        connection.execute("UPDATE wms_inventory SET on_hand=?,updated_at=? WHERE sku=?", (on_hand, now, item["sku"]))
        changed.append({**item, "on_hand_after": on_hand})
    return {"event_id": event_id, "event_type": event_type, "status": result_status, "mode": "demo-inventory-ledger", "source_sha256": digest, "note": note, "items": changed, "processed_at": now}


def create_azure_app(test_config=None):
    """Local contract simulator for the Azure Function receiver and WMS API."""
    default_path = Path(tempfile.gettempdir()) / "Tangamandapio" / "azure-wms.db"
    app = Flask(__name__)
    app.config.from_mapping(
        FUNCTION_KEY=os.getenv("FUNCTION_KEY", ""),
        DATABASE_PATH=os.getenv("AZURE_WMS_DATABASE_PATH", str(default_path)),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    _initialize(app.config["DATABASE_PATH"])
    app.extensions["metrics"] = {"requests_total": 0, "events_queued_total": 0}

    @app.before_request
    def start_request_observation():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def secure_and_observe(response):
        app.extensions["metrics"]["requests_total"] += 1
        response.headers["X-Request-ID"] = g.get("request_id", str(uuid.uuid4()))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        LOGGER.info(json.dumps({"event": "http_request", "request_id": response.headers["X-Request-ID"], "method": request.method, "path": request.path, "status": response.status_code, "duration_ms": round((time.perf_counter() - g.request_started_at) * 1000, 2), "provider": "Azure-simulated"}))
        return response

    def authorized():
        expected_key = app.config["FUNCTION_KEY"]
        return not expected_key or hmac.compare_digest(request.headers.get("x-functions-key", ""), expected_key)

    @app.get("/metrics")
    def metrics():
        values = app.extensions["metrics"]
        return ("# HELP tangamandapio_azure_simulator_requests_total HTTP responses from the local Azure contract simulator.\n"
                "# TYPE tangamandapio_azure_simulator_requests_total counter\n"
                f"tangamandapio_azure_simulator_requests_total {values['requests_total']}\n"
                "# HELP tangamandapio_azure_simulator_events_queued_total Accepted fulfillment events.\n"
                "# TYPE tangamandapio_azure_simulator_events_queued_total counter\n"
                f"tangamandapio_azure_simulator_events_queued_total {values['events_queued_total']}\n", 200,
                {"Content-Type": "text/plain; version=0.0.4"})

    @app.get("/health")
    def health():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(status="ok", provider="Azure-simulated", instance=socket.gethostname(), timestamp=datetime.now(timezone.utc).isoformat())

    @app.get("/ready")
    def ready():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(status="ready", provider="Azure-simulated")

    @app.get("/api/wms/inventory")
    def inventory():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        with _connect(app.config["DATABASE_PATH"]) as connection:
            rows = connection.execute("SELECT sku,name,unit,unit_price,on_hand,updated_at FROM wms_inventory ORDER BY sku").fetchall()
        return jsonify(provider="Azure-simulated", mode="demo-inventory-ledger", catalog_version=3, is_real_erp=False,
                       note="Inventario ficticio persistido para pruebas locales; Azure real conserva la autoridad WMS del diseño.", items=[dict(row, currency="PEN") for row in rows])

    @app.post("/api/wms/catalog")
    def update_catalog():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        payload = request.get_json(silent=True)
        products = payload.get("products") if isinstance(payload, dict) else None
        if not isinstance(products, list) or not 1 <= len(products) <= 500:
            return jsonify(error="products_must_contain_1_to_500_items"), 400
        normalized, seen = [], set()
        for product in products:
            if not isinstance(product, dict):
                return jsonify(error="invalid_product"), 400
            sku = str(product.get("sku", "")).strip().upper()
            name = str(product.get("name", "")).strip()
            unit = str(product.get("unit", "")).strip()
            raw_unit_price = product.get("unit_price")
            if isinstance(raw_unit_price, bool):
                return jsonify(error="invalid_product"), 400
            try:
                unit_price = float(raw_unit_price)
            except (TypeError, ValueError):
                return jsonify(error="invalid_product"), 400
            initial_stock = product.get("initial_stock")
            if (
                not re.fullmatch(r"[A-Z0-9_-]{3,40}", sku)
                or sku in seen
                or not name
                or len(name) > 180
                or not unit
                or len(unit) > 32
                or not math.isfinite(unit_price)
                or not 0 <= unit_price <= 1_000_000
                or isinstance(initial_stock, bool)
                or not isinstance(initial_stock, int)
                or not 0 <= initial_stock <= 1_000_000
            ):
                return jsonify(error="invalid_product", sku=sku or None), 400
            normalized.append((sku, name, unit, round(unit_price, 2), initial_stock))
            seen.add(sku)

        now = datetime.now(timezone.utc).isoformat()
        with _connect(app.config["DATABASE_PATH"]) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing = {
                    row[0]
                    for row in connection.execute(
                        "SELECT sku FROM wms_inventory WHERE sku IN (%s)"
                        % ",".join("?" for _ in normalized),
                        [item[0] for item in normalized],
                    ).fetchall()
                }
                for sku, name, unit, unit_price, initial_stock in normalized:
                    connection.execute(
                        """INSERT INTO wms_inventory(sku,name,unit,unit_price,on_hand,updated_at)
                           VALUES(?,?,?,?,?,?) ON CONFLICT(sku) DO UPDATE SET
                           name=excluded.name,unit=excluded.unit,unit_price=excluded.unit_price,
                           updated_at=excluded.updated_at""",
                        (sku, name, unit, unit_price, initial_stock, now),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        created_count = sum(1 for sku, *_ in normalized if sku not in existing)
        return jsonify(
            created=created_count,
            updated=len(normalized) - created_count,
            stock_preserved=True,
            mode="demo-inventory-ledger",
        )

    @app.post("/api/fulfillment/events")
    def receive():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="event_must_be_json_object"), 400
        event_id = str(payload.get("event_id", ""))
        event_type = str(payload.get("event_type", ""))
        if not EVENT_ID_PATTERN.fullmatch(event_id) or event_type not in {"order.created", "purchase.received"}:
            return jsonify(error="valid_event_id_and_supported_event_type_required"), 400
        with _connect(app.config["DATABASE_PATH"]) as connection:
            known_skus = {
                row[0]
                for row in connection.execute("SELECT sku FROM wms_inventory").fetchall()
            }
        items, error = _validated_items(payload, event_type, known_skus)
        if error:
            return jsonify(error=error), 400
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        connection = sqlite3.connect(app.config["DATABASE_PATH"], timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute("SELECT payload_json,payload_sha256,result_json FROM wms_events WHERE event_id=?", (event_id,)).fetchone()
            if previous:
                if previous["payload_sha256"] != digest or previous["payload_json"] != serialized:
                    connection.rollback()
                    return jsonify(error="event_id_reused_with_different_payload"), 409
                result = json.loads(previous["result_json"])
                connection.commit()
                return jsonify(status="queued_duplicate", event_id=event_id, result=result), 200
            result = _apply_event(connection, event_id, event_type, payload, digest)
            connection.execute("INSERT INTO wms_events(event_id,event_type,payload_json,payload_sha256,status,result_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (event_id, event_type, serialized, digest, result["status"], json.dumps(result, separators=(",", ":")), datetime.now(timezone.utc).isoformat()))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        app.extensions["metrics"]["events_queued_total"] += 1
        return jsonify(status="queued", event_id=event_id, sha256=digest, result=result), 202

    @app.get("/api/fulfillment/events/<event_id>")
    def event_status(event_id):
        if not authorized():
            return jsonify(status="unauthorized"), 401
        if not EVENT_ID_PATTERN.fullmatch(event_id):
            return jsonify(error="invalid_event_id"), 400
        with _connect(app.config["DATABASE_PATH"]) as connection:
            row = connection.execute("SELECT result_json FROM wms_events WHERE event_id=?", (event_id,)).fetchone()
        return jsonify(event_id=event_id, status="pending") if row is None else jsonify(json.loads(row["result_json"]))

    @app.get("/api/events")
    def events():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        with _connect(app.config["DATABASE_PATH"]) as connection:
            rows = connection.execute("SELECT event_id,event_type,payload_sha256,status,result_json,created_at FROM wms_events ORDER BY created_at DESC LIMIT 100").fetchall()
        result = [dict(row, result=json.loads(row["result_json"])) for row in rows]
        for item in result:
            item.pop("result_json", None)
        return jsonify(result)

    return app


app = create_azure_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
