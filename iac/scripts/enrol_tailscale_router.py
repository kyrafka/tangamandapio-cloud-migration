#!/usr/bin/env python3
"""Enroll a fresh project router using a short-lived root-only key file.

This command does not issue keys, publish tailnet policy, approve routes, set
up forwarding, or overwrite an existing node identity. Run on the target VM;
the secret file must already exist in volatile /run and must be supplied by a
separately authorized secret-delivery mechanism.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

NAMES = {
    'aws': {'tangamandapio-aws-primary', 'tangamandapio-aws-backup'},
    'azure': {'tangamandapio-azure-primary', 'tangamandapio-azure-backup'},
}


def build_command(cloud, key_file, hostname):
    if cloud not in NAMES or hostname not in NAMES[cloud]:
        raise ValueError('router name/cloud not authorized')
    if not re.fullmatch(r'/run/[a-zA-Z0-9_./-]+', key_file) or '..' in Path(key_file).parts:
        raise ValueError('key file must be inside /run')
    command = ['tailscale', 'up', '--auth-key=file:' + key_file,
               '--hostname=' + hostname, '--advertise-tags=tag:tangama-' + cloud + '-router',
               '--accept-dns=false', '--accept-routes=' + ('true' if cloud == 'aws' else 'false')]
    if cloud == 'azure':
        command.append('--advertise-routes=10.20.1.0/24')
    return command


def may_enrol(status):
    return isinstance(status, dict) and status.get('BackendState') == 'NeedsLogin'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud', required=True, choices=tuple(NAMES))
    parser.add_argument('--hostname', required=True)
    parser.add_argument('--auth-key-file', required=True)
    args = parser.parse_args()
    try:
        command = build_command(args.cloud, args.auth_key_file, args.hostname)
        if os.geteuid() != 0:
            raise ValueError('run as root on the project router')
        key = Path(args.auth_key_file)
        info = key.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError('key must be a root-owned regular file inaccessible to other users')
        # Reject symbolic links in every parent component as well as in the file.
        if key.resolve(strict=True) != key:
            raise ValueError('key path must not contain symbolic links')
        before = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=20)
        if not may_enrol(json.loads(before.stdout)):
            raise ValueError('router is not in NeedsLogin; existing identity preserved')
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
        if completed.returncode:
            raise ValueError('tailscale enrollment failed; inspect local service privately')
        after = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=20, check=True)
        status = json.loads(after.stdout)
        expected_tag = 'tag:tangama-' + args.cloud + '-router'
        if status.get('BackendState') != 'Running' or expected_tag not in status.get('Self', {}).get('Tags', []):
            raise ValueError('registration was not verified with the expected project tag')
        print('Router enrolled with project tag. Confirm route approval and connectivity separately.')
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        # Never emit subprocess output: it may contain credentials or login URLs.
        print('Enrollment stopped: ' + (str(exc) if isinstance(exc, ValueError) else 'local check failed'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
