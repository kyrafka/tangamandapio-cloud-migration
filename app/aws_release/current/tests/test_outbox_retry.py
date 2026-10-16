import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

_test_root = tempfile.TemporaryDirectory(prefix="tangamandapio-outbox-retry-tests-")
os.environ.setdefault("DATABASE_PATH", str(Path(_test_root.name) / "module-import.db"))
os.environ.setdefault("APP_SESSION_SECRET", "outbox-retry-test-secret-not-for-production")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin@outbox-retry.test")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "Outbox-Retry-Test-Only-2026!")

import app as portal


class OutboxRetryTests(unittest.TestCase):
    def setUp(self):
        self._database = tempfile.TemporaryDirectory(prefix="tangamandapio-outbox-db-")
        self.database = str(Path(self._database.name) / "portal.sqlite")
        self.application = portal.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": self.database,
                "APP_SESSION_SECRET": "outbox-retry-test-secret-not-for-production",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@outbox-retry.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Outbox-Retry-Test-Only-2026!",
                "AZURE_FULFILLMENT_URL": "https://wms.example.test/api/fulfillment/events",
                "AZURE_FUNCTION_KEY": "",
                "OUTBOX_RETRY_INTERVAL": 60,
                "OUTBOX_RETRY_MAX_ATTEMPTS": 10,
            }
        )

    def tearDown(self):
        self._database.cleanup()

    def add_event(self, event_id, *, status="pending", attempts=0):
        with portal.connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO outbox_events
                    (event_id, order_id, payload, status, attempts, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, 1, "{}", status, attempts, "2026-10-16T00:00:00+00:00"),
            )
            connection.commit()

    def event_state(self, event_id):
        with portal.connect(self.database) as connection:
            row = connection.execute(
                "SELECT status, attempts, last_error, delivered_at "
                "FROM outbox_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return dict(row)

    def test_retry_sweep_waits_for_backoff_then_delivers_after_503(self):
        event_id = "evt-retry-recovery-test"
        self.add_event(event_id)
        deadlines = {}
        accepted = MagicMock()
        accepted.__enter__.return_value = accepted
        accepted.read.return_value = b'{"status":"queued"}'
        upstream = "https://wms.example.test/api/fulfillment/events"

        with patch.object(
            portal,
            "urlopen",
            side_effect=[HTTPError(upstream, 503, "unavailable", {}, None), accepted],
        ) as urlopen_mock:
            first = portal.retry_pending_outbox(
                self.application, self.database, deadlines, now=100.0
            )
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["status"], "pending")
            self.assertEqual(first[0]["reason"], "HTTPError")
            self.assertEqual(self.event_state(event_id)["status"], "failed")
            self.assertEqual(self.event_state(event_id)["attempts"], 1)
            self.assertEqual(deadlines[event_id], 220.0)

            not_due = portal.retry_pending_outbox(
                self.application, self.database, deadlines, now=219.0
            )
            self.assertEqual(not_due, [])
            self.assertEqual(urlopen_mock.call_count, 1)

            recovered = portal.retry_pending_outbox(
                self.application, self.database, deadlines, now=220.0
            )

        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["status"], "delivered")
        self.assertEqual(self.event_state(event_id)["status"], "delivered")
        self.assertEqual(self.event_state(event_id)["attempts"], 2)
        self.assertIsNone(self.event_state(event_id)["last_error"])
        self.assertIsNotNone(self.event_state(event_id)["delivered_at"])
        self.assertNotIn(event_id, deadlines)
        self.assertEqual(urlopen_mock.call_count, 2)

    def test_retry_stops_at_max_attempts(self):
        event_id = "evt-retry-max-attempts-test"
        self.add_event(event_id, status="failed", attempts=3)
        self.application.config["OUTBOX_RETRY_MAX_ATTEMPTS"] = 3

        with patch.object(portal, "dispatch_outbox_event") as dispatch_mock:
            result = portal.retry_pending_outbox(
                self.application, self.database, {}, now=500.0
            )

        self.assertEqual(result, [])
        dispatch_mock.assert_not_called()
        self.assertEqual(self.event_state(event_id)["attempts"], 3)

    def test_retry_is_disabled_without_interval_or_service_url(self):
        event_id = "evt-retry-disabled-test"
        self.add_event(event_id)

        with patch.object(portal, "dispatch_outbox_event") as dispatch_mock:
            self.application.config["OUTBOX_RETRY_INTERVAL"] = 0
            self.assertEqual(
                portal.retry_pending_outbox(self.application, self.database, {}, now=1.0),
                [],
            )
            self.application.config["OUTBOX_RETRY_INTERVAL"] = 60
            self.application.config["AZURE_FULFILLMENT_URL"] = ""
            self.assertEqual(
                portal.retry_pending_outbox(self.application, self.database, {}, now=1.0),
                [],
            )

        dispatch_mock.assert_not_called()

    def test_backoff_is_capped_at_one_hour(self):
        self.assertEqual(portal.outbox_backoff_seconds(60, 20), 3600)


if __name__ == "__main__":
    unittest.main()
