import hashlib
import importlib.util
import inspect
import json
import os
import sys
import unittest
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import MagicMock, patch

import azure.functions as func


FUNCTION_DIR = Path(__file__).resolve().parents[1] / "azure_function"
sys.path.insert(0, str(FUNCTION_DIR))
with patch.dict(os.environ, {"WMS_QUEUE_NAME": "wms-fulfillment"}):
    spec = importlib.util.spec_from_file_location(
        "tangamandapio_function_app", FUNCTION_DIR / "function_app.py"
    )
    function_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(function_app)


def load_erp_module(module_name, source_path):
    erp_spec = importlib.util.spec_from_file_location(module_name, source_path)
    erp_module = importlib.util.module_from_spec(erp_spec)
    erp_spec.loader.exec_module(erp_module)
    return erp_module


ERP_SOURCE_DIR = FUNCTION_DIR.parent / "src"
ERP_RELEASE_DIR = FUNCTION_DIR.parent / "aws_release" / "current"
source_erp = load_erp_module("tangama_source_erp", ERP_SOURCE_DIR / "erp_service.py")
release_erp = load_erp_module("tangama_release_erp", ERP_RELEASE_DIR / "erp_service.py")


def make_event():
    event = {
        "event_id": "evt-test-20261008-01",
        "event_type": "order.created",
        "schema_version": "1.0",
        "recorded_at": "2026-10-08T12:00:00+00:00",
        "payload": {
            "event_id": "evt-test-20261008-01",
            "event_type": "order.created",
            "order_id": 42,
        },
    }
    event["sha256"] = hashlib.sha256(
        json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return event


class FulfillmentQueueTestCase(unittest.TestCase):
    def test_http_trigger_parameters_match_the_python_bindings(self):
        self.assertEqual(
            list(inspect.signature(function_app.health._function._func).parameters),
            ["req"],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    function_app.receive_fulfillment_event._function._func
                ).parameters
            ),
            ["req"],
        )
        self.assertEqual(
            list(
                inspect.signature(
                    function_app.fulfillment_status._function._func
                ).parameters
            ),
            ["req"],
        )
        self.assertEqual(
            list(inspect.signature(function_app.demo_inventory._function._func).parameters),
            ["req"],
        )
        self.assertEqual(
            list(inspect.signature(function_app.update_demo_catalog._function._func).parameters),
            ["req"],
        )
        self.assertEqual(
            list(inspect.signature(function_app.poison_queue_status._function._func).parameters),
            ["req"],
        )

    def test_host_config_sends_failed_messages_to_poison_after_five_attempts(self):
        config = json.loads((FUNCTION_DIR / "host.json").read_text(encoding="utf-8"))
        queue_config = config["extensions"]["queues"]
        self.assertEqual(queue_config["maxDequeueCount"], 5)
        self.assertEqual(queue_config["visibilityTimeout"], "00:01:00")

    def test_anonymous_health_supports_get_and_head_without_head_body(self):
        trigger = next(
            binding
            for binding in function_app.health._function.get_bindings()
            if binding.type == "httpTrigger"
        )
        self.assertEqual(
            [method.value for method in trigger.methods],
            ["GET", "HEAD"],
        )
        for method in ("GET", "HEAD"):
            with self.subTest(method=method):
                request = func.HttpRequest(
                    method=method,
                    url="https://example.test/api/health",
                    headers={},
                    params={},
                    body=b"",
                )
                response = function_app.health._function(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "application/json")
                if method == "HEAD":
                    self.assertEqual(response.get_body(), b"")
                else:
                    self.assertEqual(
                        json.loads(response.get_body()),
                        {"status": "ok", "service": "tangamandapio-wms"},
                    )

    def test_queue_message_validates_hash_and_writes_inventory_result(self):
        event = make_event()
        message = func.QueueMessage(
            body=json.dumps(
                {"event_id": event["event_id"], "sha256": event["sha256"]}
            ).encode("utf-8")
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_read_event_blob", return_value=event) as read_blob,
            patch.object(
                function_app,
                "_process_inventory_event",
                return_value={
                    "event_id": event["event_id"],
                    "status": "awaiting_items",
                    "mode": "demo-inventory-ledger",
                    "source_sha256": event["sha256"],
                    "note": "Evento antiguo sin líneas.",
                    "items": [],
                },
            ),
            patch.object(function_app, "_write_fulfillment_result") as write_result,
        ):
            function_app.process_fulfillment_message._function(message)

        read_blob.assert_called_once_with(event["event_id"], "managed-token")
        result = write_result.call_args.args[0]
        self.assertEqual(result["event_id"], event["event_id"])
        self.assertEqual(result["status"], "awaiting_items")
        self.assertEqual(result["mode"], "demo-inventory-ledger")
        self.assertEqual(result["source_sha256"], event["sha256"])
        self.assertIn("sin líneas", result["note"])

    def test_queue_message_with_tampered_checksum_is_rejected(self):
        event = make_event()
        event["payload"] = {"order_id": 999}
        message = func.QueueMessage(
            body=json.dumps(
                {"event_id": event["event_id"], "sha256": "0" * 64}
            ).encode("utf-8")
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_read_event_blob", return_value=event),
            patch.object(function_app, "_write_fulfillment_result") as write_result,
        ):
            with self.assertRaisesRegex(ValueError, "checksum"):
                function_app.process_fulfillment_message._function(message)
        write_result.assert_not_called()

    def test_duplicate_delivery_is_requeued_with_original_accepted_hash(self):
        event = make_event()
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/fulfillment/events",
            headers={},
            params={},
            body=json.dumps(
                {"event_id": event["event_id"], "event_type": "order.created", "order_id": 42}
            ).encode("utf-8"),
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_read_json_blob", return_value=(function_app._inventory_seed(), '"etag"')),
            patch.object(function_app, "_write_event_blob", return_value=False),
            patch.object(function_app, "_read_event_blob", return_value=event),
            patch.object(function_app, "_enqueue_event") as enqueue,
        ):
            response = function_app.receive_fulfillment_event._function(req)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(json.loads(response.get_body())["status"], "queued_duplicate")
        enqueue.assert_called_once_with(event["event_id"], event["sha256"], "managed-token")

    def test_duplicate_event_id_with_different_payload_returns_conflict(self):
        event = make_event()
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/fulfillment/events",
            headers={},
            params={},
            body=json.dumps(
                {"event_id": event["event_id"], "event_type": "order.created", "order_id": 999}
            ).encode("utf-8"),
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_read_json_blob", return_value=(function_app._inventory_seed(), '"etag"')),
            patch.object(function_app, "_write_event_blob", return_value=False),
            patch.object(function_app, "_read_event_blob", return_value=event),
            patch.object(function_app, "_enqueue_event") as enqueue,
        ):
            response = function_app.receive_fulfillment_event._function(req)

        self.assertEqual(response.status_code, 409)
        enqueue.assert_not_called()

    def test_existing_demo_result_is_not_overwritten_on_queue_redelivery(self):
        from urllib.error import HTTPError
        request_box = {}

        def conflict(request, timeout):
            request_box["request"] = request
            raise HTTPError(request.full_url, 412, "already exists", {}, None)

        with (
            patch.dict(
                os.environ,
                {"AZURE_BLOB_ACCOUNT_URL": "https://storage.test", "EVIDENCE_CONTAINER": "events"},
            ),
            patch.object(function_app, "urlopen", side_effect=conflict),
        ):
            created = function_app._write_fulfillment_result(
                {"event_id": "evt-test-20261008-01", "status": "simulated_completed"},
                "managed-token",
            )

        self.assertFalse(created)
        self.assertEqual(request_box["request"].get_header("If-none-match"), "*")

    def test_status_endpoint_reports_pending_and_completed_result(self):
        req = func.HttpRequest(
            method="GET",
            url="http://localhost/api/fulfillment/events/evt-test-20261008-01",
            headers={},
            params={},
            route_params={"event_id": "evt-test-20261008-01"},
            body=b"",
        )
        result = {"event_id": "evt-test-20261008-01", "status": "simulated_completed"}
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_read_fulfillment_result", return_value=result),
        ):
            response = function_app.fulfillment_status._function(
                req
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), result)

    def test_status_endpoint_rejects_unsafe_event_id(self):
        req = func.HttpRequest(
            method="GET",
            url="http://localhost/api/fulfillment/events/../secret",
            headers={},
            params={},
            route_params={"event_id": "../secret"},
            body=b"",
        )
        response = function_app.fulfillment_status._function(req)
        self.assertEqual(response.status_code, 400)

    def test_poison_queue_status_returns_only_approximate_count(self):
        req = func.HttpRequest(
            method="GET",
            url="http://localhost/api/wms/poison-queue",
            headers={},
            params={},
            body=b"",
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_read_queue_approximate_message_count", return_value=2) as read_count,
        ):
            response = function_app.poison_queue_status._function(req)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.get_body())
        self.assertEqual(body["approximate_message_count"], 2)
        self.assertEqual(body["queue"], "fulfillment-events-poison")
        self.assertFalse(body["payloads_exposed"])
        read_count.assert_called_once_with("fulfillment-events-poison", "managed-token")

    def test_poison_queue_status_sanitizes_access_denied(self):
        req = func.HttpRequest(
            method="GET",
            url="http://localhost/api/wms/poison-queue",
            headers={},
            params={},
            body=b"",
        )
        denied = HTTPError("https://storage.test/queue", 403, "denied", {}, None)
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_read_queue_approximate_message_count", side_effect=denied),
        ):
            response = function_app.poison_queue_status._function(req)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            json.loads(response.get_body()),
            {
                "status": "unavailable",
                "queue": "fulfillment-events-poison",
                "reason": "access_denied",
            },
        )

    def test_queue_metadata_request_uses_managed_identity_and_returns_count(self):
        response = MagicMock()
        response.headers = {"x-ms-approximate-messages-count": "7"}
        response.__enter__.return_value = response
        with (
            patch.dict(os.environ, {"AZURE_QUEUE_ACCOUNT_URL": "https://storage.test/"}),
            patch.object(function_app, "urlopen", return_value=response) as open_url,
        ):
            count = function_app._read_queue_approximate_message_count(
                "fulfillment-events-poison", "managed-token"
            )
        self.assertEqual(count, 7)
        request = open_url.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://storage.test/fulfillment-events-poison?comp=metadata",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer managed-token")
        self.assertEqual(request.get_header("X-ms-version"), "2022-11-02")

    def test_demo_inventory_transaction_deducts_stock_once_for_duplicate_delivery(self):
        event = {
            "event_id": "evt-demo-stock-20261008",
            "sha256": "a" * 64,
            "payload": {"order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]}},
        }
        state = function_app._inventory_seed()
        updated, first = function_app._fulfill_against_inventory(event, state)
        self.assertEqual(first["status"], "demo_fulfillment_completed")
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 23)
        updated_again, duplicate = function_app._fulfill_against_inventory(event, updated)
        self.assertEqual(duplicate, first)
        self.assertEqual(updated_again["items"]["SKU-ARROZ-001"]["on_hand"], 23)

    def test_purchase_receipt_increases_demo_stock_once_for_duplicate_delivery(self):
        event = {
            "event_id": "evt-demo-receipt-20261008",
            "sha256": "b" * 64,
            "payload": {
                "event_type": "purchase.received",
                "purchase_order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 3}]},
            },
        }
        state = function_app._inventory_seed()
        updated, first = function_app._fulfill_against_inventory(event, state)
        self.assertEqual(first["status"], "demo_restock_completed")
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 28)
        updated_again, duplicate = function_app._fulfill_against_inventory(event, updated)
        self.assertEqual(duplicate, first)
        self.assertEqual(updated_again["items"]["SKU-ARROZ-001"]["on_hand"], 28)

    def test_worker_rejects_unknown_event_type_without_changing_inventory(self):
        event = {
            "event_id": "evt-unknown-type-20261013",
            "event_type": "inventory.adjusted",
            "sha256": "e" * 64,
            "payload": {
                "event_type": "inventory.adjusted",
                "order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]},
            },
        }
        state = function_app._inventory_seed()
        with (
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_acquire_inventory_lease", return_value="lease-id"),
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
            patch.object(function_app, "_write_json_blob", return_value=True) as write,
            patch.object(function_app, "_release_inventory_lease"),
        ):
            result = function_app._process_inventory_event(event, "managed-token")

        self.assertEqual(result["status"], "rejected_invalid_event")
        self.assertEqual(state["items"]["SKU-ARROZ-001"]["on_hand"], 25)
        self.assertEqual(
            write.call_args.args[1]["processed_events"][event["event_id"]]["status"],
            "rejected_invalid_event",
        )

    def test_worker_rejects_conflicting_envelope_and_payload_types(self):
        event = {
            "event_id": "evt-type-mismatch-20261013",
            "event_type": "order.created",
            "sha256": "f" * 64,
            "payload": {
                "event_type": "purchase.received",
                "purchase_order": {
                    "items": [{"sku": "SKU-ARROZ-001", "quantity": 2}]
                },
            },
        }
        updated, result = function_app._fulfill_against_inventory(
            event, function_app._inventory_seed()
        )

        self.assertEqual(result["status"], "rejected_invalid_event")
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 25)
        self.assertIn("no coincide", result["note"])

    def test_http_trigger_accepts_purchase_receipt_event(self):
        payload = {
            "event_id": "evt-http-receipt-20261008",
            "event_type": "purchase.received",
            "purchase_order": {"items": [{"sku": "SKU-AZUCAR-001", "quantity": 2}]},
        }
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/fulfillment/events",
            headers={},
            params={},
            body=json.dumps(payload).encode("utf-8"),
        )
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_read_json_blob", return_value=(function_app._inventory_seed(), '"etag"')),
            patch.object(function_app, "_write_event_blob", return_value=True) as write_blob,
            patch.object(function_app, "_enqueue_event") as enqueue,
        ):
            response = function_app.receive_fulfillment_event._function(req)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(json.loads(response.get_body())["status"], "queued")
        accepted = write_blob.call_args.args[0]
        self.assertEqual(accepted["event_type"], "purchase.received")
        self.assertEqual(accepted["payload"]["purchase_order"]["items"][0]["quantity"], 2)
        enqueue.assert_called_once()

    def test_blob_lease_transaction_persists_once_and_releases_lease(self):
        event = {
            "event_id": "evt-demo-lease-20261008",
            "sha256": "d" * 64,
            "payload": {"order": {"items": [{"sku": "SKU-ACEITE-001", "quantity": 1}]}},
        }
        state = function_app._inventory_seed()
        with (
            patch.object(function_app, "_ensure_inventory_blob") as ensure,
            patch.object(function_app, "_acquire_inventory_lease", return_value="lease-id") as acquire,
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
            patch.object(function_app, "_write_json_blob", return_value=True) as write,
            patch.object(function_app, "_release_inventory_lease") as release,
        ):
            first = function_app._process_inventory_event(event, "managed-token")
            duplicate = function_app._process_inventory_event(event, "managed-token")
        self.assertEqual(first["status"], "demo_fulfillment_completed")
        self.assertEqual(duplicate, first)
        self.assertEqual(state["items"]["SKU-ACEITE-001"]["on_hand"], 17)
        self.assertEqual(write.call_count, 1)
        self.assertEqual(acquire.call_count, 2)
        self.assertEqual(release.call_count, 2)
        ensure.assert_called_with("managed-token")
        self.assertEqual(write.call_args.kwargs["if_match"], '"etag"')
        self.assertEqual(write.call_args.kwargs["lease_id"], "lease-id")

    def test_demo_inventory_rejection_is_atomic_when_stock_is_insufficient(self):
        event = {
            "event_id": "evt-demo-stock-rejected",
            "sha256": "b" * 64,
            "payload": {
                "order": {
                    "items": [
                        {"sku": "SKU-ARROZ-001", "quantity": 1},
                        {"sku": "SKU-AZUCAR-001", "quantity": 500},
                    ]
                }
            },
        }
        state = function_app._inventory_seed()
        updated, result = function_app._fulfill_against_inventory(event, state)
        self.assertEqual(result["status"], "rejected_insufficient_stock")
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 25)
        self.assertEqual(updated["items"]["SKU-AZUCAR-001"]["on_hand"], 40)

    def test_legacy_event_without_sku_lines_does_not_claim_fulfillment(self):
        event = {
            "event_id": "evt-legacy-without-items",
            "sha256": "c" * 64,
            "payload": {"order": {"customer": "Anterior", "total": 10}},
        }
        updated, result = function_app._fulfill_against_inventory(event, function_app._inventory_seed())
        self.assertEqual(result["status"], "awaiting_items")
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 25)

    def test_ingest_rejects_malformed_sku_quantity_before_blob_write(self):
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/fulfillment/events",
            headers={},
            params={},
            body=json.dumps(
                {
                    "event_id": "evt-invalid-demo-01",
                    "event_type": "order.created",
                    "order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": True}]},
                }
            ).encode("utf-8"),
        )
        with patch.object(function_app, "_managed_identity_token") as token:
            response = function_app.receive_fulfillment_event._function(req)
        self.assertEqual(response.status_code, 400)
        token.assert_not_called()

    def test_ingest_rejects_unknown_event_source_before_blob_write(self):
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/fulfillment/events",
            headers={},
            params={},
            body=json.dumps(
                {
                    "event_id": "evt-untrusted-source",
                    "event_type": "order.created",
                    "source": "unknown-external-system",
                    "order": {"items": [{"sku": "SKU-ARROZ-001", "quantity": 1}]},
                }
            ).encode("utf-8"),
        )
        with patch.object(function_app, "_managed_identity_token") as token:
            response = function_app.receive_fulfillment_event._function(req)
        self.assertEqual(response.status_code, 400)
        token.assert_not_called()

    def test_inventory_route_returns_persisted_demo_catalog(self):
        req = func.HttpRequest(method="GET", url="http://localhost/api/wms/inventory", headers={}, params={}, body=b"")
        state = function_app._inventory_seed()
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob") as ensure,
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
        ):
            response = function_app.demo_inventory._function(req)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.get_body())
        self.assertFalse(payload["is_real_erp"])
        self.assertEqual(payload["catalog_version"], function_app.DEMO_CATALOG_VERSION)
        self.assertEqual(len(payload["items"]), len(function_app.DEMO_PRODUCTS))
        ensure.assert_called_once_with("managed-token")

    def test_catalog_import_preserves_existing_stock_and_seeds_new_synthetic_skus(self):
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/wms/catalog",
            headers={},
            params={},
            body=json.dumps({"products": [
                {"sku": "SKU-ARROZ-001", "name": "Arroz actualizado", "unit": "saco", "unit_price": 45.5, "initial_stock": 999},
                {"sku": "SKU-TEST-001", "name": "Producto sintético", "unit": "caja", "unit_price": 12.25, "initial_stock": 7},
            ]}).encode("utf-8"),
        )
        state = function_app._inventory_seed()
        state["items"]["SKU-ARROZ-001"]["on_hand"] = 19
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_acquire_inventory_lease", return_value="lease-id"),
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
            patch.object(function_app, "_write_json_blob", return_value=True) as write_blob,
            patch.object(function_app, "_release_inventory_lease") as release_lease,
        ):
            response = function_app.update_demo_catalog._function(req)

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.get_body())
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["updated"], 1)
        self.assertTrue(result["stock_preserved"])
        updated = write_blob.call_args.args[1]
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["on_hand"], 19)
        self.assertEqual(updated["items"]["SKU-ARROZ-001"]["unit_price"], 45.5)
        self.assertEqual(updated["items"]["SKU-TEST-001"]["on_hand"], 7)
        self.assertEqual(updated["items"]["SKU-TEST-001"]["data_origin"], "synthetic")
        self.assertEqual(write_blob.call_args.kwargs["if_match"], '"etag"')
        self.assertEqual(write_blob.call_args.kwargs["lease_id"], "lease-id")
        release_lease.assert_called_once_with("managed-token", "lease-id")

    def test_catalog_import_accepts_maximum_500_sku_synthetic_batch(self):
        products = [
            {
                "sku": f"SKU-BULK-{index:04d}",
                "name": f"Producto sintético {index:04d}",
                "unit": "caja",
                "unit_price": 10.5,
                "initial_stock": index,
            }
            for index in range(1, 501)
        ]
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/wms/catalog",
            headers={},
            params={},
            body=json.dumps({"products": products}).encode("utf-8"),
        )
        state = function_app._inventory_seed()
        with (
            patch.object(function_app, "_managed_identity_token", return_value="managed-token"),
            patch.object(function_app, "_ensure_inventory_blob"),
            patch.object(function_app, "_acquire_inventory_lease", return_value="lease-id"),
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
            patch.object(function_app, "_write_json_blob", return_value=True) as write_blob,
            patch.object(function_app, "_release_inventory_lease") as release_lease,
        ):
            response = function_app.update_demo_catalog._function(req)

        self.assertEqual(response.status_code, 200, response.get_body())
        result = json.loads(response.get_body())
        self.assertEqual((result["created"], result["updated"]), (500, 0))
        updated_state = write_blob.call_args.args[1]
        self.assertEqual(len(updated_state["items"]), len(function_app.DEMO_PRODUCTS) + 500)
        self.assertEqual(updated_state["items"]["SKU-BULK-0500"]["on_hand"], 500)
        self.assertEqual(write_blob.call_args.kwargs["if_match"], '"etag"')
        self.assertEqual(write_blob.call_args.kwargs["lease_id"], "lease-id")
        release_lease.assert_called_once_with("managed-token", "lease-id")

    def test_catalog_import_rejects_501_skus_before_cloud_access(self):
        products = [
            {
                "sku": f"SKU-LIMIT-{index:04d}",
                "name": f"Producto sintético {index:04d}",
                "unit": "caja",
                "unit_price": 10.5,
                "initial_stock": 0,
            }
            for index in range(1, 502)
        ]
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/wms/catalog",
            headers={},
            params={},
            body=json.dumps({"products": products}).encode("utf-8"),
        )
        with patch.object(function_app, "_managed_identity_token") as managed_identity:
            response = function_app.update_demo_catalog._function(req)

        self.assertEqual(response.status_code, 400)
        self.assertIn("500", response.get_body().decode("utf-8"))
        managed_identity.assert_not_called()

    def test_catalog_import_rejects_boolean_price_before_cloud_access(self):
        req = func.HttpRequest(
            method="POST",
            url="http://localhost/api/wms/catalog",
            headers={},
            params={},
            body=json.dumps({"products": [
                {"sku": "SKU-BOOL-001", "name": "Producto", "unit": "caja", "unit_price": True, "initial_stock": 2},
            ]}).encode("utf-8"),
        )
        with patch.object(function_app, "_managed_identity_token") as managed_identity:
            response = function_app.update_demo_catalog._function(req)
        self.assertEqual(response.status_code, 400)
        managed_identity.assert_not_called()

    def test_imported_sku_is_valid_for_a_subsequent_wms_transaction(self):
        state = function_app._inventory_seed()
        state["items"]["SKU-TEST-001"] = {
            "sku": "SKU-TEST-001", "name": "Producto sintético", "unit": "caja",
            "unit_price": 12.25, "initial_stock": 7, "on_hand": 7,
        }
        event = {
            "event_id": "evt-imported-sku-001",
            "event_type": "order.created",
            "payload": {"order": {"items": [{"sku": "SKU-TEST-001", "quantity": 2}]}},
        }
        updated, result = function_app._fulfill_against_inventory(event, state)
        self.assertEqual(result["status"], "demo_fulfillment_completed")
        self.assertEqual(updated["items"]["SKU-TEST-001"]["on_hand"], 5)

    def test_synthetic_catalog_matches_source_release_names_and_sale_prices(self):
        self.assertEqual(source_erp.ERP_DEMO_PRODUCTS, release_erp.ERP_DEMO_PRODUCTS)
        erp_by_sku = {product[0]: product for product in source_erp.ERP_DEMO_PRODUCTS}
        self.assertEqual(set(erp_by_sku), set(function_app.DEMO_PRODUCTS))
        for sku, product in function_app.DEMO_PRODUCTS.items():
            self.assertEqual(product["name"], erp_by_sku[sku][1])
            self.assertEqual(product["unit"], erp_by_sku[sku][2])
            self.assertEqual(product["unit_price"], erp_by_sku[sku][3])

    def test_catalog_upgrade_only_adds_missing_synthetic_skus_and_preserves_balances(self):
        old_state = function_app._inventory_seed()
        old_state.pop("catalog_version")
        old_state["items"] = {
            sku: item
            for sku, item in old_state["items"].items()
            if sku in {"SKU-ARROZ-001", "SKU-AZUCAR-001", "SKU-ACEITE-001"}
        }
        old_state["items"]["SKU-ARROZ-001"]["on_hand"] = 19
        old_state["processed_events"] = {"evt-existing-demo": {"status": "done"}}

        with (
            patch.object(
                function_app,
                "_read_json_blob",
                side_effect=[(old_state, '"etag-before"'), (old_state, '"etag-after"')],
            ),
            patch.object(function_app, "_acquire_inventory_lease", return_value="lease-id"),
            patch.object(function_app, "_write_json_blob", return_value=True) as write_blob,
            patch.object(function_app, "_release_inventory_lease") as release_lease,
        ):
            function_app._ensure_inventory_blob("managed-token")

        write_blob.assert_called_once()
        migrated = write_blob.call_args.args[1]
        self.assertEqual(set(migrated["items"]), set(function_app.DEMO_PRODUCTS))
        self.assertEqual(migrated["items"]["SKU-ARROZ-001"]["on_hand"], 19)
        self.assertEqual(migrated["items"]["SKU-CAFE-001"]["on_hand"], 12)
        self.assertEqual(migrated["processed_events"], {"evt-existing-demo": {"status": "done"}})
        self.assertEqual(migrated["catalog_version"], function_app.DEMO_CATALOG_VERSION)
        self.assertEqual(write_blob.call_args.kwargs["if_match"], '"etag-after"')
        self.assertEqual(write_blob.call_args.kwargs["lease_id"], "lease-id")
        release_lease.assert_called_once_with("managed-token", "lease-id")

    def test_current_catalog_upgrade_is_a_no_op_when_all_skus_exist(self):
        state = function_app._inventory_seed()
        with (
            patch.object(function_app, "_read_json_blob", return_value=(state, '"etag"')),
            patch.object(function_app, "_acquire_inventory_lease") as acquire,
            patch.object(function_app, "_write_json_blob") as write,
        ):
            function_app._ensure_inventory_blob("managed-token")
        acquire.assert_not_called()
        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
