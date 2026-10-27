import importlib.util
import json
import os
import sys
import tempfile
import unittest
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


APP_PATH = Path(__file__).resolve().parents[1] / "current" / "app.py"
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="portal-rds-secret-tests-")
_environment = {
    "DATABASE_URL": "",
    "DATABASE_PATH": str(Path(_bootstrap_dir.name) / "bootstrap.sqlite3"),
    "DATABASE_NAME": "tangamandapio",
    "DB_SECRET_ARN": "",
    "APP_SESSION_SECRET": "test-only-rds-secret-session-key",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "VOICE_RECORDINGS_ENABLED": "false",
}
with patch.dict(os.environ, _environment):
    if str(APP_PATH.parent) not in sys.path:
        sys.path.insert(0, str(APP_PATH.parent))
    spec = importlib.util.spec_from_file_location("portal_rds_secret_test", APP_PATH)
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)


class FakeSecretsManager:
    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    def get_secret_value(self, *, SecretId):
        self.calls.append(SecretId)
        return {"SecretString": json.dumps(self.values.pop(0))}


class FakePostgreSQLPool:
    def __init__(self, postgres_client, _min_connections, _max_connections, *args, **kwargs):
        self.postgres_client = postgres_client
        self.connect_args = args
        self.connect_kwargs = kwargs
        self.available = []
        self.connections = []

    def getconn(self):
        if self.available:
            return self.available.pop()
        connection = self.postgres_client.connect(
            *self.connect_args, **self.connect_kwargs
        )
        self.connections.append(connection)
        return connection

    def putconn(self, connection, close=False):
        if close:
            connection.close()
        else:
            self.available.append(connection)

    def closeall(self):
        for connection in self.connections:
            connection.close()


class RdsSecretAuthenticationTests(unittest.TestCase):
    def setUp(self):
        portal._RDS_SECRET_CACHE.clear()
        for entry in portal._POSTGRES_POOLS.values():
            entry.pool.closeall()
        portal._POSTGRES_POOLS.clear()
        self.secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-AbCd"
        self.target = portal.configured_database_target({
            "DATABASE_URL": "",
            "DATABASE_PATH": ":memory:",
            "DATABASE_NAME": "tangamandapio",
            "DB_SECRET_ARN": self.secret_arn,
        })

    def tearDown(self):
        portal._RDS_SECRET_CACHE.clear()
        for entry in portal._POSTGRES_POOLS.values():
            entry.pool.closeall()
        portal._POSTGRES_POOLS.clear()

    @staticmethod
    def secret(password):
        return {
            "username": "portal_user",
            "password": password,
            "host": "database.internal.example",
            "port": 5432,
        }

    def install_clients(self, secrets_client, postgres_client):
        boto3 = SimpleNamespace(client=Mock(return_value=secrets_client))
        psycopg2 = types.ModuleType("psycopg2")
        psycopg2.__path__ = []
        psycopg2.connect = postgres_client.connect
        psycopg2.OperationalError = postgres_client.OperationalError
        pool = types.ModuleType("psycopg2.pool")
        pool.ThreadedConnectionPool = lambda *args, **kwargs: FakePostgreSQLPool(
            postgres_client, *args, **kwargs
        )
        with patch.dict(
            sys.modules,
            {"boto3": boto3, "psycopg2": psycopg2, "psycopg2.pool": pool},
        ):
            return portal.connect(self.target)

    def test_secret_reference_selects_postgres_without_embedding_password(self):
        self.assertTrue(self.target.startswith("rds-secret://"))
        self.assertTrue(portal.is_postgresql(self.target))
        self.assertNotIn("password", self.target.lower())
        self.assertNotIn("portal_user", self.target)

    def test_reads_runtime_secret_and_reuses_short_cache(self):
        secrets_client = FakeSecretsManager([self.secret("first-secret-value")])
        raw_connection = SimpleNamespace(close=Mock(), rollback=Mock(), closed=0)
        postgres = SimpleNamespace(connect=Mock(return_value=raw_connection), OperationalError=RuntimeError)

        with self.install_clients(secrets_client, postgres) as connection:
            self.assertIsInstance(connection, portal.PostgreSQLConnection)
            self.assertEqual(secrets_client.calls, [self.secret_arn])
            self.assertEqual(postgres.connect.call_args.kwargs["dbname"], "tangamandapio")
            self.assertEqual(postgres.connect.call_args.kwargs["password"], "first-secret-value")
            self.assertEqual(postgres.connect.call_args.kwargs["sslmode"], "require")
        raw_connection.rollback.assert_called_once()
        raw_connection.close.assert_not_called()

        with self.install_clients(secrets_client, postgres):
            pass
        self.assertEqual(secrets_client.calls, [self.secret_arn])
        self.assertEqual(postgres.connect.call_count, 1)
        self.assertEqual(raw_connection.rollback.call_count, 2)

    def test_authentication_failure_refreshes_secret_once(self):
        secrets_client = FakeSecretsManager([
            self.secret("rotated-out-value"),
            self.secret("current-value"),
        ])

        class PgOperationalError(Exception):
            def __init__(self, message, pgcode=None):
                super().__init__(message)
                self.pgcode = pgcode

        raw_connection = SimpleNamespace(close=Mock(), rollback=Mock(), closed=0)
        postgres = SimpleNamespace(
            OperationalError=PgOperationalError,
            connect=Mock(side_effect=[
                PgOperationalError("authentication rejected", pgcode="28P01"),
                raw_connection,
            ]),
        )

        with self.install_clients(secrets_client, postgres) as connection:
            self.assertIsInstance(connection, portal.PostgreSQLConnection)
        self.assertEqual(secrets_client.calls, [self.secret_arn, self.secret_arn])
        self.assertEqual(
            [call.kwargs["password"] for call in postgres.connect.call_args_list],
            ["rotated-out-value", "current-value"],
        )
        raw_connection.rollback.assert_called_once()
        raw_connection.close.assert_not_called()

    def test_restored_database_host_overrides_host_in_retained_secret(self):
        retained_secret = self.secret("current-value")
        retained_secret["host"] = "old-database.example"
        secrets_client = FakeSecretsManager([retained_secret])
        raw_connection = SimpleNamespace(close=Mock(), rollback=Mock(), closed=0)
        postgres = SimpleNamespace(connect=Mock(return_value=raw_connection), OperationalError=RuntimeError)

        with patch.dict(os.environ, {"DB_HOST": "restored-database.internal"}):
            with self.install_clients(secrets_client, postgres):
                pass
        self.assertEqual(postgres.connect.call_args.kwargs["host"], "restored-database.internal")

    def test_non_authentication_failure_does_not_repeat_secret_request(self):
        secrets_client = FakeSecretsManager([self.secret("current-value")])

        class PgOperationalError(Exception):
            pgcode = "08006"

        postgres = SimpleNamespace(
            OperationalError=PgOperationalError,
            connect=Mock(side_effect=PgOperationalError("connection unavailable")),
        )

        with self.assertRaises(PgOperationalError):
            self.install_clients(secrets_client, postgres)
        self.assertEqual(secrets_client.calls, [self.secret_arn])
        self.assertEqual(postgres.connect.call_count, 1)


if __name__ == "__main__":
    unittest.main()
