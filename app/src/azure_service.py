import hashlib
import hmac
import json
import logging
import os
import re
import socket
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request


LOGGER = logging.getLogger("tangamandapio.azure_simulator")
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def create_azure_app(test_config=None):
    """Local contract simulator for the Azure Function receiver."""
    app = Flask(__name__)
    app.config.from_mapping(
        FUNCTION_KEY=os.getenv("FUNCTION_KEY", ""), MAX_CONTENT_LENGTH=1024 * 1024
    )
    if test_config:
        app.config.update(test_config)

    received_events = {}
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
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "no-store"
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
                    "provider": "Azure-simulated",
                }
            )
        )
        return response

    @app.get("/metrics")
    def metrics():
        values = app.extensions["metrics"]
        return (
            "# HELP tangamandapio_azure_simulator_requests_total HTTP responses from the local Azure contract simulator.\n"
            "# TYPE tangamandapio_azure_simulator_requests_total counter\n"
            f"tangamandapio_azure_simulator_requests_total {values['requests_total']}\n"
            "# HELP tangamandapio_azure_simulator_events_queued_total Accepted fulfillment events.\n"
            "# TYPE tangamandapio_azure_simulator_events_queued_total counter\n"
            f"tangamandapio_azure_simulator_events_queued_total {values['events_queued_total']}\n",
            200,
            {"Content-Type": "text/plain; version=0.0.4"},
        )

    def authorized():
        expected_key = app.config["FUNCTION_KEY"]
        if not expected_key:
            return True
        return hmac.compare_digest(request.headers.get("x-functions-key", ""), expected_key)

    @app.get("/health")
    def health():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(
            status="ok",
            provider="Azure-simulated",
            instance=socket.gethostname(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @app.post("/api/fulfillment/events")
    def receive():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        payload = request.get_json(silent=True)
        event_id = str((payload or {}).get("event_id", ""))
        if not isinstance(payload, dict) or not EVENT_ID_PATTERN.fullmatch(event_id):
            return jsonify(error="event_id válido es obligatorio"), 400
        if event_id in received_events:
            return jsonify(status="duplicate", event=received_events[event_id]), 200

        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        event = {
            "event_id": event_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "sha256": digest,
            "payload": payload,
        }
        received_events[event_id] = event
        app.extensions["metrics"]["events_queued_total"] += 1
        return jsonify(status="queued", event=event), 202

    @app.get("/ready")
    def ready():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(status="ready", provider="Azure-simulated")

    @app.get("/api/events")
    def events():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(list(received_events.values()))

    return app


app = create_azure_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
