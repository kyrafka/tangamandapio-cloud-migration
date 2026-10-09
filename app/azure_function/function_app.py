import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from email.utils import format_datetime
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
SKU_PATTERN = re.compile(r"^[A-Z0-9_-]{3,40}$")
INVENTORY_BLOB = "inventory/state.json"
DEMO_PRODUCTS = {
    "SKU-ARROZ-001": {
        "name": "Arroz premium · saco 50 kg",
        "unit": "saco",
        "unit_price": 42.50,
        "initial_stock": 25,
    },
    "SKU-AZUCAR-001": {
        "name": "Azúcar rubia · saco 50 kg",
        "unit": "saco",
        "unit_price": 37.50,
        "initial_stock": 40,
    },
    "SKU-ACEITE-001": {
        "name": "Aceite vegetal · caja x 12",
        "unit": "caja",
        "unit_price": 86.00,
        "initial_stock": 18,
    },
}


def _inventory_seed() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1,
        "mode": "demo-inventory-ledger",
        "initialized_at": now,
        "updated_at": now,
        "items": {
            sku: {
                "sku": sku,
                "name": product["name"],
                "unit": product["unit"],
                "unit_price": product["unit_price"],
                "currency": "PEN",
                "initial_stock": product["initial_stock"],
                "on_hand": product["initial_stock"],
            }
            for sku, product in DEMO_PRODUCTS.items()
        },
        "processed_events": {},
    }


def _validated_items(payload: dict) -> tuple[list[dict] | None, str | None]:
    order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
    items = order.get("items", payload.get("items"))
    if items is None:
        return None, None
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        return None, "items debe incluir entre 1 y 20 líneas"
    normalized = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            return None, "cada línea debe ser un objeto SKU/cantidad"
        sku = str(item.get("sku", ""))
        quantity = item.get("quantity")
        if not SKU_PATTERN.fullmatch(sku) or sku not in DEMO_PRODUCTS:
            return None, "SKU fuera del catálogo de laboratorio"
        if sku in seen:
            return None, "no se permiten SKU repetidos en el mismo pedido"
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or not 1 <= quantity <= 1000
        ):
            return None, "quantity debe ser un entero entre 1 y 1000"
        normalized.append({"sku": sku, "quantity": quantity})
        seen.add(sku)
    return normalized, None


def _blob_url(blob_name: str) -> str:
    return (
        f"{os.environ['AZURE_BLOB_ACCOUNT_URL']}/"
        f"{os.environ['EVIDENCE_CONTAINER']}/{quote(blob_name, safe='/')}"
    )


def _read_json_blob(blob_name: str, token: str) -> tuple[dict, str | None]:
    request = Request(
        _blob_url(blob_name),
        headers=_storage_headers(token, "application/json"),
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8")), response.headers.get("ETag")


def _write_json_blob(
    blob_name: str,
    document: dict,
    token: str,
    *,
    if_none_match: bool = False,
    if_match: str | None = None,
    lease_id: str | None = None,
) -> bool:
    headers = {
        **_storage_headers(token, "application/json"),
        "x-ms-blob-type": "BlockBlob",
    }
    if if_none_match:
        headers["If-None-Match"] = "*"
    if if_match:
        headers["If-Match"] = if_match
    if lease_id:
        headers["x-ms-lease-id"] = lease_id
    request = Request(
        _blob_url(blob_name),
        data=json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        headers=headers,
        method="PUT",
    )
    try:
        with urlopen(request, timeout=15):
            return True
    except HTTPError as error:
        if error.code in (409, 412):
            return False
        raise


def _ensure_inventory_blob(token: str) -> None:
    try:
        _read_json_blob(INVENTORY_BLOB, token)
        return
    except HTTPError as error:
        if error.code != 404:
            raise
    _write_json_blob(INVENTORY_BLOB, _inventory_seed(), token, if_none_match=True)


def _acquire_inventory_lease(token: str) -> str:
    lease_id = str(uuid.uuid4())
    request = Request(
        f"{_blob_url(INVENTORY_BLOB)}?comp=lease",
        data=b"",
        headers={
            **_storage_headers(token, "application/octet-stream"),
            "x-ms-lease-action": "acquire",
            "x-ms-lease-duration": "60",
            "x-ms-proposed-lease-id": lease_id,
        },
        method="PUT",
    )
    with urlopen(request, timeout=15) as response:
        return response.headers.get("x-ms-lease-id", lease_id)


def _release_inventory_lease(token: str, lease_id: str) -> None:
    request = Request(
        f"{_blob_url(INVENTORY_BLOB)}?comp=lease",
        data=b"",
        headers={
            **_storage_headers(token, "application/octet-stream"),
            "x-ms-lease-action": "release",
            "x-ms-lease-id": lease_id,
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=10):
            pass
    except HTTPError as error:
        # The finite lease may expire if the host is stopped while processing.
        if error.code not in (409, 412):
            raise


def _fulfill_against_inventory(event: dict, state: dict) -> tuple[dict, dict]:
    """Pure, idempotent inventory transaction; all amounts are lab stock."""
    event_id = event["event_id"]
    prior = state.setdefault("processed_events", {}).get(event_id)
    if prior:
        return state, dict(prior)

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    items, validation_error = _validated_items(payload)
    now = datetime.now(timezone.utc).isoformat()
    if validation_error:
        result = {
            "event_id": event_id,
            "status": "rejected_invalid_items",
            "mode": "demo-inventory-ledger",
            "processed_at": now,
            "source_sha256": event.get("sha256"),
            "note": validation_error,
            "items": [],
        }
    elif not items:
        result = {
            "event_id": event_id,
            "status": "awaiting_items",
            "mode": "demo-inventory-ledger",
            "processed_at": now,
            "source_sha256": event.get("sha256"),
            "note": "El evento no incluye SKU y cantidad; no se modificó el inventario de laboratorio.",
            "items": [],
        }
    else:
        unavailable = []
        for item in items:
            stock = int(state["items"][item["sku"]]["on_hand"])
            if item["quantity"] > stock:
                unavailable.append({**item, "available": stock})
        if unavailable:
            result = {
                "event_id": event_id,
                "status": "rejected_insufficient_stock",
                "mode": "demo-inventory-ledger",
                "processed_at": now,
                "source_sha256": event.get("sha256"),
                "note": "Stock insuficiente en el inventario ficticio; no se descontó ninguna línea.",
                "items": unavailable,
            }
        else:
            fulfilled = []
            for item in items:
                product = state["items"][item["sku"]]
                product["on_hand"] = int(product["on_hand"]) - item["quantity"]
                fulfilled.append({**item, "on_hand_after": product["on_hand"]})
            result = {
                "event_id": event_id,
                "status": "demo_fulfillment_completed",
                "mode": "demo-inventory-ledger",
                "processed_at": now,
                "source_sha256": event.get("sha256"),
                "note": "Pedido aplicado una sola vez al inventario ficticio de laboratorio; no es un ERP real.",
                "items": fulfilled,
            }
    state["processed_events"][event_id] = result
    state["updated_at"] = now
    return state, result


def _process_inventory_event(event: dict, token: str) -> dict:
    _ensure_inventory_blob(token)
    lease_id = _acquire_inventory_lease(token)
    try:
        state, etag = _read_json_blob(INVENTORY_BLOB, token)
        prior = state.get("processed_events", {}).get(event["event_id"])
        if prior:
            return dict(prior)
        updated, result = _fulfill_against_inventory(event, state)
        if not etag:
            raise RuntimeError("inventory state has no ETag")
        if not _write_json_blob(
            INVENTORY_BLOB,
            updated,
            token,
            if_match=etag,
            lease_id=lease_id,
        ):
            raise RuntimeError("inventory state changed despite the active lease")
        return result
    finally:
        _release_inventory_lease(token, lease_id)


def _managed_identity_token() -> str:
    """Obtiene un token de Storage con la identidad administrada de la App."""
    endpoint = os.environ["IDENTITY_ENDPOINT"]
    identity_header = os.environ["IDENTITY_HEADER"]
    separator = "&" if "?" in endpoint else "?"
    request = Request(
        f"{endpoint}{separator}api-version=2019-08-01&resource="
        "https%3A%2F%2Fstorage.azure.com%2F",
        headers={"X-IDENTITY-HEADER": identity_header},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def _storage_headers(token: str, content_type: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
        "x-ms-date": format_datetime(datetime.now(timezone.utc), usegmt=True),
        "x-ms-version": "2022-11-02",
    }


def _write_event_blob(document: dict, token: str) -> bool:
    """Guarda el evento; devuelve False si el id ya estaba registrado."""
    account_url = os.environ["AZURE_BLOB_ACCOUNT_URL"]
    container = os.environ["EVIDENCE_CONTAINER"]
    event_id = quote(document["event_id"], safe="")
    request = Request(
        f"{account_url}/{container}/{event_id}.json",
        data=json.dumps(document, separators=(",", ":")).encode("utf-8"),
        headers={
            **_storage_headers(token, "application/json"),
            "x-ms-blob-type": "BlockBlob",
            # Event ids are immutable. A retry may re-enqueue the accepted
            # event, but must never replace its audit record.
            "If-None-Match": "*",
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=15):
            return True
    except HTTPError as error:
        if error.code in (409, 412):
            return False
        raise


def _read_event_blob(event_id: str, token: str) -> dict:
    """Loads the immutable order event that was accepted by the HTTP endpoint."""
    account_url = os.environ["AZURE_BLOB_ACCOUNT_URL"]
    container = os.environ["EVIDENCE_CONTAINER"]
    request = Request(
        f"{account_url}/{container}/{quote(event_id, safe='')}.json",
        headers=_storage_headers(token, "application/json"),
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_fulfillment_result(document: dict, token: str) -> bool:
    """Persists a clearly labeled demo WMS result once per event."""
    account_url = os.environ["AZURE_BLOB_ACCOUNT_URL"]
    container = os.environ["EVIDENCE_CONTAINER"]
    event_id = quote(document["event_id"], safe="")
    request = Request(
        f"{account_url}/{container}/fulfillment/{event_id}.json",
        data=json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        headers={
            **_storage_headers(token, "application/json"),
            "x-ms-blob-type": "BlockBlob",
            "If-None-Match": "*",
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=15):
            return True
    except HTTPError as error:
        if error.code in (409, 412):
            return False
        raise


def _read_fulfillment_result(event_id: str, token: str) -> dict:
    account_url = os.environ["AZURE_BLOB_ACCOUNT_URL"]
    container = os.environ["EVIDENCE_CONTAINER"]
    request = Request(
        f"{account_url}/{container}/fulfillment/{quote(event_id, safe='')}.json",
        headers=_storage_headers(token, "application/json"),
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _enqueue_event(event_id: str, sha256: str, token: str) -> None:
    queue_url = os.environ["AZURE_QUEUE_ACCOUNT_URL"]
    queue_name = os.environ["WMS_QUEUE_NAME"]
    message = base64.b64encode(
        json.dumps({"event_id": event_id, "sha256": sha256}).encode("utf-8")
    ).decode("ascii")
    payload = f"<QueueMessage><MessageText>{message}</MessageText></QueueMessage>"
    request = Request(
        f"{queue_url}/{queue_name}/messages",
        data=payload.encode("utf-8"),
        headers=_storage_headers(token, "application/xml"),
        method="POST",
    )
    with urlopen(request, timeout=15):
        pass


def _has_valid_integration_token(req: func.HttpRequest) -> bool:
    """Optionally validates a Key Vault-backed token after Function auth."""
    expected_token = os.getenv("WMS_SHARED_TOKEN", "")
    supplied_token = req.headers.get("X-WMS-Token", "")
    return not expected_token or hmac.compare_digest(supplied_token, expected_token)


@app.route(route="fulfillment/events", methods=["POST"])
def receive_fulfillment_event(req: func.HttpRequest) -> func.HttpResponse:
    """Stores and enqueues an idempotent, synthetic fulfillment event."""
    if not _has_valid_integration_token(req):
        return func.HttpResponse("token de integración inválido", status_code=401)

    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("JSON inválido", status_code=400)
    if not isinstance(payload, dict):
        return func.HttpResponse("el evento debe ser un objeto JSON", status_code=400)

    event_id = str(payload.get("event_id", ""))
    event_type = str(payload.get("event_type", ""))
    if not EVENT_ID_PATTERN.fullmatch(event_id) or event_type != "order.created":
        return func.HttpResponse(
            "event_id válido y event_type=order.created son obligatorios",
            status_code=400,
        )
    _, items_error = _validated_items(payload)
    if items_error:
        return func.HttpResponse(items_error, status_code=400)

    recorded_at = datetime.now(timezone.utc).isoformat()
    document = {
        "event_id": event_id,
        "event_type": event_type,
        "schema_version": os.getenv("EVENT_SCHEMA_VERSION", "1.0"),
        "recorded_at": recorded_at,
        "payload": payload,
    }
    serialized = json.dumps(document, separators=(",", ":"), sort_keys=True)
    document["sha256"] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    token = _managed_identity_token()
    created = _write_event_blob(document, token)
    if created:
        accepted_document = document
    else:
        accepted_document = _read_event_blob(event_id, token)
        # A client retry with the same ID must refer to the same order. Do not
        # silently acknowledge a reused ID carrying different business data.
        if (
            accepted_document.get("event_type") != event_type
            or accepted_document.get("payload") != payload
        ):
            return func.HttpResponse("event_id ya usado con otro contenido", status_code=409)
        logging.info("duplicate_event_requeued event_id=%s", event_id)
    # Always enqueue after the durable blob write. If the first attempt wrote
    # the blob but failed before sending to Queue, an outbox retry must repair
    # that partial delivery. The consumer is idempotent by event_id.
    _enqueue_event(event_id, accepted_document["sha256"], token)
    logging.info(
        "queued_event event_id=%s sha256=%s duplicate=%s",
        event_id,
        document["sha256"],
        not created,
    )
    return func.HttpResponse(
        json.dumps(
            {
                "event_id": event_id,
                "status": "queued" if created else "queued_duplicate",
                "sha256": accepted_document["sha256"],
            }
        ),
        status_code=202,
        mimetype="application/json",
    )


@app.queue_trigger(
    arg_name="message",
    queue_name=os.getenv("WMS_QUEUE_NAME", "wms-fulfillment"),
    connection="AzureWebJobsStorage",
)
def process_fulfillment_message(message: func.QueueMessage) -> None:
    """Consumes events into the fictitious, durable lab inventory ledger."""
    raw_body = message.get_body().decode("utf-8")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        payload = json.loads(base64.b64decode(raw_body, validate=True).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("queue message must be a JSON object")

    event_id = str(payload.get("event_id", ""))
    expected_hash = str(payload.get("sha256", ""))
    if not EVENT_ID_PATTERN.fullmatch(event_id) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("queue message has an invalid event id or hash")

    token = _managed_identity_token()
    event = _read_event_blob(event_id, token)
    stored_hash = str(event.get("sha256", ""))
    hash_document = dict(event)
    hash_document.pop("sha256", None)
    actual_hash = hashlib.sha256(
        json.dumps(hash_document, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    if event.get("event_id") != event_id or stored_hash != expected_hash or actual_hash != stored_hash:
        raise ValueError("stored event does not match the queued checksum")

    result = _process_inventory_event(event, token)
    result["event_type"] = event.get("event_type")
    created = _write_fulfillment_result(result, token)
    logging.info(
        "wms_demo_%s event_id=%s sha256=%s status=%s",
        "result_written" if created else "already_processed",
        event_id,
        stored_hash,
        result["status"],
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Sonda pública mínima: confirma que el runtime indexó la aplicación."""
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "tangamandapio-wms"}),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="fulfillment/events/{event_id}", methods=["GET"])
def fulfillment_status(req: func.HttpRequest) -> func.HttpResponse:
    """Returns the demo WMS result; the Function key is required by default."""
    event_id = str(req.route_params.get("event_id", ""))
    if not EVENT_ID_PATTERN.fullmatch(event_id):
        return func.HttpResponse("event_id inválido", status_code=400)
    token = _managed_identity_token()
    try:
        result = _read_fulfillment_result(event_id, token)
    except HTTPError as error:
        if error.code == 404:
            return func.HttpResponse(
                json.dumps({"event_id": event_id, "status": "pending"}),
                status_code=200,
                mimetype="application/json",
            )
        raise
    return func.HttpResponse(
        json.dumps(result, separators=(",", ":")),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="wms/inventory", methods=["GET"])
def demo_inventory(req: func.HttpRequest) -> func.HttpResponse:
    """Returns the fictional sample catalog and current lab stock."""
    token = _managed_identity_token()
    _ensure_inventory_blob(token)
    state, _ = _read_json_blob(INVENTORY_BLOB, token)
    items = sorted(state.get("items", {}).values(), key=lambda item: item["sku"])
    return func.HttpResponse(
        json.dumps(
            {
                "provider": "Azure Functions + Blob Storage",
                "mode": "demo-inventory-ledger",
                "is_real_erp": False,
                "updated_at": state.get("updated_at"),
                "note": "Catálogo y existencias ficticias para la demostración; no representa inventario comercial real.",
                "items": items,
            },
            separators=(",", ":"),
        ),
        status_code=200,
        mimetype="application/json",
    )
