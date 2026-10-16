import importlib.util
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


LOAD_TEST_PATH = Path(__file__).resolve().parents[1] / "performance" / "load_test.py"
SPEC = importlib.util.spec_from_file_location("tangama_load_test", LOAD_TEST_PATH)
LOAD_TEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOAD_TEST)


class LoadTestSummaryTests(unittest.TestCase):
    def test_distinguishes_http_denials_from_transport_errors(self):
        summary = LOAD_TEST.summarize_outcomes(
            [
                (10.0, 200, None),
                (11.0, 403, "HTTPError"),
                (12.0, 403, "HTTPError"),
                (13.0, 0, "URLError"),
            ]
        )

        self.assertEqual(
            summary,
            {
                "status_counts": {"200": 1, "403": 2, "network_error": 1},
                "error_types": {"HTTPError": 2, "URLError": 1},
            },
        )

    def test_empty_results_produce_empty_diagnostics(self):
        self.assertEqual(
            LOAD_TEST.summarize_outcomes([]),
            {"status_counts": {}, "error_types": {}},
        )


class DirectHTTPSOriginTests(unittest.TestCase):
    def test_direct_origin_keeps_certificate_validation_enabled(self):
        opener = LOAD_TEST.build_opener_for_direct_https(
            "https://portal.example.test/health", "203.0.113.10"
        )
        handler = next(
            item for item in opener.handlers
            if isinstance(item, LOAD_TEST._DirectHTTPSHandler)
        )
        self.assertEqual(handler.connect_host, "203.0.113.10")
        self.assertTrue(handler._context.check_hostname)
        self.assertEqual(handler._context.verify_mode, LOAD_TEST.ssl.CERT_REQUIRED)

    def test_direct_origin_rejects_http_and_embedded_credentials(self):
        for url in (
            "http://portal.example.test/health",
            "https://user:password@portal.example.test/health",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LOAD_TEST.build_opener_for_direct_https(url, "203.0.113.10")

    def test_request_uses_direct_opener_when_provided(self):
        opener = MagicMock()
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"{}"
        opener.open.return_value = response

        with patch.object(
            LOAD_TEST,
            "urlopen",
            side_effect=AssertionError("default transport must not be used"),
        ):
            _, status, error = LOAD_TEST.request_once(
                "https://portal.example.test/health", 2, opener
            )

        self.assertEqual(status, 200)
        self.assertIsNone(error)
        opener.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
