"""The periodic export can only create the daily backup in its container."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "iac/scripts"))
from postgres_blob_export import authorized_blob_url, source_environment


class ScheduledBackupUrlTests(unittest.TestCase):
    def test_export_uses_reader_secret_when_runtime_is_restricted(self):
        environment = (b"DB_HOST=project.us-east-2.rds.amazonaws.com\0DATABASE_NAME=tangamandapio\0"
                       b"DB_SECRET_ARN=app-secret\0DATABASE_SCHEMA_MODE=verify\0DB_BACKUP_SECRET_ARN=reader-secret\0")
        with patch("postgres_blob_export.quiet_command", return_value=b"42"), \
             patch("postgres_blob_export.Path.read_bytes", return_value=environment), \
             patch("postgres_blob_export.aws_text", return_value='{"username":"tangama_backup_reader","password":"test-only"}') as read:
            result = source_environment("us-east-2", Path("ca.pem"))
            self.assertEqual(result["PGUSER"], "tangama_backup_reader")
            self.assertIn("reader-secret", read.call_args.args[1])

    def test_export_refuses_to_fall_back_to_runtime_role(self):
        environment = (b"DB_HOST=project.us-east-2.rds.amazonaws.com\0DATABASE_NAME=tangamandapio\0"
                       b"DB_SECRET_ARN=app-secret\0DATABASE_SCHEMA_MODE=verify\0")
        with patch("postgres_blob_export.quiet_command", return_value=b"42"), \
             patch("postgres_blob_export.Path.read_bytes", return_value=environment), \
             patch("postgres_blob_export.aws_text") as read:
            with self.assertRaisesRegex(RuntimeError, "dedicated backup"):
                source_environment("us-east-2", Path("ca.pem"))
            read.assert_not_called()

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
