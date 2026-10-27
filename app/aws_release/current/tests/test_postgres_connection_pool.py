import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from flask import session

import app as portal


class FakeRawConnection:
    def __init__(self):
        self.closed = 0
        self.rollback_calls = 0

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.closed = 1


class FakeThreadedConnectionPool:
    instances = []

    def __init__(self, min_connections, max_connections, dsn, **kwargs):
        self.max_connections = max_connections
        self.connections = []
        self.available = []
        self.returned = []
        type(self).instances.append(self)

    def getconn(self):
        if self.available:
            return self.available.pop()
        if len(self.connections) < self.max_connections:
            connection = FakeRawConnection()
            self.connections.append(connection)
            return connection
        raise RuntimeError("fake pool capacity exceeded")

    def putconn(self, connection, close=False):
        self.returned.append((connection, close))
        if close:
            connection.close()
        else:
            self.available.append(connection)

    def closeall(self):
        for connection in self.connections:
            connection.close()


class PostgreSQLConnectionPoolTests(unittest.TestCase):
    database_url = "postgresql://portal:secret@example.test/portal"

    def setUp(self):
        FakeThreadedConnectionPool.instances.clear()
        self.psycopg2 = types.ModuleType("psycopg2")
        self.psycopg2.OperationalError = type("OperationalError", (Exception,), {})
        self.psycopg2.connect_calls = []
        self.psycopg2.connect = self._direct_connect
        pool_module = types.ModuleType("psycopg2.pool")
        pool_module.ThreadedConnectionPool = FakeThreadedConnectionPool
        self.psycopg2.pool = pool_module
        self.modules = patch.dict(
            sys.modules,
            {"psycopg2": self.psycopg2, "psycopg2.pool": pool_module},
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.registry = getattr(portal, "_POSTGRES_POOLS", None)
        if self.registry is not None:
            for entry in self.registry.values():
                entry.pool.closeall()
            self.registry.clear()
        self.addCleanup(self._clear_registry)

    def _direct_connect(self, *args, **kwargs):
        self.psycopg2.connect_calls.append((args, kwargs))
        return FakeRawConnection()

    def _clear_registry(self):
        if self.registry is not None:
            for entry in self.registry.values():
                entry.pool.closeall()
            self.registry.clear()

    def test_database_scopes_reuse_a_connection_and_return_it_clean(self):
        with patch.dict(os.environ, {"DB_POOL_MAX_CONNECTIONS": "2"}):
            with portal.connect(self.database_url):
                pass
            with portal.connect(self.database_url):
                pass

        self.assertEqual(len(FakeThreadedConnectionPool.instances), 1)
        pool = FakeThreadedConnectionPool.instances[0]
        self.assertEqual(pool.max_connections, 2)
        self.assertEqual(len(pool.connections), 1)
        self.assertEqual(len(pool.returned), 2)
        self.assertEqual(pool.connections[0].rollback_calls, 2)
        self.assertEqual(pool.connections[0].closed, 0)
        self.assertEqual(self.psycopg2.connect_calls, [])

    def test_pool_wait_is_bounded_and_does_not_exceed_its_connection_limit(self):
        with patch.dict(
            os.environ,
            {
                "DB_POOL_MAX_CONNECTIONS": "2",
                "DB_POOL_ACQUIRE_TIMEOUT_SECONDS": "0.02",
            },
        ):
            first_context = portal.connect(self.database_url)
            first_context.__enter__()
            second_context = portal.connect(self.database_url)
            second_context.__enter__()
            try:
                with self.assertRaises(TimeoutError):
                    portal.connect(self.database_url)
            finally:
                first_context.__exit__(None, None, None)
                second_context.__exit__(None, None, None)

        pool = FakeThreadedConnectionPool.instances[0]
        self.assertEqual(len(pool.connections), 2)
        self.assertEqual(len(self.psycopg2.connect_calls), 0)

    def test_authenticated_user_is_looked_up_once_per_request(self):
        database_target = "sqlite:///not-opened-by-this-test.db"
        user_row = {
            "id": 42,
            "username": "operator@example.test",
            "role": "operations",
            "company_id": 1,
            "active": True,
            "must_change_password": False,
            "auth_version": 7,
            "company": "Test company",
        }
        with portal.app.test_request_context("/api/orders"):
            session["portal_user_id"] = 42
            session["portal_user_version"] = 7
            with patch.object(
                portal,
                "portal_user_row",
                side_effect=[dict(user_row), dict(user_row)],
            ) as user_lookup:
                first = portal.current_portal_user(database_target)
                second = portal.current_portal_user(database_target)

        self.assertEqual(user_lookup.call_count, 1)
        self.assertEqual(first["role"], "operations")
        self.assertEqual(second["role"], "operations")
        self.assertNotIn("auth_version", first)
        self.assertNotIn("auth_version", second)

    def test_pool_saturation_returns_a_retryable_service_unavailable(self):
        with tempfile.TemporaryDirectory(prefix="portal-pool-timeout-") as directory:
            application = portal.create_app(
                {
                    "TESTING": False,
                    "DATABASE_URL": "",
                    "DATABASE_PATH": os.path.join(directory, "portal.sqlite"),
                    "BOOTSTRAP_ADMIN_USERNAME": "admin@pool-test.example",
                    "BOOTSTRAP_ADMIN_PASSWORD": "Pool-Test-Admin-2026!",
                    "FORCE_BOOTSTRAP_PASSWORD_CHANGE": False,
                    "FORCE_INITIAL_PASSWORD_CHANGE": False,
                    "CSRF_ENABLED": False,
                }
            )
            client = application.test_client()
            login = client.post(
                "/api/auth/login",
                json={
                    "username": "admin@pool-test.example",
                    "password": "Pool-Test-Admin-2026!",
                },
            )
            self.assertEqual(login.status_code, 200)

            with patch.object(
                portal,
                "connect",
                side_effect=portal.DatabasePoolAcquireTimeout("private pool detail"),
            ):
                response = client.get("/api/orders")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json(), {"error": "database_busy"})
        self.assertEqual(response.headers["Retry-After"], "1")
        self.assertNotIn("private pool detail", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
