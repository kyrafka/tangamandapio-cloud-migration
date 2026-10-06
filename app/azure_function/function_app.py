import base64
import hashlib
import hmac
import json
import logging
import os
import re
from email.utils import format_datetime
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


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
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=15):
            return True
    except HTTPError as error:
        if error.code == 409:
            return False
        raise


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

    event_id = str(payload.get("event_id", ""))
    event_type = str(payload.get("event_type", ""))
    if not EVENT_ID_PATTERN.fullmatch(event_id) or event_type != "order.created":
        return func.HttpResponse(
            "event_id válido y event_type=order.created son obligatorios",
            status_code=400,
        )

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
    if not _write_event_blob(document, token):
        logging.info("duplicate_event event_id=%s", event_id)
        return func.HttpResponse(
            json.dumps({"event_id": event_id, "status": "duplicate"}),
            status_code=200,
            mimetype="application/json",
        )
    _enqueue_event(event_id, document["sha256"], token)
    logging.info("queued_event event_id=%s sha256=%s", event_id, document["sha256"])
    return func.HttpResponse(
        json.dumps(
            {"event_id": event_id, "status": "queued", "sha256": document["sha256"]}
        ),
        status_code=202,
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(_: func.HttpRequest) -> func.HttpResponse:
    """Sonda pública mínima: confirma que el runtime indexó la aplicación."""
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "tangamandapio-wms"}),
        status_code=200,
        mimetype="application/json",
    )
