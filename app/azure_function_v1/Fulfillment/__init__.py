import base64
import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import azure.functions as func


EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def _managed_identity_token() -> str:
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
    url = (
        f"{os.environ['AZURE_BLOB_ACCOUNT_URL']}/"
        f"{os.environ['EVIDENCE_CONTAINER']}/"
        f"{quote(document['event_id'], safe='')}.json"
    )
    request = Request(
        url,
        data=json.dumps(document, separators=(",", ":")).encode("utf-8"),
        headers={
            **_storage_headers(token, "application/json"),
            "x-ms-blob-type": "BlockBlob",
            # Evita que un reintento con el mismo event_id sobrescriba la
            # evidencia ya aceptada; Storage responde 412 ante duplicados.
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


def _enqueue_event(event_id: str, sha256: str, token: str) -> None:
    message = base64.b64encode(
        json.dumps({"event_id": event_id, "sha256": sha256}).encode("utf-8")
    ).decode("ascii")
    body = f"<QueueMessage><MessageText>{message}</MessageText></QueueMessage>"
    request = Request(
        f"{os.environ['AZURE_QUEUE_ACCOUNT_URL']}/"
        f"{os.environ['WMS_QUEUE_NAME']}/messages",
        data=body.encode("utf-8"),
        headers=_storage_headers(token, "application/xml"),
        method="POST",
    )
    with urlopen(request, timeout=15):
        pass


def main(req: func.HttpRequest) -> func.HttpResponse:
    expected_token = os.getenv("WMS_SHARED_TOKEN", "")
    if expected_token and not hmac.compare_digest(
        req.headers.get("X-WMS-Token", ""), expected_token
    ):
        return func.HttpResponse("token de integración inválido", status_code=401)

    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("JSON inválido", status_code=400)

    event_id = str(payload.get("event_id", ""))
    if not EVENT_ID_PATTERN.fullmatch(event_id) or payload.get("event_type") != "order.created":
        return func.HttpResponse(
            "event_id válido y event_type=order.created son obligatorios",
            status_code=400,
        )

    document = {
        "event_id": event_id,
        "event_type": "order.created",
        "schema_version": os.getenv("EVENT_SCHEMA_VERSION", "1.0"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
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
