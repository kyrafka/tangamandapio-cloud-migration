import hashlib
import importlib.util
import inspect
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import azure.functions as func


FUNCTION_DIR = Path(__file__).resolve().parents[1] / "azure_function"
sys.path.insert(0, str(FUNCTION_DIR))
with patch.dict(os.environ, {"WMS_QUEUE_NAME": "wms-fulfillment"}):
    spec = importlib.util.spec_from_file_location(
        "tangamandapio_function_app", FUNCTION_DIR / "function_app.py"
    )
    function_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(function_app)


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
        self.assertEqual(len(payload["items"]), 3)
        ensure.assert_called_once_with("managed-token")


if __name__ == "__main__":
    unittest.main()
