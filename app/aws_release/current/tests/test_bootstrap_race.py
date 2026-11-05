import os
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch


_bootstrap_import_sandbox = tempfile.TemporaryDirectory(
    prefix="tangamandapio-bootstrap-race-import-"
)
_import_environment = {
    "DATABASE_URL": "",
    "DATABASE_PATH": str(Path(_bootstrap_import_sandbox.name) / "bootstrap.sqlite"),
    "APP_SESSION_SECRET": "test-only-bootstrap-race-secret",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "DB_SECRET_ARN": "",
    "VOICE_RECORDINGS_BUCKET": "",
    "VOICE_RECORDINGS_ENABLED": "false",
    "AUTO_DISPATCH_EVENTS": "false",
    "OUTBOX_RETRY_INTERVAL": "0",
}
with patch.dict(os.environ, _import_environment):
    import app as portal


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class ConcurrentBootstrapConnection:
    def __init__(self):
        self.company_insert = ""
        self.company_lookup_count = 0
        self.commit_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=()):
        normalized = " ".join(statement.split())
        if normalized.startswith("INSERT INTO companies"):
            self.company_insert = normalized
            return Cursor(row=None)  # Another app instance won the unique-key race.
        if normalized == "SELECT id FROM companies WHERE slug = ?":
            self.company_lookup_count += 1
            return Cursor(row=None if self.company_lookup_count == 1 else {"id": 41})
        if normalized.startswith("SELECT id, role FROM portal_users"):
            return Cursor(rows=[])
        raise AssertionError(f"Unexpected SQL during bootstrap: {normalized}")

    def commit(self):
        self.commit_count += 1


class BootstrapRaceTests(unittest.TestCase):
    def test_company_seed_recovers_from_concurrent_unique_key_conflict(self):
        connection = ConcurrentBootstrapConnection()
        app = SimpleNamespace(config={"BOOTSTRAP_ADMIN_PASSWORD": ""})

        with patch.object(portal, "connect", return_value=connection):
            portal.ensure_portal_bootstrap(app, "unused-test-database")

        self.assertIn("ON CONFLICT (slug) DO NOTHING", connection.company_insert)
        self.assertIn("RETURNING id", connection.company_insert)
        self.assertEqual(connection.company_lookup_count, 2)
        self.assertEqual(connection.commit_count, 1)


if __name__ == "__main__":
    unittest.main()
