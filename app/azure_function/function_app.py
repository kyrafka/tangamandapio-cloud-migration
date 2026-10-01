import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def _client_config():
    # Importar los SDK de datos bajo demanda evita que un problema de
    # dependencias en Oryx impida que el host indexe *toda* la Function App.
    from azure.identity import DefaultAzureCredential

    return {
        "blob_account_url": os.environ["AZURE_BLOB_ACCOUNT_URL"],
        "queue_account_url": os.environ["AZURE_QUEUE_ACCOUNT_URL"],
        "queue_name": os.environ["WMS_QUEUE_NAME"],
        "container_name": os.environ["EVIDENCE_CONTAINER"],
        "credential": DefaultAzureCredential(
            exclude_interactive_browser_credential=True
        ),
    }


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

    # Estos SDK se requieren para procesar el evento, no para que Azure
    # descubra y publique la ruta HTTP durante el arranque.
    from azure.core.exceptions import ResourceExistsError
    from azure.storage.blob import BlobClient
    from azure.storage.queue import QueueClient

    config = _client_config()
    blob = BlobClient(
        account_url=config["blob_account_url"],
        container_name=config["container_name"],
        blob_name=f"{event_id}.json",
        credential=config["credential"],
    )

    try:
        blob.upload_blob(json.dumps(document), overwrite=False)
    except ResourceExistsError:
        logging.info("duplicate_event event_id=%s", event_id)
        return func.HttpResponse(
            json.dumps({"event_id": event_id, "status": "duplicate"}),
            status_code=200,
            mimetype="application/json",
        )

    queue = QueueClient(
        account_url=config["queue_account_url"],
        queue_name=config["queue_name"],
        credential=config["credential"],
    )
    queue.send_message(
        json.dumps({"event_id": event_id, "sha256": document["sha256"]}),
        time_to_live=timedelta(days=7),
    )
    logging.info("queued_event event_id=%s sha256=%s", event_id, document["sha256"])
    return func.HttpResponse(
        json.dumps(
            {"event_id": event_id, "status": "queued", "sha256": document["sha256"]}
        ),
        status_code=202,
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def health(_: func.HttpRequest) -> func.HttpResponse:
    """Confirma que el runtime indexó la aplicación antes de probar Storage."""
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "tangamandapio-wms"}),
        status_code=200,
        mimetype="application/json",
    )
