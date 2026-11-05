import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "iac" / "scripts" / "estimate_cloud_costs.ps1"
POWERSHELL = os.environ.get("POWERSHELL", "powershell.exe")


class CostEstimateCultureTests(unittest.TestCase):
    def test_currency_uses_invariant_decimal_separator(self):
        command = (
            "[System.Threading.Thread]::CurrentThread.CurrentCulture = "
            "[Globalization.CultureInfo]::GetCultureInfo('es-ES'); "
            f"& '{SCRIPT}'"
        )
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(
            result.stdout,
            r"Modeled AWS subtotal \(not all-in\)\s+\$\s*91\.92",
        )


if __name__ == "__main__":
    unittest.main()
