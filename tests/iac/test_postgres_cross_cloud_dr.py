import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'iac' / 'scripts' / 'postgres_dr_pilot.py'


class PostgresDrPilotTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HELPER.exists(), 'PostgreSQL DR helper is missing')
        spec = importlib.util.spec_from_file_location('postgres_dr_pilot', HELPER)
        self.dr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.dr)
        if os.name != 'posix':
            permissions = patch.object(self.dr, 'private_regular_file')
            permissions.start()
            self.addCleanup(permissions.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.archive = self.directory / 'backup.dump'
        self.manifest = self.directory / 'backup.json'

    def write_archive(self):
        self.archive.write_bytes(b'synthetic PostgreSQL archive')
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps({'sha256': digest, 'source_major': 18,
                                             'source_server': '10.1.1.1:5432', 'source_system_id': '111',
                                             'dump_major': 18}), encoding='utf-8')
        return digest, hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def restore_verified(self, digest, manifest_digest):
        self.assertIn('expected_manifest_sha256', inspect.signature(self.dr.restore_isolated).parameters,
                      'independently supplied manifest hash guard is missing')
        return self.dr.restore_isolated('target', self.archive, self.manifest, digest, manifest_digest)

    def test_rejects_older_clients_and_target(self):
        with self.assertRaises(self.dr.DRFailure):
            self.dr.check_versions(source_major=18, dump_major=17)
        with self.assertRaises(self.dr.DRFailure):
            self.dr.check_versions(source_major=18, dump_major=18, restore_major=17, target_major=18)
        with self.assertRaises(self.dr.DRFailure):
            self.dr.check_versions(source_major=18, dump_major=18, restore_major=18, target_major=17)

    def test_never_inherits_password_or_host_overrides(self):
        with patch.dict(os.environ, {'PGPASSWORD': 'do-not-leak', 'PGHOST': 'wrong-host',
                                     'PGSERVICEFILE': '/safe/services', 'PGPASSFILE': '/safe/pass'}, clear=True):
            env = self.dr.connection_environment('source')
        self.assertNotIn('PGPASSWORD', env)
        self.assertNotIn('PGHOST', env)
        self.assertEqual(env['PGSERVICE'], 'source')
        self.assertEqual(env['PGSSLMODE'], 'verify-full')
        self.assertEqual(env['PGPASSFILE'], '/safe/pass')

    def test_private_directory_rejects_permissive_mode(self):
        entry = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=1000)
        with patch.object(self.dr.os, 'name', 'posix'), \
             patch.object(self.dr.os, 'geteuid', return_value=1000, create=True), \
             patch.object(Path, 'lstat', return_value=entry), \
             self.assertRaises(self.dr.DRFailure):
            self.dr.require_private_directory(self.directory)

    def test_private_directory_accepts_owner_only_mode(self):
        entry = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=1000)
        with patch.object(self.dr.os, 'name', 'posix'), \
             patch.object(self.dr.os, 'geteuid', return_value=1000, create=True), \
             patch.object(Path, 'lstat', return_value=entry):
            self.dr.require_private_directory(self.directory)

    def test_dump_records_archive_hash_and_source_version(self):
        def run(args, service=None):
            if args[0] == 'pg_dump':
                Path(args[args.index('--file') + 1]).write_bytes(b'synthetic PostgreSQL archive')
            return ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run):
            result = self.dr.create_dump('source', self.archive, self.manifest)
        self.assertEqual(result['sha256'], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(json.loads(self.manifest.read_text(encoding='utf-8'))['source_major'], 18)

    def test_dump_failure_removes_its_partial_plaintext_archive(self):
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=self.dr.DRFailure('dump failed')), \
             self.assertRaises(self.dr.DRFailure):
            self.dr.create_dump('source', self.archive, self.manifest)
        self.assertFalse(self.archive.exists())
        self.assertFalse(self.manifest.exists())

    def test_dump_rejects_source_cluster_change_and_cleans_archive(self):
        def run(args, service=None):
            if args[0] == 'pg_dump':
                Path(args[args.index('--file') + 1]).write_bytes(b'synthetic PostgreSQL archive')
            return ''
        identities = [{'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'},
                      {'major': 18, 'server': '10.1.1.2:5432', 'system_id': '222'}]
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', side_effect=identities), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run), \
             self.assertRaises(self.dr.DRFailure):
            self.dr.create_dump('source', self.archive, self.manifest)
        self.assertFalse(self.archive.exists())
        self.assertFalse(self.manifest.exists())

    def test_dump_cleanup_failure_is_explicit(self):
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=self.dr.DRFailure('dump failed')), \
             patch.object(Path, 'unlink', side_effect=PermissionError), \
             self.assertRaisesRegex(self.dr.DRFailure, 'cleanup failed'):
            self.dr.create_dump('source', self.archive, self.manifest)

    def test_restore_cleanup_failure_does_not_report_success(self):
        digest, manifest_digest = self.write_archive()
        def run(args, service=None):
            if args[0] == 'dropdb':
                raise self.dr.DRFailure('drop failed')
            return '4\n' if args[0] == 'psql' else ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run), \
             self.assertRaisesRegex(self.dr.DRFailure, 'Cleanup failed; delete temporary database tangama_dr_'):
            self.restore_verified(digest, manifest_digest)
        journal = self.manifest.with_name(self.manifest.name + '.restore-journal.json')
        self.assertTrue(journal.exists(), 'cleanup journal must remain after cleanup failure')
        self.assertRegex(json.loads(journal.read_text())['database'], r'^tangama_dr_[0-9a-f]{24}$')

    def test_restore_creates_private_cleanup_journal_before_creating_database(self):
        digest, manifest_digest = self.write_archive()
        journal = self.manifest.with_name(self.manifest.name + '.restore-journal.json')
        def run(args, service=None):
            if args[0] == 'createdb':
                self.assertTrue(journal.exists(), 'journal must exist before createdb')
                self.assertEqual(json.loads(journal.read_text())['database'], args[-1])
            return '4\n' if args[0] == 'psql' else ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run):
            self.restore_verified(digest, manifest_digest)
        self.assertFalse(journal.exists(), 'journal must be removed after successful cleanup')

    def test_ambiguous_database_creation_keeps_cleanup_journal(self):
        digest, manifest_digest = self.write_archive()
        def run(args, service=None):
            if args[0] == 'createdb':
                raise self.dr.DRFailure('ambiguous create')
            return ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run), \
             self.assertRaisesRegex(self.dr.DRFailure, 'creation was ambiguous'):
            self.restore_verified(digest, manifest_digest)
        journal = self.manifest.with_name(self.manifest.name + '.restore-journal.json')
        self.assertTrue(journal.exists())

    def test_all_database_commands_disable_interactive_password_prompts(self):
        digest, manifest_digest = self.write_archive()
        calls = []
        def run(args, service=None):
            calls.append(args)
            return '4\n' if args[0] == 'psql' else ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run):
            self.restore_verified(digest, manifest_digest)
        for args in calls:
            self.assertIn('--no-password', args, f'{args[0]} may prompt for a password')

    def test_restore_treats_archive_name_as_operand_not_option(self):
        digest, manifest_digest = self.write_archive()
        calls = []
        def run(args, service=None):
            calls.append(args)
            return '4\n' if args[0] == 'psql' else ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run):
            self.restore_verified(digest, manifest_digest)
        args = next(args for args in calls if args[0] == 'pg_restore')
        self.assertEqual(args[-2], '--')
        self.assertEqual(args[-1], str(self.archive))

    def test_command_failure_never_exposes_subprocess_output(self):
        result = subprocess.CompletedProcess(['pg_dump'], 1, stdout='secret value', stderr='secret value')
        with patch.object(self.dr.subprocess, 'run', return_value=result), \
             self.assertRaises(self.dr.DRFailure) as caught:
            self.dr.run_checked(['pg_dump', '--version'])
        self.assertNotIn('secret value', str(caught.exception))

    def test_existing_archive_is_never_overwritten(self):
        self.archive.write_bytes(b'existing data')
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked') as run, \
             self.assertRaises(self.dr.DRFailure):
            self.dr.create_dump('source', self.archive, self.manifest)
        run.assert_not_called()
        self.assertEqual(self.archive.read_bytes(), b'existing data')

    def test_bad_hash_stops_before_contacting_target(self):
        _, manifest_digest = self.write_archive()
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server') as server, \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified('0' * 64, manifest_digest)
        server.assert_not_called()

    def test_tampered_manifest_stops_before_contacting_target(self):
        digest, manifest_digest = self.write_archive()
        self.manifest.write_text(self.manifest.read_text().replace('111', '222'))
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server') as server, \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified(digest, manifest_digest)
        server.assert_not_called()

    def test_oversized_manifest_is_rejected_before_hashing(self):
        digest, manifest_digest = self.write_archive()
        self.manifest.write_bytes(b'x' * 4097)
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'sha256_file', return_value='0' * 64) as hash_file, \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified(digest, manifest_digest)
        hash_file.assert_not_called()

    def test_rejects_source_and_target_on_same_server_before_create(self):
        digest, manifest_digest = self.write_archive()
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.1.1.1:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'run_checked') as run, \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified(digest, manifest_digest)
        run.assert_not_called()

    def test_rejects_same_cluster_even_with_a_different_ip(self):
        digest, manifest_digest = self.write_archive()
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '111'}), \
             patch.object(self.dr, 'run_checked') as run, \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified(digest, manifest_digest)
        run.assert_not_called()

    def test_drops_temporary_database_when_restore_fails(self):
        digest, manifest_digest = self.write_archive()
        calls = []
        def run(args, service=None):
            calls.append(args)
            if args[0] == 'pg_restore':
                raise self.dr.DRFailure('restore failed')
            return ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run), \
             self.assertRaises(self.dr.DRFailure):
            self.restore_verified(digest, manifest_digest)
        created = next(args[-1] for args in calls if args[0] == 'createdb')
        dropped = next(args[-1] for args in calls if args[0] == 'dropdb')
        self.assertRegex(created, r'^tangama_dr_[0-9a-f]{24}$')
        self.assertEqual(created, dropped)

    def test_restore_success_requires_nonzero_table_count_and_cleanup(self):
        digest, manifest_digest = self.write_archive()
        calls = []
        def run(args, service=None):
            calls.append(args)
            return '4\n' if args[0] == 'psql' else ''
        with patch.object(self.dr, 'require_private_directory'), \
             patch.object(self.dr, 'inspect_server', return_value={'major': 18, 'server': '10.2.2.2:5432', 'system_id': '222'}), \
             patch.object(self.dr, 'client_major', return_value=18), \
             patch.object(self.dr, 'run_checked', side_effect=run):
            result = self.restore_verified(digest, manifest_digest)
        self.assertEqual(result['public_tables'], 4)
        self.assertTrue(result['cleanup_completed'])
        self.assertEqual([x[0] for x in calls], ['createdb', 'pg_restore', 'psql', 'dropdb'])


if __name__ == '__main__':
    unittest.main()
