import json
import unittest
from pathlib import Path

POLICY = Path(__file__).resolve().parents[2] / 'iac' / 'environments' / 'azure-rebuild' / 'postgres-backup-lifecycle.json'


class PostgresBackupLifecycleTests(unittest.TestCase):
    def test_terraform_protects_backup_storage_and_vault_from_destruction(self):
        source = (POLICY.parents[2] / 'modules' / 'azure_operations' / 'main.tf').read_text(encoding='utf-8')
        for resource in ('azurerm_storage_account" "this', 'azurerm_key_vault" "operations'):
            block = source.split('resource "' + resource + '" {', 1)[1].split('\nresource ', 1)[0]
            self.assertRegex(block, r'prevent_destroy\s*=\s*true', msg=resource)

    def test_terraform_recreates_private_backup_container_and_policy(self):
        source = (POLICY.parents[2] / 'modules' / 'azure_operations' / 'main.tf').read_text(encoding='utf-8')
        self.assertIn('resource "azurerm_storage_container" "postgres_backups"', source)
        self.assertIn('resource "azurerm_storage_management_policy" "postgres_backups"', source)
        self.assertIn('tangama-postgres-backups/postgres/', source)
        self.assertIn('delete_after_days_since_modification_greater_than = 30', source)

    def test_retention_is_scoped_only_to_encrypted_backup_objects(self):
        self.assertTrue(POLICY.exists(), 'The Azure PostgreSQL backup lifecycle policy must exist')
        policy = json.loads(POLICY.read_text(encoding='utf-8'))
        self.assertEqual(len(policy['rules']), 1)
        rule = policy['rules'][0]
        self.assertTrue(rule['enabled'])
        self.assertEqual(rule['definition']['filters']['blobTypes'], ['blockBlob'])
        self.assertEqual(rule['definition']['filters']['prefixMatch'], ['tangama-postgres-backups/postgres/'])
        self.assertEqual(rule['definition']['actions']['baseBlob']['delete']['daysAfterModificationGreaterThan'], 30)


if __name__ == '__main__':
    unittest.main()
