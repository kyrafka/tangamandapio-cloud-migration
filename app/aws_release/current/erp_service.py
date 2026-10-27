"""Local ERP extension and internal mail for the Tangamandapio portal.

The ERP owns commercial metadata and finance records. Inventory quantities are
always read from the configured WMS endpoint (Azure in the cloud deployment).
This module deliberately does not create a second stock ledger.
"""

import json
import logging
import math
import re
import secrets
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, g, jsonify, request


ERP_ROLES = {
    "erp_admin": "Administración ERP",
    "erp_sales": "Ventas",
    "erp_finance": "Finanzas",
    "erp_purchasing": "Compras",
    "erp_master_data": "Datos maestros",
    "erp_auditor": "Auditoría ERP",
}
ERP_PERMISSIONS = {
    "erp_admin": {"master:read", "master:write", "sales:read", "sales:write", "purchase:read", "purchase:write", "finance:read", "finance:write", "reports:read"},
    "erp_sales": {"master:read", "sales:read", "sales:write", "reports:read"},
    "erp_finance": {"master:read", "sales:read", "purchase:read", "finance:read", "finance:write", "reports:read"},
    "erp_purchasing": {"master:read", "master:write", "purchase:read", "purchase:write", "reports:read"},
    "erp_master_data": {"master:read", "master:write", "reports:read"},
    "erp_auditor": {"master:read", "sales:read", "purchase:read", "finance:read", "reports:read"},
}
INTERNAL_PORTAL_ROLES = ("sales", "warehouse", "operations", "admin", "auditor")
SKU_PATTERN = re.compile(r"^[A-Z0-9_-]{3,40}$")
ERP_DEMO_PRODUCTS = (
    ("SKU-ARROZ-001", "Arroz premium · saco 50 kg", "saco", 42.50, 35.00),
    ("SKU-AZUCAR-001", "Azúcar rubia · saco 50 kg", "saco", 37.50, 31.00),
    ("SKU-ACEITE-001", "Aceite vegetal · caja x 12", "caja", 86.00, 72.00),
    ("SKU-CAFE-001", "Café tostado · saco 10 kg", "saco", 128.00, 104.00),
    ("SKU-FREJOL-001", "Fréjol canario · saco 25 kg", "saco", 119.90, 98.00),
    ("SKU-QUINUA-001", "Quinua blanca · saco 25 kg", "saco", 172.00, 140.00),
    ("SKU-AVENA-001", "Avena tradicional · saco 25 kg", "saco", 91.50, 74.00),
    ("SKU-FIDEOS-001", "Fideos tallarín · caja x 20", "caja", 64.00, 52.00),
    ("SKU-LECHE-001", "Leche evaporada · caja x 48", "caja", 154.80, 131.00),
    ("SKU-ATUN-001", "Atún en conserva · caja x 48", "caja", 218.00, 180.00),
    ("SKU-GALLETAS-001", "Galletas surtidas · caja x 24", "caja", 55.00, 41.50),
    ("SKU-MAIZ-001", "Maíz amarillo · saco 50 kg", "saco", 89.90, 73.00),
)
LOGGER = logging.getLogger("tangamandapio.erp.mail")


def now_text():
    return datetime.now(timezone.utc).isoformat()


def _smtp_settings(app):
    security = str(app.get("ERP_SMTP_SECURITY", "starttls")).strip().lower()
    host = str(app.get("ERP_SMTP_HOST", "")).strip()
    sender = str(app.get("ERP_SMTP_FROM", "")).strip()
    try:
        port = int(app.get("ERP_SMTP_PORT", 587))
    except (TypeError, ValueError):
        port = 587
    username = str(app.get("ERP_SMTP_USERNAME", ""))
    password = str(app.get("ERP_SMTP_PASSWORD", ""))
    auth_valid = (not username and not password) or (bool(username) and bool(password) and security in {"starttls", "ssl"})
    if security not in {"starttls", "ssl", "none"}:
        security = "invalid"
    return {
        "host": host,
        "port": port,
        "security": security,
        "username": username,
        "password": password,
        "sender": sender,
        "recipient_domain": str(app.get("ERP_SMTP_RECIPIENT_DOMAIN", "")).strip().lower().lstrip("@"),
        # An allowlisted organization domain is mandatory to prevent a relay
        # from turning portal usernames into arbitrary external recipients.
        "configured": bool(host and sender and app.get("ERP_SMTP_RECIPIENT_DOMAIN") and auth_valid and 1 <= port <= 65535 and security != "invalid"),
    }


def _mail_address(username, domain_override=""):
    username = str(username or "").strip()
    if domain_override:
        labels = domain_override.split(".")
        if len(domain_override) > 253 or len(labels) < 2 or any(
            not label or len(label) > 63 or not label[0].isalnum() or not label[-1].isalnum()
            or any(not (char.isalnum() or char == "-") for char in label)
            for label in labels
        ):
            return ""
        local = username.split("@", 1)[0].strip().lower()
        if not local or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
            return ""
        address = f"{local}@{domain_override}"
    else:
        display_name, address = parseaddr(username)
        if display_name or address != username:
            return ""
    local, separator, domain = address.rpartition("@")
    if (len(address) > 254 or not separator or not local or any(char.isspace() or char in "<>" for char in address)
            or "." not in domain or domain.startswith(".") or domain.endswith(".")):
        return ""
    return address


def _deliver_smtp(app, *, sender_username, recipient_username, subject, body, message_id=None):
    """Send a copy through a configured SMTP relay; the request never chooses its recipient address."""
    settings = _smtp_settings(app)
    if not settings["host"]:
        return {"status": "portal_only", "error": None, "message_id": None}
    if not settings["configured"]:
        return {"status": "smtp_failed", "error": "smtp_configuration_invalid", "message_id": None}
    sender = _mail_address(settings["sender"])
    recipient = _mail_address(recipient_username, settings["recipient_domain"])
    reply_to = _mail_address(sender_username, settings["recipient_domain"])
    if not sender or not recipient:
        return {"status": "recipient_address_missing", "error": "internal_account_has_no_mail_address", "message_id": None}
    if not reply_to:
        reply_to = sender
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message["Reply-To"] = reply_to
    smtp_message_id = f"<{uuid.uuid4()}@{sender.rsplit('@', 1)[1]}>"
    message["Message-ID"] = smtp_message_id
    message["X-Portal-Message-ID"] = str(message_id or "internal")
    message.set_content(body)
    try:
        if settings["security"] == "ssl":
            client = smtplib.SMTP_SSL(
                settings["host"], settings["port"], timeout=6,
                context=ssl.create_default_context(),
            )
        else:
            client = smtplib.SMTP(settings["host"], settings["port"], timeout=6)
        with client:
            client.ehlo()
            if settings["security"] == "starttls":
                if not client.has_extn("starttls"):
                    return {"status": "smtp_failed", "error": "smtp_tls_unavailable", "message_id": smtp_message_id}
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if settings["username"] or settings["password"]:
                if settings["security"] == "none":
                    return {"status": "smtp_failed", "error": "smtp_auth_requires_tls", "message_id": smtp_message_id}
                if not settings["username"] or not settings["password"]:
                    return {"status": "smtp_failed", "error": "smtp_auth_configuration_invalid", "message_id": smtp_message_id}
                client.login(settings["username"], settings["password"])
            refused = client.send_message(message, from_addr=sender, to_addrs=[recipient])
            if refused:
                return {"status": "smtp_failed", "error": "smtp_recipient_rejected", "message_id": smtp_message_id}
        return {"status": "accepted_by_smtp", "error": None, "message_id": smtp_message_id}
    except (OSError, smtplib.SMTPException, ssl.SSLError, ValueError) as error:
        LOGGER.warning("SMTP delivery failed (%s)", type(error).__name__)
        return {"status": "smtp_failed", "error": f"smtp_{type(error).__name__.lower()}", "message_id": smtp_message_id}


def initialize_erp_database(connection, postgres=False):
    """Create additive ERP tables; safe to call at every local app startup."""
    identity = "BIGSERIAL PRIMARY KEY" if postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    number = "BIGINT" if postgres else "INTEGER"
    timestamp = "TIMESTAMPTZ" if postgres else "TEXT"
    money = "NUMERIC(14,2)" if postgres else "REAL"
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_user_roles (
            user_id {number} NOT NULL REFERENCES portal_users(id),
            role_code TEXT NOT NULL,
            created_at {timestamp} NOT NULL,
            granted_by {number},
            PRIMARY KEY (user_id, role_code),
            CHECK (role_code IN ('erp_admin','erp_sales','erp_finance','erp_purchasing','erp_master_data','erp_auditor'))
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_partners (
            id {identity},
            kind TEXT NOT NULL CHECK (kind IN ('customer','supplier','both')),
            name TEXT NOT NULL,
            tax_id TEXT UNIQUE,
            email TEXT,
            phone TEXT,
            address TEXT,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by {number} REFERENCES portal_users(id),
            created_at {timestamp} NOT NULL
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_products (
            id {identity},
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            unit TEXT NOT NULL,
            sale_price {money} NOT NULL CHECK (sale_price >= 0),
            purchase_cost {money} NOT NULL CHECK (purchase_cost >= 0),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            updated_by {number} REFERENCES portal_users(id),
            updated_at {timestamp} NOT NULL
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_sales_orders (
            id {identity},
            partner_id {number} NOT NULL REFERENCES erp_partners(id),
            reference TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            total {money} NOT NULL CHECK (total >= 0),
            event_id TEXT UNIQUE,
            created_by {number} NOT NULL REFERENCES portal_users(id),
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_sales_order_lines (
            id {identity},
            sales_order_id {number} NOT NULL REFERENCES erp_sales_orders(id),
            sku TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price {money} NOT NULL CHECK (unit_price >= 0),
            line_total {money} NOT NULL CHECK (line_total >= 0)
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_purchase_orders (
            id {identity},
            partner_id {number} NOT NULL REFERENCES erp_partners(id),
            reference TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            total {money} NOT NULL CHECK (total >= 0),
            event_id TEXT UNIQUE,
            created_by {number} NOT NULL REFERENCES portal_users(id),
            created_at {timestamp} NOT NULL,
            updated_at {timestamp} NOT NULL
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_purchase_order_lines (
            id {identity},
            purchase_order_id {number} NOT NULL REFERENCES erp_purchase_orders(id),
            sku TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_cost {money} NOT NULL CHECK (unit_cost >= 0),
            line_total {money} NOT NULL CHECK (line_total >= 0)
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS erp_financial_documents (
            id {identity},
            kind TEXT NOT NULL CHECK (kind IN ('receivable','payable')),
            reference TEXT NOT NULL UNIQUE,
            partner_id {number} REFERENCES erp_partners(id),
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            description TEXT NOT NULL,
            amount {money} NOT NULL CHECK (amount >= 0),
            status TEXT NOT NULL CHECK (status IN ('open','paid','void')),
            due_date TEXT,
            settled_at {timestamp},
            created_by {number} NOT NULL REFERENCES portal_users(id),
            created_at {timestamp} NOT NULL,
            UNIQUE (kind, source_type, source_id)
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS internal_messages (
            id {identity},
            sender_user_id {number} NOT NULL REFERENCES portal_users(id),
            recipient_user_id {number} NOT NULL REFERENCES portal_users(id),
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at {timestamp} NOT NULL,
            read_at {timestamp}
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS internal_mail_delivery (
            message_id {number} PRIMARY KEY REFERENCES internal_messages(id) ON DELETE CASCADE,
            smtp_status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            smtp_message_id TEXT,
            updated_at {timestamp} NOT NULL
        )"""
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_erp_sales_status ON erp_sales_orders(status, created_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_erp_purchase_status ON erp_purchase_orders(status, created_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_erp_finance_status ON erp_financial_documents(kind, status, due_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_internal_mail_recipient ON internal_messages(recipient_user_id, created_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_internal_mail_sender ON internal_messages(sender_user_id, created_at)")
    for sku, name, unit, sale_price, purchase_cost in ERP_DEMO_PRODUCTS:
        connection.execute(
            """INSERT INTO erp_products(sku,name,unit,sale_price,purchase_cost,active,updated_at)
               VALUES (?,?,?,?,?,TRUE,?) ON CONFLICT(sku) DO NOTHING""",
            (sku, name, unit, sale_price, purchase_cost, now_text()),
        )
    connection.commit()


def grant_default_erp_roles(connection, user_id, portal_role, granted_by=None):
    defaults = {"admin": ("erp_admin",), "sales": ("erp_sales",), "auditor": ("erp_auditor",)}
    for role_code in defaults.get(portal_role, ()):
        connection.execute(
            """INSERT INTO erp_user_roles(user_id,role_code,created_at,granted_by)
               VALUES (?,?,?,?) ON CONFLICT(user_id,role_code) DO NOTHING""",
            (user_id, role_code, now_text(), granted_by),
        )


def _wms_base_url(app):
    base = str(app.config.get("AZURE_FULFILLMENT_URL", "")).strip().rstrip("/")
    suffix = "/api/fulfillment/events"
    return base[:-len(suffix)] if base.endswith(suffix) else base


def _wms_headers(app):
    headers = {"Accept": "application/json"}
    key = str(app.config.get("AZURE_FUNCTION_KEY", "")).strip()
    if key:
        headers["x-functions-key"] = key
    return headers


def fetch_wms_inventory(app):
    base = _wms_base_url(app)
    if not base:
        return None, "not_configured"
    try:
        with urlopen(Request(f"{base}/api/wms/inventory", headers=_wms_headers(app)), timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            return None, "invalid_response"
        return payload, None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None, "unavailable"


def update_wms_catalog(app, products):
    """Sync synthetic product masters to the inventory authority first."""
    base = _wms_base_url(app)
    if not base:
        return None, "not_configured"
    body = json.dumps({"products": products}, separators=(",", ":")).encode("utf-8")
    try:
        with urlopen(
            Request(
                f"{base}/api/wms/catalog",
                data=body,
                headers={**_wms_headers(app), "Content-Type": "application/json"},
                method="POST",
            ),
            timeout=15,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("stock_preserved") is not True:
            return None, "invalid_response"
        return payload, None
    except HTTPError as error:
        return None, "rejected" if error.code in (400, 413, 422) else "unavailable"
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None, "unavailable"


def fetch_wms_event(app, event_id):
    base = _wms_base_url(app)
    if not base:
        return None, "not_configured"
    try:
        with urlopen(
            Request(f"{base}/api/fulfillment/events/{quote(event_id, safe='')}", headers=_wms_headers(app)),
            timeout=4,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return (payload, None) if isinstance(payload, dict) else (None, "invalid_response")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None, "unavailable"


def _money_rows(rows, fields):
    result = []
    for row in rows:
        item = dict(row)
        for field in fields:
            if item.get(field) is not None:
                item[field] = round(float(item[field]), 2)
        result.append(item)
    return result


def register_erp_routes(
    app,
    database_path,
    *,
    connect,
    insert_and_return_id,
    insert_audit,
    write_audit,
    require_roles,
    dispatch_outbox_event,
):
    bp = Blueprint("erp", __name__)
    staff = require_roles(*INTERNAL_PORTAL_ROLES)

    def require_erp(permission):
        def decorate(endpoint):
            @wraps(endpoint)
            def wrapped(*args, **kwargs):
                user = g.portal_user
                if user["role"] == "admin":
                    return endpoint(*args, **kwargs)
                with connect(database_path) as connection:
                    role_rows = connection.execute(
                        "SELECT role_code FROM erp_user_roles WHERE user_id = ?", (user["id"],)
                    ).fetchall()
                allowed = any(permission in ERP_PERMISSIONS.get(row["role_code"], set()) for row in role_rows)
                if not allowed:
                    return jsonify(error="erp_permission_required", permission=permission), 403
                g.erp_role_codes = [row["role_code"] for row in role_rows]
                return endpoint(*args, **kwargs)
            return wrapped
        return decorate

    def internal_user(endpoint):
        return staff(endpoint)

    @bp.get("/access")
    @internal_user
    def erp_access():
        user = g.portal_user
        with connect(database_path) as connection:
            roles = [row["role_code"] for row in connection.execute(
                "SELECT role_code FROM erp_user_roles WHERE user_id = ? ORDER BY role_code", (user["id"],)
            ).fetchall()]
        if user["role"] == "admin" and "erp_admin" not in roles:
            roles.append("erp_admin")
        permissions = sorted({permission for role in roles for permission in ERP_PERMISSIONS.get(role, set())})
        return jsonify(roles=roles, role_labels=ERP_ROLES, permissions=permissions)

    @bp.get("/users")
    @require_roles("admin")
    def erp_users():
        with connect(database_path) as connection:
            users = connection.execute(
                """SELECT u.id,u.username,u.role,u.active,c.name AS company
                   FROM portal_users u LEFT JOIN companies c ON c.id=u.company_id
                   WHERE u.role != 'customer' ORDER BY u.username"""
            ).fetchall()
            roles = connection.execute("SELECT user_id,role_code FROM erp_user_roles").fetchall()
        by_user = {}
        for row in roles:
            by_user.setdefault(row["user_id"], []).append(row["role_code"])
        return jsonify([dict(row, erp_roles=by_user.get(row["id"], [])) for row in users])

    @bp.put("/users/<int:user_id>/roles")
    @require_roles("admin")
    def set_erp_roles(user_id):
        payload = request.get_json(silent=True) or {}
        roles = payload.get("roles")
        if (
            not isinstance(roles, list)
            or any(not isinstance(role, str) or role not in ERP_ROLES for role in roles)
            or len(set(roles)) != len(roles)
        ):
            return jsonify(error="invalid_erp_roles"), 400
        with connect(database_path) as connection:
            target = connection.execute("SELECT id,role FROM portal_users WHERE id=? AND active=TRUE", (user_id,)).fetchone()
            if target is None or target["role"] == "customer":
                return jsonify(error="internal_user_not_found"), 404
            if target["role"] == "admin" and "erp_admin" not in roles:
                return jsonify(error="portal_admin_requires_erp_admin"), 400
            current_roles = {
                row["role_code"]
                for row in connection.execute(
                    "SELECT role_code FROM erp_user_roles WHERE user_id=?", (user_id,)
                ).fetchall()
            }
            changed = current_roles != set(roles)
            if changed:
                connection.execute("DELETE FROM erp_user_roles WHERE user_id=?", (user_id,))
                for role in roles:
                    connection.execute(
                        "INSERT INTO erp_user_roles(user_id,role_code,created_at,granted_by) VALUES (?,?,?,?)",
                        (user_id, role, now_text(), g.portal_user["id"]),
                    )
                connection.execute(
                    "UPDATE portal_users SET auth_version=auth_version+1 WHERE id=?",
                    (user_id,),
                )
            insert_audit(
                connection,
                g.portal_user["id"],
                "erp.roles.update",
                "portal_user",
                user_id,
                {"roles": roles, "changed": changed, "sessions_revoked": changed},
            )
            connection.commit()
        return jsonify(user_id=user_id, roles=roles, sessions_revoked=changed)

    @bp.get("/overview")
    @internal_user
    def erp_overview():
        user = g.portal_user
        if user["role"] == "admin":
            role_codes = {"erp_admin"}
        else:
            with connect(database_path) as connection:
                role_codes = {
                    row["role_code"]
                    for row in connection.execute(
                        "SELECT role_code FROM erp_user_roles WHERE user_id=?", (user["id"],)
                    ).fetchall()
                }
            if not role_codes:
                return jsonify(error="erp_permission_required"), 403
        permissions = set().union(
            *(ERP_PERMISSIONS.get(role_code, set()) for role_code in role_codes)
        )
        with connect(database_path) as connection:
            metrics = {}
            if "sales:read" in permissions:
                metrics["sales_orders"] = connection.execute(
                    "SELECT COUNT(*) AS n FROM erp_sales_orders"
                ).fetchone()["n"]
            if "purchase:read" in permissions:
                metrics["purchase_orders"] = connection.execute(
                    "SELECT COUNT(*) AS n FROM erp_purchase_orders"
                ).fetchone()["n"]
            if "master:read" in permissions:
                metrics["products"] = connection.execute(
                    "SELECT COUNT(*) AS n FROM erp_products WHERE active=TRUE"
                ).fetchone()["n"]
                metrics["partners"] = connection.execute(
                    "SELECT COUNT(*) AS n FROM erp_partners WHERE active=TRUE"
                ).fetchone()["n"]
            if "finance:read" in permissions:
                metrics["open_receivables"] = connection.execute(
                    "SELECT COALESCE(SUM(amount),0) AS n FROM erp_financial_documents WHERE kind='receivable' AND status='open'"
                ).fetchone()["n"]
                metrics["open_payables"] = connection.execute(
                    "SELECT COALESCE(SUM(amount),0) AS n FROM erp_financial_documents WHERE kind='payable' AND status='open'"
                ).fetchone()["n"]
            unread = connection.execute("SELECT COUNT(*) AS n FROM internal_messages WHERE recipient_user_id=? AND read_at IS NULL", (user["id"],)).fetchone()["n"]
        inventory, wms_error = fetch_wms_inventory(app)
        return jsonify(
            metrics={key: round(float(value), 2) if key.startswith("open_") else int(value) for key, value in metrics.items()},
            unread_messages=int(unread),
            wms={"status": "connected" if inventory else wms_error, "mode": (inventory or {}).get("mode"), "note": (inventory or {}).get("note")},
        )

    @bp.get("/partners")
    @internal_user
    @require_erp("master:read")
    def list_partners():
        with connect(database_path) as connection:
            rows = connection.execute("SELECT * FROM erp_partners ORDER BY LOWER(name),id DESC LIMIT 300").fetchall()
        return jsonify([dict(row, active=bool(row["active"])) for row in rows])

    @bp.post("/partners")
    @internal_user
    @require_erp("master:write")
    def create_partner():
        payload = request.get_json(silent=True) or {}
        kind = str(payload.get("kind", ""))
        name = str(payload.get("name", "")).strip()
        tax_id = str(payload.get("tax_id", "")).strip() or None
        email = str(payload.get("email", "")).strip().lower() or None
        phone = str(payload.get("phone", "")).strip() or None
        address = str(payload.get("address", "")).strip() or None
        if kind not in {"customer", "supplier", "both"} or not name or len(name) > 160 or (tax_id and len(tax_id) > 32) or (email and (len(email) > 254 or "@" not in email)):
            return jsonify(error="invalid_partner"), 400
        with connect(database_path) as connection:
            try:
                partner_id = insert_and_return_id(connection,
                    "INSERT INTO erp_partners(kind,name,tax_id,email,phone,address,active,created_by,created_at) VALUES (?,?,?,?,?,?,TRUE,?,?)",
                    (kind, name, tax_id, email, phone, address, g.portal_user["id"], now_text()))
                connection.commit()
            except Exception as error:
                if "unique" in str(error).lower() or "duplicate" in str(error).lower():
                    return jsonify(error="partner_tax_id_already_exists"), 409
                raise
        write_audit(database_path, g.portal_user["id"], "erp.partner.create", "erp_partner", partner_id, {"kind": kind})
        return jsonify(id=partner_id, kind=kind, name=name, tax_id=tax_id), 201

    @bp.get("/products")
    @internal_user
    @require_erp("master:read")
    def list_products():
        inventory, wms_error = fetch_wms_inventory(app)
        stock_by_sku = {item.get("sku"): item for item in (inventory or {}).get("items", []) if isinstance(item, dict)}
        with connect(database_path) as connection:
            rows = connection.execute("SELECT * FROM erp_products ORDER BY sku").fetchall()
        products = []
        for row in rows:
            item = dict(row)
            remote = stock_by_sku.get(item["sku"])
            item["sale_price"] = round(float(item["sale_price"]), 2)
            item["purchase_cost"] = round(float(item["purchase_cost"]), 2)
            item["active"] = bool(item["active"])
            item["on_hand"] = remote.get("on_hand") if remote else None
            item["stock_source"] = "Azure WMS" if remote else wms_error or "sku_not_in_wms"
            products.append(item)
        return jsonify(products=products, wms={"status": "connected" if inventory else wms_error, "mode": (inventory or {}).get("mode"), "note": (inventory or {}).get("note")})

    @bp.post("/products")
    @internal_user
    @require_erp("master:write")
    def save_product():
        payload = request.get_json(silent=True) or {}
        sku = str(payload.get("sku", "")).strip().upper()
        name = str(payload.get("name", "")).strip()
        unit = str(payload.get("unit", "")).strip()
        raw_sale_price = payload.get("sale_price")
        raw_purchase_cost = payload.get("purchase_cost")
        if isinstance(raw_sale_price, bool) or isinstance(raw_purchase_cost, bool):
            return jsonify(error="invalid_prices"), 400
        try:
            sale_price, purchase_cost = float(raw_sale_price), float(raw_purchase_cost)
        except (TypeError, ValueError):
            return jsonify(error="invalid_prices"), 400
        if not SKU_PATTERN.fullmatch(sku) or not name or len(name) > 180 or not unit or len(unit) > 32 or not math.isfinite(sale_price) or not math.isfinite(purchase_cost) or min(sale_price, purchase_cost) < 0 or max(sale_price, purchase_cost) > 1_000_000:
            return jsonify(error="invalid_product"), 400
        initial_stock = payload.get("initial_stock", 0)
        if isinstance(initial_stock, bool) or not isinstance(initial_stock, int) or not 0 <= initial_stock <= 1_000_000:
            return jsonify(error="invalid_initial_stock"), 400
        wms_result, wms_error = update_wms_catalog(
            app,
            [{"sku": sku, "name": name, "unit": unit, "unit_price": sale_price, "initial_stock": initial_stock}],
        )
        if not wms_result:
            return jsonify(error="wms_catalog_sync_failed", reason=wms_error), 503
        with connect(database_path) as connection:
            connection.execute(
                """INSERT INTO erp_products(sku,name,unit,sale_price,purchase_cost,active,updated_by,updated_at)
                   VALUES (?,?,?,?,?,TRUE,?,?) ON CONFLICT(sku) DO UPDATE SET
                   name=excluded.name,unit=excluded.unit,sale_price=excluded.sale_price,
                   purchase_cost=excluded.purchase_cost,active=TRUE,updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
                (sku, name, unit, sale_price, purchase_cost, g.portal_user["id"], now_text()),
            )
            connection.commit()
        write_audit(database_path, g.portal_user["id"], "erp.product.upsert", "erp_product", sku, {"sale_price": sale_price, "purchase_cost": purchase_cost})
        return jsonify(sku=sku, name=name, unit=unit, sale_price=sale_price, purchase_cost=purchase_cost), 200

    @bp.post("/products/import")
    @internal_user
    @require_erp("master:write")
    def import_products():
        payload = request.get_json(silent=True) or {}
        raw_products = payload.get("products")
        if not isinstance(raw_products, list) or not 1 <= len(raw_products) <= 500:
            return jsonify(error="products_must_contain_1_to_500_items"), 400
        products, seen = [], set()
        for index, raw in enumerate(raw_products, start=2):
            if not isinstance(raw, dict):
                return jsonify(error="invalid_product_row", row=index), 400
            sku = str(raw.get("sku", "")).strip().upper()
            name = str(raw.get("name", "")).strip()
            unit = str(raw.get("unit", "")).strip()
            raw_sale_price = raw.get("sale_price")
            raw_purchase_cost = raw.get("purchase_cost")
            if isinstance(raw_sale_price, bool) or isinstance(raw_purchase_cost, bool):
                return jsonify(error="invalid_product_prices", row=index), 400
            try:
                sale_price = float(raw_sale_price)
                purchase_cost = float(raw_purchase_cost)
            except (TypeError, ValueError):
                return jsonify(error="invalid_product_prices", row=index), 400
            initial_stock = raw.get("initial_stock")
            if (
                not SKU_PATTERN.fullmatch(sku)
                or sku in seen
                or not name
                or len(name) > 180
                or not unit
                or len(unit) > 32
                or not math.isfinite(sale_price)
                or not math.isfinite(purchase_cost)
                or min(sale_price, purchase_cost) < 0
                or max(sale_price, purchase_cost) > 1_000_000
                or isinstance(initial_stock, bool)
                or not isinstance(initial_stock, int)
                or not 0 <= initial_stock <= 1_000_000
            ):
                return jsonify(error="invalid_product_row", row=index, sku=sku or None), 400
            product = {
                "sku": sku,
                "name": name,
                "unit": unit,
                "sale_price": round(sale_price, 2),
                "purchase_cost": round(purchase_cost, 2),
                "initial_stock": initial_stock,
            }
            products.append(product)
            seen.add(sku)

        wms_products = [
            {
                "sku": item["sku"],
                "name": item["name"],
                "unit": item["unit"],
                "unit_price": item["sale_price"],
                "initial_stock": item["initial_stock"],
            }
            for item in products
        ]
        wms_result, wms_error = update_wms_catalog(app, wms_products)
        if not wms_result:
            return jsonify(error="wms_catalog_sync_failed", reason=wms_error), 503

        created_count = 0
        with connect(database_path) as connection:
            try:
                for item in products:
                    current = connection.execute(
                        "SELECT 1 FROM erp_products WHERE sku=?", (item["sku"],)
                    ).fetchone()
                    if current is None:
                        created_count += 1
                    connection.execute(
                        """INSERT INTO erp_products(sku,name,unit,sale_price,purchase_cost,active,updated_by,updated_at)
                           VALUES (?,?,?,?,?,TRUE,?,?) ON CONFLICT(sku) DO UPDATE SET
                           name=excluded.name,unit=excluded.unit,sale_price=excluded.sale_price,
                           purchase_cost=excluded.purchase_cost,active=TRUE,updated_by=excluded.updated_by,
                           updated_at=excluded.updated_at""",
                        (
                            item["sku"], item["name"], item["unit"], item["sale_price"],
                            item["purchase_cost"], g.portal_user["id"], now_text(),
                        ),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        write_audit(
            database_path,
            g.portal_user["id"],
            "erp.product.import",
            "erp_product_catalog",
            None,
            {"rows": len(products), "created": created_count, "updated": len(products) - created_count, "stock_preserved": True},
        )
        return jsonify(
            imported=len(products),
            created=created_count,
            updated=len(products) - created_count,
            stock_preserved=True,
            wms_mode=wms_result.get("mode"),
        ), 200

    def normalize_lines(raw_lines, connection, price_field):
        if not isinstance(raw_lines, list) or not 1 <= len(raw_lines) <= 20:
            return None, "items_must_have_1_to_20_lines"
        normalized, seen = [], set()
        for raw in raw_lines:
            if not isinstance(raw, dict):
                return None, "invalid_line"
            sku = str(raw.get("sku", "")).strip().upper()
            quantity = raw.get("quantity")
            if not SKU_PATTERN.fullmatch(sku) or isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000 or sku in seen:
                return None, "invalid_sku_quantity_or_duplicate_line"
            product = connection.execute("SELECT sku,name,unit,sale_price,purchase_cost FROM erp_products WHERE sku=? AND active=TRUE", (sku,)).fetchone()
            if product is None:
                return None, "product_not_found"
            price = round(float(product[price_field]), 2)
            normalized.append({"sku": sku, "name": product["name"], "unit": product["unit"], "quantity": quantity, "unit_price": price, "line_total": round(price * quantity, 2)})
            seen.add(sku)
        return normalized, None

    def inventory_has_skus(lines):
        inventory, error = fetch_wms_inventory(app)
        if not inventory:
            return None, error
        remote_skus = {item.get("sku") for item in inventory.get("items", []) if isinstance(item, dict)}
        missing = [line["sku"] for line in lines if line["sku"] not in remote_skus]
        return (None, "sku_not_in_azure_wms:" + ",".join(missing)) if missing else (inventory, None)

    @bp.get("/sales/orders")
    @internal_user
    @require_erp("sales:read")
    def list_sales_orders():
        with connect(database_path) as connection:
            orders = connection.execute(
                """SELECT o.*,p.name AS partner_name FROM erp_sales_orders o JOIN erp_partners p ON p.id=o.partner_id
                   ORDER BY o.id DESC LIMIT 100"""
            ).fetchall()
            result = []
            for order in orders:
                item = dict(order)
                item["total"] = round(float(item["total"]), 2)
                item["items"] = [dict(line, unit_price=round(float(line["unit_price"]), 2), line_total=round(float(line["line_total"]), 2)) for line in connection.execute("SELECT sku,product_name,quantity,unit_price,line_total FROM erp_sales_order_lines WHERE sales_order_id=? ORDER BY id", (item["id"],)).fetchall()]
                result.append(item)
        return jsonify(result)

    @bp.post("/sales/orders")
    @internal_user
    @require_erp("sales:write")
    def create_sales_order():
        payload = request.get_json(silent=True) or {}
        try:
            partner_id = int(payload.get("partner_id"))
        except (TypeError, ValueError):
            return jsonify(error="customer_required"), 400
        created = now_text()
        with connect(database_path) as connection:
            partner = connection.execute("SELECT id,name,kind,active FROM erp_partners WHERE id=?", (partner_id,)).fetchone()
            if partner is None or not partner["active"] or partner["kind"] not in {"customer", "both"}:
                return jsonify(error="customer_not_found"), 400
            lines, error = normalize_lines(payload.get("items"), connection, "sale_price")
            if error:
                return jsonify(error=error), 400
        inventory, error = inventory_has_skus(lines)
        if error:
            return jsonify(error="wms_unavailable_or_sku_missing", detail=error), 503
        total = round(sum(line["line_total"] for line in lines), 2)
        reference = "VTA-{}-{}".format(datetime.now(timezone.utc).strftime("%Y%m%d"), secrets.token_hex(3).upper())
        event_id = f"evt-{uuid.uuid4().hex}"
        with connect(database_path) as connection:
            order_id = insert_and_return_id(connection,
                "INSERT INTO erp_sales_orders(partner_id,reference,status,total,event_id,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (partner_id, reference, "awaiting_wms", total, event_id, g.portal_user["id"], created, created))
            for line in lines:
                connection.execute(
                    "INSERT INTO erp_sales_order_lines(sales_order_id,sku,product_name,quantity,unit_price,line_total) VALUES (?,?,?,?,?,?)",
                    (order_id, line["sku"], line["name"], line["quantity"], line["unit_price"], line["line_total"]))
            event = {"event_id": event_id, "event_type": "order.created", "schema_version": "1.0", "source": "tangamandapio-erp", "occurred_at": created, "order": {"id": order_id, "reference": reference, "customer": partner["name"], "total": total, "items": [{"sku": line["sku"], "quantity": line["quantity"]} for line in lines]}}
            connection.execute("INSERT INTO outbox_events(event_id,order_id,payload,status,attempts,created_at) VALUES (?,?,?,'pending',0,?)", (event_id, order_id, json.dumps(event, separators=(",", ":")), created))
            connection.commit()
        delivery = dispatch_outbox_event(app, database_path, event_id)
        write_audit(database_path, g.portal_user["id"], "erp.sales_order.create", "erp_sales_order", order_id, {"event_id": event_id, "total": total, "sku_count": len(lines)})
        return jsonify(id=order_id, reference=reference, event_id=event_id, partner=partner["name"], total=total, status="awaiting_wms", delivery=delivery, wms_mode=inventory.get("mode")), 201

    def reconcile_erp_event(kind, document_id):
        table = "erp_sales_orders" if kind == "sales" else "erp_purchase_orders"
        with connect(database_path) as connection:
            doc = connection.execute(f"SELECT id,partner_id,reference,status,total,event_id FROM {table} WHERE id=?", (document_id,)).fetchone()
            if doc is None:
                return None, (jsonify(error="document_not_found"), 404)
            if not doc["event_id"]:
                return dict(doc), None
        result, error = fetch_wms_event(app, doc["event_id"])
        if error:
            return None, (jsonify(error="wms_status_unavailable", detail=error), 503)
        status = str(result.get("status", "pending"))
        completed = status in ({"demo_fulfillment_completed", "fulfilled", "completed"} if kind == "sales" else {"demo_restock_completed", "restocked", "completed"})
        rejected = status.startswith("rejected_") or status in {"rejected", "failed"}
        if completed and status.startswith("demo_"):
            next_status = "received_demo" if kind == "purchase" else "completed_demo"
        else:
            next_status = "completed" if completed else ("rejected" if rejected else "awaiting_wms")
        with connect(database_path) as connection:
            connection.execute(f"UPDATE {table} SET status=?,updated_at=? WHERE id=?", (next_status, now_text(), document_id))
            if completed:
                fin_kind = "receivable" if kind == "sales" else "payable"
                ref_prefix = "CxC" if kind == "sales" else "CxP"
                source_type = "sales_order" if kind == "sales" else "purchase_order"
                description = ("Venta " if kind == "sales" else "Compra ") + doc["reference"]
                connection.execute(
                    """INSERT INTO erp_financial_documents(kind,reference,partner_id,source_type,source_id,description,amount,status,created_by,created_at)
                       VALUES (?,?,?,?,?,?,?,'open',?,?) ON CONFLICT(kind,source_type,source_id) DO NOTHING""",
                    (fin_kind, f"{ref_prefix}-{doc['reference']}", doc["partner_id"], source_type, str(document_id), description, doc["total"], g.portal_user["id"], now_text()),
                )
            connection.commit()
        return {**dict(doc), "status": next_status, "wms_result": result}, None

    @bp.post("/sales/orders/<int:order_id>/refresh")
    @internal_user
    @require_erp("sales:read")
    def refresh_sales_order(order_id):
        value, error = reconcile_erp_event("sales", order_id)
        if error:
            return error
        return jsonify(value)

    @bp.get("/purchases/orders")
    @internal_user
    @require_erp("purchase:read")
    def list_purchase_orders():
        with connect(database_path) as connection:
            orders = connection.execute("SELECT o.*,p.name AS partner_name FROM erp_purchase_orders o JOIN erp_partners p ON p.id=o.partner_id ORDER BY o.id DESC LIMIT 100").fetchall()
            result = []
            for order in orders:
                item = dict(order)
                item["total"] = round(float(item["total"]), 2)
                item["items"] = [dict(line, unit_cost=round(float(line["unit_cost"]), 2), line_total=round(float(line["line_total"]), 2)) for line in connection.execute("SELECT sku,product_name,quantity,unit_cost AS unit_cost,line_total FROM erp_purchase_order_lines WHERE purchase_order_id=? ORDER BY id", (item["id"],)).fetchall()]
                result.append(item)
        return jsonify(result)

    @bp.post("/purchases/orders")
    @internal_user
    @require_erp("purchase:write")
    def create_purchase_order():
        payload = request.get_json(silent=True) or {}
        try:
            partner_id = int(payload.get("partner_id"))
        except (TypeError, ValueError):
            return jsonify(error="supplier_required"), 400
        created = now_text()
        with connect(database_path) as connection:
            partner = connection.execute("SELECT id,name,kind,active FROM erp_partners WHERE id=?", (partner_id,)).fetchone()
            if partner is None or not partner["active"] or partner["kind"] not in {"supplier", "both"}:
                return jsonify(error="supplier_not_found"), 400
            lines, error = normalize_lines(payload.get("items"), connection, "purchase_cost")
            if error:
                return jsonify(error=error), 400
        inventory, error = inventory_has_skus(lines)
        if error:
            return jsonify(error="wms_unavailable_or_sku_missing", detail=error), 503
        total = round(sum(line["line_total"] for line in lines), 2)
        reference = "OC-{}-{}".format(datetime.now(timezone.utc).strftime("%Y%m%d"), secrets.token_hex(3).upper())
        with connect(database_path) as connection:
            order_id = insert_and_return_id(connection,
                "INSERT INTO erp_purchase_orders(partner_id,reference,status,total,created_by,created_at,updated_at) VALUES (?,?, 'ordered', ?,?,?,?)",
                (partner_id, reference, total, g.portal_user["id"], created, created))
            for line in lines:
                connection.execute("INSERT INTO erp_purchase_order_lines(purchase_order_id,sku,product_name,quantity,unit_cost,line_total) VALUES (?,?,?,?,?,?)", (order_id, line["sku"], line["name"], line["quantity"], line["unit_price"], line["line_total"]))
            connection.commit()
        write_audit(database_path, g.portal_user["id"], "erp.purchase_order.create", "erp_purchase_order", order_id, {"reference": reference, "total": total})
        return jsonify(id=order_id, reference=reference, partner=partner["name"], total=total, status="ordered", wms_mode=inventory.get("mode")), 201

    @bp.post("/purchases/orders/<int:order_id>/receive")
    @internal_user
    @require_erp("purchase:write")
    def receive_purchase_order(order_id):
        with connect(database_path) as connection:
            order = connection.execute("SELECT o.*,p.name AS partner_name FROM erp_purchase_orders o JOIN erp_partners p ON p.id=o.partner_id WHERE o.id=?", (order_id,)).fetchone()
            if order is None:
                return jsonify(error="purchase_order_not_found"), 404
            if order["status"] == "received_demo" or order["status"] == "received":
                return jsonify(id=order_id, reference=order["reference"], status=order["status"], duplicate=True), 200
            if order["status"] != "ordered":
                return jsonify(error="purchase_order_not_receivable", status=order["status"]), 409
            lines = [dict(row) for row in connection.execute("SELECT sku,quantity FROM erp_purchase_order_lines WHERE purchase_order_id=? ORDER BY id", (order_id,)).fetchall()]
            event_id = f"evt-{uuid.uuid4().hex}"
            created = now_text()
            event = {"event_id": event_id, "event_type": "purchase.received", "schema_version": "1.0", "source": "tangamandapio-erp", "occurred_at": created, "purchase_order": {"id": order_id, "reference": order["reference"], "supplier": order["partner_name"], "items": lines}}
            connection.execute("UPDATE erp_purchase_orders SET status='receipt_pending',event_id=?,updated_at=? WHERE id=?", (event_id, created, order_id))
            connection.execute("INSERT INTO outbox_events(event_id,order_id,payload,status,attempts,created_at) VALUES (?,?,?,'pending',0,?)", (event_id, order_id, json.dumps(event, separators=(",", ":")), created))
            connection.commit()
        delivery = dispatch_outbox_event(app, database_path, event_id)
        write_audit(database_path, g.portal_user["id"], "erp.purchase_order.receive_requested", "erp_purchase_order", order_id, {"event_id": event_id})
        return jsonify(id=order_id, reference=order["reference"], event_id=event_id, status="receipt_pending", delivery=delivery), 202

    @bp.post("/purchases/orders/<int:order_id>/refresh")
    @internal_user
    @require_erp("purchase:read")
    def refresh_purchase_order(order_id):
        value, error = reconcile_erp_event("purchase", order_id)
        if error:
            return error
        return jsonify(value)

    @bp.get("/finance/documents")
    @internal_user
    @require_erp("finance:read")
    def list_finance_documents():
        with connect(database_path) as connection:
            rows = connection.execute("""SELECT f.*,p.name AS partner_name FROM erp_financial_documents f
                LEFT JOIN erp_partners p ON p.id=f.partner_id ORDER BY f.id DESC LIMIT 200""").fetchall()
        return jsonify(_money_rows(rows, ("amount",)))

    @bp.post("/finance/expenses")
    @internal_user
    @require_erp("finance:write")
    def create_expense():
        payload = request.get_json(silent=True) or {}
        description = str(payload.get("description", "")).strip()
        due_date = str(payload.get("due_date", "")).strip() or None
        reference = str(payload.get("reference", "")).strip()
        try:
            amount = round(float(payload.get("amount")), 2)
            partner_id = int(payload["partner_id"]) if payload.get("partner_id") else None
        except (TypeError, ValueError):
            return jsonify(error="invalid_expense"), 400
        import math
        if not description or len(description) > 180 or not math.isfinite(amount) or amount <= 0 or amount > 10_000_000 or (due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_date)):
            return jsonify(error="invalid_expense"), 400
        if not reference:
            reference = f"GTO-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3).upper()}"
        with connect(database_path) as connection:
            if partner_id:
                partner = connection.execute("SELECT id,kind FROM erp_partners WHERE id=? AND active=TRUE", (partner_id,)).fetchone()
                if partner is None or partner["kind"] not in {"supplier", "both"}:
                    return jsonify(error="supplier_not_found"), 400
            try:
                document_id = insert_and_return_id(connection,
                    "INSERT INTO erp_financial_documents(kind,reference,partner_id,source_type,source_id,description,amount,status,due_date,created_by,created_at) VALUES ('payable',?,?, 'manual',?,?,?,'open',?,?,?)",
                    (reference, partner_id, uuid.uuid4().hex, description, amount, due_date, g.portal_user["id"], now_text()))
                connection.commit()
            except Exception as error:
                if "unique" in str(error).lower() or "duplicate" in str(error).lower():
                    return jsonify(error="financial_reference_already_exists"), 409
                raise
        write_audit(database_path, g.portal_user["id"], "erp.finance.expense.create", "financial_document", document_id, {"amount": amount})
        return jsonify(id=document_id, reference=reference, kind="payable", amount=amount, status="open"), 201

    @bp.post("/finance/documents/<int:document_id>/settle")
    @internal_user
    @require_erp("finance:write")
    def settle_document(document_id):
        with connect(database_path) as connection:
            row = connection.execute("SELECT id,status FROM erp_financial_documents WHERE id=?", (document_id,)).fetchone()
            if row is None:
                return jsonify(error="financial_document_not_found"), 404
            if row["status"] == "paid":
                return jsonify(id=document_id, status="paid", duplicate=True), 200
            if row["status"] != "open":
                return jsonify(error="financial_document_not_open"), 409
            connection.execute("UPDATE erp_financial_documents SET status='paid',settled_at=? WHERE id=? AND status='open'", (now_text(), document_id))
            connection.commit()
        write_audit(database_path, g.portal_user["id"], "erp.finance.document.settle", "financial_document", document_id)
        return jsonify(id=document_id, status="paid")

    @bp.get("/mail/users")
    @internal_user
    def mail_users():
        with connect(database_path) as connection:
            rows = connection.execute("SELECT id,username FROM portal_users WHERE active=TRUE AND role != 'customer' ORDER BY username").fetchall()
        return jsonify([dict(row) for row in rows])

    @bp.get("/mail/status")
    @internal_user
    def mail_status():
        settings = _smtp_settings(app.config)
        return jsonify(
            transport="smtp" if settings["configured"] else "portal_only",
            smtp_configured=settings["configured"],
            security=settings["security"] if settings["configured"] else None,
            recipient_domain=settings["recipient_domain"] or None,
            note=("El relay SMTP acepta el envío; la entrega final depende de sus buzones y políticas."
                  if settings["configured"] else "El mensaje queda en la bandeja privada del portal."),
        )

    @bp.post("/mail/smtp-test")
    @require_roles("admin")
    def mail_smtp_test():
        settings = _smtp_settings(app.config)
        if not settings["configured"]:
            return jsonify(error="smtp_not_configured"), 409
        user = g.portal_user
        result = _deliver_smtp(
            app.config,
            sender_username=user["username"],
            recipient_username=user["username"],
            subject="Prueba del correo corporativo",
            body="Prueba de conectividad SMTP iniciada desde el panel administrativo.",
        )
        if result["status"] != "accepted_by_smtp":
            return jsonify(error=result["error"] or result["status"], status=result["status"]), 502
        write_audit(database_path, user["id"], "mail.smtp.test", "smtp_relay", None, {"status": result["status"]})
        return jsonify(status=result["status"], message_id=result["message_id"])

    @bp.get("/mail")
    @internal_user
    def mail_list():
        folder = request.args.get("folder", "inbox")
        user_id = g.portal_user["id"]
        if folder not in {"inbox", "sent"}:
            return jsonify(error="invalid_mail_folder"), 400
        column = "recipient_user_id" if folder == "inbox" else "sender_user_id"
        peer_column = "sender_user_id" if folder == "inbox" else "recipient_user_id"
        with connect(database_path) as connection:
            rows = connection.execute(
                f"""SELECT m.id,m.subject,m.body,m.created_at,m.read_at,m.sender_user_id,m.recipient_user_id,
                    sender.username AS sender,recipient.username AS recipient,
                    COALESCE(delivery.smtp_status,'portal_only') AS smtp_status,
                    delivery.attempts AS smtp_attempts, delivery.last_error AS smtp_error
                    FROM internal_messages m JOIN portal_users sender ON sender.id=m.sender_user_id
                    JOIN portal_users recipient ON recipient.id=m.recipient_user_id
                    LEFT JOIN internal_mail_delivery delivery ON delivery.message_id=m.id
                    WHERE m.{column}=? ORDER BY m.id DESC LIMIT 100""", (user_id,)
            ).fetchall()
        result = [dict(row) for row in rows]
        if folder == "inbox":
            for item in result:
                item["unread"] = item["read_at"] is None
        return jsonify(result)

    @bp.post("/mail")
    @internal_user
    def send_internal_message():
        payload = request.get_json(silent=True) or {}
        try:
            recipient_id = int(payload.get("recipient_id"))
        except (TypeError, ValueError):
            return jsonify(error="recipient_required"), 400
        subject = str(payload.get("subject", "")).strip()
        body = str(payload.get("body", "")).strip()
        if not subject or len(subject) > 160 or any(ord(char) < 32 for char in subject) or not body or len(body) > 20000:
            return jsonify(error="invalid_message"), 400
        with connect(database_path) as connection:
            recipient = connection.execute("SELECT id,username FROM portal_users WHERE id=? AND active=TRUE AND role!='customer'", (recipient_id,)).fetchone()
            if recipient is None:
                return jsonify(error="internal_recipient_not_found"), 404
            sender = connection.execute("SELECT username FROM portal_users WHERE id=? AND active=TRUE", (g.portal_user["id"],)).fetchone()
            message_id = insert_and_return_id(connection,
                "INSERT INTO internal_messages(sender_user_id,recipient_user_id,subject,body,created_at) VALUES (?,?,?,?,?)",
                (g.portal_user["id"], recipient_id, subject, body, now_text()))
            connection.commit()
        delivery = _deliver_smtp(
            app.config,
            sender_username=sender["username"],
            recipient_username=recipient["username"],
            subject=subject,
            body=body,
            message_id=message_id,
        )
        settings = _smtp_settings(app.config)
        with connect(database_path) as connection:
            connection.execute(
                """INSERT INTO internal_mail_delivery(message_id,smtp_status,attempts,last_error,smtp_message_id,updated_at)
                   VALUES (?,?,?,?,?,?) ON CONFLICT(message_id) DO UPDATE SET
                   smtp_status=excluded.smtp_status,
                   attempts=internal_mail_delivery.attempts+excluded.attempts,
                   last_error=excluded.last_error,
                   smtp_message_id=excluded.smtp_message_id,
                   updated_at=excluded.updated_at""",
                (message_id, delivery["status"], int(settings["configured"]), delivery["error"], delivery["message_id"], now_text()),
            )
            connection.commit()
        write_audit(database_path, g.portal_user["id"], "mail.internal.send", "internal_message", message_id, {"recipient_id": recipient_id})
        return jsonify(id=message_id, subject=subject, status="sent_internal", smtp_status=delivery["status"], smtp_error=delivery["error"]), 201

    @bp.post("/mail/<int:message_id>/read")
    @internal_user
    def mark_internal_message_read(message_id):
        with connect(database_path) as connection:
            row = connection.execute("SELECT id,read_at FROM internal_messages WHERE id=? AND recipient_user_id=?", (message_id, g.portal_user["id"])).fetchone()
            if row is None:
                return jsonify(error="message_not_found"), 404
            if row["read_at"] is None:
                connection.execute("UPDATE internal_messages SET read_at=? WHERE id=? AND recipient_user_id=? AND read_at IS NULL", (now_text(), message_id, g.portal_user["id"]))
                connection.commit()
        return jsonify(id=message_id, read=True)

    app.register_blueprint(bp, url_prefix="/api/erp")
