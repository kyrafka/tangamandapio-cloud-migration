"""Unit tests for safe failure behavior in the live Azure smoke harness."""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import run_live_azure_erp_smoke as smoke


class AzureCliTimeoutTests(unittest.TestCase):
    @patch.object(smoke.shutil, "which", side_effect=[None, "az"])
    @patch.object(smoke.subprocess, "run")
    def test_cli_timeout_is_bounded_and_reported_without_secrets(
        self, run_mock, _which_mock
    ) -> None:
        run_mock.side_effect = subprocess.TimeoutExpired(
            cmd=["az", "functionapp", "show"],
            timeout=smoke.AZURE_CLI_TIMEOUT_SECONDS,
        )

        with self.assertRaisesRegex(smoke.SmokeFailure, "timed out.*no event was sent"):
            smoke.azure_cli("functionapp", "show", "--name", "demo")

        self.assertEqual(
            run_mock.call_args.kwargs["timeout"], smoke.AZURE_CLI_TIMEOUT_SECONDS
        )

    @patch.object(smoke.shutil, "which", side_effect=[None, "az"])
    @patch.object(smoke.subprocess, "run")
    def test_successful_cli_output_is_returned(self, run_mock, _which_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["az", "account", "show"], returncode=0, stdout="{\"state\":\"Enabled\"}\n", stderr=""
        )

        result = smoke.azure_cli("account", "show")

        self.assertEqual(result, '{"state":"Enabled"}')
        self.assertEqual(
            run_mock.call_args.kwargs["timeout"], smoke.AZURE_CLI_TIMEOUT_SECONDS
        )


class AzureEventPollingTests(unittest.TestCase):
    @patch.object(smoke, "urlopen")
    def test_gateway_and_server_errors_are_classified_as_transient(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = HTTPError(
            "https://azure.example.test", 503, "temporarily unavailable", {}, None
        )

        with self.assertRaisesRegex(smoke.AzureTransientReadError, "HTTP 503"):
            smoke.azure_json("https://azure.example.test/event", "not-printed")

    @patch.object(smoke, "urlopen")
    def test_authorization_errors_fail_immediately(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = HTTPError(
            "https://azure.example.test", 401, "unauthorized", {}, None
        )

        with self.assertRaisesRegex(smoke.SmokeFailure, "HTTP 401") as raised:
            smoke.azure_json("https://azure.example.test/event", "not-printed")

        self.assertNotIn("not-printed", str(raised.exception))

    @patch.object(smoke.time, "sleep")
    @patch.object(smoke, "azure_json", side_effect=[
        smoke.AzureTransientReadError("temporary network failure"),
        {"status": "demo_fulfillment_completed"},
    ])
    def test_event_poll_retries_transient_reads_without_resending_event(
        self, azure_json_mock, _sleep_mock
    ) -> None:
        result = smoke.wait_for_result("https://azure.example.test", "key", "evt-test")

        self.assertEqual(result["status"], "demo_fulfillment_completed")
        self.assertEqual(azure_json_mock.call_count, 2)

    @patch.object(smoke.time, "sleep")
    @patch.object(smoke, "azure_json", side_effect=smoke.SmokeFailure("unauthorized"))
    def test_event_poll_does_not_retry_permanent_errors(
        self, azure_json_mock, _sleep_mock
    ) -> None:
        with self.assertRaisesRegex(smoke.SmokeFailure, "unauthorized"):
            smoke.wait_for_result("https://azure.example.test", "key", "evt-test")

        self.assertEqual(azure_json_mock.call_count, 1)


class AzureIngressGuardTests(unittest.TestCase):
    @patch.object(smoke, "urlopen")
    def test_http_error_status_is_checked_without_reading_body(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = HTTPError(
            "https://azure.example.test", 401, "unauthorized", {}, None
        )

        smoke.require_http_status(
            "https://azure.example.test/events", {"event_id": "probe-event"}, 401
        )

        request = urlopen_mock.call_args.args[0]
        self.assertNotIn("x-functions-key", request.headers)

    @patch.object(smoke, "urlopen")
    def test_mismatched_status_fails_without_echoing_function_key(self, urlopen_mock) -> None:
        urlopen_mock.return_value.__enter__.return_value.status = 202

        with self.assertRaisesRegex(smoke.SmokeFailure, "returned HTTP 202; expected 400") as raised:
            smoke.require_http_status(
                "https://azure.example.test/events",
                {"event_id": "probe-event"},
                400,
                "sensitive-function-key",
            )

        self.assertNotIn("sensitive-function-key", str(raised.exception))

    @patch.object(smoke, "azure_json", return_value={"status": "pending"})
    @patch.object(smoke, "require_http_status")
    def test_live_ingress_guards_reject_and_do_not_persist_probe(
        self, require_http_status_mock, azure_json_mock
    ) -> None:
        smoke.verify_ingress_guards("https://azure.example.test", "secret-key")

        self.assertEqual(require_http_status_mock.call_count, 2)
        self.assertEqual(require_http_status_mock.call_args_list[0].args[2], 401)
        self.assertEqual(require_http_status_mock.call_args_list[1].args[2], 400)
        azure_json_mock.assert_called_once()

    @patch.object(smoke, "azure_json", return_value={"status": "demo_fulfillment_completed"})
    @patch.object(smoke, "require_http_status")
    def test_ingress_guard_fails_if_rejected_probe_was_persisted(
        self, _require_http_status_mock, _azure_json_mock
    ) -> None:
        with self.assertRaisesRegex(smoke.SmokeFailure, "unexpectedly created an event"):
            smoke.verify_ingress_guards("https://azure.example.test", "secret-key")


class AzureSaleCompensationSafetyTests(unittest.TestCase):
    @patch.object(smoke, "current_demo_stock", return_value=8)
    @patch.object(smoke, "azure_json")
    def test_pending_sale_is_not_compensated(self, azure_json_mock, stock_mock) -> None:
        azure_json_mock.return_value = {"status": "pending"}

        with self.assertRaisesRegex(smoke.SmokeFailure, "still pending; no compensation was sent"):
            smoke.sale_mutation_confirmed("https://azure.example.test", "key", "evt-sale", 8)

        stock_mock.assert_not_called()

    @patch.object(smoke, "current_demo_stock", return_value=7)
    @patch.object(smoke, "azure_json", return_value={"status": "demo_fulfillment_completed"})
    def test_one_unit_deduction_is_confirmed_before_compensation(self, _event_mock, _stock_mock) -> None:
        self.assertTrue(
            smoke.sale_mutation_confirmed("https://azure.example.test", "key", "evt-sale", 8)
        )

    @patch.object(smoke, "current_demo_stock", return_value=8)
    @patch.object(smoke, "azure_json", return_value={"status": "failed"})
    def test_unchanged_baseline_needs_no_compensation(self, _event_mock, _stock_mock) -> None:
        self.assertFalse(
            smoke.sale_mutation_confirmed("https://azure.example.test", "key", "evt-sale", 8)
        )

    @patch.object(smoke, "current_demo_stock", return_value=5)
    @patch.object(smoke, "azure_json", return_value={"status": "failed"})
    def test_unexpected_stock_level_is_not_compensated_by_guess(self, _event_mock, _stock_mock) -> None:
        with self.assertRaisesRegex(smoke.SmokeFailure, "unexpected level; no compensation was sent"):
            smoke.sale_mutation_confirmed("https://azure.example.test", "key", "evt-sale", 8)


class PoisonQueueMetadataTests(unittest.TestCase):
    @patch.object(smoke, "azure_json")
    def test_empty_queue_metadata_is_accepted_without_exposing_payloads(self, azure_json_mock) -> None:
        azure_json_mock.return_value = {
            "status": "ok",
            "approximate_message_count": 0,
            "payloads_exposed": False,
        }

        smoke.require_empty_poison_queue("https://azure.example.test", "key", "before")

        azure_json_mock.assert_called_once_with(
            "https://azure.example.test/api/wms/poison-queue", "key"
        )

    @patch.object(smoke, "azure_json", return_value={
        "status": "ok", "approximate_message_count": 2, "payloads_exposed": False
    })
    def test_nonempty_queue_stops_without_reading_messages(self, _azure_json_mock) -> None:
        with self.assertRaisesRegex(smoke.SmokeFailure, "no messages were read or changed"):
            smoke.require_empty_poison_queue("https://azure.example.test", "key", "before")

    @patch.object(smoke, "azure_json", return_value={
        "status": "unavailable", "payloads_exposed": False
    })
    def test_unavailable_metadata_stops_before_event_mutation(self, _azure_json_mock) -> None:
        with self.assertRaisesRegex(smoke.SmokeFailure, "metadata is unavailable.*no messages were read"):
            smoke.require_empty_poison_queue("https://azure.example.test", "key", "before")


if __name__ == "__main__":
    unittest.main()
