import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOAD_TEST = PROJECT_ROOT / "tests" / "performance" / "transactional_load_test.py"


class TransactionalLoadIsolationTests(unittest.TestCase):
    def test_import_does_not_write_to_parent_database_path(self):
        with tempfile.TemporaryDirectory(prefix="tangama-load-isolation-test-") as temp_dir:
            unexpected_database = Path(temp_dir) / "parent-database.sqlite"
            environment = os.environ.copy()
            environment.update(
                {
                    "DATABASE_URL": "",
                    "DATABASE_PATH": str(unexpected_database),
                    "LOG_LEVEL": "ERROR",
                }
            )
            import_code = (
                "import importlib.util; "
                f"spec=importlib.util.spec_from_file_location('load_test', r'{LOAD_TEST}'); "
                "module=importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(module); module.load_portal_module()"
            )
            result = subprocess.run(
                [sys.executable, "-c", import_code],
                cwd=PROJECT_ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(unexpected_database.exists())


if __name__ == "__main__":
    unittest.main()
