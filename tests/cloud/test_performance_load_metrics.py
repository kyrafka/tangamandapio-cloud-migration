import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
