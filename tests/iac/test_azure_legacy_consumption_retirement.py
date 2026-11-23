import re
import unittest
from pathlib import Path


IAC = Path(__file__).resolve().parents[2] / "iac"
MODULE = IAC / "modules" / "azure_operations"
LEGACY = (
    "azurerm_service_plan.function",
    "azurerm_linux_function_app.wms",
    "azurerm_role_assignment.function_package_reader",
    "azurerm_role_assignment.function_blob",
    "azurerm_role_assignment.function_queue",
    "azurerm_role_assignment.function_poison_queue_reader",
    "azurerm_monitor_metric_alert.function_http_5xx",
    "azurerm_monitor_metric_alert.function_latency",
)


class LegacyConsumptionRetirementTests(unittest.TestCase):
    def test_production_root_excludes_legacy_compute_and_monitors(self):
        source = (IAC / "environments" / "azure-rebuild" / "main.tf").read_text()
        self.assertRegex(source, r"deploy_legacy_consumption\s*=\s*false")

    def test_legacy_resources_are_optional_and_existing_demo_addresses_move(self):
        source = (MODULE / "main.tf").read_text()
        moved = (MODULE / "moved.tf").read_text() if (MODULE / "moved.tf").exists() else ""
        for address in LEGACY:
            with self.subTest(address=address):
                resource_type, name = address.split(".")
                block = source.split(f'resource "{resource_type}" "{name}" {{', 1)[1]
                self.assertRegex(block.split("\nresource ", 1)[0], r"count\s*=\s*var\.deploy_legacy_consumption\s*\?\s*1\s*:\s*0")
                escaped = re.escape(address)
                self.assertRegex(moved, rf"from\s*=\s*{escaped}\s+to\s*=\s*{escaped}\[0\]")

    def test_shared_storage_and_monitoring_remain_available(self):
        source = (MODULE / "main.tf").read_text()
        for resource_type, name in (
            ("azurerm_storage_account", "this"),
            ("azurerm_key_vault", "operations"),
            ("azurerm_storage_queue", "fulfillment"),
            ("azurerm_storage_container", "postgres_backups"),
            ("azurerm_application_insights", "wms"),
            ("azurerm_monitor_action_group", "operations"),
        ):
            with self.subTest(resource=name):
                block = source.split(f'resource "{resource_type}" "{name}" {{', 1)[1]
                self.assertNotIn("deploy_legacy_consumption", block.split("\nresource ", 1)[0])


if __name__ == "__main__":
    unittest.main()
