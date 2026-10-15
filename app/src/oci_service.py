import hmac
import json
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request


LOGGER = logging.getLogger("andemarket.oci")


def create_oci_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SERVICE_TOKEN=os.getenv("SERVICE_TOKEN", ""), MAX_CONTENT_LENGTH=1024 * 1024
    )
    if test_config:
        app.config.update(test_config)

    received_events = []

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
                    "provider": "OCI-simulated",
                }
            )
        )
        return response

    def authorized():
        expected_token = app.config["SERVICE_TOKEN"]
        if not expected_token:
            return True
        supplied = request.headers.get("Authorization", "")
        expected = f"Bearer {expected_token}"
        return hmac.compare_digest(supplied, expected)

    @app.get("/health")
    def health():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(
            status="ok",
            provider="OCI-simulated",
            instance=socket.gethostname(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @app.post("/api/receive")
    def receive():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not payload:
            return jsonify(error="se requiere un objeto JSON"), 400

        event = {
            "sequence": len(received_events) + 1,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        received_events.append(event)
        return jsonify(status="accepted", event=event), 202

    @app.get("/ready")
    def ready():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(status="ready", provider="OCI-simulated")

    @app.get("/api/events")
    def events():
        if not authorized():
            return jsonify(status="unauthorized"), 401
        return jsonify(received_events)

    return app


app = create_oci_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8081")))
