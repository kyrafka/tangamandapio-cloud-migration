"""The periodic export can only create the daily backup in its container."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iac/scripts"))
from postgres_blob_export import authorized_blob_url


class ScheduledBackupUrlTests(unittest.TestCase):
    def test_append_daily_object_to_create_only_container_authorization(self):
        host = "storage.blob.core.windows.net"
        token_url = f"https://{host}/backups?sp=c&sr=c&spr=https&sig=signature"
        self.assertEqual(
            authorized_blob_url(token_url, host, "backups", "postgres/20261119-daily.json", True),
            f"https://{host}/backups/postgres/20261119-daily.json?sp=c&sr=c&spr=https&sig=signature",
        )
        with self.assertRaises(ValueError):
            authorized_blob_url(token_url.replace("sp=c", "sp=cw"), host, "backups", "postgres/20261119-daily.json", True)
        with self.assertRaises(ValueError):
            authorized_blob_url(token_url, host, "backups", "../other.json", True)
