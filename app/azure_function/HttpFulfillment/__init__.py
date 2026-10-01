import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone

import azure.functions as func


EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Persist and queue one idempotent synthetic WMS fulfillment event."""
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

    # Do not import SDKs during function discovery: Azure can publish the
    # endpoints even while an Oryx dependency error is being diagnosed.
    from azure.core.exceptions import ResourceExistsError
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobClient
    from azure.storage.queue import QueueClient

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

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    blob = BlobClient(
        account_url=os.environ["AZURE_BLOB_ACCOUNT_URL"],
        container_name=os.environ["EVIDENCE_CONTAINER"],
        blob_name=f"{event_id}.json",
        credential=credential,
    )
    try:
        blob.upload_blob(json.dumps(document), overwrite=False)
    except ResourceExistsError:
        return func.HttpResponse(
            json.dumps({"event_id": event_id, "status": "duplicate"}),
            status_code=200,
            mimetype="application/json",
        )

    queue = QueueClient(
        account_url=os.environ["AZURE_QUEUE_ACCOUNT_URL"],
        queue_name=os.environ["WMS_QUEUE_NAME"],
        credential=credential,
    )
    queue.send_message(
        json.dumps({"event_id": event_id, "sha256": document["sha256"]}),
        time_to_live=7 * 24 * 60 * 60,
    )
    logging.info("queued_event event_id=%s", event_id)
    return func.HttpResponse(
        json.dumps({"event_id": event_id, "status": "queued", "sha256": document["sha256"]}),
        status_code=202,
        mimetype="application/json",
    )
