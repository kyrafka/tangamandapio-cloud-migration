#!/usr/bin/env python3
r"""Opt-in PostgreSQL dump and isolated restore pilot; no cloud operations.

Run on a POSIX host with a mode-0700 directory, PostgreSQL client tools and
two independently managed libpq services. Configure PGSERVICEFILE, PGPASSFILE
and PGSSLROOTCERT externally. Never put passwords in service names or CLI
arguments. Both connections force sslmode=verify-full.

  python3 postgres_dr_pilot.py dump --source-service source \
    --archive /secure/qa.dump --manifest /secure/qa.json
  python3 postgres_dr_pilot.py restore --target-service isolated \
    --archive /secure/qa.dump --manifest /secure/qa.json --expected-sha256 HASH \
    --expected-manifest-sha256 MANIFEST_HASH

The archive is plaintext and sensitive. Example, after arranging a trusted
age recipient and an Azure identity with Blob access (neither is created here):

  age -r "$DR_AGE_RECIPIENT" -o /secure/qa.dump.age /secure/qa.dump
  age -r "$DR_AGE_RECIPIENT" -o /secure/qa.json.age /secure/qa.json
  az storage blob upload --auth-mode login --account-name "$DR_ACCOUNT" \
    --container-name "$DR_CONTAINER" --name qa.dump.age --file /secure/qa.dump.age
  az storage blob upload --auth-mode login --account-name "$DR_ACCOUNT" \
    --container-name "$DR_CONTAINER" --name qa.json.age --file /secure/qa.json.age

Preserve both hashes independently from the Blob. On recovery, download and
decrypt into another private directory, then use restore with the trusted
original digests. Manage the remaining plaintext according to your retention
policy; file deletion does not guarantee media erasure.

Only restore a trusted dump: pg_restore executes SQL. The target must be a
dedicated isolated cluster with restricted permissions and network access.
Both PostgreSQL users must be allowed to query pg_control_system(); without a
reliable cluster identity the pilot stops. An abrupt process or host failure
may leave a temporary database or plaintext archive requiring manual cleanup.
Before database creation, a private `<manifest>.restore-journal.json` records
its target and generated name; keep and inspect it after ambiguous failures.
This helper does not encrypt, upload, schedule backups or prove Blob recovery.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys


class DRFailure(Exception):
    """A sanitized error safe to report without command output or credentials."""


def connection_environment(service: str | None) -> dict[str, str]:
    allowed = {'PATH', 'HOME', 'USER', 'LOGNAME', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP',
               'TMPDIR', 'LANG', 'LC_ALL', 'LC_CTYPE', 'PGSERVICEFILE', 'PGPASSFILE',
               'PGSSLROOTCERT', 'PGSSLCERT', 'PGSSLKEY'}
    environment = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    if service:
        validate_service(service)
        environment['PGSERVICE'] = service
        environment['PGSSLMODE'] = 'verify-full'
        environment['PGCONNECT_TIMEOUT'] = '10'
    return environment


def validate_service(service: str) -> None:
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', service):
        raise DRFailure('Invalid libpq service name.')


def connection_string(service: str, database: str | None = None) -> str:
    validate_service(service)
    if database and not re.fullmatch(r'tangama_dr_[0-9a-f]{24}', database):
        raise DRFailure('Invalid temporary database name.')
    return f'service={service}' + (f' dbname={database}' if database else '') + ' sslmode=verify-full'


def run_checked(args: list[str], service: str | None = None) -> str:
    try:
        completed = subprocess.run(args, env=connection_environment(service),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, timeout=600, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise DRFailure(f'{Path(args[0]).name} could not complete; details withheld.') from None
    if completed.returncode:
        raise DRFailure(f'{Path(args[0]).name} failed; details withheld.')
    return completed.stdout


def client_major(binary: str) -> int:
    version = run_checked([binary, '--version'])
    match = re.search(r'PostgreSQL\)?\s+(\d+)', version)
    if not match:
        raise DRFailure(f'Unable to determine {binary} version.')
    return int(match.group(1))


def check_versions(source_major: int, dump_major: int, restore_major: int | None = None,
                   target_major: int | None = None) -> None:
    if source_major < 10 or dump_major < source_major:
        raise DRFailure('pg_dump must be at least as new as the source PostgreSQL server.')
    if (restore_major is None) != (target_major is None):
        raise DRFailure('Both restore and target server versions are required.')
    if restore_major is not None and (restore_major != dump_major or target_major < dump_major):
        raise DRFailure('Use the same pg_restore major as pg_dump and a target at least that new.')


def inspect_server(service: str) -> dict:
    query = ("SELECT current_setting('server_version_num'), "
             "coalesce(inet_server_addr()::text,''), coalesce(inet_server_port()::text,''), "
             "coalesce((SELECT ssl::int FROM pg_stat_ssl WHERE pid=pg_backend_pid()),0), "
             "(SELECT system_identifier::text FROM pg_control_system())")
    output = run_checked(['psql', '--no-password', '-X', '-A', '-t', '-F', '|', '-v', 'ON_ERROR_STOP=1',
                          '--dbname', connection_string(service), '-c', query], service).strip()
    try:
        version, address, port, ssl, system_id = output.split('|')
        major, port_number = int(version) // 10000, int(port)
        ipaddress.ip_address(address)
        if ssl != '1' or not 1 <= port_number <= 65535 or major < 10 or not re.fullmatch(r'[0-9]{1,32}', system_id):
            raise ValueError
    except (ValueError, TypeError):
        raise DRFailure('Server identity, PostgreSQL version or TLS could not be verified.') from None
    return {'major': major, 'server': f'{address}:{port_number}', 'system_id': system_id}


def require_private_directory(directory: Path) -> None:
    if os.name != 'posix':
        raise DRFailure('This pilot requires a POSIX host with a private directory.')
    try:
        info = directory.lstat()
    except OSError:
        raise DRFailure('Archive directory is unavailable.') from None
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or
            info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise DRFailure('Archive directory must be owned by the current user and mode 0700 or stricter.')


def private_regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError:
        raise DRFailure('Archive or manifest is unavailable.') from None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
            info.st_mode & 0o077 or info.st_nlink != 1):
        raise DRFailure('Archive and manifest must be owner-only regular files without extra links.')


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def create_private_file(path: Path) -> None:
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        os.close(fd)
    except OSError:
        raise DRFailure('Archive and manifest must be new files in private directories.') from None


def create_dump(source_service: str, archive: Path, manifest: Path) -> dict:
    archive, manifest = Path(archive), Path(manifest)
    if archive.absolute() == manifest.absolute():
        raise DRFailure('Archive and manifest must be different files.')
    require_private_directory(archive.parent)
    require_private_directory(manifest.parent)
    source = inspect_server(source_service)
    dump_major = client_major('pg_dump')
    check_versions(source['major'], dump_major)
    created = []
    try:
        create_private_file(archive)
        created.append(archive)
        run_checked(['pg_dump', '--no-password', '--format=custom', '--no-owner', '--no-privileges',
                     '--dbname', connection_string(source_service), '--file', str(archive)], source_service)
        source_after = inspect_server(source_service)
        if source_after['system_id'] != source['system_id'] or source_after['major'] != source['major']:
            raise DRFailure('Source cluster identity or PostgreSQL version changed during the dump.')
        private_regular_file(archive)
        if not archive.stat().st_size:
            raise DRFailure('pg_dump created an empty archive.')
        digest = sha256_file(archive)
        metadata = {'sha256': digest, 'source_major': source['major'],
                    'source_server': source['server'], 'source_system_id': source['system_id'],
                    'dump_major': dump_major}
        create_private_file(manifest)
        created.append(manifest)
        manifest.write_text(json.dumps(metadata, sort_keys=True) + '\n', encoding='utf-8')
        return {**metadata, 'manifest_sha256': sha256_file(manifest)}
    except BaseException:
        cleanup_failed = False
        for path in reversed(created):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise DRFailure('Plaintext cleanup failed; remove the archive and manifest manually.') from None
        raise


def restore_isolated(target_service: str, archive: Path, manifest: Path,
                     expected_sha256: str, expected_manifest_sha256: str) -> dict:
    archive, manifest = Path(archive), Path(manifest)
    if not re.fullmatch(r'[a-f0-9]{64}', expected_sha256) or not re.fullmatch(r'[a-f0-9]{64}', expected_manifest_sha256):
        raise DRFailure('Trusted lowercase SHA-256 values for archive and manifest are required.')
    require_private_directory(archive.parent)
    require_private_directory(manifest.parent)
    private_regular_file(archive)
    private_regular_file(manifest)
    if manifest.stat().st_size > 4096:
        raise DRFailure('Invalid backup manifest.')
    if not hmac.compare_digest(sha256_file(manifest), expected_manifest_sha256):
        raise DRFailure('Manifest SHA-256 does not match the independently supplied digest.')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
        source_major = int(metadata['source_major'])
        dump_major = int(metadata['dump_major'])
        source_server = str(metadata['source_server'])
        source_system_id = str(metadata['source_system_id'])
        manifest_hash = str(metadata['sha256'])
        if not re.fullmatch(r'[0-9]{1,32}', source_system_id):
            raise ValueError
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError):
        raise DRFailure('Invalid backup manifest.') from None
    actual_hash = sha256_file(archive)
    if not hmac.compare_digest(actual_hash, expected_sha256) or not hmac.compare_digest(manifest_hash, expected_sha256):
        raise DRFailure('Archive SHA-256 does not match the independently supplied digest.')
    target = inspect_server(target_service)
    if target['server'] == source_server or target['system_id'] == source_system_id:
        raise DRFailure('Restore target must be a separate PostgreSQL cluster.')
    restore_major = client_major('pg_restore')
    check_versions(source_major, dump_major, restore_major, target['major'])
    if client_major('dropdb') < 13:
        raise DRFailure('dropdb 13 or newer is required for temporary-database cleanup.')
    database = 'tangama_dr_' + secrets.token_hex(12)
    maintenance = connection_string(target_service)
    journal = manifest.with_name(manifest.name + '.restore-journal.json')
    create_private_file(journal)
    try:
        with journal.open('w', encoding='utf-8') as output:
            json.dump({'database': database, 'target_service': target_service,
                       'target_server': target['server'], 'target_system_id': target['system_id']}, output)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
    except OSError:
        try:
            journal.unlink(missing_ok=True)
        except OSError:
            raise DRFailure('Journal preparation failed; remove the incomplete journal manually.') from None
        raise DRFailure('Journal preparation failed; no database creation was attempted.') from None
    try:
        run_checked(['createdb', '--no-password', '--maintenance-db', maintenance, database], target_service)
    except DRFailure:
        raise DRFailure(f'Temporary database creation was ambiguous; inspect {database} on the isolated target using the cleanup journal.') from None
    try:
        run_checked(['pg_restore', '--no-password', '--exit-on-error', '--single-transaction', '--no-owner',
                     '--no-privileges', '--dbname', connection_string(target_service, database),
                     '--', str(archive)], target_service)
        count = run_checked(['psql', '--no-password', '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                             '--dbname', connection_string(target_service, database), '-c',
                             "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"], target_service).strip()
        if not count.isdigit() or int(count) < 1:
            raise DRFailure('Restore produced no verifiable public tables.')
        result = {'archive_sha256': actual_hash, 'public_tables': int(count),
                  'target_server': target['server'], 'cleanup_completed': True,
                  'data_equivalence_verified': False}
    finally:
        try:
            run_checked(['dropdb', '--no-password', '--if-exists', '--force', '--maintenance-db', maintenance, database], target_service)
        except DRFailure:
            raise DRFailure(f'Cleanup failed; delete temporary database {database} on the isolated target.') from None
        try:
            journal.unlink()
        except OSError:
            raise DRFailure('Temporary database was removed, but the cleanup journal remains; remove it manually.') from None
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    dump = sub.add_parser('dump')
    dump.add_argument('--source-service', required=True)
    dump.add_argument('--archive', required=True, type=Path)
    dump.add_argument('--manifest', required=True, type=Path)
    restore = sub.add_parser('restore')
    restore.add_argument('--target-service', required=True)
    restore.add_argument('--archive', required=True, type=Path)
    restore.add_argument('--manifest', required=True, type=Path)
    restore.add_argument('--expected-sha256', required=True)
    restore.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        result = (create_dump(args.source_service, args.archive, args.manifest) if args.action == 'dump'
                  else restore_isolated(args.target_service, args.archive, args.manifest, args.expected_sha256,
                                        args.expected_manifest_sha256))
        print(json.dumps(result, sort_keys=True))
        return 0
    except DRFailure as error:
        print(f'DR pilot stopped: {error}', file=sys.stderr)
        return 2
    except Exception:
        print('DR pilot stopped: unexpected error; details withheld.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
