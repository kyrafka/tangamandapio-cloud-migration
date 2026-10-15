#!/usr/bin/env python3
"""Concurrent order-flow test against an isolated in-process Flask app.

This deliberately does not accept a URL: all writes go to a temporary SQLite
database, event delivery is disabled, and no AWS/Azure/SMTP service is called.
"""

import argparse
import json
import logging
import math
import os
import secrets
import statistics
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = PROJECT_ROOT / "app" / "aws_release" / "current"
ADMIN_USERNAME = "load-test-admin@example.test"
ADMIN_PASSWORD = secrets.token_urlsafe(32)
APP_SESSION_SECRET = secrets.token_urlsafe(32)


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def load_portal_module():
    # Put the package directory first so the release's app.py cannot be
    # shadowed by the repository's top-level app/ namespace package.
    sys.path.insert(0, str(RELEASE_DIR))
    import app as portal  # pylint: disable=import-outside-toplevel

    return portal


def authenticated_client(application):
    client = application.test_client()
    anonymous_session = client.get("/api/auth/session")
    if anonymous_session.status_code != 200:
        raise RuntimeError(f"test session initialization failed: {anonymous_session.status_code}")
    csrf = anonymous_session.get_json()["csrf_token"]
    login = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    if login.status_code != 200:
        raise RuntimeError(f"isolated test login failed: {login.status_code}")
    session = client.get("/api/auth/session")
    if session.status_code != 200 or not session.get_json().get("authenticated"):
        raise RuntimeError("isolated test session was not authenticated")
    client.csrf_token = session.get_json()["csrf_token"]
    return client


def run_transaction(client, run_id, worker_index, sequence):
    reference = f"perf-{run_id}-{worker_index}-{sequence}"
    started = time.perf_counter()
    created = client.post(
        "/api/orders",
        json={
            "customer": f"Synthetic load customer {worker_index}-{sequence}",
            "reference": reference,
            "total": 12.34,
        },
        headers={"X-CSRF-Token": client.csrf_token},
    )
    if created.status_code != 201:
        return {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "created": False,
            "read_back": False,
            "error": f"create_http_{created.status_code}",
            "order_id": None,
            "reference": reference,
        }

    body = created.get_json() or {}
    order_id = body.get("id")
    if not isinstance(order_id, int):
        return {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "created": False,
            "read_back": False,
            "error": "create_response_missing_order_id",
            "order_id": None,
            "reference": reference,
        }

    detail = client.get(f"/api/orders/{order_id}")
    detail_body = detail.get_json() or {}
    order_body = detail_body.get("order") or {}
    readable = (
        detail.status_code == 200
        and order_body.get("id") == order_id
        and order_body.get("reference") == reference
    )
    error = None
    if not readable:
        error = (
            f"read_http_{detail.status_code}"
            if detail.status_code != 200
            else "read_payload_mismatch"
        )
    return {
        "latency_ms": (time.perf_counter() - started) * 1000,
        "created": True,
        "read_back": readable,
        "error": error,
        "order_id": order_id,
        "reference": reference,
    }


def run_worker(client, worker_index, count, run_id):
    outcomes = []
    for sequence in range(count):
        outcomes.append(run_transaction(client, run_id, worker_index, sequence))
    return outcomes


def run_test(request_count, concurrency, max_p95_ms):
    portal = load_portal_module()
    logging.getLogger("tangamandapio.api").setLevel(logging.ERROR)
    run_id = uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="tangama-transactional-load-") as temp_dir:
        database_path = str(Path(temp_dir) / "isolated-load.sqlite")
        previous_log_level = os.environ.get("LOG_LEVEL")
        os.environ["LOG_LEVEL"] = "ERROR"
        try:
            application = portal.create_app(
                {
                    "TESTING": True,
                    "DATABASE_URL": "",
                    "DATABASE_PATH": database_path,
                    "APP_SESSION_SECRET": APP_SESSION_SECRET,
                    "SECRET_KEY": APP_SESSION_SECRET,
                    "BOOTSTRAP_ADMIN_USERNAME": ADMIN_USERNAME,
                    "BOOTSTRAP_ADMIN_PASSWORD": ADMIN_PASSWORD,
                    "INTERNAL_ERP_ENABLED": False,
                    "AZURE_FULFILLMENT_URL": "",
                    "AZURE_FUNCTION_KEY": "",
                    "AUTO_DISPATCH_EVENTS": False,
                    "OUTBOX_RETRY_INTERVAL": 0,
                    "VOICE_RECORDINGS_ENABLED": False,
                    "METRICS_ENABLED": False,
                    "ALARM_NOTIFICATION_TOPIC_ARN": "",
                }
            )
        finally:
            if previous_log_level is None:
                os.environ.pop("LOG_LEVEL", None)
            else:
                os.environ["LOG_LEVEL"] = previous_log_level
        logging.getLogger("tangamandapio.api").setLevel(logging.ERROR)

        clients = [authenticated_client(application) for _ in range(concurrency)]
        work_sizes = [request_count // concurrency] * concurrency
        for index in range(request_count % concurrency):
            work_sizes[index] += 1

        started = time.perf_counter()
        outcomes = []
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(run_worker, client, index, count, run_id)
                for index, (client, count) in enumerate(zip(clients, work_sizes))
            ]
            for future in as_completed(futures):
                outcomes.extend(future.result())
        elapsed_seconds = time.perf_counter() - started

        expected_prefix = f"perf-{run_id}-%"
        with portal.connect(database_path) as connection:
            persisted_orders = connection.execute(
                "SELECT COUNT(*) AS total FROM orders WHERE reference LIKE ?",
                (expected_prefix,),
            ).fetchone()["total"]
            persisted_events = connection.execute(
                """
                SELECT COUNT(*) AS total FROM outbox_events
                WHERE order_id IN (
                    SELECT id FROM orders WHERE reference LIKE ?
                )
                """,
                (expected_prefix,),
            ).fetchone()["total"]
            pending_events = connection.execute(
                """
                SELECT COUNT(*) AS total FROM outbox_events
                WHERE status = 'pending' AND order_id IN (
                    SELECT id FROM orders WHERE reference LIKE ?
                )
                """,
                (expected_prefix,),
            ).fetchone()["total"]

        latencies = [item["latency_ms"] for item in outcomes]
        errors = [item for item in outcomes if item["error"]]
        created_count = sum(item["created"] for item in outcomes)
        read_back_count = sum(item["read_back"] for item in outcomes)
        unique_order_ids = len(
            {item["order_id"] for item in outcomes if item["order_id"] is not None}
        )
        result = {
            "test_id": "PT-PERF-02",
            "scope": "in-process Flask test client; temporary SQLite database",
            "cloud_writes": False,
            "external_services": False,
            "endpoints": ["POST /api/orders", "GET /api/orders/{id}"],
            "requests": request_count,
            "concurrency": concurrency,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "throughput_transactions_per_second": round(request_count / elapsed_seconds, 2)
            if elapsed_seconds
            else 0.0,
            "latency_ms": {
                "min": round(min(latencies), 2) if latencies else 0.0,
                "mean": round(statistics.fmean(latencies), 2) if latencies else 0.0,
                "p95": round(percentile(latencies, 0.95), 2),
                "max": round(max(latencies), 2) if latencies else 0.0,
            },
            "created_http_201": created_count,
            "read_back_http_200": read_back_count,
            "unique_order_ids": unique_order_ids,
            "persisted_orders": persisted_orders,
            "persisted_outbox_events": persisted_events,
            "pending_outbox_events_expected_without_dispatch": pending_events,
            "errors": [item["error"] for item in errors[:20]],
            "error_count": len(errors),
            "thresholds": {"max_p95_ms": max_p95_ms, "max_error_rate": 0.0},
        }
        result["passed"] = (
            len(outcomes) == request_count
            and created_count == request_count
            and read_back_count == request_count
            and unique_order_ids == request_count
            and persisted_orders == request_count
            and persisted_events == request_count
            and pending_events == request_count
            and not errors
            and result["latency_ms"]["p95"] <= max_p95_ms
        )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-p95-ms", type=float, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.requests <= 500:
        parser.error("--requests must be between 1 and 500")
    if not 1 <= args.concurrency <= min(32, args.requests):
        parser.error("--concurrency must be between 1 and min(32, requests)")
    if args.max_p95_ms <= 0:
        parser.error("--max-p95-ms must be positive")

    result = run_test(args.requests, args.concurrency, args.max_p95_ms)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    print(output, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(output)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
