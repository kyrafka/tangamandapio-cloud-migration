import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash

APP_PATH = Path(__file__).resolve().parents[1] / "current" / "app.py"
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="portal-admin-recovery-import-")
_import_environment = {
    "DATABASE_URL": "",
    "DATABASE_PATH": str(Path(_bootstrap_dir.name) / "bootstrap.sqlite3"),
    "APP_SESSION_SECRET": "admin-recovery-test-session-secret",
    "BOOTSTRAP_ADMIN_USERNAME": "admin@recovery.test",
    "BOOTSTRAP_ADMIN_PASSWORD": "Module-Import-Password-2026!",
    "DB_SECRET_ARN": "",
    "VOICE_RECORDINGS_BUCKET": "",
    "VOICE_RECORDINGS_ENABLED": "false",
}
with patch.dict(os.environ, _import_environment):
    if str(APP_PATH.parent) not in sys.path:
        sys.path.insert(0, str(APP_PATH.parent))
    spec = importlib.util.spec_from_file_location("portal_admin_recovery", APP_PATH)
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)


class AdministratorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self._db = tempfile.TemporaryDirectory(prefix="tangamandapio-admin-recovery-")
        self.database = str(Path(self._db.name) / "portal.sqlite")
        self.application = portal.create_app(
            {
                "TESTING": True,
                "DATABASE_URL": "",
                "DATABASE_PATH": self.database,
                "APP_SESSION_SECRET": "admin-recovery-test-session-secret",
                "BOOTSTRAP_ADMIN_USERNAME": "admin@recovery.test",
                "BOOTSTRAP_ADMIN_PASSWORD": "Initial-Password-2026!",
                "RESET_BOOTSTRAP_ADMIN_PASSWORD": False,
                "BOOTSTRAP_ADMIN_PASSWORD_RESET_VERSION": "",
            }
        )

    def tearDown(self):
        self._db.cleanup()

    def admin_row(self):
        with portal.connect(self.database) as connection:
            return connection.execute(
                "SELECT id, password_hash, auth_version, must_change_password "
                "FROM portal_users WHERE username = ?",
                ("admin@recovery.test",),
            ).fetchone()

    def test_explicit_recovery_resets_once_per_secret_version(self):
        initial = self.admin_row()
        self.assertTrue(
            check_password_hash(initial["password_hash"], "Initial-Password-2026!")
        )
        self.assertFalse(initial["must_change_password"])

        self.application.config.update(
            RESET_BOOTSTRAP_ADMIN_PASSWORD=True,
            BOOTSTRAP_ADMIN_PASSWORD_RESET_VERSION="secret-version-1",
            BOOTSTRAP_ADMIN_PASSWORD="Temporary-Recovery-Password-1!",
        )
        portal.ensure_portal_bootstrap(self.application, self.database)
        recovered = self.admin_row()
        self.assertTrue(
            check_password_hash(
                recovered["password_hash"], "Temporary-Recovery-Password-1!"
            )
        )
        self.assertTrue(recovered["must_change_password"])
        self.assertEqual(recovered["auth_version"], initial["auth_version"] + 1)

        # A second ASG instance starting with the same Secrets Manager version
        # must not overwrite a password the administrator has already changed.
        self.application.config["BOOTSTRAP_ADMIN_PASSWORD"] = "Ignored-Second-Instance!"
        portal.ensure_portal_bootstrap(self.application, self.database)
        repeated = self.admin_row()
        self.assertTrue(
            check_password_hash(
                repeated["password_hash"], "Temporary-Recovery-Password-1!"
            )
        )
        self.assertEqual(repeated["auth_version"], recovered["auth_version"])

        # An explicit new secret version is a new, auditable recovery event.
        self.application.config.update(
            BOOTSTRAP_ADMIN_PASSWORD_RESET_VERSION="secret-version-2",
            BOOTSTRAP_ADMIN_PASSWORD="Temporary-Recovery-Password-2!",
        )
        portal.ensure_portal_bootstrap(self.application, self.database)
        rotated = self.admin_row()
        self.assertTrue(
            check_password_hash(
                rotated["password_hash"], "Temporary-Recovery-Password-2!"
            )
        )
        self.assertEqual(rotated["auth_version"], repeated["auth_version"] + 1)

    def test_password_version_without_explicit_flag_does_not_reset(self):
        self.application.config.update(
            BOOTSTRAP_ADMIN_PASSWORD="Must-Not-Replace-Existing!",
            RESET_BOOTSTRAP_ADMIN_PASSWORD=False,
            BOOTSTRAP_ADMIN_PASSWORD_RESET_VERSION="secret-version-unarmed",
        )
        portal.ensure_portal_bootstrap(self.application, self.database)
        existing = self.admin_row()
        self.assertTrue(
            check_password_hash(existing["password_hash"], "Initial-Password-2026!")
        )
        self.assertFalse(existing["must_change_password"])
        with portal.connect(self.database) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'portal_admin_recovery_events'"
            ).fetchone()
        self.assertIsNone(table)


if __name__ == "__main__":
    unittest.main()
